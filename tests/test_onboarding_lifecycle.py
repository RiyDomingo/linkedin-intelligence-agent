"""Synthetic lifecycle acceptance and adversarial recovery, with no live account."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'skills/li-context/scripts'), str(REPO / 'skills/li-read/scripts'), str(REPO / 'tools/linkedin')]
import onboarding as o
import professional_memory as m
from account_context import retain
from gateway import Gateway
from policy import begin_task, set_enabled
from read_layer import ingest
from intelligence import brief

class SyntheticUpstream:
    def __init__(self, posts_fail=False):
        self.calls = []
        self.posts_fail = posts_fail
    async def call(self, name, arguments):
        self.calls.append((name, arguments))
        if arguments.get('sections') == 'posts' and self.posts_fail:
            raise RuntimeError('UPSTREAM_ERROR')
        return {'url': 'https://www.linkedin.com/in/alex-example/',
                'sections': {'main_profile': 'Alex Example. Research engineer.',
                             'experience': 'Engineer at Example Robotics',
                             'posts': 'I measure uncertainty before testing prototypes.'}}
    async def close(self):
        self.calls.append(('closed', {}))

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='onboarding-fixture-')
        self.parent = Path(self.temp.name)
        self.root = self.parent / '.linkedin-agent'
    def tearDown(self):
        self.temp.cleanup()
    def seed(self):
        source = m.add_bio(self.root, 'Alex Example develops robotics measurement tools.')
        m.ingest(self.root, source['source_id'], [
            {'field': 'person', 'value': 'Alex Example'},
            {'field': 'current_roles', 'value': 'Research engineer'},
            {'field': 'education', 'value': 'Example University'},
            {'field': 'interests', 'value': 'Robotics measurement', 'kind': 'INTEREST', 'inferred': True},
            {'field': 'projects', 'value': 'Prototype test tools'}])
        return source
    def review_ready(self):
        o.start(self.root)
        o.choose_connection(self.root, 'without_linkedin')
        self.seed()
        return o.enrichment_done(self.root)
    def strategy_ready(self):
        view = self.review_ready()
        o.confirm_profile(self.root, view['review_token'], True)
    def brief_ready(self):
        self.strategy_ready()
        o.set_strategy(self.root, 'goals', ['Find collaborators', 'Share expertise'], True)
        o.set_strategy(self.root, 'audiences', ['Robotics researchers'], True)
    def complete(self):
        self.brief_ready()
        first = o.run_first_brief(self.root)
        o.deliver(self.root, first['receipt'], True)
        return first
    def restart_status(self):
        result = subprocess.run([sys.executable, str(REPO/'skills/li-context/scripts/onboarding.py'),
                                 '--root', str(self.root), 'status'], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    def test_fresh_detection_does_not_write(self):
        result = o.status(self.root)
        self.assertTrue(result['onboarding_required'])
        self.assertEqual(result['phase'], 'WELCOME')
        self.assertFalse(self.root.exists())
    def test_start_creates_user_memory_and_private_state(self):
        result = o.start(self.root)
        self.assertEqual(result['status'], 'in_progress')
        self.assertEqual(result['user_id'], m.initialize(self.root)['user_id'])
        self.assertTrue((self.root/'identity/voice.md').is_file())
        self.assertEqual((self.root/'onboarding/state.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root/'onboarding').stat().st_mode & 0o777, 0o700)
    def test_start_reuses_existing_context(self):
        self.seed()
        before = (self.root/'memory/store.json').read_bytes()
        o.start(self.root)
        self.assertEqual((self.root/'memory/store.json').read_bytes(), before)
        self.assertTrue(o.preview(self.root)['sections'])
    def test_start_is_idempotent_at_partial_phase(self):
        o.start(self.root); o.choose_connection(self.root, 'account'); o.begin_learning(self.root)
        self.assertEqual(o.start(self.root)['phase'], 'ACQUIRING_CONTEXT')
    def test_linkedin_optional_complete_with_resume_and_website(self):
        o.start(self.root); o.choose_connection(self.root, 'without_linkedin')
        file = self.parent/'resume.md'; file.write_text('Alex Example. Robotics engineer. Example University.')
        source = m.add_document(self.root, file)
        m.ingest(self.root, source['source_id'], [{'field': 'current_roles', 'value': 'Robotics engineer'}])
        m.add_web_evidence(self.root, 'https://example.org/',
            {'source_type':'PUBLIC_WEB', 'url':'https://example.org/', 'content':'Prototype measurement tools', 'retrieved_at':m.now()},
            'User-selected website', items=[{'field':'projects', 'value':'Prototype measurement tools'}])
        view = o.enrichment_done(self.root)
        o.confirm_profile(self.root, view['review_token'], True)
        o.set_strategy(self.root, 'goals', ['Find collaborators'], True)
        o.set_strategy(self.root, 'audiences', ['Robotics researchers'], True)
        first = o.run_first_brief(self.root)
        o.deliver(self.root, first['receipt'], True)
        self.assertEqual(o.status(self.root)['status'], 'complete')
        self.assertFalse(o.readiness(self.root)['linkedin_enabled'])
        self.assertEqual(o.readiness(self.root)['authentication'], 'UNVERIFIED')
    def account_learn(self, posts_fail=False):
        o.start(self.root); o.choose_connection(self.root, 'account'); o.begin_learning(self.root)
        set_enabled(self.root, True); begin_task(self.root, onboarding=True)
        upstream = SyntheticUpstream(posts_fail); gateway = Gateway(self.root, upstream)
        packet = asyncio.run(gateway.dispatch('read_my_profile', {'stage': 'experience'}))
        retain(self.root, {'receipt_id': packet['receipt_id'], 'items': [{'data': {
            'name': 'Alex Example', 'headline': 'Research engineer', 'roles': ['Engineer at Example Robotics'],
            'education': ['Example University'], 'skills': ['Python'], 'projects': ['Measurement tools']}}]})
        packet = asyncio.run(gateway.dispatch('read_my_posts', {'stage': 'onboarding'}))
        if packet.get('receipt_id'):
            retain(self.root, {'receipt_id': packet['receipt_id'], 'items': [{'data': {
                'text': 'I measure uncertainty before testing prototypes.', 'author': 'Alex Example', 'url': None}}],
                'summary': {'voice': [{'text': 'Short technical sentences', 'label': 'INFERRED'}]}})
        result = o.learned(self.root)
        asyncio.run(gateway.dispatch('close_session'))
        return result, upstream
    def test_account_first_builds_memory_without_manual_profile_input(self):
        result, upstream = self.account_learn()
        self.assertEqual(result['onboarding']['phase'], 'ENRICHMENT')
        fields = {s['field'] for s in o.preview(self.root)['sections']}
        self.assertIn('education', fields); self.assertIn('voice_patterns', fields)
        self.assertEqual(len(upstream.calls), 3)
        self.assertEqual(m.load_history(self.root), [])
    def test_partial_account_posts_failure_keeps_profile_and_progress(self):
        result, _ = self.account_learn(posts_fail=True)
        self.assertEqual(result['onboarding']['phase'], 'ENRICHMENT')
        self.assertTrue(result['onboarding']['context_built'])
        caps = result['capabilities']['live_capabilities']
        self.assertIn(caps['profile']['state'], ('SUCCESS', 'PARTIAL_READ'))
        self.assertEqual(caps['own_posts']['state'], 'UPSTREAM_ERROR')
        self.assertEqual(caps['feed']['state'], 'UNVERIFIED')
        self.assertTrue(o.enrichment_done(self.root)['sections'])
    def test_interrupt_after_connection_resumes_same_phase(self):
        o.start(self.root); o.choose_connection(self.root, 'account')
        self.assertEqual(self.restart_status()['phase'], 'CONNECTING')
    def test_interrupt_during_acquisition_resumes_same_phase(self):
        o.start(self.root); o.choose_connection(self.root, 'account'); o.begin_learning(self.root)
        self.assertEqual(self.restart_status()['phase'], 'ACQUIRING_CONTEXT')
    def test_interrupt_after_acquisition_preserves_memory(self):
        self.account_learn()
        self.assertEqual(self.restart_status()['phase'], 'ENRICHMENT')
        self.assertTrue(o.preview(self.root)['sections'])
    def test_interrupt_after_enrichment_preserves_pending_review(self):
        self.review_ready()
        self.assertEqual(self.restart_status()['phase'], 'REVIEW')
    def test_interrupt_before_first_brief_preserves_strategy(self):
        self.brief_ready()
        self.assertEqual(self.restart_status()['phase'], 'FIRST_VALUE')
        self.assertIn('Robotics researchers', o.strategy_context(self.root)['audiences'])
    def test_interrupt_after_generated_brief_is_not_complete(self):
        self.brief_ready(); first = o.run_first_brief(self.root)
        result = self.restart_status()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['brief_receipt'], first['receipt'])
        self.assertFalse(result['first_brief_completed'])
    def test_returning_complete_user_never_reruns(self):
        self.complete()
        state = (self.root/'onboarding/state.json').read_bytes()
        self.assertFalse(self.restart_status()['onboarding_required'])
        self.assertEqual(o.start(self.root)['status'], 'complete')
        self.assertEqual((self.root/'onboarding/state.json').read_bytes(), state)
    def test_offline_returning_user_keeps_complete_and_memory(self):
        self.complete(); set_enabled(self.root, False)
        with patch('socket.socket', side_effect=AssertionError('Network forbidden')):
            self.assertEqual(o.start(self.root)['status'], 'complete')
            self.assertTrue(o.preview(self.root)['sections'])
            result = brief(self.root)
            self.assertTrue(result['professional_context']['context'])
            self.assertTrue(result['strategic_context']['goals'])
    def test_preview_labels_and_source_provenance(self):
        self.review_ready(); m.correct(self.root, 'current_roles', 'primary', 'Senior engineer')
        sections = o.preview(self.root)['sections']
        labels = {s['status'] for s in sections}
        self.assertEqual(labels, {'Confirmed', 'Observed', 'Inferred'})
        self.assertTrue(all(s['sources'] for s in sections))
    def test_missing_preview_sections_not_fabricated(self):
        o.start(self.root)
        self.assertEqual(o.preview(self.root)['sections'], [])
    def test_empty_context_cannot_complete_review(self):
        o.start(self.root); o.choose_connection(self.root, 'without_linkedin')
        with self.assertRaises(ValueError): o.enrichment_done(self.root)
        self.assertEqual(o.status(self.root)['phase'], 'ENRICHMENT')
    def test_confirmation_requires_human_acceptance(self):
        view = self.review_ready()
        with self.assertRaises(ValueError): o.confirm_profile(self.root, view['review_token'])
        self.assertEqual(o.status(self.root)['phase'], 'REVIEW')
    def test_review_does_not_upgrade_all_inferences(self):
        view = self.review_ready(); o.confirm_profile(self.root, view['review_token'], True)
        interest = next(s for s in o.preview(self.root)['sections'] if s['field'] == 'interests')
        self.assertEqual(interest['label'], 'INFERRED')
    def test_changed_profile_cannot_use_old_review_token(self):
        view = self.review_ready(); m.correct(self.root, 'current_roles', 'primary', 'Senior engineer')
        with self.assertRaises(ValueError): o.confirm_profile(self.root, view['review_token'], True)
    def test_correction_survives_second_process_and_reingestion(self):
        self.review_ready(); m.correct(self.root, 'interests', 'primary', 'Dependable measurement', 'INTEREST')
        s = m.add_bio(self.root, 'Still discussing robotics measurement.')
        m.ingest(self.root, s['source_id'], [{'field': 'interests', 'value': 'Robotics measurement', 'kind': 'INTEREST', 'inferred': True}])
        self.restart_status()
        interest = next(s for s in o.preview(self.root)['sections'] if s['field']=='interests')
        self.assertEqual(interest['value'], 'Dependable measurement')
        self.assertEqual(interest['status'], 'Confirmed')
    def test_source_conflict_preserved_in_preview(self):
        self.review_ready()
        source = m.register_source(self.root, 'website', 'https://example.org/', m.digest('other'))
        m.ingest(self.root, source['source_id'], [{'field': 'current_roles', 'value': 'Consultant'}])
        group = next(s for s in o.preview(self.root)['sections'] if s['field']=='current_roles')
        self.assertTrue(group['conflict']); self.assertEqual(len(group['sources']), 2)
        self.assertEqual(group['value'], 'Research engineer')
    def test_identical_source_is_not_duplicated(self):
        self.review_ready(); count = len(m._read(self.root)['evidence'])
        self.seed(); self.assertEqual(len(m._read(self.root)['evidence']), count)
    def test_failed_enrichment_keeps_context_and_phase(self):
        self.review_ready(); before = m.summary(self.root)['context']
        with self.assertRaises(ValueError): m.add_document(self.root, self.parent/'missing.pdf')
        self.assertEqual(m.summary(self.root)['context'], before)
        self.assertEqual(o.status(self.root)['phase'], 'REVIEW')
    def test_failed_replacement_keeps_previous_working_version(self):
        self.review_ready(); before = o.preview(self.root)['review_token']
        source = m.add_bio(self.root, 'Unnormalized replacement')
        with self.assertRaises(ValueError): m.ingest(self.root, source['source_id'], [{'field': 'person', 'value': ''}])
        self.assertEqual(o.preview(self.root)['review_token'], before)
    def test_authentication_challenge_pauses_and_manual_resume_does_not_read(self):
        o.start(self.root); o.choose_connection(self.root, 'account'); o.begin_learning(self.root)
        o.block(self.root, 'AUTH_CHALLENGE')
        self.assertEqual(self.restart_status()['status'], 'blocked')
        with self.assertRaises(ValueError): o.learned(self.root)
        self.assertEqual(o.resume(self.root)['phase'], 'ACQUIRING_CONTEXT')
        self.assertFalse((self.root/'account/task.json').exists())
    def test_auth_failure_can_continue_without_linkedin(self):
        o.start(self.root); o.choose_connection(self.root, 'account'); o.block(self.root, 'NOT_AUTHENTICATED')
        result = o.resume(self.root, without_linkedin=True)
        self.assertEqual(result['phase'], 'ENRICHMENT'); self.assertEqual(result['linkedin_step'], 'without_linkedin')
    def test_goals_are_not_inferred_from_career(self):
        self.strategy_ready()
        self.assertEqual(o.strategy_context(self.root)['goals'], [])
        self.assertIn('goals', o.question_policy(self.root)['strategic_questions'])
    def test_unconfirmed_inferred_audience_still_requires_selection(self):
        self.strategy_ready(); source = m.add_bio(self.root, 'Suggested audience')
        m.ingest(self.root, source['source_id'], [{'field': 'audiences', 'value': 'Investors', 'inferred': True}])
        self.assertIn('audiences', o.question_policy(self.root)['strategic_questions'])
    def test_goals_multiple_selections_persist_as_confirmed(self):
        self.brief_ready(); self.restart_status()
        result = o.strategy_context(self.root)['goals']
        self.assertEqual(result, ['Find collaborators; Share expertise'])
        self.assertEqual(next(g for g in m.summary(self.root)['context'] if g['field']=='goals')['preferred']['label'], 'USER_CONFIRMED')
    def test_audience_proposals_depend_on_profile_evidence(self):
        self.review_ready(); result = o.audience_proposals(self.root)
        self.assertIn('Research engineer', json.dumps(result['basis']))
        self.assertNotIn('Investors', json.dumps(result))
        self.assertEqual(result['confirmed_audiences'], [])
    def test_known_confirmed_goals_audiences_are_not_asked_again(self):
        view = self.review_ready()
        m.correct(self.root, 'goals', 'primary', 'Find collaborators', 'POSITIONING')
        m.correct(self.root, 'audiences', 'primary', 'Robotics researchers', 'POSITIONING')
        result = o.confirm_profile(self.root, view['review_token'], True)
        self.assertEqual(result['phase'], 'FIRST_VALUE')
        self.assertEqual(result['questions']['strategic_questions'], [])
    def test_known_valid_context_is_reported_before_questions(self):
        self.review_ready()
        self.assertTrue({'current_roles','education','interests'}.issubset(o.question_policy(self.root)['known_fields']))
    def test_changed_audience_updates_future_briefs_without_rerun(self):
        self.complete(); o.set_strategy(self.root, 'audiences', ['Product engineers'], True)
        result = brief(self.root)
        self.assertEqual(result['strategic_context']['audiences'], ['Product engineers'])
        self.assertEqual(o.status(self.root)['status'], 'complete')
    def test_strategy_without_confirmation_refused(self):
        self.strategy_ready()
        with self.assertRaises(ValueError): o.set_strategy(self.root, 'goals', ['Find collaborators'])
        self.assertEqual(o.strategy_context(self.root)['goals'], [])
    def test_empty_strategy_or_many_values_refused(self):
        self.strategy_ready()
        for values in ([], [''], ['x']*11):
            with self.subTest(values=values), self.assertRaises(ValueError): o.set_strategy(self.root, 'goals', values, True)
    def test_strategy_guard_refuses_credentials(self):
        self.strategy_ready()
        with self.assertRaises(ValueError): o.set_strategy(self.root, 'goals', ['password=secret'], True)
    def test_no_first_value_before_strategy(self):
        self.strategy_ready()
        with self.assertRaises(ValueError): o.run_first_brief(self.root)
    def test_zero_opportunity_first_brief_is_valid_useful_coverage(self):
        self.brief_ready(); result = o.run_first_brief(self.root)
        self.assertEqual(result['brief']['actions'], [])
        self.assertIn('No supported material action', result['brief']['message'])
        self.assertIn('read_status', result['brief'])
        self.assertTrue(result['brief']['professional_context']['context'])
        self.assertTrue(result['brief']['strategic_context']['goals'])
    def test_first_brief_uses_real_signal_not_generic_tips(self):
        self.brief_ready()
        now = datetime.now(timezone.utc).isoformat()
        ingest(self.root, {'schema_version':1, 'source':{'type':'manual', 'provider':'user-signal', 'identifier':'discussion',
                'retrieved_at':now, 'visibility':'public'}, 'capabilities':['feed'], 'coverage':'partial',
                'items':[{'kind':'post','id':'signal-1','capability':'feed',
                'data':{'text':'How should robotics researchers quantify measurement uncertainty?', 'timestamp':now},
                'assessment':{'relevance':1.0,'can_contribute':True,'label':'USER-PROVIDED'}}]})
        first = o.run_first_brief(self.root)
        self.assertEqual(len(first['brief']['actions']), 1)
        self.assertEqual(first['brief']['actions'][0]['id'], 'signal-1')
        self.assertIn('measurement uncertainty', first['brief']['actions'][0]['signal'])
        self.assertIn('Robotics researchers', json.dumps(first['brief']['strategic_context']))
        self.assertEqual(first['brief']['research_signals'], [])
    def test_first_brief_generated_before_delivered_not_complete(self):
        self.brief_ready(); o.run_first_brief(self.root)
        self.assertFalse(o.status(self.root)['first_brief_completed'])
    def test_brief_receipt_cannot_be_fabricated(self):
        self.brief_ready()
        with self.assertRaises(ValueError): o.deliver(self.root, 'a'*64, True)
    def test_delivery_requires_display_attestation(self):
        self.brief_ready(); first = o.run_first_brief(self.root)
        with self.assertRaises(ValueError): o.deliver(self.root, first['receipt'])
    def test_changed_strategy_invalidates_undelivered_brief(self):
        self.brief_ready(); first = o.run_first_brief(self.root)
        o.set_strategy(self.root, 'goals', ['Stay current'], True)
        with self.assertRaises(ValueError): o.deliver(self.root, first['receipt'], True)
    def test_changed_profile_routes_back_to_review_before_brief(self):
        self.brief_ready(); m.correct(self.root, 'current_roles', 'primary', 'Senior engineer')
        result = o.run_first_brief(self.root)
        self.assertTrue(result['review_required']); self.assertEqual(o.status(self.root)['phase'], 'REVIEW')
    def test_changed_profile_after_brief_cannot_complete(self):
        self.brief_ready(); first = o.run_first_brief(self.root)
        m.correct(self.root, 'current_roles', 'primary', 'Senior engineer')
        with self.assertRaises(ValueError): o.deliver(self.root, first['receipt'], True)
    def test_tampered_saved_brief_refused(self):
        self.brief_ready(); first = o.run_first_brief(self.root)
        p = self.root/'onboarding/first-brief.json'; payload=json.loads(p.read_text()); payload['brief']['message']='Invented'
        p.write_text(json.dumps(payload))
        with self.assertRaises(ValueError): o.deliver(self.root, first['receipt'], True)
    def test_completed_handoff_has_exactly_five_real_workflows(self):
        self.complete(); workflows=o.status(self.root)['workflows']
        self.assertEqual(len(workflows), 5)
        for w in workflows:
            for skill in w['skills']:
                self.assertTrue((REPO/'skills'/skill/'SKILL.md').exists(), skill)
        self.assertNotIn('onboarding', [w['id'] for w in workflows])
        self.assertEqual(len(list((REPO/'skills').glob('*/SKILL.md'))), 20)
    def test_reset_preview_has_no_side_effects(self):
        self.complete(); state=(self.root/'onboarding/state.json').read_bytes()
        self.assertTrue(o.reset(self.root)['requires_confirmation'])
        self.assertEqual((self.root/'onboarding/state.json').read_bytes(),state)
    def test_review_reset_preserves_memory_goals_and_auth(self):
        self.complete(); set_enabled(self.root,True)
        memory_before=(self.root/'memory/store.json').read_bytes()
        control_before=(self.root/'account/control.json').read_bytes()
        result=o.reset(self.root,True)
        self.assertEqual(result['phase'],'REVIEW'); self.assertFalse(result['first_brief_completed'])
        self.assertEqual((self.root/'memory/store.json').read_bytes(),memory_before)
        self.assertEqual((self.root/'account/control.json').read_bytes(),control_before)
        o.confirm_profile(self.root,o.preview(self.root)['review_token'],True)
        self.assertEqual(o.status(self.root)['phase'],'FIRST_VALUE')
    def test_reset_without_context_goes_to_enrichment(self):
        self.complete(); m.reset(self.root,'all-memory',True)
        self.assertEqual(o.reset(self.root,True)['phase'],'ENRICHMENT')
    def test_complete_user_cannot_be_reconnected_by_start(self):
        self.complete()
        with self.assertRaises(ValueError):o.choose_connection(self.root,'account')
    def test_wrong_user_state_refused(self):
        o.start(self.root); p=self.root/'onboarding/state.json'; data=json.loads(p.read_text());data['user_id']='usr_'+'a'*32;p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):o.status(self.root)
    def test_two_project_users_are_isolated(self):
        self.complete(); other=self.parent/'other'/'.linkedin-agent'; o.start(other)
        self.assertNotEqual(o.status(other)['user_id'],o.status(self.root)['user_id'])
        self.assertEqual(o.strategy_context(other)['goals'],[])
        self.assertEqual(o.status(other)['phase'],'WELCOME')
    def test_corrupt_json_preserved(self):
        o.start(self.root);p=self.root/'onboarding/state.json';p.write_text('{bad')
        with self.assertRaises(ValueError):o.start(self.root)
        self.assertEqual(p.read_text(),'{bad')
    def test_unknown_version_refused(self):
        o.start(self.root);p=self.root/'onboarding/state.json';data=json.loads(p.read_text());data['version']=2;p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):o.status(self.root)
    def test_impossible_completion_refused(self):
        o.start(self.root);p=self.root/'onboarding/state.json';data=json.loads(p.read_text());data.update(phase='COMPLETE',status='complete');p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):o.status(self.root)
    def test_symlinked_lifecycle_directory_refused(self):
        self.root.mkdir();target=self.parent/'outside';target.mkdir();(self.root/'onboarding').symlink_to(target,target_is_directory=True)
        with self.assertRaises(ValueError):o.start(self.root)
        self.assertEqual(list(target.iterdir()),[])
    def test_oversized_state_refused(self):
        o.start(self.root);p=self.root/'onboarding/state.json';p.write_text(' '*64001)
        with self.assertRaises(ValueError):o.status(self.root)
    def test_public_export_excludes_lifecycle_and_auth(self):
        self.complete();out=self.parent/'export.json';m.export_context(self.root,out)
        payload=json.loads(out.read_text());self.assertNotIn('onboarding',payload)
        self.assertNotIn('authentication',payload)
    def test_cli_invalid_transition_has_no_private_traceback(self):
        result=subprocess.run([sys.executable,str(REPO/'skills/li-context/scripts/onboarding.py'),'--root',str(self.root),'run-brief'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertNotIn('Traceback',result.stderr)
        self.assertNotIn(str(self.root),result.stderr)
    def test_git_ignore_protects_onboarding(self):
        result=subprocess.run(['git','check-ignore','--stdin'],cwd=REPO,input='.linkedin-agent/onboarding/state.json\n.linkedin-agent/onboarding/first-brief.json\n',capture_output=True,text=True,check=True)
        self.assertEqual(len(result.stdout.splitlines()),2)
    def test_all_five_workflows_receive_selected_strategy(self):
        self.complete()
        for workflow in o.WORKFLOWS:
            handoff=o.workflow_context(self.root,workflow['id'])
            self.assertTrue(handoff['onboarding_complete'])
            context=handoff['strategic_context']
            self.assertIn('Find collaborators',context['goals'][0],workflow['id'])
            self.assertEqual(context['audiences'],['Robotics researchers'])
            self.assertTrue(set(g['field'] for g in handoff['professional_context']['context']).issubset(set(o.WORKFLOW_FIELDS[workflow['id']])))
    def test_unknown_workflow_refused(self):
        with self.assertRaises(ValueError):o.workflow_context(self.root,'onboarding')
    def test_missing_saved_complete_receipt_refused(self):
        self.complete();(self.root/'onboarding/first-brief.json').unlink()
        with self.assertRaises(ValueError):o.status(self.root)
    def test_malformed_capabilities_fail_closed_without_modifying_progress(self):
        o.start(self.root);p=self.root/'account/status.json';p.parent.mkdir();p.write_text('{"capabilities":[]}')
        before=(self.root/'onboarding/state.json').read_bytes()
        with self.assertRaises(ValueError):o.readiness(self.root)
        self.assertEqual((self.root/'onboarding/state.json').read_bytes(),before)
    def test_stale_role_not_treated_as_known_current_information(self):
        o.start(self.root)
        source=m.register_source(self.root,'linkedin','https://linkedin.com/in/alex-example/',m.digest('old'),'2020-01-01T00:00:00Z')
        m.ingest(self.root,source['source_id'],[{'field':'current_roles','value':'Historical role'}])
        self.assertNotIn('current_roles',o.question_policy(self.root)['known_fields'])
    def test_material_conflict_is_reported_but_confirmation_resolves_question(self):
        self.review_ready();other=m.register_source(self.root,'website','https://example.org/',m.digest('other'))
        m.ingest(self.root,other['source_id'],[{'field':'current_roles','value':'Consultant'}])
        self.assertIn('current_roles',o.question_policy(self.root)['material_conflicts'])
        m.correct(self.root,'current_roles','primary','Research engineer')
        self.assertNotIn('current_roles',o.question_policy(self.root)['material_conflicts'])
    def test_context_website_source_known_without_asking_url_again(self):
        self.review_ready();web=m.register_source(self.root,'website','https://example.org/',m.digest('site'))
        m.ingest(self.root,web['source_id'],[{'field':'projects','value':'Public measurement tools'}])
        self.assertTrue(any(s['reference']=='https://example.org/' for s in m.sources(self.root)))
        self.assertEqual(set(o.question_policy(self.root)['strategic_questions']),{'goals','audiences'})
    def test_filled_curated_audience_is_reused_without_repeat_question(self):
        view=self.review_ready()
        (self.root/'identity/audience.md').write_text('My important readers are robotics research teams and product engineers.')
        self.assertNotIn('audiences',o.question_policy(self.root)['strategic_questions'])
        o.confirm_profile(self.root,view['review_token'],True)
        self.assertTrue(o.status(self.root)['audiences_configured'])
        o.set_strategy(self.root,'goals',['Find collaborators'],True)
        self.assertEqual(o.status(self.root)['phase'],'FIRST_VALUE')
    def test_onboarding_state_and_receipt_use_private_permissions(self):
        self.complete()
        for file in ('onboarding/state.json','onboarding/first-brief.json','onboarding/lock'):
            self.assertEqual((self.root/file).stat().st_mode & 0o777,0o600)
    def test_resume_reconciles_strategy_persisted_before_checkpoint_write(self):
        self.strategy_ready()
        m.correct(self.root,'goals','primary','Find collaborators','POSITIONING')
        m.correct(self.root,'audiences','primary','Robotics researchers','POSITIONING')
        self.assertEqual(o.status(self.root)['phase'],'STRATEGY')
        self.assertEqual(o.question_policy(self.root)['strategic_questions'],[])
        self.assertEqual(o.resume(self.root)['phase'],'FIRST_VALUE')
        result=o.run_first_brief(self.root)
        self.assertTrue(result['brief']['strategic_context']['goals'])
    def test_impossible_review_checkpoint_refused(self):
        o.start(self.root);p=self.root/'onboarding/state.json';data=json.loads(p.read_text());data['phase']='REVIEW';p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):o.status(self.root)
    def test_sources_removed_before_confirmation_cannot_complete_empty_profile(self):
        self.review_ready()
        for source in m.sources(self.root):
            if source['kind']!='confirmation':m.remove_source(self.root,source['id'])
        view=o.preview(self.root)
        with self.assertRaises(ValueError):o.confirm_profile(self.root,view['review_token'],True)
        self.assertEqual(o.reset(self.root,True)['phase'],'ENRICHMENT')
    def test_account_enrichment_resume_bio_website_and_link_preserves_conflicts(self):
        self.account_learn()
        file=self.parent/'resume.md';file.write_text('Alex Example. Senior robotics engineer.')
        resume=m.add_document(self.root,file)
        m.ingest(self.root,resume['source_id'],[{'field':'current_roles','value':'Senior robotics engineer'}])
        bio=m.add_bio(self.root,'Alex Example consults on robotics measurement.')
        m.ingest(self.root,bio['source_id'],[{'field':'current_roles','value':'Measurement consultant'}])
        for kind,url,field,value in [('website','https://example.org/','projects','Prototype measurement tools'),
                                     ('link','https://example.org/university','education','Example University')]:
            receipt={'source_type':'PUBLIC_WEB','url':url,'content':value,'retrieved_at':m.now()}
            m.add_web_evidence(self.root,url,receipt,'User-selected professional source',kind,[{'field':field,'value':value}])
            before=len(m._read(self.root)['evidence'])
            m.add_web_evidence(self.root,url,receipt,'User-selected professional source',kind,[{'field':field,'value':value}])
            self.assertEqual(len(m._read(self.root)['evidence']),before)
        view=o.enrichment_done(self.root)
        roles=next(g for g in view['sections'] if g['field']=='current_roles')
        self.assertTrue(roles['conflict']);self.assertEqual(len(roles['sources']),2)
        self.assertTrue({'linkedin','resume','bio','website','link'}.issubset({s['kind'] for s in m.sources(self.root)}))
        m.correct(self.root,'current_roles','primary','Senior robotics engineer')
        view=o.preview(self.root)
        o.confirm_profile(self.root,view['review_token'],True)
        self.assertEqual(next(g for g in view['sections'] if g['field']=='current_roles')['status'],'Confirmed')
    def test_no_network_in_lifecycle_or_first_brief(self):
        with patch('socket.socket',side_effect=AssertionError('No network')):
            self.complete()

if __name__=='__main__':unittest.main()
