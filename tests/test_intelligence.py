"""Read-source, normalization, degraded-mode and action-boundary regression tests."""
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
READ = ROOT / 'skills/li-read/scripts'
sys.path.insert(0, str(READ))
from models import normalize_envelope, freshness, parse_time, FIELDS
from read_layer import ingest, load_cache, refresh, status, config, import_csv, tools, purge, FileProvider, ReadProvider, atomic_save
from intelligence import brief, weekly, load_relationships, active_items, priorities, memory_lookup, memory_overlap, memory
from context import append_history, summarize, initialize

NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
RECENT = '2026-10-02T08:00:00Z'


def source(**changes):
    return {'type':'manual','provider':'manual-1','identifier':'supplied-data',
            'retrieved_at':RECENT,'url':None,'visibility':'public','confidence':None,**changes}


def item(kind='post', identifier='p1', capability='own_posts', **data):
    defaults={'text':'We added a review field.', 'timestamp':RECENT} if kind in ('post','comment','message') else {}
    return {'kind':kind,'id':identifier,'capability':capability,'data':{**defaults,**data}}


def envelope(items=None, **changes):
    records=items if items is not None else [item()]
    return {'schema_version':1,'source':source(), 'capabilities':list(dict.fromkeys(i['capability'] for i in records)),
            'coverage':'partial','items':records,**changes}


class FakeReadProvider:
    def __init__(self, identifier, source_type='manual', capability='own_posts', response=None, fail=False):
        self.id=identifier
        self.source_type=source_type
        self.capabilities=[capability]
        self.enabled=True
        self.response=response
        self.fail=fail
        self.calls=[]

    def read(self, capability):
        self.calls.append(capability)
        if self.fail:
            raise OSError('read unavailable')
        return self.response


class NormalizationTests(unittest.TestCase):
    def test_all_kinds_unknown_fields_are_null(self):
        for kind,cap in [('profile','profile'),('post','own_posts'),('comment','own_comments'),('person','network'),('analytics','analytics'),('message','inbox')]:
            with self.subTest(kind=kind):
                raw=item(kind,kind,cap)
                raw['data']={}
                n=normalize_envelope(envelope([raw]))['items'][0]
                self.assertEqual(set(n['data']),set(FIELDS[kind]))
                self.assertTrue(all(v is None for v in n['data'].values()))
                self.assertEqual(n['provenance']['label'],'USER-PROVIDED')

    def test_profile(self):
        n=normalize_envelope(envelope([item('profile','me','profile',name='Me',roles=['Founder'],headline='Engineer')]))
        self.assertEqual(n['items'][0]['data']['roles'],['Founder'])
        self.assertIsNone(n['items'][0]['data']['education'])

    def test_comments(self):
        n=normalize_envelope(envelope([item('comment','c1','own_comments',parent_post='p1',reactions=0)]))
        self.assertEqual(n['items'][0]['data']['reactions'],0)
        self.assertEqual(n['items'][0]['data']['parent_post'],'p1')

    def test_analytics_null_not_zero(self):
        n=normalize_envelope(envelope([item('analytics','a1','analytics',date='2026-10-02',post_id='p1',impressions=100)]))
        self.assertIsNone(n['items'][0]['data']['clicks'])

    def test_research_packet_provenance(self):
        raw=item('research','r1','research',title='Public report',text='Supported scoped finding',timestamp=RECENT)
        n=normalize_envelope(envelope([raw],source=source(type='web_research',url='https://example.com/report')))
        self.assertEqual(n['items'][0]['provenance']['label'],'WEB-VERIFIED')
        with self.assertRaises(ValueError):normalize_envelope(envelope([raw],source=source(type='web_research')))

    def test_post_metadata(self):
        n=normalize_envelope(envelope([item(media=['document: public report'],claims=['pilot observation'],evidence_used=['report-id'])]))
        self.assertEqual(n['items'][0]['data']['media'],['document: public report'])

    def test_unknown_data_dropped(self):
        n=normalize_envelope(envelope([item(password='not-retained')]))
        self.assertNotIn('password',n['items'][0]['data'])

    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):normalize_envelope(envelope([item(),item()]))

    def test_wrong_capability(self):
        with self.assertRaises(ValueError):normalize_envelope(envelope([item('post','p1','inbox')]))

    def test_bad_metrics(self):
        for value in (-1,True,float('nan'),'10'):
            with self.subTest(value=value),self.assertRaises(ValueError):normalize_envelope(envelope([item(reactions=value)]))

    def test_bad_timestamp(self):
        for value in ('today','20261002','2026-10-02T08:00:00','2026-W40-5'):
            with self.subTest(value=value),self.assertRaises(ValueError):normalize_envelope(envelope([item(timestamp=value)]))

    def test_timezone_and_date_precision(self):
        self.assertEqual(parse_time('2026-10-02T10:00:00+02:00').hour,8)
        n=normalize_envelope(envelope([item(timestamp='2026-10-02')]))
        self.assertEqual(n['items'][0]['data']['timestamp'],'2026-10-02')

    def test_source_timestamp_requires_timezone(self):
        with self.assertRaises(ValueError):normalize_envelope(envelope(source=source(retrieved_at='2026-10-02')))

    def test_unsafe_urls(self):
        for url in ('file:///secret','https://user:password@example.com','https://example.com/?token=secret'):
            with self.subTest(url=url),self.assertRaises(ValueError):normalize_envelope(envelope([item(url=url)]))

    def test_missing_item_identifier(self):
        bad=item();bad.pop('id')
        with self.assertRaises(ValueError):normalize_envelope(envelope([bad]))

    def test_malformed(self):
        for payload in ([],{},envelope(items=[] ,coverage='unknown'),envelope(source=source(confidence=2))):
            with self.subTest(payload=payload),self.assertRaises(ValueError):normalize_envelope(payload)


class ReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'.linkedin-agent'

    def test_no_provider_manual(self):
        s=status(self.root,NOW)
        self.assertEqual(s['mode'],'Manual')
        self.assertTrue(all(c['state']=='unavailable' for c in s['capabilities'].values()))
        self.assertEqual(brief(self.root,NOW)['actions'],[])

    def test_public_snapshot_mode_honest(self):
        ingest(self.root,envelope(source=source(type='public_web')),now=NOW)
        result=status(self.root,NOW)
        self.assertEqual(result['mode'],'Partial Read')
        self.assertFalse(result['live_account_client'])

    def test_one_provider(self):
        payload=envelope(source=source(provider='export',type='user_export'),coverage='complete')
        provider=FakeReadProvider('export','user_export',response=payload)
        refresh(self.root,[provider],NOW)
        self.assertEqual(provider.calls,['own_posts'])
        self.assertEqual(len(load_cache(self.root)['items']),1)

    def test_fallback_on_failure(self):
        first=FakeReadProvider('official','official',fail=True)
        second=FakeReadProvider('export','user_export',response=envelope(source=source(provider='export',type='user_export'),coverage='complete'))
        result=refresh(self.root,[second,first],NOW)
        attempts=result['capabilities']['own_posts']['refresh_attempts']
        self.assertEqual(attempts[0]['state'],'error')
        self.assertEqual(attempts[1]['provider'],'export')

    def test_fallback_on_stale(self):
        stale=FakeReadProvider('official','official',response=envelope(source=source(provider='official',type='official',retrieved_at='2026-09-01T08:00:00Z'),coverage='complete'))
        fresh=FakeReadProvider('export','user_export',response=envelope(source=source(provider='export',type='user_export'),coverage='complete'))
        s=refresh(self.root,[stale,fresh],NOW)
        self.assertEqual(s['capabilities']['own_posts']['selected_provider'],'export')

    def test_partial_falls_back(self):
        first=FakeReadProvider('official','official',response=envelope(source=source(provider='official',type='official')))
        second=FakeReadProvider('export','user_export',response=envelope(source=source(provider='export',type='user_export'),coverage='complete'))
        refresh(self.root,[first,second],NOW)
        self.assertEqual(second.calls,['own_posts'])

    def test_unavailable_capability_no_calls(self):
        provider=FakeReadProvider('manual',response=envelope(source=source(provider='manual')))
        refresh(self.root,[provider],NOW)
        self.assertNotIn('inbox',provider.calls)

    def test_malformed_response_fallback(self):
        first=FakeReadProvider('official','official',response={})
        second=FakeReadProvider('manual','manual',response=envelope(source=source(provider='manual')))
        s=refresh(self.root,[first,second],NOW)
        self.assertEqual(s['capabilities']['own_posts']['refresh_attempts'][0]['state'],'error')
        self.assertEqual(len(load_cache(self.root)['items']),1)

    def test_provider_identity_mismatch(self):
        p=FakeReadProvider('claimed','official',response=envelope())
        s=refresh(self.root,[p],NOW)
        self.assertEqual(s['capabilities']['own_posts']['state'],'unavailable')
        self.assertEqual(load_cache(self.root)['items'],[])

    def test_import_incremental(self):
        self.assertEqual(ingest(self.root,envelope(),now=NOW)['new'],1)
        old=load_cache(self.root)['items'][0]
        counts=ingest(self.root,envelope(),now=NOW+timedelta(hours=1))
        new=load_cache(self.root)['items'][0]
        self.assertEqual(counts['unchanged'],1)
        self.assertEqual(old['content_hash'],new['content_hash'])
        self.assertEqual(old['last_changed'],new['last_changed'])
        self.assertFalse(new['changed'])

    def test_update(self):
        ingest(self.root,envelope(),now=NOW)
        counts=ingest(self.root,envelope([item(text='The revised actual text.')]),now=NOW+timedelta(hours=1))
        self.assertEqual(counts['updated'],1)
        self.assertTrue(load_cache(self.root)['items'][0]['changed'])
        self.assertEqual(len(load_cache(self.root)['items']),1)

    def test_older_snapshot_cannot_overwrite(self):
        ingest(self.root,envelope(),now=NOW)
        old=envelope([item(text='Older text')],source=source(retrieved_at='2026-09-01T00:00:00Z'))
        self.assertEqual(ingest(self.root,old,now=NOW)['older_ignored'],1)
        self.assertEqual(load_cache(self.root)['items'][0]['data']['text'],'We added a review field.')

    def test_future_retrieval_rejected(self):
        with self.assertRaises(ValueError):ingest(self.root,envelope(source=source(retrieved_at='2027-01-01T00:00:00Z')),now=NOW)
        self.assertFalse(self.root.exists())

    def test_fresh_retrieval_old_event_stale(self):
        n=normalize_envelope(envelope([item(timestamp='2026-09-01T00:00:00Z')]))['items'][0]
        self.assertEqual(freshness(n,NOW)['state'],'stale')

    def test_unknown_event(self):
        n=normalize_envelope(envelope([item(timestamp=None)]))['items'][0]
        self.assertEqual(freshness(n,NOW)['state'],'unknown-event-time')

    def test_private_requires_optin(self):
        payload=envelope([item('message','m1','inbox')],source=source(visibility='private'))
        with self.assertRaises(ValueError):ingest(self.root,payload,now=NOW)
        self.assertFalse(self.root.exists())
        ingest(self.root,payload,True,NOW)
        self.assertEqual(len(load_cache(self.root)['items']),1)

    def test_cache_permissions(self):
        ingest(self.root,envelope(),now=NOW)
        if os.name=='posix':
            self.assertEqual(stat.S_IMODE((self.root/'read/cache.json').stat().st_mode),0o600)

    def test_cli_status_malformed_cache_controlled(self):
        import subprocess
        atomic_save(self.root,'read/cache.json',{'schema_version':1,'items':[],'status':{'feed':[]}})
        p=subprocess.run([sys.executable,str(READ/'read_layer.py'),'--root',str(self.root),'status'],text=True,capture_output=True,timeout=10)
        self.assertEqual(p.returncode,2)
        self.assertNotIn('Traceback',p.stderr)

    def test_complete_snapshot_retires_missing_keeps_memory(self):
        ingest(self.root,envelope(coverage='complete'),now=NOW)
        empty=envelope([],source=source(retrieved_at='2026-10-02T10:00:00Z'),capabilities=['own_posts'],coverage='complete')
        counts=ingest(self.root,empty,now=NOW)
        self.assertEqual(counts['retired'],1)
        self.assertFalse(load_cache(self.root)['items'][0]['active'])
        self.assertEqual(active_items(self.root),[])
        self.assertEqual(len(memory_lookup(self.root,'review field')),1)

    def test_old_complete_snapshot_does_not_retire_new_data(self):
        ingest(self.root,envelope(),now=NOW)
        empty=envelope([],source=source(retrieved_at='2026-10-01T10:00:00Z'),capabilities=['own_posts'],coverage='complete')
        self.assertEqual(ingest(self.root,empty,now=NOW)['retired'],0)
        self.assertTrue(load_cache(self.root)['items'][0]['active'])

    def test_old_item_cannot_revive_retired_activity(self):
        ingest(self.root,envelope(),now=NOW)
        empty=envelope([],source=source(retrieved_at='2026-10-02T10:00:00Z'),capabilities=['own_posts'],coverage='complete')
        ingest(self.root,empty,now=NOW)
        self.assertEqual(ingest(self.root,envelope(),now=NOW)['older_ignored'],1)
        self.assertFalse(load_cache(self.root)['items'][0]['active'])

    def test_empty_complete_watermark_blocks_unseen_older_activity(self):
        empty=envelope([],source=source(retrieved_at='2026-10-02T10:00:00Z'),capabilities=['own_comments'],coverage='complete')
        ingest(self.root,empty,now=NOW)
        raw=item('comment','unseen','own_comments',text='What changed in your review process?')
        raw['assessment']={'reply_expected':True}
        old=envelope([raw],source=source(retrieved_at='2026-10-01T10:00:00Z'))
        self.assertEqual(ingest(self.root,old,now=NOW)['older_ignored'],1)
        self.assertEqual(active_items(self.root),[])
        self.assertEqual(brief(self.root,NOW)['actions'],[])
        newer=envelope([raw],source=source(retrieved_at='2026-10-02T11:00:00Z'))
        self.assertEqual(ingest(self.root,newer,now=NOW)['new'],1)
        self.assertEqual(brief(self.root,NOW)['actions'][0]['id'],'unseen')

    def test_complete_watermark_capability_scoped_and_validated(self):
        empty=envelope([],capabilities=['own_comments'],coverage='complete')
        ingest(self.root,empty,now=NOW)
        older_post=envelope(source=source(retrieved_at='2026-10-01T10:00:00Z'))
        self.assertEqual(ingest(self.root,older_post,now=NOW)['new'],1)
        cache=load_cache(self.root)
        cache['complete_snapshots']=[{'provider':'manual-1','capability':'own_comments','retrieved_at':'bad'}]
        atomic_save(self.root,'read/cache.json',cache)
        with self.assertRaises(ValueError):load_cache(self.root)

    def test_unknown_inbox_visibility_requires_optin(self):
        raw=item('message','m1','inbox')
        raw['assessment']={'reply_expected':True}
        payload=envelope([raw],source=source(visibility='unknown'))
        with self.assertRaises(ValueError):ingest(self.root,payload,now=NOW)
        ingest(self.root,payload,allow_private=True,now=NOW)
        self.assertEqual(brief(self.root,NOW)['actions'],[])
        self.assertEqual(brief(self.root,NOW,include_private=True)['actions'][0]['id'],'m1')

    def test_malformed_cached_status(self):
        ingest(self.root,envelope(),now=NOW)
        for bad in ({'feed':[]},{'feed':{'state':'available','attempts':'not-list'}},
                    {'feed':{'state':'available','attempts':[[]],'last_refreshed':RECENT}}):
            path=self.root/'read/cache.json'
            payload=json.loads(path.read_text());payload['status']=bad;path.write_text(json.dumps(payload))
            with self.subTest(status=bad),self.assertRaises(ValueError):status(self.root,NOW)

    def test_tampered_cache_rejected(self):
        ingest(self.root,envelope(),now=NOW)
        path=self.root/'read/cache.json';payload=json.loads(path.read_text())
        payload['items'][0]['data']['text']='tampered';path.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):load_cache(self.root)

    def test_csv_mapping(self):
        path=Path(self.tmp.name)/'posts.csv';path.write_text('Post ID,Content,Date\np1,Actual text,2026-10-02\n')
        payload=import_csv(path,'post','own_posts',source(type='user_export'),{'id':'Post ID','text':'Content','timestamp':'Date'})
        ingest(self.root,payload,now=NOW)
        self.assertEqual(load_cache(self.root)['items'][0]['data']['text'],'Actual text')
        self.assertIsNone(load_cache(self.root)['items'][0]['data']['reactions'])

    def test_csv_malformed(self):
        path=Path(self.tmp.name)/'bad.csv'
        for content in ('id,text,text\np1,a,b\n','id,text\np1,a,extra\n','id,text\np1\n'):
            path.write_text(content)
            with self.subTest(content=content),self.assertRaises(ValueError):import_csv(path,'post','own_posts',source())

    def test_file_provider_disabled_and_enabled(self):
        (self.root/'imports').mkdir(parents=True)
        (self.root/'imports/data.json').write_text(json.dumps(envelope()))
        spec={'id':'manual-1','source_type':'manual','enabled':False,'path':'imports/data.json','capabilities':['own_posts']}
        atomic_save(self.root,'sources.json',{'schema_version':1,'providers':[spec]})
        self.assertEqual(refresh(self.root,now=NOW)['capabilities']['own_posts']['state'],'unavailable')
        spec['enabled']=True
        atomic_save(self.root,'sources.json',{'schema_version':1,'providers':[spec]})
        self.assertEqual(refresh(self.root,now=NOW)['capabilities']['own_posts']['state'],'partial')

    def test_expired_status(self):
        ingest(self.root,envelope(),now=NOW)
        self.assertEqual(status(self.root,NOW+timedelta(days=10))['capabilities']['own_posts']['state'],'stale')

    def test_config_credentials_refused(self):
        atomic_save(self.root,'sources.json',{'schema_version':1,'providers':[],'token':'bad'})
        with self.assertRaises(ValueError):config(self.root)

    def test_config_traversal_refused(self):
        atomic_save(self.root,'sources.json',{'schema_version':1,'providers':[{'id':'x','source_type':'manual','enabled':True,'path':'imports/../../secret','capabilities':['profile']}]})
        with self.assertRaises(ValueError):config(self.root)

    def test_optional_tools_no_hard_dependency(self):
        from unittest.mock import patch
        with patch('read_layer.shutil.which',return_value=None):
            result=tools(self.root)
        self.assertFalse(result['agent_reach']['installed'])
        self.assertFalse(result['agent_reach']['enabled'])
        self.assertEqual(result['network_calls'],0)
        self.assertEqual(brief(self.root,NOW)['actions'],[])

    def test_purge_preview_preserves_then_explicit_purge(self):
        initialize(self.root)
        ingest(self.root,envelope(),now=NOW)
        (self.root/'imports').mkdir()
        (self.root/'imports/source.json').write_text('{}')
        self.assertEqual(len(purge(self.root)['would_remove']),2)
        self.assertTrue((self.root/'read/cache.json').exists())
        self.assertEqual(purge(self.root,True)['removed'],2)
        self.assertTrue((self.root/'identity/voice.md').exists())
        self.assertTrue((self.root/'relationships.json').exists())
        self.assertEqual(brief(self.root,NOW)['actions'],[])

    def test_cache_symlink_refused(self):
        (self.root/'read').mkdir(parents=True)
        outside=Path(self.tmp.name)/'outside';outside.write_text('keep')
        (self.root/'read/cache.json').symlink_to(outside)
        with self.assertRaises(ValueError):ingest(self.root,envelope(),now=NOW)
        self.assertEqual(outside.read_text(),'keep')

    def test_purge_symlink_refused(self):
        (self.root/'imports').mkdir(parents=True)
        outside=Path(self.tmp.name)/'outside';outside.write_text('keep')
        (self.root/'imports/link').symlink_to(outside)
        with self.assertRaises(ValueError):purge(self.root,True)
        self.assertEqual(outside.read_text(),'keep')


class IntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'.linkedin-agent'

    def test_one_high_value_reply(self):
        comment=item('comment','c1','own_comments',parent_post='p1',text='Have you measured review time after the change?')
        ingest(self.root,envelope([item(),comment]),now=NOW)
        result=brief(self.root,NOW)
        self.assertEqual(len(result['actions']),1)
        self.assertEqual(result['actions'][0]['category'],'RESPOND')
        self.assertEqual(result['actions'][0]['label'],'INFERRED')
        self.assertIn('{{',result['actions'][0]['draft']['text'])

    def test_many_low_value_signals(self):
        comments=[item('comment',f'c{x}','own_comments',parent_post='p1',text='Great post!') for x in range(30)]
        ingest(self.root,envelope([item(),*comments]),now=NOW)
        self.assertEqual(brief(self.root,NOW)['actions'],[])

    def test_relevance_not_enough_for_comment(self):
        atomic_save(self.root,'priorities.json',{'topics':['review'],'projects':[]})
        ingest(self.root,envelope([item('post','network-p1','public_posts',text='Review workflows deserve attention.')]),now=NOW)
        self.assertEqual(brief(self.root,NOW)['actions'],[])

    def test_substantive_contribution_required(self):
        atomic_save(self.root,'priorities.json',{'topics':['review'],'projects':[]})
        signal=item('post','network-p1','public_posts',text='Review workflows deserve attention.')
        signal['assessment']={'can_contribute':True}
        ingest(self.root,envelope([signal]),now=NOW)
        self.assertEqual(brief(self.root,NOW)['actions'][0]['category'],'COMMENT')

    def test_competing_priorities_reply_before_comment(self):
        comment=item('comment','reply','own_comments',parent_post='p1',text='Have you measured the change against the prior review?')
        network=item('post','network','public_posts',text='Review tools')
        network['assessment']={'can_contribute':True,'relevance':1}
        ingest(self.root,envelope([item(),network,comment]),now=NOW)
        self.assertEqual([a['category'] for a in brief(self.root,NOW)['actions']],['RESPOND','COMMENT'])
    def test_cross_provider_reply_retains_all_observations(self):
        c=item('comment','reply','own_comments',text='Have you measured the review change?')
        c['assessment']={'reply_expected':True}
        ingest(self.root,envelope([c]),now=NOW)
        ingest(self.root,envelope([c],source=source(provider='second')),now=NOW)
        actions=brief(self.root,NOW)['actions']
        self.assertEqual(len(actions),1)
        self.assertEqual({o['provider'] for o in actions[0]['observations']},{'manual-1','second'})
    def test_private_duplicate_does_not_hide_public_reply(self):
        c=item('comment','reply','own_comments',text='Have you measured the review change?')
        c['assessment']={'reply_expected':True}
        ingest(self.root,envelope([c]),now=NOW)
        private=envelope([c],source=source(provider='private',visibility='private',retrieved_at='2026-10-02T10:00:00Z'))
        ingest(self.root,private,allow_private=True,now=NOW)
        actions=brief(self.root,NOW)['actions']
        self.assertEqual(len(actions),1)
        self.assertEqual(actions[0]['source']['visibility'],'public')
        self.assertEqual(len(actions[0]['observations']),1)

    def test_stale_data_no_urgency(self):
        comment=item('comment','c1','own_comments',parent_post='p1',timestamp='2026-09-01T08:00:00Z',text='Have you measured review time after the change?')
        ingest(self.root,envelope([item(),comment]),now=NOW)
        result=brief(self.root,NOW)
        self.assertEqual(result['actions'],[])
        self.assertEqual(result['stale_or_undated'][0]['state'],'stale')

    def test_unknown_event_no_action(self):
        msg=item('message','m1','inbox',timestamp=None)
        msg['assessment']={'reply_expected':True}
        ingest(self.root,envelope([msg]),allow_private=True,now=NOW)
        self.assertEqual(brief(self.root,NOW,include_private=True)['actions'],[])

    def test_resolved_no_reply(self):
        c=item('comment','c1','own_comments',parent_post='p1',text='Have you measured review time after the change?')
        c['assessment']={'resolved':True}
        ingest(self.root,envelope([item(),c]),now=NOW)
        self.assertEqual(brief(self.root,NOW)['actions'],[])

    def test_max_five(self):
        comments=[item('comment',f'c{x}','own_comments',parent_post='p1',text='Have you measured review time after the change?') for x in range(10)]
        ingest(self.root,envelope([item(),*comments]),now=NOW)
        result=brief(self.root,NOW)
        self.assertEqual(len(result['actions']),5)
        self.assertEqual(result['suppressed_candidates'],5)

    def test_follow_up_explicit_only(self):
        person={'id':'peer','name':'Example peer','why_they_matter':'Pending research question','owes_reply':True,
                'relationship_type':'professional peer','provenance':source(visibility='private')}
        atomic_save(self.root,'relationships.json',{'schema_version':1,'people':[person]})
        self.assertEqual(brief(self.root,NOW)['actions'][0]['category'],'FOLLOW UP')
        person['owes_reply']=None
        atomic_save(self.root,'relationships.json',{'schema_version':1,'people':[person]})
        self.assertEqual(brief(self.root,NOW)['actions'],[])

    def test_future_relationship_does_not_create_followup(self):
        person={'id':'peer','name':'Example peer','why_they_matter':'Pending question','owes_reply':True,
                'provenance':source(retrieved_at='2027-01-01T08:00:00Z')}
        atomic_save(self.root,'relationships.json',{'schema_version':1,'people':[person]})
        result=brief(self.root,NOW)
        self.assertEqual(result['actions'],[])
        self.assertEqual(result['stale_or_undated'][0]['state'],'invalid-future')

    def test_complete_empty_refresh_no_phantom_brief(self):
        sample=json.loads((ROOT/'skills/li-read/assets/sample-read.json').read_text())
        ingest(self.root,sample,now=NOW)
        empty={**sample,'source':{**sample['source'],'retrieved_at':RECENT},'coverage':'complete','items':[]}
        ingest(self.root,empty,now=NOW)
        self.assertEqual(brief(self.root,NOW)['actions'],[])
        self.assertEqual(len(memory(self.root)),1)

    def test_sensitive_relationship_field_refused(self):
        person={'id':'peer','religion':'unsupported enrichment','provenance':source()}
        atomic_save(self.root,'relationships.json',{'schema_version':1,'people':[person]})
        with self.assertRaises(ValueError):load_relationships(self.root)

    def test_weekly_no_vanity_inference(self):
        initialize(self.root)
        append_history(self.root,{'id':'p1','date':'2026-10-01','topic':'review','angle':'new field','hook':'The checklist missed it.','body':'Actual published copy.','cta':'','metrics':{'reactions':100}},True)
        result=weekly(self.root,NOW)
        self.assertEqual(result['published_posts'],1)
        observation=result['performance_learning'][0]['observations']
        self.assertEqual(observation['reactions'],100)
        self.assertIsNone(observation['opportunities'])
        self.assertIsNone(observation['meaningful_comments'])
    def test_weekly_history_uses_same_rolling_window_as_read_activity(self):
        for day in ('2026-09-25','2026-09-26','2026-10-02','2026-10-03'):
            append_history(self.root,{'id':day,'date':day,'topic':'review','angle':'field','hook':'Checklist','body':'Actual published copy.','cta':''},True)
        result=weekly(self.root,NOW)
        self.assertEqual(result['published_posts'],2)

    def test_history_extended_metadata(self):
        append_history(self.root,{'id':'p1','date':'2026-10-01','topic':'review','angle':'new field','hook':'The checklist missed it.','body':'Actual copy.','cta':'','project':'Checklist','company':'Example Co','people_mentioned':['Example peer'],'evidence_used':['public-report']},True)
        summary=summarize(self.root)
        self.assertEqual(summary['company_counts'],{'Example Co':1})
        self.assertEqual(summary['project_counts'],{'Checklist':1})
        self.assertEqual(summary['people_counts'],{'Example peer':1})

    def test_import_not_confirmed_publication_history(self):
        ingest(self.root,envelope(),now=NOW)
        self.assertEqual(weekly(self.root,NOW)['published_posts'],0)

    def test_sample_selective(self):
        payload=json.loads((ROOT/'skills/li-read/assets/sample-read.json').read_text())
        ingest(self.root,payload,now=NOW)
        result=brief(self.root,NOW)
        self.assertEqual([a['id'] for a in result['actions']],['demo-c1','demo-n1'])
        self.assertNotIn('demo-c2',[a['id'] for a in result['actions']])

    def test_imported_prior_post_lookup(self):
        ingest(self.root,envelope(),now=NOW)
        found=memory_lookup(self.root,'review field')
        self.assertEqual(len(found),1)
        self.assertFalse(found[0]['confirmed_publication'])
        self.assertEqual(found[0]['date'],RECENT)
        self.assertIsNone(found[0]['topic'])

    def test_imported_hook_repetition(self):
        ingest(self.root,envelope(),now=NOW)
        found=memory_overlap(self.root,{'hook':'We added a review field.'})
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]['reasons'][0]['field'],'hook')
        self.assertFalse(found[0]['confirmed_publication'])

    def test_memory_does_not_write_history(self):
        ingest(self.root,envelope(),now=NOW)
        memory(self.root)
        self.assertFalse((self.root/'history/posts.jsonl').exists())

    def test_action_boundary_api(self):
        forbidden={'publish','post','comment','reply','like','react','connect','follow','send_message','send_dm','edit_profile','upload'}
        for cls in (FileProvider,ReadProvider):
            self.assertFalse(forbidden.intersection(name for name in dir(cls) if callable(getattr(cls,name,None))))
        import ast
        for path in READ.glob('*.py'):
            parsed=ast.parse(path.read_text())
            imports={node.names[0].name for node in ast.walk(parsed) if isinstance(node,ast.Import)}
            self.assertFalse(imports & {'requests','httpx','subprocess','socket','selenium','playwright'})
            for node in ast.walk(parsed):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                    self.assertNotIn(node.func.id,{'eval','exec'})


if __name__=='__main__':
    unittest.main()
