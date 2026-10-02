"""Safe fixture compositions for the release gate; no account or model calls."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for skill in ('li-read', 'li-context', 'li-research', 'li-human'):
    sys.path.insert(0, str(ROOT / 'skills' / skill / 'scripts'))
from read_layer import ingest, load_cache
from intelligence import brief, weekly, memory_lookup
from context import append_history
from orchestrator import Provider, execute
from evidence import assess, signals, load
from humanize import humanize, load_lexicon
from detect import analyze

NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)


class ReleaseWorkflows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        sample = json.loads((ROOT / 'skills/li-read/assets/sample-read.json').read_text())
        ingest(self.root, sample, now=NOW)

    def test_A_daily_and_D_engagement_preserve_selectivity_and_boundary(self):
        result = brief(self.root, NOW)
        self.assertEqual([(a['id'], a['category']) for a in result['actions']],
                         [('demo-c1', 'RESPOND'), ('demo-n1', 'COMMENT')])
        self.assertFalse(result['read_status']['live_account_client'])
        self.assertTrue(all(a['source'] and a['observations'] for a in result['actions']))
        self.assertFalse((self.root / 'history/posts.jsonl').exists())

    def test_B_ideation_without_evidence_does_not_manufacture_external_signals(self):
        # Idea selection is semantic skill work; deterministic evidence is empty.
        self.assertEqual(signals(load(self.root), ['review'], now=NOW), [])
        self.assertEqual(weekly(self.root, NOW)['published_posts'], 0)

    def test_C_topic_memory_keeps_observations_distinct_from_publications(self):
        found = memory_lookup(self.root, 'review')
        self.assertTrue(found)
        self.assertTrue(all(not r['confirmed_publication'] for r in found))
        append_history(self.root, {'id': 'confirmed', 'date': '2026-10-01',
            'topic': 'review', 'angle': 'evidence', 'hook': 'Review evidence.',
            'body': 'Actual fixture publication about review.', 'cta': ''}, True)
        found = memory_lookup(self.root, 'review')
        self.assertTrue(any(r['confirmed_publication'] for r in found))
        self.assertTrue(any(not r['confirmed_publication'] for r in found))

    def test_E_latest_supplied_post_comments_are_not_all_reply_obligations(self):
        items = load_cache(self.root)['items']
        own = [i for i in items if i['capability'] == 'own_posts']
        latest = max(own, key=lambda i: i['data']['timestamp'])
        comments = [i for i in items if i['kind'] == 'comment' and i['data']['parent_post'] == latest['id']]
        self.assertEqual({i['id'] for i in comments}, {'demo-c1', 'demo-c2'})
        selected = brief(self.root, NOW)['actions']
        self.assertIn('demo-c1', [a['id'] for a in selected])
        self.assertNotIn('demo-c2', [a['id'] for a in selected])

    def test_F_source_to_claim_review_to_draft_preserves_unknown_metrics(self):
        # A dated fixture stands in for a development; no live industry claim.
        provider = Provider('fixture', frozenset({'PAGE_FETCH'}), True,
            retrieve=lambda r: [{'url': r['url'], 'content': 'The fixture report describes a review checklist.',
                                 'published_at': '2026-10-02'}])
        result = execute({'operation': 'retrieve_url', 'purpose': 'CURRENT_EVENT',
            'url': 'https://example.org/report', 'public_input': True, 'max_age_hours': 24},
            [provider], self.root)
        self.assertEqual(result['evidence'][0]['assessment']['verification'], 'NEEDS_VERIFICATION')
        assessed = assess(self.root, result['evidence'][0]['id'], {
            'source_quality': 'PRIMARY', 'verification': 'SOURCE_SUPPORTED',
            'supported_claims': ['The fixture report describes a review checklist.'],
            'qualification': 'Synthetic test source; no performance claim supported.'})
        draft = assessed['assessment']['supported_claims'][0] + '\n\nMeasured improvement: {{verified metric}}.'
        cleaned, _ = humanize(draft, load_lexicon())
        self.assertIn('{{verified metric}}', cleaned)
        self.assertEqual(load(self.root)[0]['observations'][0]['provider'], 'fixture')
        self.assertIsInstance(analyze(cleaned, load_lexicon()), dict)

    def test_G_supplied_rewrite_needs_no_provider_or_research_cache(self):
        def forbidden(r):
            raise AssertionError('Rewrite attempted external retrieval')
        result = execute({'operation': 'local_only', 'purpose': 'LOCAL_WRITING', 'public_input': True},
            [Provider('fixture', frozenset({'PAGE_FETCH'}), True, retrieve=forbidden)], self.root)
        self.assertEqual(result['state'], 'NO_RETRIEVAL')
        self.assertEqual(result['attempts'], [])
        cleaned, _ = humanize('I checked the review. It missed one dependency.', load_lexicon())
        self.assertIn('one dependency', cleaned)
        self.assertFalse((self.root / 'research/cache.json').exists())

    def test_H_weekly_keeps_unconfirmed_activity_out_of_publication_totals(self):
        result = weekly(self.root, NOW)
        self.assertEqual(result['published_posts'], 0)
        self.assertTrue(result['observed_own_activity'])
        self.assertEqual(result['performance_learning'], [])
        self.assertTrue(result['pending_and_emerging']['actions'])
