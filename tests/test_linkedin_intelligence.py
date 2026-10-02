"""Risk tiers, session discovery, retention, identity and large authorized datasets."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/li-research/scripts'))
from orchestrator import Provider,request,execute,choose
from discovery import prepare_request,classify_intent
from discovery_workflow import session_discovery,cached,read_cache,enrichment_plan,enrich_candidates,cache_key
from evidence import normalize
from read_layer import ingest,load_cache,status
NOW=datetime(2026,10,2,tzinfo=timezone.utc)


def req(**kw):
    return {'operation':'discover_linkedin','purpose':'COMPANY_RESEARCH','public_input':True,
            'query':'Find LinkedIn biomechanics researchers','max_age_hours':24,**kw}


def row(i=0,organization='Example University'):
    return {'url':f'https://linkedin.com/in/person-{i}','title':f'Jane Example {i} biomechanics {organization}',
            'display_name_if_available':f'Jane Example {i}','snippet':f'biomechanics at {organization}'}


def packet(queries,rows):
    return {'source':'codex_session_search','searches':[{'query':q,'retrieved_at':NOW.isoformat(),'results':r} for q,r in zip(queries,rows)]}


class IntelligenceTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def run_rows(self,value=None):
        value=value or req()
        return session_discovery(self.root,value,packet(request(value)['queries'],[[row(i) for i in range(100)]]),NOW)
    def test_defaults_and_requested_limits(self):
        for limit in (25,50,100,1000):
            with tempfile.TemporaryDirectory() as d:
                value=req(limit=limit)
                result=session_discovery(d,value,packet([value['query']],[[row(i) for i in range(100)]]),NOW)
                self.assertEqual(len(result['candidates']),min(limit,100))
        self.assertEqual(request(req())['limit'],25);self.assertEqual(request(req())['query_budget'],3)
        self.assertEqual(request(req(query='Find 10,000 LinkedIn profiles'))['limit'],100)
    def test_ten_queries_max_and_cross_query_dedup(self):
        queries=[f'LinkedIn biomechanics specialty {i}' for i in range(10)]
        value=req(queries=queries,query_budget=10,limit=100)
        rows=[[row(0),row(i+1)] for i in range(10)]
        result=session_discovery(self.root,value,packet(queries,rows),NOW)
        self.assertEqual(result['limits']['queries_used'],10);self.assertEqual(len(result['candidates']),11)
        shared=next(r for r in result['candidates'] if r['linkedin_url'].endswith('person-0'))
        self.assertEqual(len(shared['search_observations']),10)
        with self.assertRaises(ValueError):request(req(queries=queries+['extra'],query_budget=10))
    def test_each_query_requests_only_remaining_candidates(self):
        limits=[]
        def index(r):
            limits.append(r['limit'])
            offset=0 if len(limits)==1 else 10
            return [row(i+offset) for i in range(10 if len(limits)==1 else r['limit'])]
        p=Provider('agent_reach_discovery',frozenset({'LINKEDIN_DISCOVERY'}),True,retrieve=index)
        result=execute(req(queries=['biomechanics one','biomechanics two']),[p],self.root,NOW)
        self.assertEqual(limits,[25,15]);self.assertEqual(len(result['candidates']),25)

    def test_stop_when_requested_count_reached(self):
        calls=[]
        p=Provider('agent_reach_discovery',frozenset({'LINKEDIN_DISCOVERY'}),True,retrieve=lambda r:calls.append(r['query']) or [row(i) for i in range(50)])
        result=execute(req(queries=['biomechanics first','biomechanics second']),[p],self.root,NOW)
        self.assertEqual(len(calls),1);self.assertEqual(len(result['candidates']),25)
    def test_queries_stop_when_no_new_candidates_added(self):
        queries=['biomechanics first','biomechanics second','biomechanics third']
        calls=[]
        p=Provider('agent_reach_discovery',frozenset({'LINKEDIN_DISCOVERY'}),True,retrieve=lambda r:calls.append(r['query']) or [row()])
        result=execute(req(queries=queries),[p],self.root,NOW)
        self.assertEqual(len(calls),2);self.assertEqual(len(result['candidates']),1)

    def test_cache_reuses_search_and_has_only_minimal_metadata(self):
        result=self.run_rows()
        hit=cached(self.root,request(req()),NOW+timedelta(hours=1))
        self.assertEqual(len(hit['candidates']),25)
        stored=(self.root/'discovery/cache.json').read_text()
        self.assertNotIn('profile_html',stored);self.assertNotIn('public_research',stored)
        self.assertFalse((self.root/'read/cache.json').exists());self.assertFalse((self.root/'relationships.json').exists())
        self.assertEqual(result['transport'],'codex_session_search')
    def test_discovery_cache_honors_task_freshness_budget(self):
        self.run_rows()
        self.assertIsNone(cached(self.root,request(req(max_age_hours=0)),NOW))
        self.assertIsNone(cached(self.root,request(req(max_age_hours=1)),NOW+timedelta(hours=2)))
        self.assertIsNotNone(cached(self.root,request(req(max_age_hours=3)),NOW+timedelta(hours=2)))

    def test_cached_execute_does_not_call_provider(self):
        self.run_rows()
        p=Provider('agent_reach_discovery',frozenset({'LINKEDIN_DISCOVERY'}),True,retrieve=lambda r:self.fail('Repeated index call'))
        result=execute(req(),[p],self.root,NOW+timedelta(hours=1))
        self.assertEqual(result['state'],'CACHED');self.assertEqual(result['queries_used_now'],0)
    def test_repeated_empty_queries_stop_before_full_budget(self):
        queries=[f'biomechanics variation {i}' for i in range(10)];calls=[]
        p=Provider('agent_reach_discovery',frozenset({'LINKEDIN_DISCOVERY'}),True,retrieve=lambda r:calls.append(r['query']) or [])
        execute(req(queries=queries,query_budget=10),[p],self.root,NOW)
        self.assertEqual(len(calls),2)

    def test_cache_retention_bound_and_private_permissions(self):
        for i in range(25):
            now=NOW+timedelta(seconds=i);value=req(query=f'Find LinkedIn biomechanics {i}')
            handoff=packet([value['query']],[[row(i)]])
            handoff['searches'][0]['retrieved_at']=now.isoformat()
            session_discovery(self.root,value,handoff,now)
        cache=read_cache(self.root,NOW+timedelta(seconds=30))
        self.assertEqual(len(cache['tasks']),20)
        self.assertEqual((self.root/'discovery/cache.json').stat().st_mode & 0o777,0o600)
        self.assertEqual((self.root/'discovery').stat().st_mode & 0o777,0o700)

    def test_cache_rejects_opaque_envelope_fields(self):
        self.run_rows();path=self.root/'discovery/cache.json';data=json.loads(path.read_text());data['private_blob']='not metadata';path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):cached(self.root,request(req()),NOW)

    def test_expired_cache_purged_on_access(self):
        self.run_rows();self.assertIsNone(cached(self.root,request(req()),NOW+timedelta(hours=25)))
        self.assertEqual(json.loads((self.root/'discovery/cache.json').read_text())['tasks'],{})
    def test_ttl_config_bounded_and_nan_rejected(self):
        for ttl in (0,73,float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):request(req(cache_ttl_hours=ttl))
        self.assertEqual(request(req(cache_ttl_hours=12))['cache_ttl_hours'],12)
    def test_cache_symlink_refused(self):
        (self.root/'discovery').symlink_to(self.root.parent,target_is_directory=True)
        with self.assertRaises(ValueError):cached(self.root,request(req()),NOW)
    def test_malformed_and_tampered_cache_refused(self):
        self.run_rows();p=self.root/'discovery/cache.json';data=json.loads(p.read_text())
        entry=next(iter(data['tasks'].values()));entry['result']['candidates'][0]['verification']='VERIFIED'
        p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):cached(self.root,request(req()),NOW)
    def test_unmatched_or_future_search_receipts_refused(self):
        value=packet(['wrong'],[[row()]])
        with self.assertRaises(ValueError):session_discovery(self.root,req(),value,NOW)
        value=packet([req()['query']],[[row()]])
        value['searches'][0]['retrieved_at']=(NOW+timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):session_discovery(self.root,req(),value,NOW)
    def test_handoff_cannot_claim_exa_or_unknown_scraper_transport(self):
        value=packet([req()['query']],[[row()]])
        for name in ('exa','linkedin-scraper','jina'):
            value['source']=name
            with self.assertRaises(ValueError):session_discovery(self.root,req(),value,NOW)
    def test_contact_and_private_query_refused(self):
        for query in ('Find LinkedIn contacts secret@example.com','confidential investor message LinkedIn research','<script>find</script> LinkedIn people'):
            with self.assertRaises(ValueError):request(req(query=query))
        with self.assertRaises(ValueError):request({**req(),'relationship_notes':'private'})
    def test_import_and_automation_intents_distinct(self):
        for text,expected in (('Analyze my imported LinkedIn profile','LINKEDIN_IMPORTED_DATA'),('Open this LinkedIn profile and scrape it','LINKEDIN_DIRECT_AUTOMATION'),('Send this person a connection request','LINKEDIN_DIRECT_AUTOMATION')):
            self.assertEqual(classify_intent(text),expected)
        self.assertIsNone(classify_intent('Research this professor'))
        self.assertEqual(choose(request({**req(),'operation':'imported_linkedin'}),[])['state'],'LINKEDIN_IMPORTED_DATA')
    def test_direct_actions_and_api_never_invoke_provider(self):
        p=Provider('scrapling',frozenset({'LINKEDIN_DIRECT_AUTOMATION','LINKEDIN_APPROVED_API'}),True,retrieve=lambda r:self.fail('Unsafe provider invoked'))
        for op,state in (('linkedin_automation','DISABLED'),('approved_linkedin_api','UNAVAILABLE')):
            self.assertEqual(execute({**req(),'operation':op},[p],self.root,NOW)['state'],state)
    def test_no_security_override_request_fields(self):
        for key in ('allow_linkedin','stealth','cookies','solve_cloudflare','auto_publish','api_scopes','direct_fetch_limit'):
            with self.assertRaises(ValueError):request({**req(),key:True})
    def test_default_and_max_enrichment_bounds(self):
        result=self.run_rows()
        self.assertEqual(len(enrichment_plan(result,request(req()))),10)
        self.assertEqual(len(enrichment_plan(result,request(req(enrichment_limit=20)))),20)
        self.assertEqual(enrichment_plan(result,request(req(enrichment_limit=0))),[])
        with self.assertRaises(ValueError):request(req(enrichment_limit=21))
    def test_enrichment_query_uses_normal_public_router(self):
        plan=enrichment_plan(self.run_rows(),request(req()))
        self.assertIsNone(classify_intent(plan[0]['query']))
    def test_enrichment_no_names_does_not_invent_identity(self):
        result=self.run_rows()
        for candidate in result['candidates']:candidate['display_name_if_available']=None
        self.assertEqual(enrichment_plan(result,request(req())),[])
    def public_receipt(self,name='Jane Example 0',signal='Example University'):
        return {'url':'https://university.example.org/bio','opened':True,'provider':'scrapling',
                'content':name+' researches biomechanics at '+signal,'retrieved_at':NOW.isoformat(),
                'identity_signals':[{'kind':'organization','value':signal}]}
    def test_public_enrichment_identity_and_reranking(self):
        result=self.run_rows();chosen=result['candidates'][2];target=chosen['linkedin_url']
        result=enrich_candidates(result,request(req()),lambda task:[self.public_receipt(chosen['display_name_if_available'])] if task['linkedin_url']==target else [],NOW)
        self.assertEqual(result['auto_enriched'],1);self.assertEqual(result['enrichment_attempted'],10)
        self.assertEqual(result['candidates'][0]['linkedin_url'],target)
        self.assertEqual(result['candidates'][0]['identity_status'],'CORROBORATED_INFERRED')
        self.assertEqual(result['candidates'][0]['verification'],'SEARCH_METADATA')
        self.assertEqual(result['candidates'][0]['public_research'][0]['verification'],'NEEDS_VERIFICATION')
    def test_composed_enrichment_preserves_cache_and_provenance(self):
        index_calls=[]
        p=Provider('agent_reach_discovery',frozenset({'LINKEDIN_DISCOVERY'}),True,retrieve=lambda r:index_calls.append(r['query']) or [row()])
        result=execute(req(enrichment_limit=1),[p],self.root,NOW,enrichment_handler=lambda task:[self.public_receipt()])
        self.assertEqual(result['auto_enriched'],1);self.assertEqual(len(result['attempts']),1)
        self.assertEqual(len(result['candidates'][0]['search_observations']),1)
        hit=execute(req(enrichment_limit=1),[p],self.root,NOW+timedelta(hours=1),enrichment_handler=lambda task:[self.public_receipt()])
        self.assertEqual(hit['state'],'CACHED');self.assertEqual(hit['auto_enriched'],1);self.assertEqual(len(index_calls),1)
        stored=(self.root/'discovery/cache.json').read_text();self.assertNotIn('public_research',stored)

    def test_same_name_alone_stays_ambiguous(self):
        receipt=self.public_receipt();receipt['identity_signals']=[]
        result=enrich_candidates(self.run_rows(),request(req(enrichment_limit=1)),lambda task:[receipt],NOW)
        self.assertEqual(result['candidates'][0]['identity_status'],'AMBIGUOUS')
    def test_conflicting_organization_stays_ambiguous(self):
        result=enrich_candidates(self.run_rows(),request(req(enrichment_limit=1)),lambda task:[self.public_receipt(signal='Another University')],NOW)
        self.assertEqual(result['candidates'][0]['identity_status'],'AMBIGUOUS')
    def test_enrichment_rejects_linkedin_jina_private_and_snippets(self):
        for url in ('https://linkedin.com/in/p','https://r.jina.ai/https://linkedin.com/in/p','http://127.0.0.1/'):
            receipt={**self.public_receipt(),'url':url}
            result=enrich_candidates(self.run_rows(),request(req(enrichment_limit=1)),lambda task:[receipt],NOW)
            self.assertEqual(result['candidates'][0]['public_research'],[])
        receipt={**self.public_receipt(),'opened':False}
        result=enrich_candidates(self.run_rows(),request(req(enrichment_limit=1)),lambda task:[receipt],NOW)
        self.assertEqual(result['candidates'][0]['public_research'],[])
    def test_enrichment_calls_at_most_twenty(self):
        calls=[]
        result=enrich_candidates(self.run_rows(),request(req(enrichment_limit=20)),lambda task:calls.append(task['query']) or [],NOW)
        self.assertEqual(len(calls),20);self.assertEqual(result['enrichment_attempted'],20);self.assertEqual(result['auto_enriched'],0)
    def test_enrichment_cannot_promote_discovery_evidence(self):
        candidate=self.run_rows()['candidates'][0]
        with self.assertRaises(ValueError):normalize({**candidate,'url':candidate['linkedin_url'],'content':'snippet'},'search',NOW)
    def test_enrichment_result_tampering_cannot_promote_snippets(self):
        result=self.run_rows();result['candidates'][0]['verification']='VERIFIED'
        with self.assertRaises(ValueError):enrich_candidates(result,request(req()),lambda task:[],NOW)

    def test_enrichment_drops_opaque_fields_and_restores_zero_boundaries(self):
        result=self.run_rows();result['private_notes']='not metadata';result['limits']['linkedin_page_fetches']=99
        result['candidates'][0]['private_notes']='not metadata'
        output=enrich_candidates(result,request(req(enrichment_limit=0)),lambda task:self.fail('No enrichment'),NOW)
        self.assertNotIn('private_notes',json.dumps(output));self.assertEqual(output['limits']['linkedin_page_fetches'],0)

    def test_health_distinguishes_session_and_standalone(self):
        sys.path.insert(0,str(ROOT/'tools/web'))
        spec=importlib.util.spec_from_file_location('intelligence_bridge',ROOT/'tools/web/research.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cap=module.linkedin_capabilities([],self.root,True)
        self.assertEqual(cap['discovery']['state'],'PARTIAL');self.assertEqual(cap['approved_api']['state'],'UNAVAILABLE')
        self.assertEqual(cap['direct_scraping'],'DISABLED');self.assertEqual(cap['automated_actions'],'DISABLED')
        self.assertEqual(cap['imported_data']['profile']['adapter'],'AVAILABLE')
        self.assertEqual(cap['imported_data']['profile']['state'],'UNAVAILABLE')
        health=module.agent_reach_health([],self.root,True)
        self.assertEqual(health['linkedin_scraper'],'DISABLED');self.assertNotIn('READY',str(health))
        path=self.root/'discovery/validation.json';path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({'private_inbox':'must not appear in status'}))
        with self.assertRaises(ValueError):module.agent_reach_health([],self.root,True)

    def test_large_authorized_dataset_ignores_discovery_caps(self):
        counts={'post':2000,'comment':400,'person':1500,'analytics':600}
        caps={'post':'own_posts','comment':'own_comments','person':'network','analytics':'analytics'}
        data={'post':{'text':'Historical project insight','reactions':7},'comment':{'text':'Supplied discussion comment'},'person':{'name':'Exported contact','company':'Example organization'},'analytics':{'date':'2026-01-01','impressions':1000}}
        items=[{'kind':kind,'id':f'{kind}-{i}','capability':caps[kind],'data':data[kind]} for kind,count in counts.items() for i in range(count)]
        source={'type':'user_export','provider':'authorized-export','identifier':'user-file','retrieved_at':NOW.isoformat(),'visibility':'public'}
        envelope={'schema_version':1,'source':source,'capabilities':list(caps.values()),'items':items,'coverage':'partial'}
        result=ingest(self.root,envelope,now=NOW)
        self.assertEqual(result['new'],4500);self.assertEqual(len(load_cache(self.root)['items']),4500)
        for kind,count in counts.items():self.assertEqual(status(self.root,NOW)['capabilities'][caps[kind]]['cached_items'],count)
    def test_full_local_history_processed_without_discovery_caps(self):
        from context import load_history
        path=self.root/'history/posts.jsonl';path.parent.mkdir()
        with path.open('w') as f:
            for i in range(2000):
                record={'id':str(i),'date':'2026-01-01','topic':'engineering','angle':'project insight','hook':'A specific lesson','body':f'Actual supplied example {i}','cta':'','tags':[],'metrics':{}}
                f.write(json.dumps(record)+'\n')
        self.assertEqual(len(load_history(self.root)),2000)

    def test_private_import_still_requires_opt_in(self):
        envelope={'schema_version':1,'source':{'type':'user_export','provider':'private','identifier':'export','retrieved_at':NOW.isoformat(),'visibility':'private'},'capabilities':['inbox'],'coverage':'partial','items':[{'kind':'message','id':'m1','capability':'inbox','data':{'text':'private'}}]}
        with self.assertRaises(ValueError):ingest(self.root,envelope,now=NOW)
        self.assertEqual(ingest(self.root,envelope,allow_private=True,now=NOW)['new'],1)

if __name__=='__main__':unittest.main()
