#!/usr/bin/env python3
"""Preview or append project MCP registrations without overwriting existing settings."""
import argparse
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
NAMES = ('scrapling_local', 'playwright_local', 'brightdata_fallback')


def render(root):
    template = (ROOT / 'tools/web/codex-mcp.toml.example').read_text(encoding='utf-8')
    return template.replace('__LAUNCHER__', json.dumps(str(root / 'tools/web/run_mcp.py')))


def merge(existing, addition):
    old, new = tomllib.loads(existing), tomllib.loads(addition)
    conflicts = set(old.get('mcp_servers', {})) & set(new['mcp_servers'])
    if conflicts:
        raise ValueError('Existing MCP registrations preserved; review conflicts: ' + ', '.join(sorted(conflicts)))
    result = existing.rstrip() + '\n\n' + addition if existing.strip() else addition
    tomllib.loads(result)
    return result


def configure(root, write=False):
    target = root / '.codex/config.toml'
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError('Refusing symlinked Codex configuration')
    addition = render(root)
    existing = target.read_text(encoding='utf-8') if target.exists() else ''
    merged = merge(existing, addition)
    if write:
        target.parent.mkdir(exist_ok=True)
        # Configuration is a trusted local single-writer operation.
        target.write_text(merged, encoding='utf-8')
    return {'path': str(target), 'servers': list(NAMES), 'written': write,
            'brightdata_enabled': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='append reviewed entries to local config')
    try:
        print(json.dumps(configure(ROOT, parser.parse_args().write), indent=2))
    except (OSError, ValueError) as exc:
        print(f'Web configuration: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
