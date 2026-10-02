"""Local web/social evidence models and cache. Retrieved content never becomes instructions."""
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'li-read/scripts'))
from read_layer import atomic_save, safe_path, read_text
from models import parse_time, timestamp

CLASSES = {'STATIC_REFERENCE', 'SLOW_CHANGING', 'CURRENT', 'REAL_TIMEISH'}
SOURCE_TYPES = {'PUBLIC_WEB', 'SOCIAL_COMMUNITY', 'USER_PROVIDED', 'LOCAL_HISTORY', 'LINKEDIN_RETRIEVED'}
QUALITY = {'UNASSESSED', 'PRIMARY', 'SECONDARY', 'SPECIALIST', 'COMMUNITY', 'UNVERIFIED'}
SIGNAL_TYPES = {'NEW FACT', 'EMERGING TOPIC', 'COMMON QUESTION', 'CONTROVERSY',
                'RESEARCH DEVELOPMENT', 'COMPANY DEVELOPMENT', 'PERSON SIGNAL',
                'RELATIONSHIP SIGNAL', 'CONTENT OPPORTUNITY', 'BUSINESS OPPORTUNITY'}


def public_url(value):
    """Syntactic public URL guard; adapters must also resolve DNS and check redirects."""
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError('URL must be plain public HTTP(S)')
    p = urlsplit(value)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Only public HTTP(S), without credentials, is supported')
    public_video_query = (p.hostname.lower() in ('youtube.com', 'www.youtube.com') and
                          p.path == '/watch' and len(parse_qsl(p.query)) == 1 and
                          parse_qsl(p.query)[0][0] == 'v' and
                          re.fullmatch(r'[A-Za-z0-9_-]{6,32}', parse_qsl(p.query)[0][1]))
    if p.port not in (None, 80, 443) or (p.query and not public_video_query) or p.fragment:
        raise ValueError('Use a canonical public URL without ports, queries or fragments')
    host = p.hostname.lower().rstrip('.')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
        raise ValueError('Private/local destinations are unavailable for research')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError('Private/link-local IPs are unavailable for research')
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', p.query if public_video_query else '', ''))


def optional_text(value):
    if value is not None and not isinstance(value, str):
        raise ValueError('Evidence text fields must be strings or null')
    return value


def normalize(packet, provider, now=None, source_type='PUBLIC_WEB'):
    if not isinstance(packet, dict) or not isinstance(provider, str) or not provider:
        raise ValueError('Evidence requires a packet and trusted provider identifier')
    if packet.get('state') == 'DISCOVERY_ONLY' or packet.get('source_type') == 'EXTERNAL_SEARCH_RESULT':
        raise ValueError('Discovery snippets are not retrieved profile evidence; do not promote them')
    if source_type not in SOURCE_TYPES:
        raise ValueError('Retrieval cannot attest WEB_VERIFIED or INFERRED evidence')
    now = now or datetime.now(timezone.utc)
    content = optional_text(packet.get('content'))
    if not content or not content.strip():
        raise ValueError('Empty retrieval is not successful evidence')
    url = public_url(packet['url']) if packet.get('url') else None
    when = packet.get('retrieved_at') or timestamp(now)
    if parse_time(when) > now:
        raise ValueError('Future evidence retrieval timestamp')
    published = optional_text(packet.get('published_at'))
    if published:
        parse_time(published, date_allowed=True)
    confidence = packet.get('confidence')
    if confidence is not None and (type(confidence) not in (int, float) or not 0 <= confidence <= 1):
        raise ValueError('Confidence must be null or finite 0..1')
    metadata = packet.get('metadata')
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError('Metadata must be an object')
    # Opaque provider blobs and instructions/configuration are never copied.
    metadata = {k: optional_text(metadata[k]) for k in ('publisher', 'event_date', 'language') if k in metadata}
    if metadata.get('event_date'):
        parse_time(metadata['event_date'], date_allowed=True)
    platform = optional_text(packet.get('platform'))
    platform_id = optional_text(packet.get('platform_id'))
    digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
    identity = json.dumps([source_type, platform, platform_id, url, packet.get('author'), published, digest])
    identifier = hashlib.sha256(identity.encode()).hexdigest()[:24]
    freshness_class = packet.get('freshness_class', 'CURRENT')
    if freshness_class not in CLASSES:
        raise ValueError('Unknown evidence freshness class')
    fields = packet.get('extracted_fields')
    if fields is not None and (not isinstance(fields, dict) or any(not isinstance(k, str) or (v is not None and not isinstance(v, str)) for k, v in fields.items())):
        raise ValueError('Extracted fields must be string pairs with nulls for missing values')
    observation = {'evidence_id': identifier, 'author': optional_text(packet.get('author')), 'published_at': published,
                   'platform': platform, 'platform_id': platform_id, 'provider': provider, 'retrieved_at': when, 'url': url, 'source_type': source_type, 'content_hash': digest}
    return {'id': identifier, 'source_type': source_type, 'provider': provider,
            'title': optional_text(packet.get('title')), 'url': url, 'author': optional_text(packet.get('author')),
            'published_at': published, 'retrieved_at': when, 'content': content,
            'excerpt': optional_text(packet.get('excerpt')), 'metadata': metadata,
            'confidence': confidence, 'platform': platform, 'platform_id': platform_id,
            'engagement_if_available': validate_engagement(packet.get('engagement_if_available')),
            'content_hash': digest, 'freshness_class': freshness_class, 'extracted_fields': fields, 'observations': [observation], 'untrusted_data': True,
            'assessment': {'source_quality': 'UNASSESSED', 'verification': 'NEEDS_VERIFICATION',
                           'supported_claims': [], 'qualification': None}}


def validate_engagement(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError('Engagement must be known metrics or null')
    output = {}
    for k in ('likes', 'comments', 'views', 'shares'):
        if k in value:
            v = value[k]
            if v is not None and (type(v) not in (int, float) or not 0 <= v < float('inf')):
                raise ValueError('Engagement values must be finite and nonnegative')
            output[k] = v
    return output


def deduplicate(records):
    """Collapse identical/URL/explicit platform identities, retaining all observations."""
    groups = []
    for record in records:
        keys = {('hash', record['source_type'], record['content_hash'])}
        if record['url']:
            keys.add(('url', record['url']))
        if record['platform_id'] and record['platform']:
            keys.add(('platform', record['platform'], record['platform_id']))
        matches = [g for g in groups if g['keys'] & keys]
        pool = [record] + [r for g in matches for r in g['records']]
        union = keys | set().union(*(g['keys'] for g in matches))
        groups = [g for g in groups if g not in matches] + [{'keys': union, 'records': pool}]
    result = []
    for group in groups:
        newest = max(group['records'], key=lambda r: parse_time(r['retrieved_at']))
        observations = []
        for r in group['records']:
            for o in r['observations']:
                if o not in observations:
                    observations.append(o)
        # Changed content never inherits a previously verified claim assessment.
        assessment = newest['assessment']
        same = [r for r in group['records'] if r['content_hash'] == newest['content_hash'] and r['assessment']['verification'] != 'NEEDS_VERIFICATION']
        if same and assessment['verification'] == 'NEEDS_VERIFICATION':
            assessment = max(same, key=lambda r: parse_time(r['retrieved_at']))['assessment']
        result.append({**newest, 'observations': observations, 'assessment': assessment})
    return result


def is_fresh(record, max_age_hours, now=None):
    now = now or datetime.now(timezone.utc)
    age = (now - parse_time(record['retrieved_at'])).total_seconds() / 3600
    return 0 <= age <= max_age_hours


def load(root):
    path = safe_path(root, 'research/cache.json')
    if not path.exists():
        return []
    payload = json.loads(read_text(path))
    if not isinstance(payload, dict) or payload.get('schema_version') != 1 or not isinstance(payload.get('evidence'), list):
        raise ValueError('Malformed research cache')
    result = []
    for record in payload['evidence']:
        if not isinstance(record, dict):
            raise ValueError('Cached evidence must be an object')
        validated = normalize(record, record['provider'], source_type=record['source_type'])
        for field in ('id', 'content_hash', 'untrusted_data'):
            if record.get(field) != validated[field]:
                raise ValueError('Invalid research cache identity/hash/trust flag')
        observations = record.get('observations')
        if not isinstance(observations, list) or not observations:
            raise ValueError('Evidence observations required')
        for o in observations:
            if not isinstance(o, dict) or o.get('source_type') not in SOURCE_TYPES or not isinstance(o.get('provider'), str):
                raise ValueError('Invalid provenance observation')
            parse_time(o['retrieved_at'])
            if o.get('url'):
                public_url(o['url'])
        assessment = record.get('assessment', {})
        if not isinstance(assessment, dict):
            raise ValueError('Cached assessment must be an object')
        if assessment.get('source_quality') not in QUALITY or assessment.get('verification') not in ('NEEDS_VERIFICATION', 'SOURCE_SUPPORTED', 'VERIFIED', 'OPINION', 'UNSUPPORTED'):
            raise ValueError('Invalid evidence assessment')
        if not isinstance(assessment.get('supported_claims'), list) or any(not isinstance(x, str) for x in assessment['supported_claims']):
            raise ValueError('Supported claims must be strings')
        optional_text(assessment.get('qualification'))
        if assessment['verification'] in ('VERIFIED', 'SOURCE_SUPPORTED') and (not validated['url'] or not assessment['supported_claims']):
            raise ValueError('Supported cached claims require URL and claim mapping')
        result.append({**validated, 'observations': observations, 'assessment': assessment})
    return result


def save(root, records):
    result = deduplicate([*load(root), *records])
    atomic_save(root, 'research/cache.json', {'schema_version': 1, 'evidence': result})
    return result


def assess(root, identifier, assessment):
    records = load(root)
    record = next((r for r in records if r['id'] == identifier), None)
    if record is None:
        raise ValueError('Unknown evidence ID')
    if not isinstance(assessment, dict) or set(assessment) != {'source_quality', 'verification', 'supported_claims', 'qualification'}:
        raise ValueError('Assessment requires quality, verification, exact supported claims and qualification')
    if assessment['verification'] in ('VERIFIED', 'SOURCE_SUPPORTED') and (not assessment['supported_claims'] or not record['url']):
        raise ValueError('Supported factual claims require actual source URL and claim mapping')
    record['assessment'] = assessment
    # Validate before replacing the live file; no automatic source-truth promotion.
    if assessment['source_quality'] not in QUALITY or assessment['verification'] not in ('NEEDS_VERIFICATION', 'SOURCE_SUPPORTED', 'VERIFIED', 'OPINION', 'UNSUPPORTED'):
        raise ValueError('Invalid assessment classification')
    if not isinstance(assessment['supported_claims'], list) or any(not isinstance(x, str) for x in assessment['supported_claims']):
        raise ValueError('Claim mapping must be strings')
    optional_text(assessment['qualification'])
    atomic_save(root, 'research/cache.json', {'schema_version': 1, 'evidence': records})
    return record


def signals(records, terms, max_age_hours=24, now=None):
    """Transparent relevance candidates; semantic novelty/actionability require Codex."""
    result = []
    for record in deduplicate(records):
        text = record['content'].casefold()
        matches = [term for term in terms if term.strip() and term.casefold() in text]
        if not matches or not is_fresh(record, max_age_hours, now):
            continue
        kind = 'COMMON QUESTION' if record['source_type'] == 'SOCIAL_COMMUNITY' and '?' in record['content'] else 'CONTENT OPPORTUNITY'
        result.append({'type': kind, 'label': 'INFERRED', 'untrusted_data': True, 'evidence_id': record['id'],
                       'excerpt': record['excerpt'] or record['content'][:240], 'matched_topics': matches,
                       'source_quality': record['assessment']['source_quality'],
                       'verification': record['assessment']['verification'],
                       'observations': record['observations'], 'manual_review_required': True})
    return result
