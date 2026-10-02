#!/usr/bin/env python3
"""Optional live adapters for the central li-research router; no LinkedIn account client."""
import argparse
import asyncio
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tomllib
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'skills/li-research/scripts'))
from orchestrator import Provider, RetrievalFailure, request, choose, execute, health, FAILURES
from evidence import public_url, timestamp, parse_time, signals, load


def network_url(url):
    url = public_url(url)
    if (urlsplit(url).hostname or '').lower().rstrip('.').split('.')[-2:] == ['linkedin', 'com']:
        raise RetrievalFailure('AUTH_REQUIRED')
    try:
        addresses = socket.getaddrinfo(urlsplit(url).hostname, None)
    except OSError:
        raise RetrievalFailure('NETWORK_ERROR')
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise RetrievalFailure('AUTH_REQUIRED')  # Access boundary, never managed escalation.
    return url


def checked_get(url):
    from scrapling.fetchers import Fetcher
    for _ in range(4):
        url = network_url(url)
        try:
            response = Fetcher.get(url, timeout=20, retries=0, follow_redirects=False,
                                   stealthy_headers=False)
        except Exception as exc:
            if 'timeout' in str(exc).lower():
                raise RetrievalFailure('TIMEOUT')
            raise RetrievalFailure('NETWORK_ERROR')
        if response.status in (301, 302, 303, 307, 308):
            url = urljoin(url, response.headers.get('location') or response.headers.get('Location') or '')
            continue
        if response.status in (401,):
            raise RetrievalFailure('AUTH_REQUIRED')
        if response.status in (403,):
            raise RetrievalFailure('BLOCKED')
        if response.status == 429:
            raise RetrievalFailure('RATE_LIMIT')
        if response.status == 404:
            raise RetrievalFailure('NOT_FOUND')
        if response.status != 200:
            raise RetrievalFailure('NETWORK_ERROR')
        return response
    raise RetrievalFailure('NETWORK_ERROR')


def packet(response, selectors=None):
    return {'url': public_url(response.url), 'title': response.css('title::text').get(),
            'content': response.markdown(main_content_only=True),
            'retrieved_at': timestamp(datetime.now(timezone.utc)),
            'extracted_fields': {k: response.css(v).get() for k, v in selectors.items()} if selectors else None}


async def mcp_call(component, calls):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = dict(os.environ)
    params = StdioServerParameters(command=sys.executable, env=env,
                                   args=[str(ROOT / 'tools/web/run_mcp.py'), component])
    results = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=60) as session:
            await session.initialize()
            try:
                for name, args in calls:
                    result = await session.call_tool(name, args)
                    if result.is_error:
                        raise RetrievalFailure('CAPABILITY_MISMATCH')
                    results.append(result)
            finally:
                if component == 'playwright':
                    await session.call_tool('browser_close', {})
    return results


def text(result):
    return '\n'.join(c.text for c in result.content if c.type == 'text')


def browser(req):
    url = network_url(req['url'])
    calls = [('browser_navigate', {'url': url})]
    calls += [('browser_click', {'target': s['target']}) for s in req.get('steps', [])]
    calls += [('browser_snapshot', {})]
    results = asyncio.run(mcp_call('playwright', calls))
    content = text(results[-1])
    # Actual reported final URL/title, never guessed from the request.
    import re
    match = re.search(r'Page URL: (\S+)', content)
    final = network_url(match.group(1)) if match else None
    if final is None:
        raise RetrievalFailure('PARSE_FAILURE')
    title = re.search(r'Page Title: (.+)', content)
    return [{'url': final, 'title': title.group(1) if title else None, 'content': content}]


def scrape(req):
    if req['javascript_required']:
        if req.get('selectors'):
            raise RetrievalFailure('CAPABILITY_MISMATCH')
        from scrapling.fetchers import DynamicFetcher
        from run_mcp import browser_path
        def setup(page):
            def guard(route):
                try:
                    if route.request.method not in ('GET', 'HEAD'):
                        raise ValueError('Read-only browser')
                    network_url(route.request.url)
                    response = route.fetch(max_redirects=0, timeout=20000)
                    if 300 <= response.status < 400:
                        raise ValueError('Use the canonical nonredirecting public URL')
                    route.fulfill(response=response)
                except Exception:
                    route.abort('blockedbyclient')
            page.context.route('**/*', guard)
            page.context.route_web_socket('**/*', lambda ws: ws.close())
        response = DynamicFetcher.fetch(network_url(req['url']), headless=True,
                                         executable_path=browser_path(), page_setup=setup, google_search=False,
                                         timeout=30000, additional_args={'service_workers': 'block'})
        if response.status != 200:
            raise RetrievalFailure('NETWORK_ERROR')
        return [packet(response)]
    if req['operation'] != 'crawl_site':
        return [packet(checked_get(req['url']), req.get('selectors'))]
    # Small HTTP breadth-first ingestion, one request at a time, no browser farm.
    root = req['url']
    host = urlsplit(root).netloc
    robots_url = urljoin(root, '/robots.txt')
    robots = RobotFileParser()
    try:
        response = checked_get(robots_url)
        robots.parse(response.body.decode('utf-8', errors='replace').splitlines())
    except RetrievalFailure as exc:
        if exc.reason != 'NOT_FOUND':
            raise  # Never reinterpret a blocked robots request as permission.
        robots.parse([])
    queue, seen, results = [root], set(), []
    import time
    while queue and len(results) < req['max_pages']:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if not robots.can_fetch('LinkedInResearchToolkit', url):
            continue
        response = checked_get(url)
        results.append(packet(response))
        for link in response.css('a::attr(href)').getall():
            # Bound the frontier as well as successful pages; denied links must
            # not turn a small crawl into an unbounded robots/queue scan.
            if len(seen) + len(queue) >= req['max_pages']:
                break
            try:
                candidate = public_url(urljoin(response.url, link))
            except ValueError:
                continue
            if urlsplit(candidate).netloc == host and candidate not in seen and candidate not in queue:
                queue.append(candidate)
        if queue and len(results) < req['max_pages']:
            time.sleep(0.5)
    return results


def specialist(req):
    if req['platform'] != 'v2ex':
        raise RetrievalFailure('AUTH_REQUIRED')
    binary = shutil.which('agent-reach')
    if not binary:
        raise RetrievalFailure('PROVIDER_DISABLED')
    # Reuse the existing isolated interpreter; never read account configuration/cookies.
    interpreter = Path(binary).read_text(encoding='utf-8').splitlines()[0].removeprefix('#!')
    if not Path(interpreter).is_file():
        raise RetrievalFailure('PROVIDER_DISABLED')
    code = 'import json; from agent_reach.channels.v2ex import V2EXChannel; print(json.dumps(V2EXChannel().get_hot_topics(limit=3)))'
    env = dict(os.environ)
    env.pop('API_TOKEN', None)
    try:
        result = subprocess.run([interpreter, '-c', code], env=env, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        raise RetrievalFailure('TIMEOUT') from None
    if result.returncode:
        raise RetrievalFailure('NETWORK_ERROR')
    rows = json.loads(result.stdout)
    return [{'url': r.get('url'), 'platform': 'v2ex', 'platform_id': str(r['id']),
             'title': r.get('title'), 'author': r.get('author'),
             'metadata': {'publisher': 'V2EX public hot topics (not query search)'},
             'published_at': datetime.fromtimestamp(r['created'], timezone.utc).isoformat() if r.get('created') else None,
             'content': (r.get('title') or '') + '\n' + (r.get('content') or '')} for r in rows]


def managed(req):
    # This adapter never enables/configures Bright Data or provisions accounts itself.
    if req['operation'] not in ('retrieve_url', 'search_web', 'research_topic'):
        raise RetrievalFailure('CAPABILITY_MISMATCH')
    if req.get('url'):
        args = {'url': network_url(req['url'])}
        name = 'scrape_as_markdown'
    else:
        args = {'query': req['query']}
        name = 'search_engine'
    results = asyncio.run(mcp_call('brightdata', [(name, args)]))
    return [{'url': req.get('url'), 'content': text(results[0])}]


def providers(root=".linkedin-agent"):
    from read_layer import config
    research_settings = config(root).get("research", {})
    config = ROOT / '.codex/config.toml'
    servers = tomllib.loads(config.read_text(encoding='utf-8')).get('mcp_servers', {}) if config.exists() else {}
    from read_layer import safe_path, read_text
    receipt = safe_path(ROOT, '.web-tools/health.json')
    validations = json.loads(read_text(receipt)) if receipt.exists() else {}
    if not isinstance(validations, dict):
        raise ValueError('Malformed capability validation receipt')
    def validated(name):
        row = validations.get(name, {})
        if not isinstance(row, dict) or not isinstance(row.get('checks', {}), dict):
            raise ValueError('Malformed capability validation checks')
        checks = row.get('checks', {})
        result = set()
        for cap, when in checks.items():
            age = (datetime.now(timezone.utc) - parse_time(when)).total_seconds()
            if 0 <= age <= 86400:
                result.add(cap)
        return frozenset(result)
    def last_failure(name):
        failure = validations.get(name, {}).get('last_failure')
        if failure is None:
            return None
        if not isinstance(failure, dict) or failure.get('reason') not in FAILURES:
            raise ValueError('Malformed provider failure receipt')
        age = (datetime.now(timezone.utc) - parse_time(failure['at'])).total_seconds()
        return failure['reason'] if 0 <= age <= 86400 else None
    scrapling = (ROOT / '.venv/bin/scrapling-mcp').is_file()
    try:
        from run_mcp import browser_path
        browser_binary = bool(browser_path())
    except (OSError, ValueError, KeyError, TypeError):
        browser_binary = False
    playwright = (ROOT / 'tools/web/node_modules/@playwright/mcp/cli.js').is_file() and browser_binary and bool(shutil.which('node'))
    bright = (ROOT / 'tools/web/node_modules/@brightdata/mcp/server.js').is_file()
    return [Provider('scrapling', frozenset({'PAGE_FETCH', 'STRUCTURED_EXTRACTION'} | ({'CRAWL'} if research_settings.get('crawler_enabled', False) else set()) | ({'JAVASCRIPT'} if browser_binary else set())),
                     scrapling, 'scrapling_local' in servers and servers['scrapling_local'].get('enabled', True), 'LOCAL', 0, validated=validated('scrapling'), retrieve=scrape, last_failure=last_failure('scrapling')),
            Provider('playwright', frozenset({'PAGE_FETCH', 'INTERACTIVE_BROWSER'}), playwright,
                     'playwright_local' in servers and servers['playwright_local'].get('enabled', True), 'LOCAL', 2, validated=validated('playwright'), retrieve=browser, last_failure=last_failure('playwright')),
            Provider('agent_reach', frozenset({'SOCIAL_V2EX'}), bool(shutil.which('agent-reach')),
                     research_settings.get('agent_reach_enabled', False), 'FREE_EXTERNAL', 1, validated=validated('agent_reach'), retrieve=specialist, last_failure=last_failure('agent_reach')),
            Provider('brightdata', frozenset({'PAGE_FETCH', 'SEARCH', 'BLOCKED_RETRIEVAL'}), bright,
                     servers.get('brightdata_fallback', {}).get('enabled', False) and bool(os.environ.get('API_TOKEN')),
                     'METERED', 3, validated=validated('brightdata'), retrieve=managed, last_failure=last_failure('brightdata'))]


def record_validation(result):
    if not result.get('attempts'):
        return
    from read_layer import safe_path, read_text, atomic_save
    target = safe_path(ROOT, '.web-tools/health.json')
    rows = json.loads(read_text(target)) if target.exists() else {}
    for attempt in result['attempts']:
        cap = attempt['decision']['capability']
        row = rows.setdefault(attempt['provider'], {'checks': {}})
        checks = row.setdefault('checks', {})
        when = timestamp(datetime.now(timezone.utc))
        if attempt['failure']:
            checks.pop(cap, None)
            row['last_failure'] = {'reason': attempt['failure'], 'at': when}
        else:
            checks[cap] = when
            row.pop('last_failure', None)
    atomic_save(ROOT, '.web-tools/health.json', rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.linkedin-agent')
    parser.add_argument('command', choices=['health', 'plan', 'run'])
    parser.add_argument('request', nargs='?')
    args = parser.parse_args()
    try:
        available = providers(args.root)
        if args.command == 'health':
            from read_layer import status
            result = {'research_providers': health(available), 'linkedin_reader': status(args.root),
                      'specialist_gaps': {'SOCIAL_REDDIT': 'AUTH_REQUIRED / no approved adapter',
                                          'SOCIAL_X': 'AUTH_REQUIRED / no approved adapter',
                                          'SOCIAL_YOUTUBE': 'Installed yt-dlp not validated by this adapter'}}
        else:
            if not args.request:
                raise ValueError('Supply a minimized research request JSON')
            req = json.loads(Path(args.request).read_text(encoding='utf-8'))
            result = choose(request(req), available) if args.command == 'plan' else execute(req, available, args.root)
            if args.command == 'run':
                record_validation(result)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0 if args.command != 'run' or result['state'] in ('SUCCESS', 'CACHED', 'NO_RETRIEVAL', 'LINKEDIN_READER') else 2
    except (OSError, ValueError, KeyError, TypeError, RetrievalFailure) as exc:
        print(f'Research orchestration: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
