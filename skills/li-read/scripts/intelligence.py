#!/usr/bin/env python3
"""Selective local intelligence. Recommendations are inferred, never external actions."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys

from read_layer import load_cache, config, status, safe_path, read_text
from models import freshness, parse_time, provenance, timestamp, validate_value
from context import load_history, duplicates, summarize, similarity

CATEGORIES = ('IGNORE', 'READ', 'RESPOND', 'COMMENT', 'FOLLOW UP', 'CONTENT SIGNAL',
              'RELATIONSHIP SIGNAL', 'BUSINESS SIGNAL', 'RESEARCH SIGNAL')


def load_relationships(root):
    path = safe_path(root, 'relationships.json')
    payload = json.loads(read_text(path)) if path.exists() else {'schema_version': 1, 'people': []}
    if not isinstance(payload, dict) or payload.get('schema_version') != 1 or not isinstance(payload.get('people'), list):
        raise ValueError('relationships.json requires schema_version 1 and people list')
    result, seen = {}, set()
    fields = {'name': 'str', 'role': 'str', 'company': 'str', 'why_they_matter': 'str',
              'relationship_type': 'str', 'last_meaningful_interaction': 'time',
              'topics': 'strings', 'owes_reply': 'bool', 'follow_up_due': 'time',
              'recent_signals': 'strings', 'interaction_history': 'strings'}
    for person in payload['people']:
        if not isinstance(person, dict) or not isinstance(person.get('id'), str) or not person['id'].strip() or person['id'] in seen:
            raise ValueError('relationship ids must be nonempty and unique')
        seen.add(person['id'])
        if set(person) - {'id', 'provenance', *fields}:
            raise ValueError('unknown relationship field; sensitive enrichment is unsupported')
        normalized = {field: validate_value(person.get(field), typ) for field, typ in fields.items()}
        result[person['id']] = {'id': person['id'], **normalized, 'provenance': provenance(person.get('provenance'))}
    return result


def priorities(root):
    path = safe_path(root, 'priorities.json')
    payload = json.loads(read_text(path)) if path.exists() else {'topics': [], 'projects': []}
    if not isinstance(payload, dict) or set(payload) - {'topics', 'projects'}:
        raise ValueError('priorities.json accepts topics and projects only')
    for field in ('topics', 'projects'):
        validate_value(payload.get(field, []), 'strings')
        if payload.get(field) is None:
            raise ValueError('priority lists cannot be null')
    return {field: payload.get(field, []) for field in ('topics', 'projects')}


def tokens(text):
    return set(re.findall(r'[^\W_]+', text.casefold()))


def relevance(text, terms):
    content = tokens(text)
    return [term for term in terms if tokens(term) and tokens(term).issubset(content)]


def active_items(root, include_inactive=False):
    disabled = {p['id'] for p in config(root)['providers'] if not p['enabled']}
    # Avoid double counting identical cross-provider items; least-invasive source wins.
    from read_layer import PRIORITY
    items = sorted(load_cache(root)['items'], key=lambda i: (PRIORITY[i['provenance']['type']], i['provenance']['provider']))
    selected = {}
    for item in items:
        if item['provenance']['provider'] in disabled or (not include_inactive and not item.get('active', True)):
            continue
        key = (item['kind'], item['capability'], item['data'].get('url') or item['id'])
        prior = selected.get(key)
        if prior is None or parse_time(item['provenance']['retrieved_at']) > parse_time(prior['provenance']['retrieved_at']):
            selected[key] = item
    return list(selected.values())


def classify(item, context, now):
    """Transparent heuristics; explicit uncertainty and no automatic engagement."""
    data, hints = item['data'], item['assessment']
    fresh = freshness(item, now)
    person = context['people'].get(data.get('author_id'))
    categories, reasons, score = [], [], 0
    text = data.get('text') or ''
    matches = relevance(text, context['priorities']['topics'] + context['priorities']['projects'])
    relevant = bool(matches) or (hints['relevance'] is not None and hints['relevance'] >= .5)
    if fresh['state'] in ('stale', 'invalid-future', 'unknown-event-time'):
        return {'category': 'READ', 'categories': ['READ'], 'score': 0, 'actionable': False,
                'reason': ['Time-sensitive activity needs a fresh, dated source before recommending action'],
                'freshness': fresh, 'label': 'INFERRED'}
    if hints['resolved'] is True or hints['repetitive'] is True:
        return {'category': 'IGNORE', 'categories': ['IGNORE'], 'score': 0, 'actionable': False,
                'reason': ['Explicitly marked resolved or repetitive'], 'freshness': fresh, 'label': 'INFERRED'}
    if matches:
        score += 20
        reasons.append('Matches configured priorities: ' + ', '.join(matches))
    elif relevant:
        score += 20
        reasons.append('User-supplied relevance assessment' if hints['label'] == 'USER-PROVIDED' else 'Source/agent relevance assessment; not independently established')
    if person and person['why_they_matter']:
        score += 10
        reasons.append('Known professional relationship with recorded relevance')
        categories.append('RELATIONSHIP SIGNAL')
    if data.get('author_id') and any(r.get('author_id') == data['author_id'] and
                                    similarity(r['body'], text) >= .75 for r in context['comments']):
        return {'category': 'IGNORE', 'categories': ['IGNORE'], 'score': 0, 'actionable': False,
                'reason': ['Confirmed comment history indicates repetitive engagement'], 'freshness': fresh, 'label': 'INFERRED'}
    own_parent = item['kind'] == 'comment' and data.get('parent_post') in context['own_post_ids']
    expected = hints['reply_expected'] is True
    # A substantive question under a known own post is a candidate, not a certainty.
    question = own_parent and '?' in text and len(tokens(text)) >= 6
    if expected or question:
        score += 60 if expected and hints['label'] == 'USER-PROVIDED' else 50
        categories.insert(0, 'RESPOND')
        reasons.append(('Reply explicitly expected' if hints['label'] == 'USER-PROVIDED' else 'Source/agent suggests a reply obligation; confirm it') if expected else 'Substantive question under a known own post; inferred need to reply')
    elif item['kind'] == 'post' and item['capability'] != 'own_posts' and relevant and hints['can_contribute'] is True:
        score += 25
        categories.insert(0, 'COMMENT')
        reasons.append('User explicitly identified a substantive contribution' if hints['label'] == 'USER-PROVIDED' else 'Source/agent suggests a contribution; confirm substance before drafting')
    elif item['kind'] == 'post' and relevant:
        categories.append('CONTENT SIGNAL')
        reasons.append('Relevant discussion; substantive contribution has not been established')
    if relevant and hints['business_signal'] is True:
        score += 10
        categories.append('BUSINESS SIGNAL')
        reasons.append('User-identified business relevance; not an inferred lead')
    if relevant and hints['research_signal'] is True:
        score += 15
        categories.append('RESEARCH SIGNAL')
        reasons.append('User-identified research signal; factual verification still required')
    if hints['novelty'] is not None and hints['novelty'] >= .5:
        score += 5
        reasons.append('User supplied a novelty assessment')
    category = next((c for c in ('RESPOND', 'COMMENT', 'BUSINESS SIGNAL', 'RESEARCH SIGNAL', 'CONTENT SIGNAL', 'RELATIONSHIP SIGNAL') if c in categories), 'IGNORE')
    if category == 'IGNORE':
        reasons.append('No supported response obligation or substantive contribution')
    actionable = category in ('RESPOND', 'COMMENT', 'BUSINESS SIGNAL', 'RESEARCH SIGNAL') and score >= 35
    return {'category': category, 'categories': categories or ['IGNORE'], 'score': score, 'actionable': actionable,
            'reason': reasons, 'freshness': fresh, 'label': 'INFERRED'}


def build_context(root, items):
    own_ids = {i['id'] for i in items if i['capability'] == 'own_posts'}
    own_ids.update(i['data']['url'] for i in items if i['capability'] == 'own_posts' and i['data'].get('url'))
    posts = load_history(root)
    own_ids.update(r['id'] for r in posts)
    return {'people': load_relationships(root), 'priorities': priorities(root),
            'posts': posts, 'comments': load_history(root, 'comments'), 'own_post_ids': own_ids}


def suggested_draft(item, category):
    """No invented first-person facts: questions stay questions until agent review."""
    note = item['assessment'].get('note')
    if category == 'RESPOND':
        draft = '{{Answer the specific question using your actual evidence}}'
    elif category == 'COMMENT':
        draft = '{{Add the substantive contribution identified in your notes}}'
    else:
        draft = None
    return {'text': draft, 'status': 'DRAFT — NEEDS CONTEXT AND CLAIM REVIEW' if draft else 'ADVICE ONLY',
            'instruction': 'Apply li-reply/comment, voice, factuality and quality logic before presenting final copy',
            'context_note': note}


def brief(root, now=None, limit=5, include_private=False):
    now = now or datetime.now(timezone.utc)
    if not 0 <= limit <= 5:
        raise ValueError('brief limit must be between 0 and 5')
    items = active_items(root)
    context = build_context(root, items)
    actions, stale = [], []
    for item in items:
        if not include_private and (item['kind'] == 'message' or item['provenance']['visibility'] == 'private'):
            continue
        classified = classify(item, context, now)
        if classified['freshness']['state'] != 'fresh':
            stale.append({'id': item['id'], 'kind': item['kind'], 'state': classified['freshness']['state']})
        if not classified['actionable']:
            continue
        person = context['people'].get(item['data'].get('author_id'))
        actions.append({'id': item['id'], 'kind': item['kind'], 'category': classified['category'],
                        'score': classified['score'], 'rationale': classified['reason'], 'label': 'INFERRED',
                        'signal': item['data'].get('text'), 'source': item['provenance'],
                        'relationship': {'name': person['name'], 'type': person['relationship_type'],
                                         'last_meaningful_interaction': person['last_meaningful_interaction']} if person else None,
                        'freshness': classified['freshness'], 'draft': suggested_draft(item, classified['category'])})
    # Only explicit pending obligations, never inferred from elapsed time alone.
    for person in context['people'].values():
        due = person['follow_up_due']
        if person['owes_reply'] is not True or (due and parse_time(due, date_allowed=True) > now):
            continue
        prov = person['provenance']
        age = (now - parse_time(prov['retrieved_at'])).total_seconds()
        if age < 0 or age > 14 * 86400 or (person['last_meaningful_interaction'] and parse_time(person['last_meaningful_interaction'], date_allowed=True) > now):
            stale.append({'id': person['id'], 'kind': 'relationship', 'state': 'invalid-future' if age < 0 else 'stale'})
            continue
        actions.append({'id': person['id'], 'kind': 'relationship', 'category': 'FOLLOW UP', 'score': 70,
                        'rationale': ['Explicitly recorded pending reply/follow-up; check whether it is still owed'],
                        'label': 'INFERRED', 'signal': person['why_they_matter'], 'source': prov,
                        'relationship': {'name': person['name'], 'type': person['relationship_type'],
                                         'last_meaningful_interaction': person['last_meaningful_interaction']},
                        'draft': {'text': None, 'status': 'ADVICE ONLY', 'instruction': 'Use li-dm only with a substantive reason and supplied conversation context'}})
    # Normalized external context can inform review; it never implies a reply,
    # publication obligation, verified claim or automatic action.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'li-research/scripts'))
    from evidence import load as load_research, signals as research_signals
    research_gaps = []
    try:
        external = research_signals(load_research(root),
                                    context['priorities']['topics'] + context['priorities']['projects'],
                                    max_age_hours=24, now=now)
    except (OSError, ValueError, KeyError, TypeError):
        external = []
        research_gaps.append('Research cache unavailable or invalid; no external evidence used')
    actions.sort(key=lambda a: (-a['score'], a['id']))
    selected = actions[:limit]
    return {'as_of': timestamp(now), 'actions': selected, 'suppressed_candidates': max(0, len(actions) - limit),
            'stale_or_undated': stale, 'read_status': status(root, now),
            'research_signals': external, 'research_gaps': research_gaps,
            'message': 'No supported material action found in available data; unavailable/stale sources may hide activity' if not selected else 'Review these priorities; all external actions remain manual',
            'action_boundary': 'No autonomous LinkedIn posting, commenting, liking, messaging, connecting or profile editing is implemented.'}


def weekly(root, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    items = active_items(root)
    context = build_context(root, items)
    # Only canonical confirmed publication history. Imports do not silently become it.
    published = [r for r in context['posts'] if cutoff.date() <= parse_time(r['date'], date_allowed=True).date() <= now.date()]
    comments = [r for r in context['comments'] if cutoff.date() <= parse_time(r['date'], date_allowed=True).date() <= now.date()]
    topics = Counter(r['topic'] for r in published)
    repeated = {topic: count for topic, count in topics.items() if count > 1}
    learning = []
    analytics = [i for i in items if i['kind'] == 'analytics']
    for r in published:
        related = [i for i in analytics if i['data']['post_id'] == r['id']]
        related.sort(key=lambda i: parse_time(i['provenance']['retrieved_at']), reverse=True)
        observations = related[0]['data'] if related else r.get('metrics', {})
        fields = ('reactions', 'comments', 'meaningful_comments', 'relevant_person_engagement', 'opportunities', 'saves')
        actual = {f: observations.get(f) for f in fields}
        learning.append({'post_id': r['id'], 'topic': r['topic'], 'observations': actual,
                         'provenance': related[0]['provenance'] if related else {'label': 'LOCAL-HISTORY'},
                         'freshness': freshness(related[0], now) if related else None,
                         'hypothesis': 'Compare strategic outcomes and comment content before selecting a theme; this observation alone does not establish a strategy'})
    return {'period': {'start': cutoff.date().isoformat(), 'end': now.date().isoformat()},
            'published_posts': len(published), 'confirmed_public_comments': len(comments),
            'observed_own_activity': [{'id': i['id'], 'timestamp': i['data'].get('timestamp'), 'provenance': i['provenance']}
                                      for i in items if i['capability'] == 'own_posts' and i['data'].get('timestamp') and
                                      cutoff <= parse_time(i['data']['timestamp'], date_allowed=True) <= now],
            'themes': dict(topics), 'repeated_topics_for_angle_review': repeated,
            'meaningful_interactions': [{'id': p['id'], 'name': p['name'], 'last_interaction': p['last_meaningful_interaction'],
                                         'provenance': p['provenance']} for p in context['people'].values()
                                        if p['last_meaningful_interaction'] and cutoff <= parse_time(p['last_meaningful_interaction'], date_allowed=True) <= now],
            'new_people': [{'id': i['id'], 'name': i['data'].get('name'), 'provenance': i['provenance']} for i in items
                           if i['kind'] == 'person' and cutoff <= parse_time(i['first_seen']) <= now],
            'performance_learning': learning, 'history_summary': summarize(root),
            'pending_and_emerging': brief(root, now),
            'limitations': 'Sparse/unknown metrics do not establish audience quality, leads or causality. Inferences are hypotheses, not facts.'}


def memory(root):
    """Read observations and confirmed publications without changing either layer."""
    records = []
    confirmed = load_history(root)
    ids = {r['id'] for r in confirmed}
    for r in confirmed:
        records.append({**r, 'origin': 'LOCAL-HISTORY', 'confirmed_publication': True,
                        'provenance': {'label': 'LOCAL-HISTORY'}})
    for item in active_items(root, include_inactive=True):
        if item['capability'] != 'own_posts' or item['id'] in ids:
            continue
        data = item['data']
        text = data.get('text') or ''
        records.append({'id': item['id'], 'date': data.get('timestamp'), 'topic': None,
                        'angle': None, 'hook': text.splitlines()[0] if text else None,
                        'body': data.get('text'), 'cta': None, 'project': data.get('project'),
                        'company': data.get('company'), 'people_mentioned': data.get('people_mentioned'),
                        'claims': data.get('claims'), 'evidence_used': data.get('evidence_used'),
                        'related_research': data.get('related_research'),
                        'origin': item['provenance']['label'], 'confirmed_publication': False,
                        'provenance': item['provenance']})
    return records


def memory_lookup(root, query):
    terms = tokens(query)
    if not terms:
        return []
    result = []
    for r in memory(root):
        values = [r.get(k) or '' for k in ('topic', 'angle', 'hook', 'body', 'project', 'company')]
        values += [v for k in ('people_mentioned', 'claims', 'evidence_used', 'related_research') for v in (r.get(k) or [])]
        if terms.issubset(tokens(' '.join(values))):
            result.append(r)
    return result


def memory_overlap(root, candidate):
    if not isinstance(candidate, dict):
        raise ValueError('candidate must be an object')
    for field in ('topic', 'angle', 'hook', 'body'):
        if field in candidate and not isinstance(candidate[field], str):
            raise ValueError(f'{field} must be a string')
    for field in ('anecdotes', 'claims'):
        if field in candidate:
            validate_value(candidate[field], 'strings')
            if candidate[field] is None:
                raise ValueError(f'{field} must be a list')
    result = []
    for r in memory(root):
        compatible = {**r, **{k: r.get(k) or '' for k in ('topic', 'angle', 'hook', 'body')},
                      'anecdotes': r.get('anecdotes') or [], 'claims': r.get('claims') or []}
        matches = duplicates(candidate, [compatible])
        if matches:
            result.append({**matches[0], 'origin': r['origin'], 'confirmed_publication': r['confirmed_publication'],
                           'provenance': r['provenance']})
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.linkedin-agent')
    ap.add_argument('--now', help='timezone-aware ISO timestamp for reproducible review')
    sub = ap.add_subparsers(dest='command', required=True)
    daily = sub.add_parser('brief')
    daily.add_argument('--limit', type=int, default=5)
    daily.add_argument('--include-private', action='store_true')
    sub.add_parser('weekly')
    sub.add_parser('memory')
    sub.add_parser('lookup').add_argument('query')
    sub.add_parser('overlap').add_argument('candidate', help='JSON candidate file')
    args = ap.parse_args()
    try:
        now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        if args.command == 'brief':
            result = brief(args.root, now, args.limit, args.include_private)
        elif args.command == 'weekly':
            result = weekly(args.root, now)
        elif args.command == 'memory':
            result = memory(args.root)
        elif args.command == 'lookup':
            result = memory_lookup(args.root, args.query)
        else:
            result = memory_overlap(args.root, json.loads(read_text(args.candidate)))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    main()
