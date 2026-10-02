"""Deterministic account gateway, evidence retention and refresh invariants."""
import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/linkedin'))
sys.path.insert(0,str(ROOT/'skills/li-read/scripts'))
from gateway import Gateway, clean, safe_url
from policy import TOOLS, set_enabled, begin_task, load, save, enabled, minimal_public_query
from account_context import retain, refresh_plan
from read_layer import load_cache
spec=importlib.util.spec_from_file_location('linkedin_setup',ROOT/'tools/linkedin/setup.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)


class FakeUpstream:
    def __init__(self,value=None):
        self.calls=[];self.closed=0
        self.value=value if value is not None else {'url':'https://www.linkedin.com/in/example/',
          'sections':{'main_profile':'Example professional','experience':'Example role','posts':'Observed post','feed':'Observed feed'}}
    async def call(self,name,args):
        self.calls.append((name,args))
        if isinstance(self.value,BaseException): raise self.value
        return self.value
    async def close(self): self.closed+=1


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.up=FakeUpstream();self.g=Gateway(self.root,self.up)
        set_enabled(self.root,True);begin_task(self.root)
    def tearDown(self):self.temp.cleanup()
    def call(self,name,args=None):return asyncio.run(self.g.dispatch(name,args))
    def receipt(self,cap='profile'):
        return self.call('read_my_profile' if cap=='profile' else 'read_my_posts' if cap=='own_posts' else 'read_feed')
    def test_empty_observed_posts_are_fresh(self):
        self.up.value={'sections':{'posts':'Nothing to see for now'}}
        packet=self.receipt('own_posts')
        retain(self.root,{'receipt_id':packet['receipt_id'],'items':[]})
        self.assertFalse(refresh_plan(self.root,['own_posts'])['own_posts']['refresh'])
    def test_unknown_empty_posts_still_need_refresh(self):
        self.up.value={'sections':{'posts':'Unavailable sample'}}
        packet=self.receipt('own_posts')
        retain(self.root,{'receipt_id':packet['receipt_id'],'items':[]})
        self.assertTrue(refresh_plan(self.root,['own_posts'])['own_posts']['refresh'])

    def test_catalogue_constant(self):self.assertEqual(TOOLS,('connector_status','read_my_profile','read_my_posts','read_feed','close_session'))
    def test_status_never_connects(self):self.call('connector_status');self.assertEqual(self.up.calls,[])
    def test_disabled_no_upstream(self):
        set_enabled(self.root,False);self.assertEqual(self.call('read_feed')['state'],'DISABLED');self.assertEqual(self.up.calls,[])
    def test_environment_kill_switch(self):
        with patch.dict(os.environ,{'LINKEDIN_ACCOUNT_CONNECTOR_ENABLED':'false'}): self.assertEqual(self.call('read_feed')['state'],'DISABLED')
        self.assertEqual(self.up.calls,[])
    def test_missing_task(self):
        (self.root/'account/task.json').unlink();self.assertEqual(self.call('read_feed')['state'],'TASK_REQUIRED');self.assertEqual(self.up.calls,[])
    def test_not_installed(self):
        self.g.installed=False;self.assertEqual(self.call('read_feed')['state'],'NOT_INSTALLED');self.assertEqual(self.up.calls,[])
    def test_feed_default(self):self.call('read_feed');self.assertEqual(self.up.calls,[('get_feed',{'num_posts':10})])
    def test_feed_max(self):self.call('read_feed',{'limit':20});self.assertEqual(self.up.calls[0][1]['num_posts'],20)
    def test_bad_limits(self):
        for n in (21,0,-1,'10',True,1.5,None):
            with self.assertRaises(ValueError):self.call('read_feed',{'limit':n})
        self.assertEqual(self.up.calls,[])
    def test_extra_arguments(self):
        for tool,args in [('read_feed',{'url':'https://linkedin.com'}),('read_my_profile',{'sections':'contact_info'}),('read_my_posts',{'max_scrolls':50})]:
            with self.assertRaises(ValueError):self.call(tool,args)
        self.assertEqual(self.up.calls,[])
    def test_profile_routine(self):
        self.call('read_my_profile');args=self.up.calls[0][1]
        self.assertEqual(args['max_scrolls'],2);self.assertNotIn('contact_info',args['sections'])
    def test_onboarding_requires_task(self):
        self.assertEqual(self.call('read_my_profile',{'stage':'experience'})['state'],'ONBOARDING_REQUIRED');self.assertEqual(self.up.calls,[])
    def test_onboarding_section_bounds(self):
        begin_task(self.root,True)
        for stage,n in [('experience',5),('professional',3),('interests',2)]:
            self.call('read_my_profile',{'stage':stage});self.assertEqual(self.up.calls[-1][1]['max_scrolls'],n)
    def test_own_posts_abstraction(self):
        self.call('read_my_posts');self.assertEqual(self.up.calls[0],('get_my_profile',{'sections':'posts','max_scrolls':2}))
    def test_duplicate_acquisition(self):
        self.call('read_feed');self.assertEqual(self.call('read_feed')['state'],'DUPLICATE_ACQUISITION');self.assertEqual(len(self.up.calls),1)
    def test_budget_four(self):
        value=load(self.root,'account/task.json',{});value['used']=4;save(self.root,'account/task.json',value)
        self.assertEqual(self.call('read_feed')['state'],'TASK_STOPPED_OR_BUDGET_EXHAUSTED');self.assertEqual(self.up.calls,[])
    def test_close_preserves_auth_and_cache(self):
        save(self.root,'account/observations/example.json',{'kept':True})
        self.call('close_session');self.assertEqual(self.up.closed,1);self.assertTrue((self.root/'account/observations/example.json').exists())
    def test_close_disabled_allowed(self):set_enabled(self.root,False);self.call('close_session');self.assertEqual(self.up.closed,1)
    def test_auth_failure_stops(self):
        self.up.value=RuntimeError('authentication expired password=secret')
        result=self.call('read_feed');self.assertEqual(result['state'],'NOT_AUTHENTICATED');self.assertNotIn('secret',json.dumps(result))
        self.call('read_my_posts');self.assertEqual(len(self.up.calls),1)
    def test_challenge_stops(self):
        self.up.value={'error':'AUTH_CHALLENGE'};self.assertEqual(self.call('read_feed')['state'],'AUTH_CHALLENGE')
        self.call('read_my_posts');self.assertEqual(len(self.up.calls),1)
    def test_restriction_stops(self):
        self.up.value={'sections':{},'section_errors':{'feed':{'message':'rate limited'}}}
        self.assertEqual(self.call('read_feed')['state'],'RATE_LIMIT_OR_RESTRICTION')
        self.call('read_my_posts');self.assertEqual(len(self.up.calls),1)
    def test_malformed_sections(self):
        self.up.value={'sections':{'feed':{'opaque':'data'}}};self.assertEqual(self.call('read_feed')['state'],'MALFORMED_RESPONSE')
    def test_partial_independent_capabilities(self):
        self.receipt();self.up.value={'sections':{},'section_errors':{'feed':'unavailable'}};self.receipt('feed')
        s=self.call('connector_status');self.assertEqual(s['capabilities']['profile']['state'],'PARTIAL_READ');self.assertEqual(s['capabilities']['feed']['state'],'PARTIAL_READ')
    def test_profile_section_status_accumulates(self):
        begin_task(self.root,True)
        self.call('read_my_profile',{'stage':'experience'})
        self.up.value={'sections':{'main_profile':'Example','interests':'Following example'}}
        self.call('read_my_profile',{'stage':'interests'})
        sections=self.call('connector_status')['capabilities']['profile']['sections']
        self.assertEqual(sections['experience'],'OBSERVED');self.assertEqual(sections['interests'],'OBSERVED')
    def test_empty_post_page_is_partial(self):
        self.up.value={'sections':{'posts':'Posts\nNothing to see for now'}}
        self.assertEqual(self.call('read_my_posts')['state'],'PARTIAL_READ')
    def test_sidebar_not_returned(self):
        self.assertEqual(clean('Career evidence\nWho your viewers also viewed\nUnrelated person'),'Career evidence\n')
    def test_main_profile_actual_shape(self):
        result=self.receipt();self.assertIn('main_profile',result['evidence_sections']);self.assertNotIn('posts',result['evidence_sections'])
    def test_no_positional_urls(self):
        self.up.value={'url':'https://www.linkedin.com/feed/','sections':{'feed':'A post\nAnother post'},'references':{'feed':[{'url':'/posts/b'},{'url':'/posts/a'}]}}
        result=self.receipt('feed');self.assertNotIn('references',result)
        with self.assertRaises(ValueError):retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'text':'A post','url':'https://linkedin.com/posts/b'}}]})
    def test_unknown_permalink_and_author(self):
        result=self.receipt('feed');retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'text':'Observed feed'}}]})
        d=load_cache(self.root)['items'][0]['data'];self.assertIsNone(d['url']);self.assertIsNone(d['author']);self.assertIsNone(d['timestamp'])
    def test_deduplicate_posts(self):
        result=self.receipt('own_posts');saved=retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'text':'Same'}},{'data':{'text':'Same'}}]})
        self.assertEqual(saved['retained'],1)
    def test_summary_inference_and_curated_preserved(self):
        p=self.root/'identity/voice.md';p.parent.mkdir();p.write_text('Curated voice')
        result=self.receipt();retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'name':'Example','education':None,'skills':[]}}],
          'summary':{'career':[{'text':'Example','label':'OBSERVED'}],'voice':[{'text':'Possible terse style','label':'INFERRED'}]}})
        self.assertEqual(p.read_text(),'Curated voice');self.assertEqual(len(list((self.root/'account/summaries').glob('*.json'))),1)
    def test_cannot_promote_voice_to_observed(self):
        result=self.receipt()
        with self.assertRaises(ValueError):retain(self.root,{'receipt_id':result['receipt_id'],'items':[], 'summary':{'voice':[{'text':'Voice','label':'OBSERVED'}]}})
    def test_missing_receipt(self):
        with self.assertRaises((ValueError,OSError)):retain(self.root,{'receipt_id':'0'*64,'items':[]})
    def test_secret_input_refused(self):
        result=self.receipt()
        with self.assertRaises(ValueError):retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'about':'password=secret'}}]})
    def test_unknown_metric_remains_null(self):
        result=self.receipt('own_posts');retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'text':'Post'}}]})
        self.assertIsNone(load_cache(self.root)['items'][0]['data']['impressions'])
    def test_no_confirmed_history(self):
        result=self.receipt('own_posts');retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'text':'Post'}}]})
        self.assertFalse((self.root/'history/posts.jsonl').exists())
    def test_timestamp_preserved(self):
        result=self.receipt();retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'name':'Example'}}]})
        self.assertEqual(load_cache(self.root)['items'][0]['provenance']['retrieved_at'],result['retrieved_at'])
    def test_private_permissions_and_no_raw(self):
        result=self.receipt();retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'name':'Example'}}]})
        if os.name!='nt':self.assertEqual((self.root/'read/cache.json').stat().st_mode&0o777,0o600)
        self.assertNotIn('evidence_sections',json.dumps(load(self.root,'account/receipts/'+result['receipt_id']+'.json',{})))
    def test_symlink_refused(self):
        (self.root/'account/control.json').unlink();(self.root/'account/control.json').symlink_to(self.root/'other')
        with self.assertRaises(ValueError):enabled(self.root)
    def test_cache_preserved_when_disabled(self):
        result=self.receipt();retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':{'name':'Example'}}]})
        set_enabled(self.root,False);self.assertFalse(refresh_plan(self.root,['profile'])['profile']['refresh'])
    def test_ttls_and_force(self):
        current=datetime.now(timezone.utc)
        for cap,days in [('profile',29),('own_posts',2),('feed',0)]:
            begin_task(self.root); result=self.receipt(cap)
            record=load(self.root,'account/receipts/'+result['receipt_id']+'.json',{})
            record['retrieved_at']=(current-timedelta(days=days,minutes=30)).isoformat();save(self.root,'account/receipts/'+result['receipt_id']+'.json',record)
            data={'name':'Example'} if cap=='profile' else {'text':cap}
            retain(self.root,{'receipt_id':result['receipt_id'],'items':[{'data':data}]})
        for row in refresh_plan(self.root,['profile','own_posts','feed'],current=current).values():self.assertFalse(row['refresh'])
        for row in refresh_plan(self.root,['profile','own_posts','feed'],force=True,current=current).values():self.assertTrue(row['refresh'])
        for row in refresh_plan(self.root,['profile','own_posts','feed'],current=current+timedelta(days=32)).values():self.assertTrue(row['refresh'])
    def test_simple_rewrite_no_read_plan(self):self.assertEqual(refresh_plan(self.root,[]),{})
    def test_minimal_public_query(self):
        self.assertEqual(minimal_public_query('research',['sports biomechanics']),'research sports biomechanics')
        with self.assertRaises(ValueError):minimal_public_query({'private':'career'},['topic'])
        with self.assertRaises(ValueError):minimal_public_query('topic',['private message secret'])
    def test_configuration_preserves_and_conflicts(self):
        base='[mcp_servers.scrapling_local]\ncommand="existing"\n'
        addition=setup.registration(ROOT); merged=setup.merge(base,addition);self.assertIn('command="existing"',merged)
        self.assertEqual(setup.merge(merged,addition),merged)
        with self.assertRaises(ValueError):setup.merge('[mcp_servers.linkedin_account]\ncommand="other"\n',addition)
    def test_career_dates_not_redacted(self):
        self.assertIn('2010 - 2024',clean('Engineer 2010 - 2024'))
    def test_nonobject_arguments_refused(self):
        for a in ([],False,0,''):
            with self.assertRaises(ValueError):self.call('read_feed',a)
        self.assertEqual(self.up.calls,[])
    def test_sanitization(self):
        value=clean('email@example.com password=secret authorization:token')
        self.assertNotIn('email@example.com',value);self.assertNotIn('secret',value)
        self.assertIsNone(safe_url('https://user:secret@linkedin.com/in/a'))
        self.assertEqual(safe_url('https://linkedin.com/in/a?token=x'),'https://linkedin.com/in/a')


def denied_test(operation):
    def run(self):
        with self.assertRaises(ValueError):self.call(operation)
        self.assertEqual(self.up.calls,[])
    return run
for operation in ('send_message','connect','like','comment','post','follow','edit_profile','unknown_tool','get_my_profile','get_inbox','get_conversation','search_people','raw_passthrough'):
    setattr(AccountTests,'test_denied_'+operation,denied_test(operation))

if __name__=='__main__':unittest.main()
