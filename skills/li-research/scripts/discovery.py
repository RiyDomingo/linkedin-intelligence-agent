"""Ephemeral LinkedIn search metadata. This module never retrieves candidate URLs."""
from datetime import datetime, timezone
from html import unescape
import re
from urllib.parse import quote, unquote, urlsplit, urlunsplit

DEFAULT_RESULTS = 25
MAX_RESULTS = 100
DEFAULT_QUERY_BUDGET = 3
MAX_QUERY_BUDGET = 10
LINKEDIN_PAGE_FETCHES = 0


def canonical_host(url):
    """Parsed host matching, including IDNA dots; no substring matching."""
    if not isinstance(url, str) or any(ord(c) < 32 or c.isspace() for c in url) or '\\' in url:
        raise ValueError('Malformed URL')
    host = urlsplit(url).hostname
    if not host or '%' in host:
        raise ValueError('Malformed hostname')
    return host.rstrip('.').encode('idna').decode('ascii').casefold()


def is_linkedin_url(url):
    host = canonical_host(url)
    return host == 'linkedin.com' or host.endswith('.linkedin.com')


def linkedin_target(url, depth=0):
    """Include Jina-wrapped targets; no LinkedIn URL is a fetchable next stage."""
    if depth >= 3:
        return True
    if is_linkedin_url(url):
        return True
    if canonical_host(url) == 'r.jina.ai':
        target = unquote(urlsplit(url).path.lstrip('/'))
        # Unknown reader targets fail closed rather than granting proxy access.
        return not target.startswith(('http://', 'https://')) or linkedin_target(target, depth + 1)
    return False


def classify_intent(query):
    """Conservative routing aid; ambiguous requests still need Codex interpretation."""
    if not isinstance(query, str):
        return None
    text = query.casefold()
    if re.search(r'\b(send|publish|like|connect|follow|unfollow|post|message)\b', text) and re.search(r'\b(connection request|linkedin|dm|inbox)\b', text) and not re.search(r'\b(draft|write|suggest)\b', text):
        return 'LINKEDIN_DIRECT_AUTOMATION'
    if re.search(r'\b(imported|supplied|export|snapshot|local history|my historical)\b', text) and re.search(r'\blinkedin\b', text):
        return 'LINKEDIN_IMPORTED_DATA'
    if re.search(r'\b(scrape|crawl|login|log in)\b', text) and re.search(r'\blinkedin\b', text):
        return 'LINKEDIN_DIRECT_AUTOMATION'
    site = re.search(r'\bsite:([^\s]+)', text)
    if site:
        try:
            linkedin = is_linkedin_url('https://' + site.group(1).strip('/'))
        except ValueError:
            linkedin = False
    else:
        without_urls = re.sub(r'https?://\S+|\b[a-z0-9.-]+\.[a-z]{2,}(?:/\S*)?', '', text)
        linkedin = bool(re.search(r'\blinkedin\b', without_urls))
    if not linkedin:
        return None
    if re.search(r'\b(analy[sz]e|review|audit|read|inspect|summari[sz]e)\b', text):
        return 'LINKEDIN_READ'
    if site or re.search(r'\b(find|discover|identify|search|list|who|look up)\b', text) or re.search(r'\b\d+\s+linkedin\s+(profiles|people|companies)\b', text):
        return 'LINKEDIN_DISCOVERY'
    return None


def prepare_request(req):
    query = req.get('query')
    if not isinstance(query, str) or not query.strip() or len(query) > 300:
        raise ValueError('Discovery needs a minimized public query, at most 300 characters')
    if any(req.get(k) for k in ('url', 'platform', 'steps', 'selectors', 'max_pages', 'auth_required',
                                'interaction_required', 'javascript_required', 'managed_required', 'allow_metered')):
        raise ValueError('Discovery is index metadata only: no URL fetch, browser, auth or escalation')
    match = re.search(r'\b(?:up to\s+)?([0-9][0-9,]*)\s+(?:(?:relevant|linkedin)\s+)*(?:people|profiles|researchers|professionals|companies|candidates)\b', query, re.I)
    limit = req.get('limit', int(match.group(1).replace(',', '')) if match else DEFAULT_RESULTS)
    budget = req.get('query_budget', DEFAULT_QUERY_BUDGET)
    if type(limit) is not int or limit < 1:
        raise ValueError('Discovery limit must be a positive integer')
    if type(budget) is not int or not 1 <= budget <= MAX_QUERY_BUDGET:
        raise ValueError('Discovery query budget must be 1..10')
    variants = req.get('queries', [query.strip()])
    if not isinstance(variants, list) or not 1 <= len(variants) <= budget:
        raise ValueError('Queries must fit the task budget')
    cleaned = []
    for variant in variants:
        if not isinstance(variant, str) or not variant.strip() or len(variant) > 300:
            raise ValueError('Each query must be minimized public text')
        if short_text(variant, 300) != ' '.join(variant.split()):
            raise ValueError('Remove contacts, restricted data and markup from public queries')
        if variant.strip().casefold() not in {x.casefold() for x in cleaned}:
            cleaned.append(variant.strip())
    if short_text(query, 300) != ' '.join(query.split()):
        raise ValueError('Remove private/restricted material from discovery query')
    enrich = req.get('enrichment_limit', 10)
    ttl = req.get('cache_ttl_hours', 24)
    if type(enrich) is not int or not 0 <= enrich <= 20:
        raise ValueError('Automatic enrichment must be 0..20 candidates')
    if type(ttl) not in (int, float) or not 1 <= ttl <= 72:
        raise ValueError('Discovery TTL must be finite 1..72 hours')
    return {**req, 'query': query.strip(), 'queries': cleaned, 'limit': min(limit, MAX_RESULTS),
            'query_budget': budget, 'enrichment_limit': enrich, 'cache_ttl_hours': ttl}


def candidate_url(value):
    if not isinstance(value, str) or not is_linkedin_url(value):
        raise ValueError('Not a LinkedIn candidate')
    p = urlsplit(value)
    if p.scheme not in ('https', 'http') or p.username or p.password or p.port not in (None, 80, 443):
        raise ValueError('Candidate requires a plain public LinkedIn URL')
    path = unquote(p.path)
    if any(c.isspace() or ord(c) < 32 for c in path) or '\\' in path or '%' in path or any(x in ('.', '..') for x in path.split('/')):
        raise ValueError('Malformed candidate path')
    parts = path.strip('/').split('/')
    kind = {'in': 'profile', 'company': 'company', 'posts': 'post', 'pulse': 'post'}.get(parts[0].casefold())
    if len(parts) < 2 or not parts[1]:
        raise ValueError('Candidate must identify a profile, company or post')
    if parts[:2] == ['feed', 'update'] and len(parts) == 3:
        kind = 'post'
    if kind is None or (kind in ('profile', 'company') and len(parts) != 2):
        raise ValueError('Not an allowed discovery candidate path')
    if kind in ('profile', 'company'):
        parts = [parts[0].casefold(), parts[1].casefold()]
    clean_path = '/' + '/'.join(quote(x, safe='-_:') for x in parts)
    return urlunsplit(('https', 'www.linkedin.com', clean_path, '', '')), kind


def short_text(value, maximum):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('Search metadata text must be a string or null')
    text = re.sub(r'<[^>]*>', ' ', unescape(value[:4096]))
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[contact omitted]', text)
    text = re.sub(r'(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)', '[contact omitted]', text)
    if re.search(r'\b(password|cookie|api[_ -]?key|confidential|private message|diagnosed with|suffers from|sexual orientation|political affiliation|home address|social security)\b', text, re.I):
        return '[restricted text omitted]'
    return ' '.join(text.split())[:maximum] or None


def rank_candidates(rows, query, limit=DEFAULT_RESULTS, now=None, provider='agent_reach/external-index'):
    """Allowlist short metadata, canonicalize/deduplicate, and bound ranking work."""
    if not isinstance(rows, list) or len(rows) > MAX_RESULTS:
        raise ValueError('Index response must contain at most 100 candidates per query; no harvesting')
    if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
        raise ValueError('Invalid discovery result limit')
    now = now or datetime.now(timezone.utc)
    terms = set(re.findall(r'\w+', query.casefold())) - {'find', 'linkedin', 'people', 'profiles', 'on', 'working', 'up', 'to', 'relevant', 'site', 'com'}
    selected = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Index candidates must be objects')
        try:
            url, kind = candidate_url(row.get('linkedin_url', row.get('url')))
        except (ValueError, UnicodeError):
            continue
        title = short_text(row.get('search_title', row.get('title')), 180)
        snippet = short_text(row.get('short_search_snippet', row.get('snippet')), 240)
        name = short_text(row.get('display_name_if_available'), 100)
        matches = sorted(terms & set(re.findall(r'\w+', ((title or '') + ' ' + (snippet or '')).casefold())))
        candidate = {'state': 'DISCOVERY_ONLY', 'source_type': 'EXTERNAL_SEARCH_RESULT',
                     'verification': 'SEARCH_METADATA', 'metadata_class': 'EXTERNAL_DISCOVERY_METADATA', 'untrusted_data': True,
                     'display_name_if_available': name, 'search_title': title,
                     'short_search_snippet': snippet, 'linkedin_url': url, 'candidate_type': kind,
                     'search_query': query, 'search_provider': provider,
                     'retrieved_at': now.isoformat(), 'relevance_score': len(matches),
                     'relevance_reason': 'Search metadata matches: ' + ', '.join(matches) if matches else 'Index candidate; relevance needs human review'}
        prior = selected.get(url)
        if prior is None or candidate['relevance_score'] > prior['relevance_score']:
            selected[url] = candidate
    return sorted(selected.values(), key=lambda r: (-r['relevance_score'], r['linkedin_url']))[:limit]


def report(candidates, limit, queries_used=0):
    return {'mode': 'LINKEDIN_DISCOVERY', 'candidates': candidates,
            'coverage': 'PARTIAL' if candidates else 'UNAVAILABLE',
            'limits': {'default_results': DEFAULT_RESULTS, 'effective_results': limit,
                       'hard_results': MAX_RESULTS, 'queries_used': queries_used,
                       'hard_queries': MAX_QUERY_BUDGET, 'linkedin_page_fetches': LINKEDIN_PAGE_FETCHES,
                       'linkedin_browser_visits': 0, 'linkedin_scrapes': 0},
            'retention': 'TEMPORARY DISCOVERY CACHE; no profile or relationship writes',
            'note': 'External search metadata only. LinkedIn pages were not opened or scraped. Coverage is incomplete; snippets are not verified profile facts. Discovery stops here. Requests above 100 are capped; no equivalent-query batching.'}
