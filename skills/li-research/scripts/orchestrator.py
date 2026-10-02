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

OPERATIONS = {'retrieve_url': 'PAGE_FETCH', 'search_web': 'SEARCH', 'research_topic': 'SEARCH',
              'research_social': None, 'browse_interactively': 'INTERACTIVE_BROWSER',
              'crawl_site': 'CRAWL', 'extract_structured': 'STRUCTURED_EXTRACTION',
              'retrieve_linkedin': 'LINKEDIN_READ', 'local_only': None}
SOCIAL = {'reddit': 'SOCIAL_REDDIT', 'x': 'SOCIAL_X', 'youtube': 'SOCIAL_YOUTUBE', 'v2ex': 'SOCIAL_V2EX'}
FAILURES = {'TIMEOUT', 'BLOCKED', 'AUTH_REQUIRED', 'CAPABILITY_MISMATCH', 'NOT_FOUND',
            'PROVIDER_DISABLED', 'RATE_LIMIT', 'PARSE_FAILURE', 'NETWORK_ERROR'}
PURPOSES = {'FACT_VERIFICATION', 'COMMUNITY_DISCUSSION', 'COMPANY_RESEARCH',
            'CURRENT_EVENT', 'DEEP_INGESTION', 'INTERACTIVE_WORKFLOW', 'LOCAL_WRITING'}
FIELDS = {'operation', 'purpose', 'url', 'query', 'platform', 'public_input', 'auth_required',
          'interaction_required', 'javascript_required', 'max_age_hours', 'freshness_class',
          'allow_metered', 'managed_required', 'max_pages', 'selectors', 'steps'}


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
    if operation not in ('local_only', 'retrieve_linkedin') and (type(age) not in (int, float) or not 0 <= age <= 8760):
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
    if (output['javascript_required'] or output['interaction_required']) and operation not in ('retrieve_url', 'browse_interactively'):
        raise ValueError('Combined crawl/search/structured rendering is not supported by this adapter')
    return output


def capability(req):
    if req['operation'] == 'research_social':
        return SOCIAL[req['platform']]
    if req['interaction_required']:
        return 'INTERACTIVE_BROWSER'
    if req['javascript_required']:
        return 'JAVASCRIPT'
    return OPERATIONS[req['operation']]


def choose(req, providers, attempts=()):
    if req['operation'] == 'local_only':
        return {'state': 'NO_RETRIEVAL', 'provider': None, 'reason': 'Local writing needs no external information'}
    if req['operation'] == 'retrieve_linkedin' or (req.get('url') and (urlsplit(req['url']).hostname or '').lower().rstrip('.').split('.')[-2:] == ['linkedin', 'com']):
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


def execute(value, providers, root, now=None):
    req = request(value)
    now = now or datetime.now(timezone.utc)
    plan = choose(req, providers)
    if plan['state'] in ('NO_RETRIEVAL', 'LINKEDIN_READER'):
        return {'state': plan['state'], 'evidence': [], 'attempts': [], 'decision': plan}
    if req.get('url') and not req.get('steps') and not req['javascript_required'] and not req['interaction_required'] and req['operation'] == 'retrieve_url':
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


def health(providers):
    return [{'provider': p.id, 'detected': p.available, 'configured': p.enabled,
             'status': 'DISABLED' if not p.enabled else 'UNAVAILABLE' if not p.available else 'VALIDATED' if p.validated else 'AVAILABLE_UNVALIDATED',
             'capabilities': sorted(p.capabilities), 'validated_capabilities': sorted(p.validated & p.capabilities),
             'cost': p.cost, 'latency': p.latency, 'reliability': p.reliability,
             'note': 'Tool/source validation never grants LinkedIn account access'} for p in providers]


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
