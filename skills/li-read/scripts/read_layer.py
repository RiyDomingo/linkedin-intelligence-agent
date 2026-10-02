#!/usr/bin/env python3
"""Read-only source adapters, validated local snapshots and incremental caching."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'li-context/scripts'))
from context import safe_path, read_text
from models import CAPABILITIES, SOURCE_TYPES, normalize_envelope, content_hash, freshness, parse_time, timestamp

PRIORITY = {'official': 0, 'user_export': 1, 'public_web': 2, 'web_research': 2, 'manual': 3, 'local_history': 3, 'connector': 4}
DEFAULT_CONFIG = {'schema_version': 1, 'providers': [],
                  'research': {'agent_reach_enabled': False, 'crawler_enabled': False}}


class ReadProvider(Protocol):
    """A future authorized integration implements only these read methods."""
    id: str
    source_type: str
    capabilities: list
    enabled: bool

    def read(self, capability: str) -> dict:
        """Return a schema_version 1 envelope, including actual coverage/provenance."""
        ...


class FileProvider:
    """Import or session-tool receipt; not an API/browser client."""
    def __init__(self, root, spec):
        self.root, self.spec = root, spec
        self.id, self.source_type = spec['id'], spec['source_type']
        self.capabilities, self.enabled = spec['capabilities'], spec['enabled']

    def read(self, capability):
        if capability not in self.capabilities:
            raise ValueError('unavailable capability')
        path = safe_path(self.root, self.spec['path'])
        payload = json.loads(read_text(path))
        normalized = normalize_envelope(payload)
        if normalized['source']['type'] != self.source_type or normalized['source']['provider'] != self.id:
            raise ValueError('configured provider identity does not match snapshot')
        if capability not in normalized['capabilities']:
            raise ValueError('snapshot does not expose configured capability')
        if (normalized['source']['visibility'] == 'private' or any(i['kind'] == 'message' for i in normalized['items'])) and not self.spec.get('allow_private', False):
            raise ValueError('private import requires explicit allow_private configuration')
        return payload


def config(root):
    path = safe_path(root, 'sources.json')
    value = json.loads(read_text(path)) if path.exists() else json.loads(json.dumps(DEFAULT_CONFIG))
    if not isinstance(value, dict) or value.get('schema_version') != 1 or not isinstance(value.get('providers'), list):
        raise ValueError('sources.json requires schema_version 1 and providers list')
    if set(value) - {'schema_version', 'providers', 'research'}:
        raise ValueError('unrecognized source settings; do not store credentials here')
    ids = set()
    for spec in value['providers']:
        if not isinstance(spec, dict) or set(spec) - {'id', 'source_type', 'path', 'enabled', 'capabilities', 'allow_private'}:
            raise ValueError('provider accepts only file/read settings, never credentials or commands')
        if not isinstance(spec.get('id'), str) or not spec['id'].strip() or spec['id'] in ids:
            raise ValueError('provider ids must be nonempty and unique')
        ids.add(spec['id'])
        if spec.get('source_type') not in SOURCE_TYPES or not isinstance(spec.get('enabled'), bool):
            raise ValueError('invalid source_type or enabled flag')
        if not isinstance(spec.get('path'), str) or not spec['path'].startswith('imports/'):
            raise ValueError('provider snapshots must be under imports/ inside the data root')
        safe_path(root, spec['path'])
        if not isinstance(spec.get('capabilities'), list) or any(c not in CAPABILITIES for c in spec['capabilities']):
            raise ValueError('invalid provider capabilities')
        if not isinstance(spec.get('allow_private', False), bool):
            raise ValueError('allow_private must be boolean')
    research = value.get('research', {})
    if not isinstance(research, dict) or set(research) - {'agent_reach_enabled', 'crawler_enabled'} or any(not isinstance(v, bool) for v in research.values()):
        raise ValueError('research settings are opt-in booleans only')
    return value


def load_cache(root):
    path = safe_path(root, 'read/cache.json')
    if not path.exists():
        return {'schema_version': 1, 'items': [], 'status': {}}
    payload = json.loads(read_text(path))
    if not isinstance(payload, dict) or payload.get('schema_version') != 1 or not isinstance(payload.get('items'), list) or not isinstance(payload.get('status'), dict):
        raise ValueError('malformed read cache')
    for capability, record in payload['status'].items():
        if capability not in CAPABILITIES or not isinstance(record, dict):
            raise ValueError('malformed cached capability status')
        if record.get('state') not in ('available', 'partial', 'stale', 'unavailable') or not isinstance(record.get('attempts'), list):
            raise ValueError('malformed cached capability status')
        selected = record.get('selected_provider')
        if selected is not None and not isinstance(selected, str):
            raise ValueError('invalid selected provider')
        parse_time(record.get('last_refreshed'))
        for attempt in record['attempts']:
            if not isinstance(attempt, dict) or not isinstance(attempt.get('provider'), str) or attempt.get('state') not in ('available', 'partial', 'stale', 'error'):
                raise ValueError('malformed cached source attempt')
            if attempt['state'] == 'error':
                if not isinstance(attempt.get('error'), str):
                    raise ValueError('invalid source error')
            else:
                parse_time(attempt.get('retrieved_at'))
                if type(attempt.get('count')) is not int or attempt['count'] < 0:
                    raise ValueError('invalid source item count')
                if attempt.get('coverage') not in ('partial', 'complete') or attempt.get('source_type') not in SOURCE_TYPES:
                    raise ValueError('invalid source coverage/type')
    watermarks = payload.setdefault('complete_snapshots', [])
    if not isinstance(watermarks, list):
        raise ValueError('malformed complete snapshot watermarks')
    watermark_keys = set()
    for record in watermarks:
        if not isinstance(record, dict) or not isinstance(record.get('provider'), str) or not record['provider'] or record.get('capability') not in CAPABILITIES:
            raise ValueError('malformed complete snapshot watermark')
        parse_time(record.get('retrieved_at'))
        key = (record['provider'], record['capability'])
        if key in watermark_keys:
            raise ValueError('duplicate complete snapshot watermark')
        watermark_keys.add(key)
    # Revalidate cached content/provenance and metadata before use, not only on import.
    seen = set()
    for item in payload['items']:
        env = {'schema_version': 1, 'source': item['provenance'], 'capabilities': [item['capability']],
               'items': [item], 'coverage': 'partial'}
        validated = normalize_envelope(env)['items'][0]
        if validated != {k: item[k] for k in validated}:
            raise ValueError('malformed normalized cache item')
        key = cache_key(item)
        if key in seen:
            raise ValueError('duplicate cached item')
        seen.add(key)
        for field in ('first_seen', 'last_seen', 'last_changed'):
            parse_time(item[field])
        if item.get('retired_at') is not None:
            parse_time(item['retired_at'])
        if not isinstance(item.get('active', True), bool):
            raise ValueError('invalid cache activity state')
        if item.get('content_hash') != content_hash(item) or not isinstance(item.get('changed'), bool):
            raise ValueError('invalid content hash/change state')
    return payload


def atomic_save(root, relative, value):
    path = safe_path(root, relative)
    # New sensitive-state directories and files are private on Unix.
    safe_path(root, '.').mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as fh:
            temp = fh.name
            json.dump(value, fh, indent=2, ensure_ascii=False, allow_nan=False)
            fh.write('\n')
            fh.flush()
            os.fsync(fh.fileno())
        safe_path(root, relative)  # Reject a substituted final symlink before replace.
        os.replace(temp, path)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)


def cache_key(item):
    return (item['provenance']['provider'], item['kind'], item['capability'], item['id'])


def ingest(root, payload, allow_private=False, now=None):
    normalized = normalize_envelope(payload)
    now = now or datetime.now(timezone.utc)
    if parse_time(normalized['source']['retrieved_at']) > now:
        raise ValueError('retrieval timestamp is in the future')
    if (normalized['source']['visibility'] == 'private' or any(i['kind'] == 'message' for i in normalized['items'])) and not allow_private:
        raise ValueError('private data requires explicit --allow-private')
    old = load_cache(root)
    stored = {cache_key(item): item for item in old['items']}
    watermarks = {(r['provider'], r['capability']): r['retrieved_at'] for r in old.get('complete_snapshots', [])}
    counts = {'new': 0, 'updated': 0, 'unchanged': 0, 'older_ignored': 0, 'retired': 0}
    for item in normalized['items']:
        key, digest = cache_key(item), content_hash(item)
        watermark = watermarks.get((key[0], item['capability']))
        if watermark and parse_time(item['provenance']['retrieved_at']) < parse_time(watermark):
            counts['older_ignored'] += 1
            continue
        previous = stored.get(key)
        previous_time = max(parse_time(previous['provenance']['retrieved_at']),
                            parse_time(previous['retired_at']) if previous.get('retired_at') else parse_time(previous['provenance']['retrieved_at'])) if previous else None
        if previous_time and parse_time(item['provenance']['retrieved_at']) < previous_time:
            counts['older_ignored'] += 1
            continue
        changed = previous is None or previous['content_hash'] != digest
        counts['new' if previous is None else 'updated' if changed else 'unchanged'] += 1
        stored[key] = {**item, 'content_hash': digest, 'first_seen': previous['first_seen'] if previous else timestamp(now),
                       'last_seen': timestamp(now), 'last_changed': timestamp(now) if changed else previous['last_changed'],
                       'changed': changed, 'active': True, 'retired_at': None}
    if normalized['coverage'] == 'complete':
        seen = {cache_key(i) for i in normalized['items']}
        for key, previous in stored.items():
            if key[0] == normalized['source']['provider'] and previous['capability'] in normalized['capabilities'] and key not in seen and previous.get('active', True):
                if parse_time(normalized['source']['retrieved_at']) >= parse_time(previous['provenance']['retrieved_at']):
                    previous['active'] = False
                    previous['retired_at'] = normalized['source']['retrieved_at']
                    counts['retired'] += 1
    if normalized['coverage'] == 'complete':
        for cap in normalized['capabilities']:
            key = (normalized['source']['provider'], cap)
            retrieved = normalized['source']['retrieved_at']
            if key not in watermarks or parse_time(retrieved) > parse_time(watermarks[key]):
                watermarks[key] = retrieved
    old['complete_snapshots'] = [{'provider': p, 'capability': c, 'retrieved_at': t} for (p, c), t in sorted(watermarks.items())]
    old['items'] = sorted(stored.values(), key=cache_key)
    atomic_save(root, 'read/cache.json', old)
    return counts


def refresh(root, providers=None, now=None):
    """Read only declared sources in priority order; stale/partial results fall back."""
    now = now or datetime.now(timezone.utc)
    if providers is None:
        providers = [FileProvider(root, s) for s in config(root)['providers']]
    statuses = {}
    for cap in CAPABILITIES:
        attempts, selected = [], None
        for provider in sorted((p for p in providers if p.enabled and cap in p.capabilities),
                               key=lambda p: (PRIORITY.get(p.source_type, 99), p.id)):
            try:
                normalized = normalize_envelope(provider.read(cap))
                if normalized['source']['type'] != provider.source_type or normalized['source']['provider'] != provider.id:
                    raise ValueError('provider response identity mismatch')
                if cap not in normalized['capabilities']:
                    raise ValueError('response lacks requested capability')
                items = [i for i in normalized['items'] if i['capability'] == cap]
                state = 'available' if normalized['coverage'] == 'complete' else 'partial'
                source_age = (now - parse_time(normalized['source']['retrieved_at'])).total_seconds() / 3600
                ttl = 720 if cap in ('profile', 'public_profiles') else 336 if cap == 'network' else 48 if cap == 'analytics' else 72
                if source_age < 0:
                    raise ValueError('retrieval timestamp is in the future')
                if source_age > ttl or any(freshness(i, now)['state'] in ('stale', 'invalid-future') for i in items):
                    state = 'stale'
                receipt = {**normalized, 'schema_version': 1, 'items': items, 'capabilities': [cap]}
                # normalize_envelope expects raw data, assessment with optional keys is accepted.
                allow_private = getattr(provider, 'spec', {}).get('allow_private', False)
                ingest(root, receipt, allow_private=allow_private, now=now)
                attempt = {'provider': provider.id, 'state': state, 'retrieved_at': normalized['source']['retrieved_at'],
                           'count': len(items), 'source_type': provider.source_type, 'coverage': normalized['coverage']}
                attempts.append(attempt)
                if selected is None or (selected['state'] == 'stale' and state != 'stale'):
                    selected = attempt
                if state == 'available':
                    selected = attempt
                    break
            except (OSError, ValueError, KeyError, TypeError) as exc:
                attempts.append({'provider': provider.id, 'state': 'error', 'error': str(exc)})
        statuses[cap] = {'state': selected['state'] if selected else 'unavailable', 'selected_provider': selected['provider'] if selected else None,
                         'last_refreshed': timestamp(now), 'attempts': attempts}
    cache = load_cache(root)
    cache['status'] = statuses
    atomic_save(root, 'read/cache.json', cache)
    return status(root, now=now)


def status(root, now=None):
    now = now or datetime.now(timezone.utc)
    cache = load_cache(root)
    cfg = config(root)
    enabled_ids = {p['id'] for p in cfg['providers'] if p['enabled']}
    disabled_ids = {p['id'] for p in cfg['providers'] if not p['enabled']}
    result = {}
    for cap in CAPABILITIES:
        items = [i for i in cache['items'] if i['capability'] == cap and i.get('active', True) and i['provenance']['provider'] not in disabled_ids]
        prior = cache['status'].get(cap, {})
        selected = prior.get('selected_provider')
        current = [i for i in items if selected is None or i['provenance']['provider'] == selected]
        states = [freshness(i, now)['state'] for i in current]
        state = ('stale' if states and all(s in ('stale', 'invalid-future') for s in states) else 'partial') if items else 'unavailable'
        if selected in enabled_ids and prior.get('state') in ('available', 'partial'):
            last_attempt = next((a for a in prior.get('attempts', []) if a.get('provider') == selected), {})
            retrieved = last_attempt.get('retrieved_at')
            age = (now - parse_time(retrieved)).total_seconds() / 3600 if retrieved else None
            ttl = 720 if cap in ('profile', 'public_profiles') else 336 if cap == 'network' else 48 if cap == 'analytics' else 72
            if age is not None and 0 <= age <= ttl and not any(s in ('stale', 'invalid-future') for s in states):
                state = prior['state']
        result[cap] = {'state': state, 'cached_items': len(items), 'selected_provider': selected,
                       'latest_retrieval': max((i['provenance']['retrieved_at'] for i in items), key=parse_time, default=None),
                       'refresh_attempts': prior.get('attempts', []),
                       'note': 'Local import/snapshot availability is not live LinkedIn account access'}
    external = [i for i in cache['items'] if i.get('active', True) and i['provenance']['provider'] not in disabled_ids and i['provenance']['type'] in ('public_web', 'official', 'connector')]
    usable = {cap for cap, value in result.items() if value['state'] in ('available', 'partial')}
    mode = 'Rich Read-Aware' if external and {'profile', 'own_posts', 'own_comments', 'network'}.issubset(usable) else 'Partial Read' if external else 'Manual'
    return {'mode': mode, 'live_account_client': False, 'capabilities': result,
            'configured_sources': [{'id': p['id'], 'enabled': p['enabled'], 'type': p['source_type'],
                                    'transport': 'local snapshot; external retrieval is session-tool/operator supplied'} for p in cfg['providers']],
            'note': 'Mode describes supplied read evidence, not a tested live connection. This Python build has no remote client; richer reads require legitimate session-tool receipts.'}


def import_csv(path, kind, capability, source, mapping=None):
    """Exact header mapping; does not guess ambiguous platform/export columns."""
    from models import FIELDS
    if kind not in FIELDS:
        raise ValueError('invalid kind')
    mapping = mapping or {'id': 'id', **{k: k for k in FIELDS[kind]}}
    if not isinstance(mapping, dict) or any(k not in {'id', *FIELDS[kind]} or not isinstance(v, str) for k, v in mapping.items()):
        raise ValueError('CSV mapping must map normalized field names to header strings')
    items = []
    with Path(path).open(encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or mapping.get('id') not in headers:
            raise ValueError('unique CSV headers and mapped id column required')
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f'CSV line {line}: incorrect column count')
            data = {}
            for field, column in mapping.items():
                if field == 'id' or column not in row:
                    continue
                value = row[column] if row[column] != '' else None
                typ = FIELDS[kind][field]
                if value is not None and typ == 'num':
                    try:
                        value = float(value)
                    except ValueError as exc:
                        raise ValueError(f'CSV line {line}: invalid {field}') from exc
                elif value is not None and typ in ('list', 'strings'):
                    try:
                        value = json.loads(value)
                    except ValueError as exc:
                        raise ValueError(f'CSV line {line}: {field} must be a JSON list') from exc
                data[field] = value
            items.append({'kind': kind, 'id': row[mapping['id']], 'capability': capability, 'data': data})
    envelope = {'schema_version': 1, 'source': source, 'capabilities': [capability], 'coverage': 'partial', 'items': items}
    normalize_envelope(envelope)
    return envelope


def tools(root, available_tools=()):
    cfg = config(root)
    return {'native_session_tools': list(available_tools),
            'native_note': 'Names supplied by the active Codex session; no Python connection test',
            'agent_reach': {'installed': shutil.which('agent-reach') is not None,
                            'enabled': cfg.get('research', {}).get('agent_reach_enabled', False),
                            'status': 'command presence only; accounts/backends not probed',
                            'linkedin_authenticated': 'disabled; not implemented'},
            'crawler': {'enabled': cfg.get('research', {}).get('crawler_enabled', False),
                        'status': 'session tool required; installation alone is not access'},
            'network_calls': 0}


def purge(root, confirm=False):
    """Remove only imported read cache/receipts; never code or curated history/context."""
    targets = []
    cache = safe_path(root, 'read/cache.json')
    if cache.exists():
        targets.append(cache)
    imports = safe_path(root, 'imports')
    if imports.exists():
        for path in imports.rglob('*'):
            safe = safe_path(root, path.relative_to(safe_path(root, '.')))
            if safe.is_dir():
                continue
            if not safe.is_file():
                raise ValueError('nonregular imported data refused')
            targets.append(safe)
    if not confirm:
        return {'would_remove': [str(p.relative_to(safe_path(root, '.'))) for p in targets]}
    for path in targets:
        path.unlink()
    return {'removed': len(targets), 'preserved': ['identity', 'knowledge', 'history', 'analytics', 'relationships.json', 'sources.json', 'code']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.linkedin-agent')
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('refresh')
    show = sub.add_parser('show')
    show.add_argument('--capability', choices=CAPABILITIES)
    show.add_argument('--include-private', action='store_true')
    imp = sub.add_parser('import')
    imp.add_argument('file')
    imp.add_argument('--allow-private', action='store_true')
    csvp = sub.add_parser('import-csv')
    csvp.add_argument('file')
    csvp.add_argument('--kind', required=True)
    csvp.add_argument('--capability', required=True, choices=CAPABILITIES)
    csvp.add_argument('--source', required=True, help='JSON file containing source provenance')
    csvp.add_argument('--allow-private', action='store_true')
    csvp.add_argument('--mapping', help='optional JSON normalized-field/header map')
    detect = sub.add_parser('tools')
    detect.add_argument('--available-tool', action='append', default=[])
    remove = sub.add_parser('purge')
    remove.add_argument('--confirm-import-purge', action='store_true')
    args = ap.parse_args()
    try:
        if args.command == 'status':
            result = status(args.root)
        elif args.command == 'refresh':
            result = refresh(args.root)
        elif args.command == 'tools':
            result = tools(args.root, args.available_tool)
        elif args.command == 'purge':
            result = purge(args.root, args.confirm_import_purge)
        elif args.command == 'show':
            result = [i for i in load_cache(args.root)['items'] if
                      i.get('active', True) and (not args.capability or i['capability'] == args.capability) and
                      (args.include_private or (i['kind'] != 'message' and i['provenance']['visibility'] != 'private'))]
        else:
            if args.command == 'import':
                payload = json.loads(read_text(args.file))
            else:
                source = json.loads(read_text(args.source))
                mapping = json.loads(read_text(args.mapping)) if args.mapping else None
                payload = import_csv(args.file, args.kind, args.capability, source, mapping)
            result = ingest(args.root, payload, getattr(args, 'allow_private', False))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    main()
