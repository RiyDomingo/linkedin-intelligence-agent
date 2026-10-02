#!/usr/bin/env python3
"""Local profile initialization and content memory. Standard library only."""
import argparse
from collections import Counter
from datetime import date
import csv
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid

TEMPLATES = Path(__file__).resolve().parent.parent / 'templates'
TEXT_FIELDS = ('topic', 'angle', 'hook', 'body', 'cta')
LIST_FIELDS = ('tags', 'source_material', 'anecdotes', 'claims', 'people_mentioned', 'evidence_used', 'related_research')


def safe_path(root, relative):
    """Reject traversal and symlink components in a caller-selected data area."""
    root = Path(root).absolute()
    if root.is_symlink():
        raise ValueError(f'symlink refused: {root}')
    # Canonicalize caller-selected parent (macOS /var and /tmp are aliases).
    root = root.parent.resolve() / root.name
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('relative data path required')
    target = root / rel
    for part in (target, *target.parents):
        if part.is_symlink():
            raise ValueError(f'symlink refused: {part}')
    return target


def read_text(path):
    with Path(path).open(encoding='utf-8') as fh:
        return fh.read()


def initialize(root):
    safe_path(root, '.')
    paths = [p for p in TEMPLATES.rglob('*') if p.is_file()]
    # Preflight all paths before any write; never replace existing profile data.
    targets = [(p, safe_path(root, p.relative_to(TEMPLATES))) for p in paths]
    safe_path(root, '.').mkdir(parents=True, exist_ok=True, mode=0o700)
    created = []
    for source, target in targets:
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                fh.write(read_text(source))
            created.append(str(target.relative_to(Path(root).absolute().parent.resolve() / Path(root).absolute().name)))
        except FileExistsError:
            if not target.is_file():
                raise ValueError(f'not a regular file: {target}')
    return created


def validate_record(record):
    if not isinstance(record, dict):
        raise ValueError('history entry must be an object')
    for key in TEXT_FIELDS:
        if not isinstance(record.get(key), str):
            raise ValueError(f'{key} must be a string')
    for key in ('project', 'company', 'author_id', 'parent_post'):
        if key in record and record[key] is not None and not isinstance(record[key], str):
            raise ValueError(f'{key} must be a string or null')
    for key in LIST_FIELDS:
        if not isinstance(record.get(key, []), list) or any(not isinstance(x, str) for x in record.get(key, [])):
            raise ValueError(f'{key} must be a list of strings')
    if not isinstance(record.get('id'), str) or not record['id']:
        raise ValueError('id must be a nonempty string')
    if not isinstance(record.get('date'), str):
        raise ValueError('date must be ISO YYYY-MM-DD')
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', record['date']):
        raise ValueError('date must be ISO YYYY-MM-DD')
    date.fromisoformat(record['date'])
    metrics = record.get('metrics', {})
    if not isinstance(metrics, dict):
        raise ValueError('metrics must be an object')
    for key, value in metrics.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError(f'metric {key} must be finite and nonnegative')
    return record


def load_history(root, kind='posts'):
    if kind not in ('posts', 'comments'):
        raise ValueError('history kind must be posts or comments')
    path = safe_path(root, f'history/{kind}.jsonl')
    if not path.exists():
        return []
    records, ids = [], set()
    for line_no, line in enumerate(read_text(path).splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = validate_record(json.loads(line))
            if record['id'] in ids:
                raise ValueError('duplicate id')
            ids.add(record['id'])
            records.append(record)
        except (ValueError, TypeError) as exc:
            raise ValueError(f'{kind}.jsonl line {line_no}: {exc}') from exc
    return records


def append_history(root, record, published=False, kind='posts'):
    if not published:
        raise ValueError('confirm actual publication with --published; draft approval is insufficient')
    if kind not in ('posts', 'comments'):
        raise ValueError('history kind must be posts or comments')
    record = dict(record)
    record.setdefault('id', str(uuid.uuid4()))
    # Require the actual date; do not guess from execution host time.
    for key in ('tags', 'source_material', 'anecdotes', 'claims'):
        record.setdefault(key, [])
    record.setdefault('metrics', {})
    validate_record(record)
    path = safe_path(root, f'history/{kind}.jsonl')
    safe_path(root, '.').mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Serialize writers on supported Unix systems; no shared database required.
    try:
        import fcntl
    except ImportError:
        fcntl = None
    flags = os.O_RDWR | os.O_CREAT | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'a+', encoding='utf-8') as fh:
        if fcntl:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        existing = load_history(root, kind)
        if any(r['id'] == record['id'] for r in existing):
            raise ValueError('duplicate id')
        # A valid imported final line need not have a trailing newline.
        fh.seek(0)
        content = fh.read()
        if content and not content.endswith('\n'):
            fh.write('\n')
        fh.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
        fh.flush()
    return record


def tokens(text):
    return set(re.findall(r'[^\W_]+', text.casefold()))


def similarity(a, b):
    a, b = tokens(a), tokens(b)
    return len(a & b) / len(a | b) if a and b else 0.0


def duplicates(candidate, history):
    matches = []
    for record in history:
        reasons = []
        for field in ('topic', 'angle', 'hook', 'body'):
            score = similarity(candidate.get(field, ''), record.get(field, ''))
            if score >= (0.6 if field == 'body' else 0.75):
                reasons.append({'field': field, 'similarity': round(score, 3)})
        for field in ('anecdotes', 'claims'):
            for new in candidate.get(field, []):
                if any(similarity(new, old) >= 0.75 for old in record.get(field, [])):
                    reasons.append({'field': field, 'text': new})
        if reasons:
            matches.append({'id': record['id'], 'date': record['date'], 'reasons': reasons,
                            'decision': 'Review angle and evidence; similarity alone does not reject a topic'})
    return matches


def performance_rows(root):
    path = safe_path(root, 'analytics/performance.csv')
    if not path.exists():
        return {}
    with path.open(encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        required = {'id', 'impressions', 'reactions', 'comments', 'reposts'}
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError('performance.csv has duplicate headers')
        if not required.issubset(headers):
            raise ValueError('performance.csv requires id, impressions, reactions, comments, reposts')
        result = {}
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'performance.csv line {line}: incorrect column count')
            if not row.get('id') or row['id'] in result:
                raise ValueError(f'performance.csv line {line}: missing or duplicate id')
            metrics = {}
            for key in required - {'id'}:
                if row.get(key, '') == '':
                    continue
                try:
                    value = float(row[key])
                except (ValueError, TypeError) as exc:
                    raise ValueError(f'performance.csv line {line}: invalid {key}') from exc
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f'performance.csv line {line}: invalid {key}')
                metrics[key] = value
            result[row['id']] = metrics
        return result


def summarize(root):
    history = load_history(root)
    performance = performance_rows(root)
    topics_path = safe_path(root, 'history/topics.json')
    desired = json.loads(read_text(topics_path)) if topics_path.exists() else {'themes': []}
    if not isinstance(desired, dict) or not isinstance(desired.get('themes'), list) or any(not isinstance(t, str) for t in desired['themes']):
        raise ValueError('topics.json requires a themes list of strings')
    counts = Counter(r['topic'] for r in history)
    ranked = []
    for r in history:
        m = {**r.get('metrics', {}), **performance.get(r['id'], {})}
        if m.get('impressions', 0) > 0 and all(k in m for k in ('reactions', 'comments', 'reposts')):
            ranked.append({'id': r['id'], 'topic': r['topic'], 'angle': r['angle'],
                           'engagement_rate': sum(m[k] for k in ('reactions', 'comments', 'reposts')) / m['impressions']})
    return {'posts': len(history), 'topic_counts': dict(counts),
            'project_counts': dict(Counter(r['project'] for r in history if r.get('project'))),
            'company_counts': dict(Counter(r['company'] for r in history if r.get('company'))),
            'people_counts': dict(Counter(person for r in history for person in r.get('people_mentioned', []))),
            'successful_examples': sorted(ranked, key=lambda x: (-x['engagement_rate'], x['id'])),
            'neglected_themes': [t for t in desired['themes'] if not any(similarity(t, old) >= .75 for old in counts)],
            'note': 'Rates are descriptive, not causal; unavailable metrics are not zero'}


def profile_status(root):
    paths = [p.relative_to(TEMPLATES) for p in TEMPLATES.rglob('*') if p.is_file()]
    missing, unfilled = [], []
    for rel in sorted(paths):
        path = safe_path(root, rel)
        if not path.exists():
            missing.append(str(rel))
        elif path.suffix == '.md' and '{{' in read_text(path):
            unfilled.append(str(rel))
    # Validate existing structured resources; report corrupt data, never silently skip it.
    load_history(root)
    load_history(root, 'comments')
    summarize(root)
    return {'missing': missing, 'unfilled': unfilled,
            'status': 'missing' if len(missing) == len(paths) else 'partial' if missing or unfilled else 'complete'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.linkedin-agent', help='explicit project-local data directory')
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('status')
    sub.add_parser('load').add_argument('--kind', choices=['posts', 'comments'], default='posts')
    sub.add_parser('summary')
    lookup = sub.add_parser('lookup')
    lookup.add_argument('query')
    lookup.add_argument('--kind', choices=['posts', 'comments'], default='posts')
    append = sub.add_parser('append')
    append.add_argument('record', help='JSON file with confirmed published content')
    append.add_argument('--published', action='store_true')
    append.add_argument('--kind', choices=['posts', 'comments'], default='posts')
    sub.add_parser('check').add_argument('candidate', help='JSON file; partial text fields allowed')
    args = ap.parse_args()
    try:
        if args.command == 'init':
            result = {'created': initialize(args.root)}
        elif args.command == 'status':
            result = profile_status(args.root)
        elif args.command == 'load':
            result = load_history(args.root, args.kind)
        elif args.command == 'summary':
            result = summarize(args.root)
        elif args.command == 'lookup':
            terms = tokens(args.query)
            result = [r for r in load_history(args.root, args.kind) if terms and terms.issubset(tokens(' '.join(
                [r[k] for k in TEXT_FIELDS] + [r.get(k) or '' for k in ('project', 'company', 'author_id')] +
                [value for k in LIST_FIELDS for value in r.get(k, [])])))]
        else:
            record = json.loads(read_text(args.record if args.command == 'append' else args.candidate))
            if not isinstance(record, dict):
                raise ValueError('record must be an object')
            if args.command == 'append':
                result = append_history(args.root, record, args.published, args.kind)
            else:
                for key in TEXT_FIELDS:
                    if key in record and not isinstance(record[key], str):
                        raise ValueError(f'{key} must be a string')
                for key in ('anecdotes', 'claims'):
                    if key in record and (not isinstance(record[key], list) or any(not isinstance(x, str) for x in record[key])):
                        raise ValueError(f'{key} must be a list of strings')
                result = duplicates(record, load_history(args.root))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    main()
