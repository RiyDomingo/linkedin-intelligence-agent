#!/usr/bin/env python3
"""Local discovery session handoff, bounded cache and public-evidence enrichment.

No network, credentials or account actions. Codex supplies actual search-only
results and reviewed public-source receipts; metadata never becomes profile truth.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import sys

from discovery import candidate_url, rank_candidates, short_text, linkedin_target
from evidence import safe_path, read_text, atomic_save, parse_time, public_url, normalize

CACHE_FILE = 'discovery/cache.json'
MAX_CACHE_TASKS = 20  # Engineering bound, independent of imported user records.


def cache_key(req):
    fields = {k: req[k] for k in ('query', 'queries', 'limit', 'query_budget', 'cache_ttl_hours')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def read_cache(root, now):
    path = safe_path(root, CACHE_FILE)
    if not path.exists():
        return {'schema_version': 1, 'tasks': {}}
    raw = json.loads(read_text(path))
    if not isinstance(raw, dict) or set(raw) != {'schema_version','tasks'} or raw.get('schema_version') != 1 or not isinstance(raw.get('tasks'), dict) or len(raw['tasks']) > MAX_CACHE_TASKS:
        raise ValueError('Malformed discovery cache')
    keep = {}
    for key, entry in raw['tasks'].items():
        if not isinstance(key, str) or len(key) != 64 or not isinstance(entry, dict) or set(entry) != {'created_at','expires_at','request','result'}:
            raise ValueError('Malformed discovery cache task')
        created, expires = parse_time(entry['created_at']), parse_time(entry['expires_at'])
        if created > now or not 3600 <= (expires-created).total_seconds() <= 72*3600:
            raise ValueError('Invalid discovery cache lifetime')
        if expires <= now:
            continue
        req = entry['request']
        from orchestrator import request
        req = request(req)
        if cache_key(req) != key:
            raise ValueError('Discovery cache identity mismatch')
        result = entry['result']
        rows = result.get('candidates') if isinstance(result, dict) else None
        if not isinstance(rows, list) or len(rows) > req['limit']:
            raise ValueError('Invalid cached candidates')
        # Reconstruct only minimal trusted-shape metadata; drop opaque fields.
        clean = rank_candidates(rows, req['query'], req['limit'], created, 'codex_session_search')
        if len(clean) != len(rows) or any(r.get('verification') != 'SEARCH_METADATA' or r.get('state') != 'DISCOVERY_ONLY' for r in rows):
            raise ValueError('Invalid cached discovery provenance')
        for row in clean:
            # Rank order may change by base query; provenance attaches by URL.
            previous = next(x for x in rows if x['linkedin_url'] == row['linkedin_url'])
            provider = previous.get('search_provider')
            if provider not in ('codex_session_search', 'agent_reach_discovery'):
                raise ValueError('Unknown discovery cache transport')
            row['search_provider'] = provider
            if previous.get('search_query') not in req['queries']:
                raise ValueError('Unknown cached search query')
            row['search_query'] = previous['search_query']
            row['retrieved_at'] = previous['retrieved_at']
            if not created <= parse_time(row['retrieved_at']) <= now:
                raise ValueError('Invalid cached retrieval date')
            observations = previous.get('search_observations', [])
            if not isinstance(observations, list) or len(observations) > 10:
                raise ValueError('Invalid search observations')
            row['search_observations'] = []
            for obs in observations:
                if obs.get('query') not in req['queries'] or obs.get('provider') not in ('agent_reach_discovery','codex_session_search'):
                    raise ValueError('Invalid search observation provenance')
                if parse_time(obs['retrieved_at']) > now:
                    raise ValueError('Future search observation')
                row['search_observations'].append({k:obs[k] for k in ('query','provider','retrieved_at')})
        from discovery import report
        used = result.get('limits', {}).get('queries_used')
        if type(used) is not int or not 0 <= used <= req['query_budget']:
            raise ValueError('Invalid cached query count')
        keep[key] = {'created_at':entry['created_at'],'expires_at':entry['expires_at'],'request': req, 'result': {**report(clean, req['limit'], used), 'auto_enriched': 0, 'state': 'SUCCESS', 'evidence': []}}
    if len(keep) != len(raw['tasks']):
        atomic_save(root, CACHE_FILE, {'schema_version': 1, 'tasks': keep})
    return {'schema_version': 1, 'tasks': keep}


def cached(root, req, now):
    entry = read_cache(root, now)['tasks'].get(cache_key(req))
    if not entry or req['max_age_hours'] == 0:
        return None
    age = (now-parse_time(entry['created_at'])).total_seconds()/3600
    return entry['result'] if 0 <= age <= req['max_age_hours'] else None


def cache_result(root, req, result, now):
    from datetime import timedelta
    from discovery import report
    cache = read_cache(root, now)
    # Enrichment text and private/local context never enter this cache.
    rows = rank_candidates(result['candidates'], req['query'], req['limit'], now,
                           result['candidates'][0]['search_provider'] if result['candidates'] else 'agent_reach_discovery')
    for row in rows:
        prior = next(r for r in result['candidates'] if r['linkedin_url'] == row['linkedin_url'])
        row['search_observations'] = prior['search_observations']
        row['search_query'] = prior['search_query']
        row['retrieved_at'] = prior['retrieved_at']
    received = min([parse_time(r['retrieved_at']) for r in rows], default=now)
    cache['tasks'][cache_key(req)] = {'created_at': received.isoformat(),
        'expires_at': (received+timedelta(hours=req['cache_ttl_hours'])).isoformat(),
        'request': {k:req[k] for k in ('operation','purpose','public_input','max_age_hours','query','queries','limit','query_budget','cache_ttl_hours','enrichment_limit')},
        'result': report(rows, req['limit'], result['limits']['queries_used'])}
    cache['tasks'] = dict(sorted(cache['tasks'].items(), key=lambda x:x[1]['created_at'], reverse=True)[:MAX_CACHE_TASKS])
    atomic_save(root, CACHE_FILE, cache)


def validate_result(result, req):
    """Rebuild metadata rather than trusting an editable result file's assessments."""
    from discovery import report
    if not isinstance(result,dict) or result.get('mode') != 'LINKEDIN_DISCOVERY':
        raise ValueError('Discovery result required')
    rows=result.get('candidates')
    if not isinstance(rows,list) or len(rows)>req['limit']:
        raise ValueError('Candidate set exceeds task limit')
    used=result.get('limits',{}).get('queries_used')
    if type(used) is not int or not 0<=used<=req['query_budget']:
        raise ValueError('Invalid result query count')
    cleaned=[]
    for row in rows:
        if not isinstance(row,dict) or row.get('state')!='DISCOVERY_ONLY' or row.get('verification')!='SEARCH_METADATA' or row.get('source_type')!='EXTERNAL_SEARCH_RESULT':
            raise ValueError('Unverified discovery metadata required; no profile-fact promotion')
        provider=row.get('search_provider')
        if provider not in ('codex_session_search','agent_reach_discovery'):
            raise ValueError('Unknown discovery transport')
        when=parse_time(row['retrieved_at'])
        clean=rank_candidates([row],req['query'],req['limit'],when,provider)
        if len(clean)!=1:raise ValueError('Invalid discovery candidate')
        source_query=row.get('search_query')
        if source_query not in req['queries']:raise ValueError('Unplanned source query')
        clean[0]['search_query']=source_query
        observations=row.get('search_observations',[])
        if not isinstance(observations,list) or len(observations)>10:raise ValueError('Invalid source observations')
        clean[0]['search_observations']=[]
        for observation in observations:
            if not isinstance(observation,dict) or set(observation)!={'query','provider','retrieved_at'} or observation['query'] not in req['queries'] or observation['provider'] not in ('agent_reach_discovery','codex_session_search'):
                raise ValueError('Invalid observation provenance')
            parse_time(observation['retrieved_at'])
            clean[0]['search_observations'].append(dict(observation))
        cleaned.extend(clean)
    if len({r['linkedin_url'] for r in cleaned})!=len(cleaned):
        raise ValueError('Duplicate result candidates')
    return {**report(cleaned,req['limit'],used),'state':result.get('state','SUCCESS'),'evidence':[]}


def enrichment_plan(result, req):
    rows = validate_result(result, req)['candidates']
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError('Invalid candidate set')
    maximum = req['enrichment_limit']
    if type(maximum) is not int or not 0 <= maximum <= 20:
        raise ValueError('Automatic enrichment must be 0..20')
    plan = []
    for row in rows:
        name = short_text(row.get('display_name_if_available'), 100)
        if not name or len(name.split()) < 2:
            continue  # Missing identity clues are not filled in from guessed names.
        candidate_url(row['linkedin_url'])
        topic = re.sub(r'\bsite:\S+|\blinkedin\b', '', req['query'], flags=re.I)
        query = short_text(name+' '+topic, 300)
        plan.append({'linkedin_url':row['linkedin_url'], 'query':query,
                     'operation':'research_topic', 'purpose':'COMPANY_RESEARCH',
                     'public_input':True, 'max_age_hours':24,
                     'rule':'Only non-LinkedIn public sources; name match alone does not resolve identity'})
        if len(plan) >= maximum:
            break
    return plan if maximum else []


def enrich_candidates(result, req, handler, now):
    result = validate_result(result, req)
    plan = enrichment_plan(result, req)
    by_url = {r['linkedin_url']:dict(r) for r in result['candidates']}
    attempted = 0
    enriched = 0
    for task in plan:
        attempted += 1
        row = by_url[task['linkedin_url']]
        try:
            receipts = handler(task)
            if not isinstance(receipts, list) or len(receipts) > 10:
                raise ValueError('Up to ten opened public sources per automatic candidate')
            observations = []
            for receipt in receipts:
                if not isinstance(receipt, dict):
                    raise ValueError('Public evidence receipt required')
                url = public_url(receipt.get('url'))
                if linkedin_target(url) or 'r.jina.ai' == __import__('discovery').canonical_host(url):
                    raise ValueError('Enrichment cannot fetch LinkedIn or reader proxies')
                if receipt.get('opened') is not True:
                    raise ValueError('Search snippets are not opened supporting evidence')
                provider = receipt.get('provider')
                if provider not in ('scrapling','playwright','brightdata','codex_session_public_web','agent_reach'):
                    raise ValueError('Unknown public enrichment provider')
                packet = normalize(receipt, provider, now)
                name = row['display_name_if_available'].casefold()
                content = packet['content'].casefold()
                clues = (row.get('search_title') or '')+' '+(row.get('short_search_snippet') or '')
                signals = receipt.get('identity_signals', [])
                if not isinstance(signals, list) or len(signals) > 5:
                    raise ValueError('Bounded identity signals required')
                matches = []
                for signal in signals:
                    if not isinstance(signal,dict) or signal.get('kind') not in ('organization','role','location','publication'):
                        raise ValueError('Public professional identity signals only')
                    value = short_text(signal.get('value'),100)
                    if value and len(value) >= 4 and value.casefold() in content and value.casefold() in clues.casefold():
                        matches.append({'kind':signal['kind'],'value':value})
                status = 'CORROBORATED_INFERRED' if name in content and matches else 'AMBIGUOUS'
                observations.append({'url':url,'provider':provider,'retrieved_at':packet['retrieved_at'],
                    'evidence_id':packet['id'],'identity_status':status,'matching_signals':matches,
                    'source_excerpt':short_text(receipt.get('excerpt') if isinstance(receipt.get('excerpt'),str) and receipt['excerpt'] in packet['content'] else packet['content'],240), 'verification':'NEEDS_VERIFICATION'})
            row['public_research'] = observations
            if observations:
                enriched += 1
            row['identity_status'] = 'CORROBORATED_INFERRED' if any(o['identity_status']=='CORROBORATED_INFERRED' for o in observations) else 'AMBIGUOUS'
            row['public_corroboration_count'] = sum(o['identity_status']=='CORROBORATED_INFERRED' for o in observations)
        except Exception:
            row['public_research'] = []
            row['identity_status'] = 'AMBIGUOUS'
            row['enrichment_state'] = 'UNAVAILABLE'
    ranked = sorted(by_url.values(),key=lambda r:(-r.get('public_corroboration_count',0),-r['relevance_score'],r['linkedin_url']))
    return {**result,'candidates':ranked,'auto_enriched':enriched,'enrichment_attempted':attempted,
            'enrichment_note':'Non-LinkedIn evidence only. Identity matches are inferred, not profile verification; li-fact-check still applies.'}


def session_discovery(root, value, packet, now=None):
    """Consume actual Codex search-only results, not a fabricated live Python API."""
    from orchestrator import Provider, request, execute
    req = request(value)
    if req['operation'] != 'discover_linkedin':
        raise ValueError('Discovery handoff requires discovery intent')
    if not isinstance(packet,dict) or set(packet) != {'source','searches'} or packet['source'] != 'codex_session_search':
        raise ValueError('Currently supported handoff: Codex session search-only metadata')
    searches = packet['searches']
    if not isinstance(searches,list) or not 1 <= len(searches) <= req['query_budget']:
        raise ValueError('Search receipts exceed task query budget')
    for index, search in enumerate(searches):
        if not isinstance(search,dict) or set(search) != {'query','retrieved_at','results'} or index >= len(req['queries']) or search['query'] != req['queries'][index]:
            raise ValueError('Receipts must follow the planned public queries exactly')
        when = parse_time(search['retrieved_at'])
        current = now or datetime.now(timezone.utc)
        if not 0 <= (current-when).total_seconds() <= req['cache_ttl_hours']*3600:
            raise ValueError('Discovery receipt is stale or future-dated')
        if not isinstance(search['results'],list) or len(search['results']) > 100:
            raise ValueError('Bound external search rows per query')
    prior = cached(root, req, now or datetime.now(timezone.utc))
    if prior is not None:
        return {**prior,'state':'CACHED','cache_hit':True,'queries_used_now':0,'attempts':[], 'transport':'codex_session_search'}
    actual = {s['query']:s for s in searches}
    def retrieve(r):
        if r['query'] not in actual:
            from orchestrator import RetrievalFailure
            raise RetrievalFailure('PROVIDER_DISABLED')
        return actual[r['query']]['results']
    provider=Provider('agent_reach_discovery',frozenset({'LINKEDIN_DISCOVERY'}),True,retrieve=retrieve,discovery_transport='codex_session_search')
    result=execute({**value,'queries':[s['query'] for s in searches]},[provider],root,now,cache_enabled=False)
    # Identify actual transport, without asserting this is the disabled Exa path.
    for row in result['candidates']:
        row['search_provider']='codex_session_search'
        for observation in row.get('search_observations',[]):
            observation['retrieved_at']=actual[observation['query']]['retrieved_at']
            observation['provider']='codex_session_search'
        row['retrieved_at']=actual[row['search_query']]['retrieved_at']
    result['limits']['queries_used'] = len(searches)
    result['queries_used_now'] = 0  # This helper performs no network calls.
    result['search_queries_attested'] = len(searches)
    if result['state']=='SUCCESS':
        # Cache under the original plan, so lookups reuse its receipts.
        cache_result(root,req,result,now or datetime.now(timezone.utc))
    result['transport']='codex_session_search'
    atomic_save(root, 'discovery/validation.json', {'capability':'EXTERNAL_DISCOVERY_METADATA', 'transport':'codex_session_search', 'validated_at':(now or datetime.now(timezone.utc)).isoformat(), 'query_count':result['limits']['queries_used'], 'direct_linkedin_fetches':0, 'note':'Operator-supplied actual session search receipt, not a Python network probe'})
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',default='.linkedin-agent')
    sub=ap.add_subparsers(dest='command',required=True)
    lookup=sub.add_parser('lookup');lookup.add_argument('request')
    discover=sub.add_parser('discover');discover.add_argument('request');discover.add_argument('results')
    plan=sub.add_parser('enrichment-plan');plan.add_argument('request');plan.add_argument('result')
    enrich=sub.add_parser('enrich');enrich.add_argument('request');enrich.add_argument('result');enrich.add_argument('receipts')
    sub.add_parser('purge-expired')
    args=ap.parse_args()
    try:
        from orchestrator import request
        now=datetime.now(timezone.utc)
        if args.command=='purge-expired':
            result={'active_cache_tasks':len(read_cache(args.root,now)['tasks'])}
        else:
            req=request(json.loads(read_text(args.request)))
            if req['operation']!='discover_linkedin':raise ValueError('Discovery request required')
            if args.command=='lookup':
                hit=cached(args.root,req,now)
                result={'state':'CACHED' if hit else 'MISS','result':hit}
            elif args.command=='discover':
                result=session_discovery(args.root,req,json.loads(read_text(args.results)),now)
            else:
                data=json.loads(read_text(args.result))
                if args.command=='enrichment-plan':result=enrichment_plan(data,req)
                else:
                    receipts=json.loads(read_text(args.receipts))
                    if not isinstance(receipts,dict) or len(receipts)>20:raise ValueError('At most twenty automatic candidate receipts')
                    result=enrich_candidates(data,req,lambda task:receipts.get(task['linkedin_url'],[]),now)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'Intelligence: {exc}',file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
