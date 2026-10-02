#!/usr/bin/env python3
"""Launch one pinned optional MCP server; no shell or package downloads at runtime."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]


def browser_path():
    receipt = ROOT / '.web-tools/browser.json'
    if receipt.is_symlink() or receipt.parent.is_symlink():
        raise ValueError('Symlinked browser receipt refused')
    if not receipt.is_file():
        raise ValueError('Browser not configured; follow docs/CODEX_WEB_TOOLING.md')
    path = Path(json.loads(receipt.read_text(encoding='utf-8'))['executable_path'])
    base = ROOT / '.web-tools/browsers'
    if (not path.is_absolute() or '..' in path.parts or not path.is_file() or
            not path.resolve().is_relative_to(base.resolve()) or
            any(p.is_symlink() for p in (path, *path.parents) if p == ROOT or ROOT in p.parents)):
        raise ValueError('Browser executable must be the installed local build')
    return str(path)


def launch_spec(component):
    if component not in ('scrapling', 'playwright', 'brightdata'):
        raise ValueError('Unsupported MCP component')
    env = dict(os.environ)
    if component == 'brightdata' and not env.get('API_TOKEN', '').strip():
        raise ValueError('Bright Data is disabled until API_TOKEN is supplied; local tools need no key')
    # Do not forward Bright Data credentials to other providers.
    if component != 'brightdata':
        env.pop('API_TOKEN', None)
    if component == 'scrapling':
        executable = ROOT / '.venv/bin/python'
        entrypoint = ROOT / '.venv/bin/scrapling-mcp'
        if not entrypoint.is_file():
            raise ValueError('Optional Scrapling entrypoint missing')
        # Invoke with the current interpreter; generated shebangs can retain
        # an obsolete checkout path after a directory rename.
        args = [str(executable), str(entrypoint), '--executable-path', browser_path()]
    else:
        executable = shutil.which('node')
        if not executable:
            raise ValueError('Node.js is unavailable in the Codex launch environment')
        if component == 'playwright':
            # Enforce the same read/network guard for every launcher caller.
            env['PLAYWRIGHT_MCP_INIT_PAGE'] = str(ROOT / 'tools/web/public_guard.cjs')
            env['PLAYWRIGHT_MCP_BLOCK_SERVICE_WORKERS'] = 'true'
            cli = ROOT / 'tools/web/node_modules/@playwright/mcp/cli.js'
            args = [executable, str(cli), '--headless', '--isolated',
                    '--executable-path', browser_path(), '--idle-timeout', '60000',
                    '--output-dir', str(ROOT / '.web-tools/artifacts')]
        else:
            cli = ROOT / 'tools/web/node_modules/@brightdata/mcp/server.js'
            # No social or remote-browser groups: the managed fallback is retrieval only.
            env.pop('GROUPS', None)
            env.pop('TOOLS', None)
            env['RATE_LIMIT'] = '20/1h'
            args = [executable, str(cli)]
        if not cli.is_file():
            raise ValueError('MCP dependencies missing; run npm ci --prefix tools/web --ignore-scripts')
    if not executable or not Path(executable).is_file():
        raise ValueError('Optional Python dependencies missing; install the locked web environment')
    return args, env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=['scrapling', 'playwright', 'brightdata'])
    component = parser.parse_args().component
    try:
        args, env = launch_spec(component)
        os.chdir(ROOT)
        os.execve(args[0], args, env)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Web tooling: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
