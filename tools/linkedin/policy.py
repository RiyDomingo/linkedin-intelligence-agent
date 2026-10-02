"""Local account policy and status; standard library, no browser or credentials."""
import json
import os
from pathlib import Path
import tempfile
import uuid
from datetime import datetime, timezone

VERSION = '4.26.1'
TOOLS = ('connector_status', 'read_my_profile', 'read_my_posts', 'read_feed', 'close_session')
TTL = {'profile': 30 * 86400, 'own_posts': 3 * 86400, 'feed': 3600}


def now():
    return datetime.now(timezone.utc).isoformat()


def path(root, relative):
    root = Path(root).absolute()
    if root.is_symlink():
        raise ValueError('Symlinked data root refused')
    root = root.parent.resolve() / root.name
    p = root / relative
    if '..' in Path(relative).parts or Path(relative).is_absolute():
        raise ValueError('Unsafe local path')
    for q in (p, *p.parents):
        if q != root and root not in q.parents:
            continue
        if q.is_symlink():
            raise ValueError('Symlink refused')
    return p


def load(root, relative, default):
    p = path(root, relative)
    if not p.exists():
        return default
    if not p.is_file() or p.stat().st_size > 2_000_000:
        raise ValueError('Invalid local state')
    return json.loads(p.read_text(encoding='utf-8'))


def save(root, relative, value):
    p = path(root, relative)
    missing = [q for q in (p.parent, *p.parent.parents) if not q.exists()]
    for q in reversed(missing):
        q.mkdir(mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.account-', dir=p.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, allow_nan=False, indent=2)
            out.write('\n')
        os.replace(name, p)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def enabled(root):
    value = load(root, 'account/control.json', {})
    return value.get('enabled') is True and os.environ.get('LINKEDIN_ACCOUNT_CONNECTOR_ENABLED', 'true').lower() != 'false'


def set_enabled(root, value):
    save(root, 'account/control.json', {'enabled': bool(value)})


def begin_task(root, onboarding=False):
    # Local helper, never an MCP tool. Reset once per actual user task, not per read.
    value = {'id': str(uuid.uuid4()), 'onboarding': bool(onboarding),
             'limit': 6 if onboarding else 4, 'used': 0, 'operations': [], 'stopped': False}
    save(root, 'account/task.json', value)
    return {'task_id': value['id'], 'limit': value['limit'], 'onboarding': onboarding}


def consume(root, operation, stage):
    if not enabled(root):
        raise ValueError('DISABLED')
    value = load(root, 'account/task.json', {})
    if value.get('limit') not in (4, 6) or type(value.get('used')) is not int:
        raise ValueError('TASK_REQUIRED')
    if value.get('stopped') or value['used'] >= value['limit']:
        raise ValueError('TASK_STOPPED_OR_BUDGET_EXHAUSTED')
    key = operation + ':' + stage
    if stage != 'routine' and not value.get('onboarding'):
        raise ValueError('ONBOARDING_REQUIRED')
    if key in value.get('operations', []):
        raise ValueError('DUPLICATE_ACQUISITION')
    value['used'] += 1
    value['operations'].append(key)
    save(root, 'account/task.json', value)


def stop_task(root):
    value = load(root, 'account/task.json', {})
    value['stopped'] = True
    save(root, 'account/task.json', value)


def fresh(retrieved, capability, current=None):
    try:
        age = ((current or datetime.now(timezone.utc)) - datetime.fromisoformat(retrieved.replace('Z', '+00:00'))).total_seconds()
        return 0 <= age < TTL[capability]
    except (ValueError, TypeError, KeyError):
        return False


def minimal_public_query(topic, public_terms):
    """Construct from deliberately selected public terms, not private context blobs."""
    if not isinstance(topic, str) or not isinstance(public_terms, list):
        raise ValueError('Public topic and explicit public terms required')
    parts = [topic, *public_terms]
    if len(parts) > 6 or any(not isinstance(p, str) or len(p) > 120 or '\n' in p for p in parts):
        raise ValueError('Minimized public terms required')
    import re
    if any(re.search(r'@|https?://|cookie|token|password|confidential|private message', p, re.I) for p in parts):
        raise ValueError('Private/credential-bearing query refused')
    return ' '.join(parts).strip()
