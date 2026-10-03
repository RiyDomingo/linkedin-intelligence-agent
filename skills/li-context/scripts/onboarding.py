#!/usr/bin/env python3
"""Resumable local onboarding lifecycle. No network, passwords or account actions."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sys
import professional_memory as memory
from context import safe_path, read_text, initialize as initialize_templates

PHASES = ('WELCOME', 'CONNECTING', 'ACQUIRING_CONTEXT', 'ENRICHMENT', 'REVIEW',
          'STRATEGY', 'FIRST_VALUE', 'COMPLETE')
STATUSES = ('not_started', 'in_progress', 'partial', 'blocked', 'complete')
LINKEDIN = ('undecided', 'account', 'without_linkedin')
ERRORS = ('NOT_INSTALLED', 'DISABLED', 'NOT_AUTHENTICATED', 'AUTH_CHALLENGE',
          'RATE_LIMIT_OR_RESTRICTION', 'PARTIAL_READ', 'UPSTREAM_TIMEOUT',
          'UPSTREAM_ERROR', 'MALFORMED_RESPONSE', 'SOURCE_UNAVAILABLE')
PROFILE_FIELDS = ('person', 'current_roles', 'experience', 'education', 'qualifications',
                  'skills', 'expertise', 'interests', 'projects', 'positioning',
                  'content_topics', 'voice_patterns')
WORKFLOWS = (
    {'id': 'brief', 'label': 'Brief me', 'purpose': 'What deserves my attention?', 'skills': ['li-brief', 'li-read']},
    {'id': 'create', 'label': 'Create', 'purpose': 'Find something worth saying.', 'skills': ['li-ideas', 'li-post', 'li-research']},
    {'id': 'discover', 'label': 'Discover', 'purpose': 'Find people I should know.', 'skills': ['li-read', 'li-research']},
    {'id': 'engage', 'label': 'Engage', 'purpose': 'Where can I contribute?', 'skills': ['li-engagement', 'li-comment', 'li-reply', 'li-dm']},
    {'id': 'review_plan', 'label': 'Review & Plan', 'purpose': 'Learn what works and plan next.', 'skills': ['li-weekly', 'li-plan', 'li-audit']},
)
WORKFLOW_FIELDS = {
    'brief': ('current_roles', 'interests', 'projects', 'content_topics'),
    'create': ('voice_patterns', 'expertise', 'projects', 'content_topics', 'claims'),
    'discover': ('expertise', 'interests', 'projects', 'positioning'),
    'engage': ('interests', 'relationships', 'voice_patterns', 'constraints'),
    'review_plan': ('projects', 'content_topics', 'positioning', 'claims'),
}
CHECKPOINTS = ('context_built', 'enrichment_reviewed', 'professional_context_reviewed',
               'goals_configured', 'audiences_configured', 'first_brief_completed')


def _fresh(user_id=None):
    return {'version': 1, 'user_id': user_id, 'status': 'not_started', 'phase': 'WELCOME',
            'started_at': None, 'updated_at': None, 'linkedin_step': 'undecided',
            **{key: False for key in CHECKPOINTS}, 'review_token': None,
            'brief_receipt': None, 'blocked_reason': None}


def _read(root):
    p = safe_path(root, 'onboarding/state.json')
    if not p.exists():
        return _fresh()
    if not p.is_file() or p.stat().st_size > 64_000:
        raise ValueError('Bounded onboarding state required')
    data = json.loads(read_text(p))
    memory.guard(data)
    if not isinstance(data, dict) or set(data) != set(_fresh()):
        raise ValueError('Invalid onboarding schema')
    if type(data['version']) is not int or data['version'] != 1:
        raise ValueError('Unsupported onboarding version')
    if data['phase'] not in PHASES or data['status'] not in STATUSES or data['linkedin_step'] not in LINKEDIN:
        raise ValueError('Invalid lifecycle state')
    if any(type(data[key]) is not bool for key in CHECKPOINTS):
        raise ValueError('Explicit checkpoints required')
    if not isinstance(data['user_id'], str) or not re.fullmatch(r'usr_[0-9a-f]{32}', data['user_id']):
        raise ValueError('User-scoped onboarding required')
    identity = memory._read(root)
    if not identity or identity['user_id'] != data['user_id']:
        raise ValueError('Onboarding identity differs from professional memory')
    for key in ('started_at', 'updated_at'):
        memory.timestamp(data[key])
    for key in ('review_token', 'brief_receipt'):
        if data[key] is not None and (not isinstance(data[key], str) or not re.fullmatch('[0-9a-f]{64}', data[key])):
            raise ValueError('Invalid lifecycle receipt')
    if data['blocked_reason'] is not None and data['blocked_reason'] not in ERRORS:
        raise ValueError('Invalid block category')
    if (data['status'] == 'blocked') != (data['blocked_reason'] is not None):
        raise ValueError('Invalid blocked state')
    index = PHASES.index(data['phase'])
    required = []
    if index >= PHASES.index('REVIEW'):
        required = ['context_built', 'enrichment_reviewed']
    if index >= PHASES.index('STRATEGY'):
        required += ['professional_context_reviewed']
    if index >= PHASES.index('FIRST_VALUE'):
        required += ['goals_configured', 'audiences_configured']
    if index == PHASES.index('COMPLETE'):
        required += ['first_brief_completed']
    if any(not data[key] for key in required):
        raise ValueError('Impossible onboarding checkpoints')
    if (data['phase'] == 'COMPLETE') != (data['status'] == 'complete'):
        raise ValueError('Invalid completion state')
    if data['professional_context_reviewed'] and data['review_token'] is None:
        raise ValueError('Profile review receipt required')
    if data['first_brief_completed'] and data['brief_receipt'] is None:
        raise ValueError('First brief receipt required')
    if data['phase'] in ('CONNECTING', 'ACQUIRING_CONTEXT') and data['linkedin_step'] != 'account':
        raise ValueError('Account phase requires account choice')
    if data['status'] == 'not_started':
        raise ValueError('Persisted lifecycle must have started')
    if data['status'] == 'complete':
        saved = _local_json(root, 'onboarding/first-brief.json')
        if (saved.get('user_id') != data['user_id'] or saved.get('receipt') != data['brief_receipt']
                or memory.digest(json.dumps(saved.get('brief'), sort_keys=True)) != data['brief_receipt']):
            raise ValueError('Completed onboarding requires the generated brief receipt')
    return data


def _local_json(root, relative, default=None):
    p = safe_path(root, relative)
    if not p.exists() and default is not None:
        return default
    if not p.is_file() or p.stat().st_size > memory.MAX_BYTES:
        raise ValueError('Bounded local lifecycle data required')
    value = json.loads(read_text(p))
    if not isinstance(value, dict):
        raise ValueError('Local lifecycle object required')
    memory.guard(value)
    return value


@contextmanager
def _transaction(root):
    p = safe_path(root, 'onboarding/lock')
    for q in reversed([q for q in (p.parent, *p.parent.parents) if not q.exists()]):
        q.mkdir(mode=0o700)
    import fcntl
    fd = os.open(p, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data = _read(root)
        yield data
        data['updated_at'] = memory.now()
        memory._write(root, 'onboarding/state.json', data)


def _need(data, *phases):
    if data['phase'] not in phases or data['status'] == 'blocked':
        raise ValueError('Lifecycle step is not available; resume or explicitly reopen')


def start(root):
    # Passive detection never writes; starting is an explicit local setup operation.
    existing = _read(root)
    if existing['status'] != 'not_started':
        return status(root)
    initialize_templates(root)
    user = memory.initialize(root)['user_id']
    with _transaction(root) as data:
        if data['status'] == 'not_started':
            data.update(_fresh(user))
            data.update(status='in_progress', started_at=memory.now())
    return status(root)


def _profile(root):
    snapshot = memory.summary(root, PROFILE_FIELDS, include_evidence=True)
    sections = []
    for group in snapshot['context']:
        item = group['preferred']
        if item is None:
            continue
        label = 'Confirmed' if item['label'] == 'USER_CONFIRMED' else 'Inferred' if item['label'] == 'INFERRED' else 'Observed'
        sections.append({'field': group['field'], 'key': group['key'], 'value': item['value'],
                         'status': label, 'label': item['label'], 'freshness': item['freshness'],
                         'conflict': group['conflict'], 'evidence_id': item['id'],
                         'sources': [{'id': e['source_id'], 'label': e['label'], 'value': e['value']}
                                     for e in group['evidence']]})
    curated = snapshot.get('curated_context', [])
    token = memory.digest(json.dumps({'sections': sections, 'curated': curated}, sort_keys=True))
    return {'heading': "Here's what I understand about you", 'sections': sections,
            'curated_context': curated, 'review_token': token,
            'review_is_not_blanket_factual_verification': True}


def preview(root):
    return _profile(root)


def _known(root, fields):
    snapshot = memory.summary(root, fields)
    return [g['preferred'] for g in snapshot['context']
            if g['preferred'] and g['preferred']['freshness'] == 'CURRENT'
            and g['preferred']['temporally_current']]


def strategy_context(root):
    return memory.get_strategic_context(root)


def question_policy(root):
    known = _known(root, list(PROFILE_FIELDS) + ['audiences', 'goals'])
    conflicts = {g['field'] for g in memory.summary(root, include_evidence=True)['context']
                 if g['conflict'] and g['preferred'] and g['preferred']['label'] != 'USER_CONFIRMED'}
    strategic = strategy_context(root)
    return {'known_fields': sorted({e['field'] for e in known}),
            'material_conflicts': sorted(conflicts),
            'strategic_questions': [field for field in ('goals', 'audiences') if not strategic[field]],
            'rule': 'Ask only for missing essential context, material conflicts, stale unrefreshable information or important confirmation.'}


def readiness(root):
    account = _local_json(root, 'account/status.json', {})
    enabled = _local_json(root, 'account/control.json', {}).get('enabled') is True
    enabled = enabled and os.environ.get('LINKEDIN_ACCOUNT_CONNECTOR_ENABLED', 'true').lower() != 'false'
    if not isinstance(account.get('capabilities', {}), dict):
        raise ValueError('Invalid capability collection')
    capabilities = {}
    for cap in ('profile', 'own_posts', 'feed'):
        record = account.get('capabilities', {}).get(cap, {})
        if not isinstance(record, dict):
            raise ValueError('Invalid account capability')
        capabilities[cap] = {'state': record.get('state', 'UNVERIFIED'),
                             'last_success': record.get('last_success'),
                             'last_attempt': record.get('last_attempt'),
                             'sections': record.get('sections', {}),
                             'status_is_last_observation': True}
    active = [s for s in memory.sources(root) if s['active']]
    return {'scope': 'ONE_USER_PER_PROJECT', 'linkedin_enabled': enabled,
            'authentication': account.get('authentication', 'UNVERIFIED'),
            'live_capabilities': capabilities, 'inbox': 'NOT_ENABLED',
            'sources': [{'id': s['id'], 'kind': s['kind'], 'normalized': s['current_version'] is not None}
                        for s in active], 'context_fields': question_policy(root)['known_fields'],
            'strategic_context': strategy_context(root),
            'account_actions': 'HUMAN_EXECUTED', 'memory_is_local_model_inference_may_be_remote': True}


def status(root):
    data = _read(root)
    question = question_policy(root)
    return {**data, 'onboarding_required': data['status'] != 'complete',
            'next_step': data['phase'], 'questions': question,
            'workflows': list(WORKFLOWS) if data['status'] == 'complete' else []}


def workflow_context(root, workflow):
    if workflow not in WORKFLOW_FIELDS:
        raise ValueError('One of the five operational workflows required')
    data = _read(root)
    return {'workflow': next(w for w in WORKFLOWS if w['id'] == workflow),
            'onboarding_complete': data['status'] == 'complete',
            'professional_context': memory.summary(root, WORKFLOW_FIELDS[workflow]),
            'strategic_context': strategy_context(root),
            'instruction': 'Apply confirmed goals/audiences to relevance; assess only task-relevant freshness. No account/network access is performed by this handoff.'}


def choose_connection(root, choice):
    if choice not in ('account', 'without_linkedin'):
        raise ValueError('Explicit connection choice required')
    with _transaction(root) as data:
        _need(data, 'WELCOME', 'CONNECTING', 'ACQUIRING_CONTEXT')
        data['linkedin_step'] = choice
        data['phase'] = 'CONNECTING' if choice == 'account' else 'ENRICHMENT'
        data['status'] = 'in_progress'
    return status(root)


def begin_learning(root):
    with _transaction(root) as data:
        _need(data, 'CONNECTING', 'ACQUIRING_CONTEXT')
        if data['linkedin_step'] != 'account':
            raise ValueError('Account onboarding choice required')
        data['phase'] = 'ACQUIRING_CONTEXT'
    return status(root)


def learned(root):
    # Account retention already synchronizes memory. Sync is idempotent, offline.
    data = _read(root)
    _need(data, 'ACQUIRING_CONTEXT')
    memory.sync_account(root)
    view = _profile(root)
    with _transaction(root) as data:
        _need(data, 'ACQUIRING_CONTEXT')
        data['context_built'] = bool(view['sections'] or view['curated_context'])
        data['phase'] = 'ENRICHMENT'
        data['status'] = 'partial'
    return {'onboarding': status(root), 'capabilities': readiness(root)}


def enrichment_done(root):
    # Optional failures stay in the memory source registry; no clearing or restart.
    with _transaction(root) as data:
        _need(data, 'ENRICHMENT')
        view = _profile(root)
        if not (view['sections'] or view['curated_context']):
            raise ValueError('Add at least one meaningful professional source before review')
        data.update(context_built=True, enrichment_reviewed=True, phase='REVIEW', status='partial')
    return preview(root)


def confirm_profile(root, token, confirmed=False):
    if confirmed is not True:
        raise ValueError('Explicit user review required')
    with _transaction(root) as data:
        _need(data, 'REVIEW')
        view = _profile(root)
        if not (view['sections'] or view['curated_context']):
            raise ValueError('Meaningful professional context required before confirmation')
        if token != view['review_token']:
            raise ValueError('Context changed; show and review the current preview')
        data.update(professional_context_reviewed=True, review_token=token, phase='STRATEGY')
        existing = strategy_context(root)
        data['goals_configured'] = bool(existing['goals'])
        data['audiences_configured'] = bool(existing['audiences'])
        if all(existing.values()):
            data['phase'] = 'FIRST_VALUE'
    return status(root)


def set_strategy(root, field, values, confirmed=False):
    if confirmed is not True or field not in ('goals', 'audiences'):
        raise ValueError('User-confirmed goals or audiences required')
    if not isinstance(values, list) or not 1 <= len(values) <= 10 or any(not isinstance(v, str) or not v.strip() or len(v) > 250 for v in values):
        raise ValueError('Select 1–10 bounded strategic choices')
    memory.guard(values)
    values = list(dict.fromkeys(v.strip() for v in values))
    with _transaction(root) as data:
        _need(data, 'STRATEGY', 'FIRST_VALUE', 'COMPLETE')
        memory.correct(root, field, 'primary', '; '.join(values), kind='POSITIONING')
        data[field + '_configured'] = True
        if data['phase'] == 'STRATEGY' and data['goals_configured'] and data['audiences_configured']:
            data['phase'] = 'FIRST_VALUE'
        # Changed strategy before delivery invalidates the saved brief.
        if data['phase'] != 'COMPLETE':
            data['brief_receipt'] = None
    return status(root)


def audience_proposals(root):
    # Codex reasons from this evidence, not a universal prefilled checkbox list.
    return {'basis': memory.summary(root, ['current_roles', 'expertise', 'projects', 'interests', 'positioning']),
            'confirmed_audiences': strategy_context(root)['audiences'],
            'instruction': 'Propose a short audience list grounded in this evidence. Label suggestions; never persist without user selection.'}


def _brief_input(root):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'li-read/scripts'))
    from intelligence import brief
    return brief(root, limit=5)


def run_first_brief(root):
    with _transaction(root) as data:
        _need(data, 'FIRST_VALUE')
        if data['review_token'] != _profile(root)['review_token']:
            data.update(phase='REVIEW', professional_context_reviewed=False, review_token=None, brief_receipt=None)
            result = {'review_required': True, 'preview': _profile(root)}
        else:
            strategic = strategy_context(root)
            if not all(strategic.values()):
                raise ValueError('Current confirmed strategic context required')
            result = _brief_input(root)
            receipt = memory.digest(json.dumps(result, sort_keys=True))
            memory._write(root, 'onboarding/first-brief.json', {'receipt': receipt, 'user_id': data['user_id'], 'brief': result})
            data['brief_receipt'] = receipt
            data['status'] = 'partial'
            result = {'receipt': receipt, 'brief': result, 'delivery_required': True}
    return result


def deliver(root, receipt, displayed=False):
    if displayed is not True:
        raise ValueError('Brief must be displayed to the user before completion')
    with _transaction(root) as data:
        _need(data, 'FIRST_VALUE')
        if not data['brief_receipt'] or receipt != data['brief_receipt']:
            raise ValueError('Actual generated first brief required')
        saved = _local_json(root, 'onboarding/first-brief.json')
        if saved.get('user_id') != data['user_id'] or saved.get('receipt') != receipt or memory.digest(json.dumps(saved.get('brief'), sort_keys=True)) != receipt:
            raise ValueError('First brief receipt differs')
        if data['review_token'] != _profile(root)['review_token'] or saved['brief'].get('strategic_context') != strategy_context(root):
            raise ValueError('Context changed; regenerate/review before delivery')
        data.update(first_brief_completed=True, phase='COMPLETE', status='complete')
    return {'onboarding': status(root), 'workflows': list(WORKFLOWS)}


def block(root, reason):
    if reason not in ERRORS:
        raise ValueError('Allowlisted failure category required')
    with _transaction(root) as data:
        _need(data, *PHASES[:-1])
        data.update(status='blocked', blocked_reason=reason)
    return status(root)


def resume(root, without_linkedin=False):
    with _transaction(root) as data:
        if data['status'] == 'complete':
            return status(root)
        if data['status'] == 'not_started':
            raise ValueError('Start onboarding first')
        data.update(status='partial', blocked_reason=None)
        if data['phase'] == 'STRATEGY':
            existing = strategy_context(root)
            data['goals_configured'] = bool(existing['goals'])
            data['audiences_configured'] = bool(existing['audiences'])
            if all(existing.values()):
                data['phase'] = 'FIRST_VALUE'
        if without_linkedin:
            if data['phase'] not in ('WELCOME', 'CONNECTING', 'ACQUIRING_CONTEXT'):
                raise ValueError('Connection decision already finished')
            data.update(linkedin_step='without_linkedin', phase='ENRICHMENT')
    return status(root)


def reset(root, confirmed=False):
    if confirmed is not True:
        return {'preview': 'rerun onboarding review', 'memory_deleted': False, 'authentication_deleted': False, 'requires_confirmation': True}
    with _transaction(root) as data:
        if data['status'] == 'not_started':
            raise ValueError('Start onboarding first')
        data.update(status='partial', blocked_reason=None, phase='REVIEW' if _profile(root)['sections'] or _profile(root)['curated_context'] else 'ENRICHMENT',
                    context_built=bool(_profile(root)['sections'] or _profile(root)['curated_context']),
                    enrichment_reviewed=True, professional_context_reviewed=False, review_token=None,
                    first_brief_completed=False, brief_receipt=None)
        # Goals/audiences stay in memory and are reused after review.
    return status(root)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.linkedin-agent')
    sub = ap.add_subparsers(dest='command', required=True)
    for name in ('status', 'start', 'begin-learning', 'learned', 'enrichment-done', 'preview',
                 'readiness', 'questions', 'audience-proposals', 'run-brief', 'strategy'):
        sub.add_parser(name)
    p = sub.add_parser('workflow'); p.add_argument('workflow', choices=list(WORKFLOW_FIELDS))
    p = sub.add_parser('choose'); p.add_argument('choice', choices=LINKEDIN[1:])
    p = sub.add_parser('confirm-profile'); p.add_argument('token'); p.add_argument('--confirmed', action='store_true')
    p = sub.add_parser('set-strategy'); p.add_argument('field', choices=['goals', 'audiences']); p.add_argument('values', nargs='+'); p.add_argument('--confirmed', action='store_true')
    p = sub.add_parser('deliver'); p.add_argument('receipt'); p.add_argument('--displayed', action='store_true')
    p = sub.add_parser('block'); p.add_argument('reason', choices=ERRORS)
    p = sub.add_parser('resume'); p.add_argument('--without-linkedin', action='store_true')
    p = sub.add_parser('reset'); p.add_argument('--confirmed', action='store_true')
    a = ap.parse_args()
    try:
        simple = {'status': status, 'start': start, 'begin-learning': begin_learning, 'learned': learned,
                  'enrichment-done': enrichment_done, 'preview': preview, 'readiness': readiness,
                  'questions': question_policy, 'audience-proposals': audience_proposals,
                  'run-brief': run_first_brief, 'strategy': strategy_context}
        if a.command in simple: result = simple[a.command](a.root)
        elif a.command == 'workflow': result = workflow_context(a.root, a.workflow)
        elif a.command == 'choose': result = choose_connection(a.root, a.choice)
        elif a.command == 'confirm-profile': result = confirm_profile(a.root, a.token, a.confirmed)
        elif a.command == 'set-strategy': result = set_strategy(a.root, a.field, a.values, a.confirmed)
        elif a.command == 'deliver': result = deliver(a.root, a.receipt, a.displayed)
        elif a.command == 'block': result = block(a.root, a.reason)
        elif a.command == 'resume': result = resume(a.root, a.without_linkedin)
        else: result = reset(a.root, a.confirmed)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        ap.exit(2, 'Onboarding: invalid/unavailable local input or lifecycle transition; private diagnostics suppressed\n')


if __name__ == '__main__':
    main()
