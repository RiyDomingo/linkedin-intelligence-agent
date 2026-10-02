#!/usr/bin/env python3
"""Capability-based research planning, sequential execution and normalized evidence."""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit
import sys

from evidence import public_url, normalize, deduplicate, is_fresh, load, save, assess, signals
from evidence import parse_time, timestamp, CLASSES
from discovery import classify_intent, prepare_request, linkedin_target, rank_candidates, report

OPERATIONS = {'retrieve_url': 'PAGE_FETCH', 'search_web': 'SEARCH', 'research_topic': 'SEARCH',
              'research_social': None, 'browse_interactively': 'INTERACTIVE_BROWSER',
              'crawl_site': 'CRAWL', 'extract_structured': 'STRUCTURED_EXTRACTION',
              'discover_linkedin': 'LINKEDIN_DISCOVERY', 'retrieve_linkedin': 'LINKEDIN_READ', 'imported_linkedin': 'LINKEDIN_IMPORTED_DATA',
              'approved_linkedin_api': 'LINKEDIN_APPROVED_API', 'linkedin_automation': 'LINKEDIN_DIRECT_AUTOMATION', 'local_only': None}
SOCIAL = {'reddit': 'SOCIAL_REDDIT', 'x': 'SOCIAL_X', 'youtube': 'SOCIAL_YOUTUBE', 'v2ex': 'SOCIAL_V2EX'}
FAILURES = {'TIMEOUT', 'BLOCKED', 'AUTH_REQUIRED', 'CAPABILITY_MISMATCH', 'NOT_FOUND',
            'PROVIDER_DISABLED', 'RATE_LIMIT', 'PARSE_FAILURE', 'NETWORK_ERROR'}
PURPOSES = {'FACT_VERIFICATION', 'COMMUNITY_DISCUSSION', 'COMPANY_RESEARCH',
            'CURRENT_EVENT', 'DEEP_INGESTION', 'INTERACTIVE_WORKFLOW', 'LOCAL_WRITING'}
FIELDS = {'operation', 'purpose', 'url', 'query', 'platform', 'public_input', 'auth_required',
          'interaction_required', 'javascript_required', 'max_age_hours', 'freshness_class',
          'allow_metered', 'managed_required', 'max_pages', 'selectors', 'steps', 'limit', 'query_budget', 'queries', 'enrichment_limit', 'cache_ttl_hours'}


@dataclass
class Provider:
    id: str
    capabilities: frozenset
    available: bool = False
    enabled: bool = True
    cost: str = 'UNKNOWN'
    complexity: int = 0
    latency: str = 'UNKNOWN'
    reliability: str = 'UNMEASURED'
    validated: frozenset = frozenset()
    retrieve: object = None
    last_failure: str = None
    discovery_transport: str = None


class RetrievalFailure(Exception):
    def __init__(self, reason):
        if reason not in FAILURES:
            raise ValueError('Unknown failure classification')
        self.reason = reason
        super().__init__(reason)


def request(value):
    if not isinstance(value, dict) or set(value) - FIELDS:
        raise ValueError('Unknown research request field; never supply whole profile/inbox/draft')
    operation = value.get('operation')
    purpose = value.get('purpose')
    if operation not in OPERATIONS or purpose not in PURPOSES:
        raise ValueError('Explicit supported operation and research purpose required')
    output = {**value}
    # LinkedIn intent is separated before generic search/provider selection.
    intent = classify_intent(output.get('query'))
    if operation in ('search_web', 'research_topic') and intent:
        operation = 'discover_linkedin' if intent == 'LINKEDIN_DISCOVERY' else 'imported_linkedin' if intent == 'LINKEDIN_IMPORTED_DATA' else 'linkedin_automation' if intent == 'LINKEDIN_DIRECT_AUTOMATION' else 'retrieve_linkedin'
        output['operation'] = operation
    if operation != 'discover_linkedin' and any(k in output for k in ('limit', 'query_budget', 'queries', 'enrichment_limit', 'cache_ttl_hours')):
        raise ValueError('Discovery bounds belong only to LinkedIn discovery')
    # Disclosure is explicit: no raw local context field is accepted or copied.
    if output.get('public_input') is not True:
        raise ValueError('Only explicitly minimized public research input is supported')
    for field in ('auth_required', 'interaction_required', 'javascript_required', 'allow_metered', 'managed_required'):
        if field in output and not isinstance(output[field], bool):
            raise ValueError('Request policy flags must be booleans')
        output.setdefault(field, False)
    if output['auth_required']:
        raise ValueError('Research does not escalate to authenticated access')
    if operation in ('retrieve_url', 'crawl_site', 'extract_structured', 'browse_interactively'):
        output['url'] = public_url(output.get('url'))
    if operation in ('search_web', 'research_topic', 'research_social'):
        query = output.get('query')
        if not isinstance(query, str) or not query.strip() or len(query) > 300:
            raise ValueError('Use a minimized public query, at most 300 characters')
    if operation == 'research_social' and output.get('platform') not in SOCIAL:
        raise ValueError('Explicit supported specialist platform required')
    output.setdefault('freshness_class', 'CURRENT')
    if output['freshness_class'] not in CLASSES:
        raise ValueError('Unknown freshness class')
    # Task-specific budget is required for every external request; no magic universal TTL.
    age = output.get('max_age_hours')
    if operation not in ('local_only', 'retrieve_linkedin', 'imported_linkedin', 'approved_linkedin_api', 'linkedin_automation') and (type(age) not in (int, float) or not 0 <= age <= 8760):
        raise ValueError('Supply a finite task-specific max_age_hours (0 means fresh retrieval)')
    if 'max_pages' in output and (type(output['max_pages']) is not int or not 1 <= output['max_pages'] <= 5):
        raise ValueError('Crawl bound must be 1..5 pages')
    if operation == 'crawl_site' and 'max_pages' not in output:
        raise ValueError('Deep ingestion needs an explicit small page bound')
    selectors = output.get('selectors', {})
    if not isinstance(selectors, dict) or len(selectors) > 10 or any(not isinstance(k, str) or not isinstance(v, str) for k, v in selectors.items()):
        raise ValueError('Structured extraction uses up to ten string field/CSS-selector pairs')
    steps = output.get('steps', [])
    if not isinstance(steps, list) or len(steps) > 5:
        raise ValueError('Interactive inspection allows up to five trusted read/navigation steps')
    for step in steps:
        if not isinstance(step, dict) or set(step) != {'action', 'target'} or step['action'] != 'click' or not isinstance(step['target'], str):
            raise ValueError('Only explicit trusted click inspection steps are supported')
    if steps and operation not in ('retrieve_url', 'browse_interactively'):
        raise ValueError('Click steps require a page inspection operation')
    if selectors and operation not in ('retrieve_url', 'extract_structured'):
        raise ValueError('Selectors require page retrieval or structured extraction')
    if selectors and (steps or operation == 'browse_interactively' or output['interaction_required'] or output['javascript_required']):
        raise ValueError('Combined browser inspection and structured extraction is unsupported')
    if steps:
        output['interaction_required'] = True
    if (output['javascript_required'] or output['interaction_required']) and operation not in ('retrieve_url', 'browse_interactively'):
        raise ValueError('Combined crawl/search/structured rendering is not supported by this adapter')
    return prepare_request(output) if operation == 'discover_linkedin' else output


def capability(req):
    if req['operation'] == 'research_social':
        return SOCIAL[req['platform']]
    if req['interaction_required']:
        return 'INTERACTIVE_BROWSER'
    if req['javascript_required']:
        return 'JAVASCRIPT'
    return OPERATIONS[req['operation']]


def choose(req, providers, attempts=()):
    if req['operation'] == 'linkedin_automation':
        return {'state': 'DISABLED', 'provider': None, 'capability': 'LINKEDIN_DIRECT_AUTOMATION', 'reason': 'No scraping or automated account actions; prepare recommendations/drafts only'}
    if req['operation'] == 'approved_linkedin_api':
        return {'state': 'UNAVAILABLE', 'provider': None, 'capability': 'LINKEDIN_APPROVED_API', 'reason': 'No approved API client is configured; snapshots tagged official do not grant scopes'}
    if req['operation'] == 'imported_linkedin':
        return {'state': 'LINKEDIN_IMPORTED_DATA', 'provider': None, 'capability': 'LINKEDIN_IMPORTED_DATA', 'reason': 'Analyze all authorized local data within resource constraints; discovery caps do not apply'}
    if req['operation'] == 'local_only':
        return {'state': 'NO_RETRIEVAL', 'provider': None, 'reason': 'Local writing needs no external information'}
    if req['operation'] == 'discover_linkedin':
        suitable = [p for p in providers if p.id == 'agent_reach_discovery' and p.available and p.enabled and 'LINKEDIN_DISCOVERY' in p.capabilities]
        if attempts or not suitable:
            return {'state': 'UNAVAILABLE', 'provider': None, 'capability': 'LINKEDIN_DISCOVERY',
                    'reason': 'No audited index-only Agent Reach search adapter; no page retrieval, scraper or fallback is permitted'}
        return {'state': 'SELECTED', 'provider': 'agent_reach_discovery', 'capability': 'LINKEDIN_DISCOVERY',
                'reason': 'External-index discovery; no LinkedIn fetch/fallback; bounded non-LinkedIn enrichment only'}
    if req['operation'] == 'retrieve_linkedin' or (req.get('url') and linkedin_target(req['url'])):
        return {'state': 'LINKEDIN_READER', 'provider': None, 'reason': 'Use li-read; web health grants no account access'}
    cap = capability(req)
    tried = {a['provider'] for a in attempts}
    last = attempts[-1]['failure'] if attempts else None
    if last in ('AUTH_REQUIRED', 'NOT_FOUND', 'PARSE_FAILURE', 'NETWORK_ERROR'):
        return {'state': 'UNAVAILABLE', 'provider': None, 'capability': cap, 'reason': 'Failure does not justify escalating access or cost'}
    if last == 'CAPABILITY_MISMATCH' and req['operation'] not in ('retrieve_url', 'browse_interactively'):
        return {'state': 'UNAVAILABLE', 'provider': None, 'capability': cap, 'reason': 'Interaction cannot substitute for the requested source capability'}
    desired = 'INTERACTIVE_BROWSER' if last == 'CAPABILITY_MISMATCH' else cap
    required = {desired}
    if last != 'CAPABILITY_MISMATCH' and req['operation'] == 'retrieve_url':
        required.add('PAGE_FETCH')
    candidates = []
    for p in providers:
        if p.id in tried or not p.available or not p.enabled:
            continue
        metered = p.cost in ('METERED', 'PAID')
        managed = 'BLOCKED_RETRIEVAL' in p.capabilities
        if managed:
            # Managed fallback cannot substitute for interactive/crawl/social work.
            if desired not in p.capabilities or desired not in ('PAGE_FETCH', 'SEARCH') or not req['allow_metered']:
                continue
            if not req['managed_required'] and last not in ('BLOCKED', 'RATE_LIMIT', 'TIMEOUT'):
                continue
        elif not required.issubset(p.capabilities) or req['managed_required']:
            continue
        if metered and not req['allow_metered']:
            continue
        # After a blocking/timeout failure use one justified managed path, not shotgun retries.
        if last in ('BLOCKED', 'RATE_LIMIT', 'TIMEOUT') and not managed:
            continue
        candidates.append(p)
    if not candidates:
        return {'state': 'UNAVAILABLE', 'provider': None, 'capability': desired,
                'reason': 'No enabled suitable provider; retain imports/placeholders and report the gap'}
    candidates.sort(key=lambda p: (p.cost in ('METERED', 'PAID'), p.complexity, desired not in p.validated, {'HIGH':0,'UNMEASURED':1,'LOW':2}.get(p.reliability,1), {'LOW':0,'UNKNOWN':1,'HIGH':2}.get(p.latency,1), p.id))
    chosen = candidates[0]
    return {'state': 'SELECTED', 'provider': chosen.id, 'capability': desired,
            'cost': chosen.cost, 'latency': chosen.latency, 'reliability': chosen.reliability,
            'reason': 'Suitable capability with least cost/complexity; sequential escalation only'}


def execute(value, providers, root, now=None, enrichment_handler=None, cache_enabled=True):
    req = request(value)
    now = now or datetime.now(timezone.utc)
    plan = choose(req, providers)
    if req['operation'] == 'discover_linkedin':
        return execute_discovery(req, providers, plan, now, root, enrichment_handler, cache_enabled)
    if plan['state'] in ('NO_RETRIEVAL', 'LINKEDIN_READER', 'LINKEDIN_IMPORTED_DATA', 'DISABLED') or req['operation'] == 'approved_linkedin_api':
        return {'state': plan['state'], 'evidence': [], 'attempts': [], 'decision': plan}
    if req.get('url') and not req.get('steps') and not req.get('selectors') and not req['javascript_required'] and not req['interaction_required'] and req['operation'] == 'retrieve_url':
        cached = [r for r in load(root) if r['url'] == req['url'] and is_fresh(r, req['max_age_hours'], now)]
        if cached and req['max_age_hours'] > 0:
            return {'state': 'CACHED', 'evidence': cached, 'attempts': [], 'decision': {'reason': 'Task freshness budget satisfied'}}
    attempts = []
    for _ in range(2):
        plan = choose(req, providers, attempts)
        if plan['state'] != 'SELECTED':
            break
        selected = next(p for p in providers if p.id == plan['provider'])
        if selected.retrieve is None:
            attempts.append({'provider': selected.id, 'failure': 'PROVIDER_DISABLED', 'decision': plan})
            continue
        try:
            packets = selected.retrieve(req)
            if not isinstance(packets, list) or not packets:
                raise RetrievalFailure('PARSE_FAILURE')
            if any(p.get('url') and linkedin_target(p['url']) for p in packets):
                raise RetrievalFailure('AUTH_REQUIRED')
            received = max(now, datetime.now(timezone.utc))
            records = [normalize({**p, 'freshness_class': req['freshness_class']}, selected.id, received, 'SOCIAL_COMMUNITY' if req['operation'] == 'research_social' else 'PUBLIC_WEB') for p in packets]
            if any((req['max_age_hours'] == 0 and parse_time(r['retrieved_at']) < now) or
                   (req['max_age_hours'] > 0 and not is_fresh(r, req['max_age_hours'], received)) for r in records):
                raise RetrievalFailure('PARSE_FAILURE')
            records = deduplicate(records)
            save(root, records)
            attempts.append({'provider': selected.id, 'failure': None, 'decision': plan})
            return {'state': 'SUCCESS', 'evidence': records, 'attempts': attempts, 'decision': plan}
        except RetrievalFailure as exc:
            attempts.append({'provider': selected.id, 'failure': exc.reason, 'decision': plan})
        except Exception:
            # Do not return raw provider error bodies/URLs that may contain secrets.
            attempts.append({'provider': selected.id, 'failure': 'PARSE_FAILURE', 'decision': plan})
    return {'state': 'UNAVAILABLE', 'evidence': [], 'attempts': attempts,
            'decision': choose(req, providers, attempts)}


def execute_discovery(req, providers, plan, now, root, enrichment_handler=None, cache_enabled=True):
    from discovery_workflow import cached, cache_result, enrich_candidates
    result = cached(root, req, now) if cache_enabled else None
    if result is not None:
        result = {**result, 'state': 'CACHED', 'cache_hit': True, 'queries_used_now': 0, 'attempts': [], 'decision': plan}
        if enrichment_handler is not None and req['enrichment_limit']:
            enriched = enrich_candidates(result, req, enrichment_handler, now)
            result.update({key:enriched[key] for key in ('candidates','auto_enriched','enrichment_attempted','enrichment_note')})
        return result
    result = report([], req['limit'])
    result.update(auto_enriched=0, queries_used_now=0, cache_hit=False)
    if plan['state'] != 'SELECTED':
        return {**result, 'state': 'UNAVAILABLE', 'evidence': [], 'attempts': [], 'decision': plan}
    provider = next(p for p in providers if p.id == plan['provider'])
    candidates, attempts, observations = {}, [], {}
    non_improving = 0
    for query in req['queries'][:req['query_budget']]:
        try:
            if provider.retrieve is None:
                raise RetrievalFailure('PROVIDER_DISABLED')
            result['queries_used_now'] += 1
            remaining = req['limit'] - len(candidates)
            rows = provider.retrieve({**req, 'query': query, 'limit': remaining})
            previous_count = len(candidates)
            ranked = rank_candidates(rows, query, remaining, now, provider.discovery_transport or provider.id)
            for candidate in ranked:
                url = candidate['linkedin_url']
                observations.setdefault(url, []).append({'query': query, 'provider': provider.id, 'retrieved_at': now.isoformat()})
                if url not in candidates or candidate['relevance_score'] > candidates[url]['relevance_score']:
                    candidates[url] = candidate
            attempts.append({'provider': provider.id, 'failure': None, 'decision': plan})
            # Enough results: no extra query merely to fill a larger harvest.
            non_improving = non_improving + 1 if len(candidates) == previous_count else 0
            if len(candidates) >= req['limit'] or (previous_count and non_improving) or non_improving >= 2:
                break
        except Exception as exc:
            failure = exc.reason if isinstance(exc, RetrievalFailure) else 'PARSE_FAILURE'
            attempts.append({'provider': provider.id, 'failure': failure, 'decision': plan})
            break  # No provider fallback, retries or scraper escalation.
    found = sorted(candidates.values(), key=lambda r: (-r['relevance_score'], r['linkedin_url']))[:req['limit']]
    for candidate in found:
        candidate['search_observations'] = observations[candidate['linkedin_url']]
    result.update(report(found, req['limit'], result['queries_used_now']))
    result.update(state='SUCCESS' if found or (attempts and attempts[-1]['failure'] is None) else 'UNAVAILABLE',
                  evidence=[], attempts=attempts, decision=plan)
    if found and enrichment_handler is not None and req['enrichment_limit']:
        enriched = enrich_candidates(result, req, enrichment_handler, now)
        result.update({key:enriched[key] for key in ('candidates','auto_enriched','enrichment_attempted','enrichment_note')})
    if result['state'] == 'SUCCESS' and cache_enabled:
        cache_result(root, req, result, now)
    return result


def health(providers):
    return [{'provider': p.id, 'detected': p.available, 'configured': p.enabled,
             'status': 'DISABLED' if not p.enabled else 'UNAVAILABLE' if not p.available else 'LAST_ATTEMPT_FAILED' if p.last_failure else 'VALIDATED' if p.validated else 'AVAILABLE_UNVALIDATED',
             'last_failure': p.last_failure, 'reachable_now': None,
             'capabilities': sorted(p.capabilities), 'validated_capabilities': sorted(p.validated & p.capabilities),
             'cost': p.cost, 'latency': p.latency, 'reliability': p.reliability,
             'note': 'No live probe; recent receipts attest only tested sources. Tool/source validation never grants LinkedIn account access'} for p in providers]


def stages(intent, external_needed=False):
    base = ['CONTEXT', 'LINKEDIN_READER', 'MEMORY'] if intent in ('daily', 'ideas', 'profile') else ['CONTEXT', 'MEMORY']
    if external_needed:
        base += ['RESEARCH_REQUEST', 'PROVIDER_ROUTER', 'RETRIEVAL', 'NORMALIZE', 'DEDUPLICATE', 'CLAIM_GATE']
    return base + ['REASONING', 'VOICE_DRAFT', 'QUALITY', 'HUMAN_REVIEW']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.linkedin-agent')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('evidence')
    sub.add_parser('signals').add_argument('terms', nargs='+')
    p = sub.add_parser('assess'); p.add_argument('id'); p.add_argument('assessment')
    p = sub.add_parser('ingest'); p.add_argument('packet'); p.add_argument('--provider', required=True)
    p.add_argument('--source-type', default='PUBLIC_WEB', choices=['PUBLIC_WEB', 'SOCIAL_COMMUNITY', 'USER_PROVIDED'])
    args = parser.parse_args()
    try:
        if args.command == 'evidence':
            result = load(args.root)
        elif args.command == 'signals':
            result = signals(load(args.root), args.terms)
        elif args.command == 'assess':
            result = assess(args.root, args.id, json.loads(Path(args.assessment).read_text(encoding='utf-8')))
        else:
            packet = json.loads(Path(args.packet).read_text(encoding='utf-8'))
            result = save(args.root, [normalize(packet, args.provider, source_type=args.source_type)])
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Research: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
