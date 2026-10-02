#!/usr/bin/env python3
"""Opt-in public smoke tests through the configured stdio MCP launchers."""
import argparse
import asyncio
import json
import re
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]


def text_content(result):
    if result.is_error:
        raise RuntimeError(str(result.content))
    return '\n'.join(c.text for c in result.content if c.type == 'text')


async def verify(component):
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(ROOT / 'tools/web/run_mcp.py'), component])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=60) as session:
            initialized = await session.initialize()
            available = {t.name for t in (await session.list_tools()).tools}
            report = {'component': component, 'server_version': initialized.server_info.version,
                      'initialized': True, 'tools': len(available)}
            if component == 'scrapling':
                result = await session.call_tool('make_request', {
                    'url': 'https://quotes.toscrape.com/', 'method': 'GET',
                    'extraction_type': 'markdown', 'timeout': 20, 'retries': 0})
                content = text_content(result)
                assert result.structured_content['status'] == 200
                assert 'Quotes to Scrape' in content and 'quote' in content.lower()
                report['structured_output'] = 'PASS'
                report['http_markdown'] = 'PASS'
                result = await session.call_tool('fetch', {
                    'url': 'https://quotes.toscrape.com/', 'extraction_type': 'text',
                    'google_search': False, 'timeout': 30000})
                assert 'Quotes to Scrape' in text_content(result)
                report['dynamic_text'] = 'PASS'
            else:
                try:
                    result = await session.call_tool('browser_navigate', {'url': 'https://quotes.toscrape.com/'})
                    assert 'Quotes to Scrape' in text_content(result)
                    result = await session.call_tool('browser_snapshot', {})
                    snapshot = text_content(result)
                    assert 'Quotes to Scrape' in snapshot
                    match = re.search(r'link "Next[^"]*" \[ref=([^\]]+)\]', snapshot)
                    assert match, 'Next link missing from public fixture'
                    result = await session.call_tool('browser_click', {'target': match.group(1)})
                    content = text_content(result)
                    assert '/page/2/' in content and 'Quotes to Scrape' in content
                    report['navigate_snapshot_follow_link'] = 'PASS'
                finally:
                    await session.call_tool('browser_close', {})
            return report


def error_message(exc):
    if isinstance(exc, BaseExceptionGroup):
        return '; '.join(error_message(child) for child in exc.exceptions)
    return str(exc) or type(exc).__name__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=['scrapling', 'playwright'])
    try:
        report = asyncio.run(verify(parser.parse_args().component))
        print(json.dumps(report, indent=2))
        return 0
    except (Exception, BaseExceptionGroup) as exc:
        print(f'Public smoke test failed: {error_message(exc)}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
