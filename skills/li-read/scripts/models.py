"""Allowlisted LinkedIn read models. Facts and inferred assessments stay separate."""
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from urllib.parse import urlsplit

CAPABILITIES = ('profile', 'own_posts', 'own_comments', 'feed', 'network',
                'analytics', 'inbox', 'public_profiles', 'public_posts', 'research')
KINDS = {'profile': ('profile', 'public_profiles'), 'post': ('own_posts', 'feed', 'public_posts'),
         'comment': ('own_comments',), 'person': ('network',), 'analytics': ('analytics',),
         'message': ('inbox',), 'research': ('research',)}
SOURCE_TYPES = ('manual', 'user_export', 'public_web', 'official', 'connector', 'local_history', 'web_research')
LABELS = {'manual': 'USER-PROVIDED', 'user_export': 'USER-PROVIDED',
          'public_web': 'LINKEDIN-RETRIEVED', 'official': 'LINKEDIN-RETRIEVED',
          'connector': 'LINKEDIN-RETRIEVED', 'local_history': 'LOCAL-HISTORY', 'web_research': 'WEB-VERIFIED'}
# None is retained for every missing optional field; no factual defaults.
FIELDS = {
    'profile': {'name': 'str', 'headline': 'str', 'about': 'str', 'roles': 'list',
                'companies': 'list', 'education': 'list', 'featured': 'list', 'url': 'url',
                'skills': 'strings', 'projects': 'strings', 'interests': 'strings',
                'honors': 'strings', 'certifications': 'strings', 'languages': 'strings'},
    'post': {'author': 'str', 'author_id': 'str', 'url': 'url', 'timestamp': 'time',
             'text': 'str', 'media': 'list', 'reactions': 'num', 'comments': 'num',
             'reposts': 'num', 'impressions': 'num', 'reach': 'num', 'project': 'str',
             'company': 'str', 'people_mentioned': 'strings', 'claims': 'strings',
             'evidence_used': 'strings', 'related_research': 'strings'},
    'comment': {'author': 'str', 'author_id': 'str', 'parent_post': 'str', 'url': 'url',
                'timestamp': 'time', 'text': 'str', 'reactions': 'num',
                'relationship_context': 'str'},
    'person': {'name': 'str', 'headline': 'str', 'company': 'str', 'relationship_level': 'str',
               'url': 'url', 'interaction_history': 'strings', 'recent_signals': 'strings'},
    'analytics': {'date': 'time', 'post_id': 'str', 'impressions': 'num', 'reactions': 'num',
                  'comments': 'num', 'reposts': 'num', 'clicks': 'num', 'followers_gained': 'num',
                  'saves': 'num', 'meaningful_comments': 'num', 'relevant_person_engagement': 'num',
                  'opportunities': 'num'},
    'research': {'title': 'str', 'url': 'url', 'timestamp': 'time', 'text': 'str', 'evidence_used': 'strings'},
    'message': {'author': 'str', 'author_id': 'str', 'timestamp': 'time', 'text': 'str',
                'conversation_id': 'str'}
}
ASSESSMENT = {'relevance': 'num', 'novelty': 'num', 'can_contribute': 'bool',
              'reply_expected': 'bool', 'resolved': 'bool', 'repetitive': 'bool',
              'business_signal': 'bool', 'research_signal': 'bool', 'note': 'str'}


def parse_time(value, date_allowed=False):
    if not isinstance(value, str):
        raise ValueError('timestamp must be a string')
    if date_allowed and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})', value):
        raise ValueError('timestamp requires ISO date/time with timezone')
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def timestamp(value=None):
    return (value or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate_value(value, kind):
    if value is None:
        return None
    if kind == 'str':
        if not isinstance(value, str):
            raise ValueError('expected string or null')
    elif kind == 'bool':
        if not isinstance(value, bool):
            raise ValueError('expected boolean or null')
    elif kind == 'num':
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('expected finite nonnegative number or null')
    elif kind in ('list', 'strings'):
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            # Metadata is plain text, not opaque nested blobs that could contain secrets.
            raise ValueError('expected a list of strings or null')
    elif kind == 'time':
        parse_time(value, date_allowed=True)
    elif kind == 'url':
        if not isinstance(value, str):
            raise ValueError('expected public HTTP(S) URL or null')
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('URL must be HTTP(S), without credentials, query or fragment')
    return value


def provenance(source):
    if not isinstance(source, dict) or source.get('type') not in SOURCE_TYPES:
        raise ValueError('valid source type required')
    provider = source.get('provider')
    identifier = source.get('identifier')
    if not isinstance(provider, str) or not provider.strip() or not isinstance(identifier, str) or not identifier.strip():
        raise ValueError('source provider and identifier required')
    parse_time(source.get('retrieved_at'))
    if source['type'] == 'web_research' and not source.get('url'):
        raise ValueError('web_research needs an opened supporting source URL; attestation is not automatic verification')
    visibility = source.get('visibility', 'unknown')
    if visibility not in ('public', 'private', 'unknown'):
        raise ValueError('source visibility must be public/private/unknown')
    confidence = validate_value(source.get('confidence'), 'num')
    if confidence is not None and confidence > 1:
        raise ValueError('source confidence must be 0..1 or null')
    return {'type': source['type'], 'label': LABELS[source['type']], 'provider': provider,
            'identifier': identifier, 'url': validate_value(source.get('url'), 'url'),
            'retrieved_at': source['retrieved_at'], 'confidence': confidence, 'visibility': visibility}


def normalize_envelope(payload):
    if not isinstance(payload, dict) or type(payload.get('schema_version')) is not int or payload.get('schema_version') != 1:
        raise ValueError('schema_version 1 envelope required')
    source = provenance(payload.get('source'))
    caps = payload.get('capabilities')
    if not isinstance(caps, list) or any(not isinstance(c, str) or c not in CAPABILITIES for c in caps) or len(set(caps)) != len(caps):
        raise ValueError('invalid/duplicate capabilities')
    coverage = payload.get('coverage', 'partial')
    if coverage not in ('partial', 'complete'):
        raise ValueError('coverage must be partial/complete')
    items = payload.get('items')
    if not isinstance(items, list):
        raise ValueError('items must be a list')
    result, seen = [], set()
    for index, item in enumerate(items):
        try:
            if not isinstance(item, dict) or item.get('kind') not in KINDS:
                raise ValueError('invalid item kind')
            kind = item['kind']
            cap = item.get('capability')
            if cap not in KINDS[kind] or cap not in caps:
                raise ValueError('item capability must match kind and declared coverage')
            identifier = item.get('id')
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError('stable item id required; do not invent missing source identifiers')
            key = (kind, cap, identifier)
            if key in seen:
                raise ValueError('duplicate record identifier')
            seen.add(key)
            raw = item.get('data')
            if not isinstance(raw, dict):
                raise ValueError('item data must be an object')
            data = {field: validate_value(raw.get(field), typ) for field, typ in FIELDS[kind].items()}
            assessment = item.get('assessment', {})
            if not isinstance(assessment, dict):
                raise ValueError('assessment must be an object')
            hints = {field: validate_value(assessment.get(field), typ) for field, typ in ASSESSMENT.items()}
            for field in ('relevance', 'novelty'):
                if hints[field] is not None and hints[field] > 1:
                    raise ValueError(f'{field} must be 0..1')
            result.append({'kind': kind, 'id': identifier, 'capability': cap, 'data': data,
                           'provenance': source.copy(),
                           'assessment': {'label': 'USER-PROVIDED' if source['type'] in ('manual', 'user_export', 'local_history') else 'INFERRED', **hints}})
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f'item {index + 1}: {exc}') from exc
    return {'source': source, 'capabilities': caps, 'coverage': coverage, 'items': result}


def content_hash(item):
    content = {key: item[key] for key in ('kind', 'id', 'capability', 'data', 'assessment')}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def freshness(item, now):
    """Both retrieval age and event age matter. Missing event date is unknown."""
    retrieved = parse_time(item['provenance']['retrieved_at'])
    age = (now - retrieved).total_seconds() / 3600
    ttl = 24 * (30 if item['kind'] == 'profile' else 14 if item['kind'] == 'person' else 2 if item['kind'] == 'analytics' else 3)
    event = item['data'].get('timestamp') or item['data'].get('date')
    event_age = (now - parse_time(event, date_allowed=True)).total_seconds() / 3600 if event else None
    # Fresh retrieval does not make an old post timely.
    stale = age > ttl or (item['kind'] in ('post', 'comment', 'message', 'research') and event_age is not None and event_age > 7 * 24)
    future = age < 0 or (event_age is not None and event_age < 0)
    return {'retrieval_age_hours': round(age, 2), 'event_age_hours': round(event_age, 2) if event_age is not None else None,
            'ttl_hours': ttl, 'state': 'invalid-future' if future else 'stale' if stale else
            'unknown-event-time' if item['kind'] in ('post', 'comment', 'message', 'research') and event is None else 'fresh'}
