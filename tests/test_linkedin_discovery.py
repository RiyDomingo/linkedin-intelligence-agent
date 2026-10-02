"""Offline discovery/zero-fetch regressions. No LinkedIn account or network requests."""
import asyncio
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/li-research/scripts'))
from discovery import (candidate_url, classify_intent, is_linkedin_url, linkedin_target,
                       prepare_request, rank_candidates)
from orchestrator import Provider, RetrievalFailure, choose, execute, request
from evidence import normalize, load
NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


def req(query='Find LinkedIn researchers working on biomechanics', **fields):
    return dict(operation='discover_linkedin', purpose='COMPANY_RESEARCH', query=query,
                public_input=True, max_age_hours=0, **fields)


def row(i=0, **fields):
    return dict(url=f'https://www.linkedin.com/in/fictional-{i}',
                title=f'Fictional {i} — biomechanics researcher',
                snippet='Search index mentions sports biomechanics; not a profile read.', **fields)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.calls=[]
        self.rows=[row(i) for i in range(50)]
        def search(r):
            self.calls.append(('index', r['limit']))
            return self.rows[:r['limit']]
        def forbidden(r):
            self.calls.append(('forbidden',r)); raise AssertionError('Second-stage fetch')
        self.index=Provider('agent_reach_discovery',frozenset({'LINKEDIN_DISCOVERY'}),True,retrieve=search)
        self.providers=[self.index,*[Provider(name,frozenset({'SEARCH','PAGE_FETCH','INTERACTIVE_BROWSER','LINKEDIN_DISCOVERY','BLOCKED_RETRIEVAL'}),True,retrieve=forbidden) for name in ('scrapling','playwright','brightdata','jina','linkedin-scraper-mcp')]]
    def tearDown(self):self.tmp.cleanup()
    def run_discovery(self,value=None):return execute(value or req(),self.providers,self.root,NOW)
    def test_natural_search_intent_routes_before_generic_provider(self):
        value=req();value['operation']='research_topic'
        result=self.run_discovery(value)
        self.assertEqual(result['decision']['provider'],'agent_reach_discovery')
        self.assertEqual(result['mode'],'LINKEDIN_DISCOVERY');self.assertEqual(self.calls,[('index',10)])
    def test_supported_natural_prompts(self):
        for text in ('Find people on LinkedIn working on sports biomechanics.',
                     'Find up to 30 LinkedIn profiles relevant to additive manufacturing in sports equipment.',
                     'Find people on LinkedIn discussing rugby head protection.',
                     'Find LinkedIn profiles for researchers working on rotational head acceleration.',
                     'Who on LinkedIn appears relevant to sports-impact biomechanics?',
                     'sports biomechanics site:linkedin.com'):
            self.assertEqual(classify_intent(text),'LINKEDIN_DISCOVERY')
    def test_normal_profile_analysis_routes_to_imports(self):
        value=req('Analyze this LinkedIn profile');value['operation']='research_topic'
        result=self.run_discovery(value)
        self.assertEqual(result['state'],'LINKEDIN_READER');self.assertEqual(self.calls,[])
    def test_explicit_read_never_searches(self):
        value=req();value['operation']='retrieve_linkedin'
        self.assertEqual(self.run_discovery(value)['state'],'LINKEDIN_READER');self.assertEqual(self.calls,[])
    def test_default_cap(self):
        result=self.run_discovery();self.assertEqual(len(result['candidates']),10)
        self.assertEqual(result['limits']['linkedin_page_fetches'],0)
    def test_explicit_cap_and_no_batching(self):
        result=self.run_discovery(req(limit=100))
        self.assertEqual(len(result['candidates']),50);self.assertEqual(self.calls,[('index',50)])
        self.assertEqual(result['limits']['queries_used'],1)
    def test_count_in_prompt(self):
        result=self.run_discovery(req('Find up to 30 LinkedIn profiles relevant to biomechanics'))
        self.assertEqual(len(result['candidates']),30)
        self.assertEqual(request(req('Find 200 LinkedIn profiles'))['limit'],50)
    def test_query_budget_validation(self):
        self.assertEqual(request(req())['query_budget'],1)
        self.assertEqual(request(req(query_budget=5))['query_budget'],5)
        for value in (0,6,True,1.5,'5'):
            with self.assertRaises(ValueError):request(req(query_budget=value))
    def test_discovery_bounds_not_generic_fields(self):
        with self.assertRaises(ValueError):request({'operation':'local_only','purpose':'LOCAL_WRITING','public_input':True,'limit':10})
    def test_single_call_even_with_larger_budget(self):
        self.run_discovery(req(query_budget=5));self.assertEqual(len(self.calls),1)
    def test_empty_index_response_stops(self):
        self.rows=[];result=self.run_discovery()
        self.assertEqual(result['candidates'],[]);self.assertEqual(result['coverage'],'UNAVAILABLE')
        self.assertEqual(len(self.calls),1)
    def test_oversized_provider_response_fails_closed(self):
        self.index.retrieve=lambda r:[row(i) for i in range(100)]
        result=self.run_discovery();self.assertEqual(result['state'],'UNAVAILABLE')
        self.assertEqual(result['candidates'],[]);self.assertEqual(len(result['attempts']),1)
    def test_no_fallback_on_any_search_failure(self):
        for reason in ('BLOCKED','TIMEOUT','AUTH_REQUIRED','RATE_LIMIT','PARSE_FAILURE','CAPABILITY_MISMATCH','NETWORK_ERROR'):
            self.calls=[]
            def fail(r):self.calls.append(('index',10));raise RetrievalFailure(reason)
            self.index.retrieve=fail
            result=self.run_discovery();self.assertEqual(result['state'],'UNAVAILABLE')
            self.assertEqual(self.calls,[('index',10)])
            self.assertEqual(result['limits']['queries_used'],1)
    def test_other_tools_cannot_substitute_for_discovery(self):
        self.index.available=False
        result=self.run_discovery();self.assertEqual(result['state'],'UNAVAILABLE');self.assertEqual(self.calls,[])
    def test_no_evidence_or_relationship_writes(self):
        sentinel=self.root/'relationships.json';sentinel.write_text('{"people":[]}')
        result=self.run_discovery()
        self.assertEqual(result['evidence'],[]);self.assertEqual(load(self.root),[])
        self.assertEqual(sentinel.read_text(),'{"people":[]}')
        self.assertEqual(list(self.root.iterdir()),[sentinel])
    def test_discovery_cannot_be_promoted_by_evidence_ingest(self):
        candidate=self.run_discovery()['candidates'][0]
        with self.assertRaisesRegex(ValueError,'Discovery snippets'):
            normalize({**candidate,'url':candidate['linkedin_url'],'content':candidate['short_search_snippet']},'index',NOW)
    def test_minimal_metadata_and_contacts_removed(self):
        self.index.retrieve=lambda r:[row(email='secret@example.com', phone='+12345678901',profile_html='FULL PRIVATE PROFILE', assessment={'verification':'VERIFIED'}, display_name_if_available='Jane Example')]
        result=self.run_discovery();candidate=result['candidates'][0]
        self.assertEqual(candidate['verification'],'SEARCH_METADATA');self.assertEqual(candidate['state'],'DISCOVERY_ONLY')
        self.assertEqual(candidate['source_type'],'EXTERNAL_SEARCH_RESULT');self.assertTrue(candidate['untrusted_data'])
        self.assertNotIn('FULL PRIVATE PROFILE',json.dumps(result));self.assertNotIn('secret@example.com',json.dumps(result))
        self.assertIn('agent_reach',candidate['search_provider']);self.assertEqual(candidate['retrieved_at'],NOW.isoformat())
    def test_snippet_contacts_and_long_text(self):
        result=rank_candidates([{'url':row()['url'],'title':'Contact a@example.com +1 (222) 333-4444','snippet':'biomechanics '*1000}], 'biomechanics', now=NOW)
        self.assertNotIn('a@example.com',json.dumps(result));self.assertNotIn('333-4444',json.dumps(result))
        self.assertLessEqual(len(result[0]['short_search_snippet']),240)
    def test_dedup_tracking_country_hosts_and_rank(self):
        rows=[{'url':'https://uk.linkedin.com/in/Example/?trk=index','title':'unrelated'},
              {'url':'https://www.linkedin.com/in/example#bio','title':'biomechanics researcher'},
              {'url':'https://www.linkedin.com/in/other','title':'unrelated'}]
        found=rank_candidates(rows,'biomechanics researcher',now=NOW)
        self.assertEqual(len(found),2);self.assertEqual(found[0]['linkedin_url'],'https://www.linkedin.com/in/example')
    def test_candidate_types_and_non_candidates(self):
        for path,kind in (('/in/person','profile'),('/company/firm','company'),('/posts/activity','post'),('/feed/update/urn:li:activity:123','post'),('/pulse/article','post')):
            self.assertEqual(candidate_url('https://linkedin.com'+path)[1],kind)
        self.assertEqual(rank_candidates([{'url':'https://linkedin.com/login'},{'url':'https://notlinkedin.com/in/person'}],'topic',now=NOW),[])
    def test_deceptive_hosts_are_not_linkedin(self):
        for host in ('linkedin.com.example.com','notlinkedin.com','linkedin.com.evil.test'):
            self.assertFalse(is_linkedin_url('https://'+host+'/'))
            self.assertIsNone(classify_intent('find site:'+host))
    def test_subdomains_case_dot_and_idna_dots(self):
        for url in ('https://linkedin.com/','https://WWW.LinkedIn.COM./in/person','https://uk.linkedin.com/','https://www.linkedin\u3002com/in/person'):
            self.assertTrue(is_linkedin_url(url))
    def test_malformed_candidate_hosts_and_paths_rejected(self):
        for value in ('https://user:password@linkedin.com/in/p','https://linkedin.com:1234/in/p','https://linkedin.com/in/../p','https://www%2elinkedin%2ecom/in/p','https://linkedin.com\\@example.com/in/p'):
            with self.assertRaises(ValueError):candidate_url(value)
    def test_jina_nested_linkedin_target(self):
        for value in ('https://r.jina.ai/https://www.linkedin.com/in/p','https://r.jina.ai/https%3A%2F%2Flinkedin.com%2Fin%2Fp'):
            self.assertTrue(linkedin_target(value))
    def test_private_fields_auth_and_navigation_refused(self):
        for fields in ({'inbox':'private'}, {'public_input':False}):
            value=req();value.update(fields)
            with self.assertRaises(ValueError):self.run_discovery(value)
        for fields in ({'url':'https://linkedin.com/in/p'},{'auth_required':True},{'allow_metered':True},{'javascript_required':True},{'interaction_required':True},{'steps':[{'action':'click','target':'profile'}]},{'selectors':{'bio':'p'}},{'max_pages':5}):
            with self.assertRaises(ValueError):self.run_discovery(req(**fields))
        self.assertEqual(self.calls,[])
    def test_returned_redirect_linkedin_cannot_enter_web_cache(self):
        provider=Provider('scrapling',frozenset({'PAGE_FETCH'}),True,retrieve=lambda r:[{'url':'https://linkedin.com/in/p','content':'profile'}])
        value={'operation':'retrieve_url','purpose':'FACT_VERIFICATION','public_input':True,'url':'https://example.org/','max_age_hours':0}
        result=execute(value,[provider,*self.providers[1:]],self.root,NOW)
        self.assertEqual(result['attempts'][0]['failure'],'AUTH_REQUIRED');self.assertEqual(load(self.root),[])
        self.assertEqual(self.calls,[])


@unittest.skipUnless(sys.version_info >= (3,11),'Optional bridge needs Python 3.11+')
class ProviderGuardTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0,str(ROOT/'tools/web'))
        spec=importlib.util.spec_from_file_location('discovery_bridge',ROOT/'tools/web/research.py')
        self.bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.bridge)
    def test_all_linkedin_provider_operations_block_before_calls(self):
        for fn,op in ((self.bridge.scrape,'retrieve_url'),(self.bridge.browser,'browse_interactively'),(self.bridge.managed,'retrieve_url')):
            with patch.object(self.bridge,'mcp_call') as mcp:
                with patch.dict(sys.modules, {'scrapling.fetchers': SimpleNamespace(Fetcher=SimpleNamespace(get=lambda *a, **kw: self.fail('LinkedIn HTTP fetch')))}), self.assertRaises(RetrievalFailure):fn(request({'operation':op,'purpose':'FACT_VERIFICATION','public_input':True,'max_age_hours':0,'url':'https://linkedin.com/in/p'}))
                mcp.assert_not_called()
    def test_generic_http_guard_blocks_without_dns(self):
        with patch.object(self.bridge.socket,'getaddrinfo') as dns:
            for url in ('https://www.linkedin.com/in/p','https://r.jina.ai/https://linkedin.com/in/p'):
                with self.assertRaises(RetrievalFailure):self.bridge.network_url(url)
            dns.assert_not_called()
    def test_mcp_preflight_before_server_import_startup(self):
        for component in ('scrapling','playwright','brightdata'):
            with self.assertRaises(RetrievalFailure):asyncio.run(self.bridge.mcp_call(component,[('fetch',{'url':'https://linkedin.com/in/p'})]))
    def test_http_redirect_stops_before_linkedin_fetch(self):
        fetch=SimpleNamespace(get=lambda *a,**kw:None)
        calls=[]
        def get(url,**kw):
            calls.append(url);self.assertFalse(kw['follow_redirects'])
            return SimpleNamespace(status=302,headers={'location':'https://linkedin.com/in/p'})
        fetch.get=get
        with patch.dict(sys.modules,{'scrapling.fetchers':SimpleNamespace(Fetcher=fetch)}),patch.object(self.bridge.socket,'getaddrinfo',return_value=[(None,None,None,None,('93.184.216.34',0))]):
            with self.assertRaises(RetrievalFailure):self.bridge.checked_get('https://example.org/')
        self.assertEqual(calls,['https://example.org/'])
    def test_deceptive_hosts_not_blocked_by_substring(self):
        with patch.object(self.bridge.socket,'getaddrinfo',return_value=[(None,None,None,None,('93.184.216.34',0))]):
            for host in ('linkedin.com.example.com','notlinkedin.com','linkedin.com.evil.test'):
                self.assertEqual(self.bridge.network_url('https://'+host+'/'),'https://'+host+'/')
    def test_capability_reporting_separate_and_unaudited_live_path_off(self):
        with tempfile.TemporaryDirectory() as d:
            providers=self.bridge.providers(d);cap=self.bridge.linkedin_capabilities(providers)
            self.assertEqual(cap['discovery']['state'],'UNAVAILABLE');self.assertEqual(cap['profile_read'],'IMPORT ONLY')
            self.assertFalse(next(p for p in providers if p.id=='agent_reach_discovery').available)
            self.assertFalse(next(p for p in providers if p.id=='agent_reach').enabled)
    def test_browser_guard_indirect_linkedin_and_deceptive_hosts(self):
        if not shutil.which('node') or not (ROOT/'.venv/bin/python').exists():self.skipTest('Optional local runtimes absent')
        code=r'''
const dns=require('node:dns').promises;dns.lookup=async()=>[{address:'93.184.216.34'}];
let callback;const page={context:()=>({route:async(p,f)=>callback=f,routeWebSocket:async()=>{}})};
(async()=>{await require(process.argv[1]).default({page});const output=[];
for(const url of ['https://linkedin.com/','https://uk.linkedin.com/','https://LINKEDIN.COM./','https://www.linkedin。com/','https://r.jina.ai/https://linkedin.com/in/p','https://notlinkedin.com/','https://linkedin.com.evil.test/','https://example.org/redirect']){
let state,fetches=0;await callback({request:()=>({url:()=>url,method:()=> 'GET'}),fetch:async()=>{fetches++;return {status:()=>url.endsWith('redirect')?302:200}},fulfill:async()=>state='allow',abort:async()=>state='block'});output.push([state,fetches]);}console.log(JSON.stringify(output));})().catch(()=>process.exit(1));
'''
        p=subprocess.run(['node','-e',code,str(ROOT/'tools/web/public_guard.cjs')],capture_output=True,text=True,check=True,timeout=15)
        self.assertEqual(json.loads(p.stdout),[['block',0]]*5+[['allow',1],['allow',1],['block',1]])


@unittest.skipUnless(sys.version_info >= (3,11),'Optional bootstrap needs Python 3.11+')
class BootstrapGuardTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0,str(ROOT/'tools/web'))
        spec=importlib.util.spec_from_file_location('guarded_scrapling_fixture',ROOT/'tools/web/guarded_scrapling.py')
        self.guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.guard)
    def test_direct_static_mcp_blocks_linkedin_before_transport(self):
        calls=[]
        async def original(self,url,**kw):calls.append(url)
        with self.assertRaises(RetrievalFailure):asyncio.run(self.guard.guarded_http(original,'get')(None,'https://linkedin.com/in/p'))
        self.assertEqual(calls,[])
    def test_static_public_call_disables_redirects(self):
        seen={}
        async def original(self,url,**kw):seen.update(kw);return 'response'
        import research
        with patch.object(research,'network_url',side_effect=lambda u:u):
            self.assertEqual(asyncio.run(self.guard.guarded_http(original,'get')(None,'https://example.org/',follow_redirects=True)),'response')
        self.assertFalse(seen['follow_redirects']);self.assertEqual(seen['max_redirects'],0)
    def test_static_public_write_refused(self):
        async def original(*a,**kw):self.fail('Write invoked')
        with self.assertRaises(ValueError):asyncio.run(self.guard.guarded_http(original,'post')(None,'https://example.org/'))
    def test_browser_direct_linkedin_refused(self):
        async def original(*a,**kw):self.fail('LinkedIn browser invoked')
        with self.assertRaises(RetrievalFailure):asyncio.run(self.guard.guarded_browser_fetch(original)(None,'https://linkedin.com/in/p'))
    def test_browser_installs_guard_and_preserves_internal_screenshot_action(self):
        seen={};action=object()
        async def original(self,url,**kw):seen.update(kw)
        import research
        with patch.object(research,'network_url',side_effect=lambda u:u):
            asyncio.run(self.guard.guarded_browser_fetch(original)(None,'https://example.org/',page_action=action))
        self.assertIs(seen['page_setup'],self.guard.page_guard);self.assertIs(seen['page_action'],action);self.assertFalse(seen['google_search'])
    def test_browser_init_blocks_service_workers_and_session_options(self):
        seen={}
        self.guard.guarded_browser_init(lambda self,**kw:seen.update(kw))(None,additional_args={'service_workers':'allow'})
        self.assertEqual(seen['additional_args']['service_workers'],'block')
        for opts in ({'cookies':{'session':'secret'}},{'cdp_url':'http://localhost:9222'},{'additional_args':{'storage_state':'private.json'}},{'real_chrome':True}):
            with self.assertRaises(ValueError):self.guard.guard_options(opts)
    def test_browser_setup_failure_closes_page_before_upstream_can_continue(self):
        closed=[]
        async def route(*a):raise RuntimeError('setup failed')
        async def close():closed.append(True)
        page=SimpleNamespace(context=SimpleNamespace(route=route),close=close)
        with self.assertRaises(RuntimeError):asyncio.run(self.guard.page_guard(page))
        self.assertEqual(closed,[True])
    def test_page_route_blocks_redirects_and_linkedin_before_fetch(self):
        handler=[];events=[]
        async def register(pattern,callback):handler.append(callback)
        async def websocket(*a):pass
        page=SimpleNamespace(context=SimpleNamespace(route=register,route_web_socket=websocket))
        asyncio.run(self.guard.page_guard(page))
        async def fetch(**kw):events.append('fetch');return SimpleNamespace(status=302)
        async def abort(reason):events.append('abort')
        async def fulfill(**kw):events.append('fulfill')
        route=SimpleNamespace(request=SimpleNamespace(url='https://linkedin.com/in/p',method='GET'),fetch=fetch,abort=abort,fulfill=fulfill)
        asyncio.run(handler[0](route));self.assertEqual(events,['abort'])
        import research
        route.request.url='https://example.org/'
        with patch('socket.getaddrinfo',return_value=[(None,None,None,None,('93.184.216.34',0))]):asyncio.run(handler[0](route))
        self.assertEqual(events,['abort','fetch','abort'])
    def test_jina_and_linkedin_scraper_components_never_started(self):
        import research
        for name in ('jina','linkedin','linkedin-scraper-mcp'):
            with self.assertRaises(RetrievalFailure):asyncio.run(research.mcp_call(name,[]))
    def test_managed_payload_firewall_and_axios_created_instances(self):
        if not shutil.which('node'):self.skipTest('Node absent')
        code=r'''
(async()=>{const m=await import(process.argv[1]);const out=[];
for(const url of ['https://linkedin.com/in/p','https://UK.LINKEDIN.COM./in/p','https://r.jina.ai/https://linkedin.com/in/p','https://notlinkedin.com/in/p','https://linkedin.com.evil.test/']){
try{m.inspectPayload(JSON.stringify({url}));out.push('allow')}catch{out.push('block')}}
let base,instance;const axios={interceptors:{request:{use:f=>base=f}},create:()=>({interceptors:{request:{use:f=>instance=f}}})};m.install(axios);axios.create();
for(const guard of [base,instance]){try{guard({data:{url:'https://linkedin.com/in/p'}});out.push('allow')}catch{out.push('block')}}
console.log(JSON.stringify(out));})().catch(()=>process.exit(1));
'''
        p=subprocess.run(['node','-e',code,str(ROOT/'tools/web/managed_guard.mjs')],capture_output=True,text=True,check=True,timeout=10)
        self.assertEqual(json.loads(p.stdout),['block','block','block','allow','allow','block','block'])
    def test_managed_preload_guards_actual_pinned_esm_axios_without_network(self):
        axios_path=ROOT/'tools/web/node_modules/axios/index.js'
        if not shutil.which('node') or not axios_path.is_file():
            self.skipTest('Optional pinned Node dependencies absent')
        code=r"""
(async()=>{
process.env.LINKEDIN_AGENT_GUARD_COMPONENT='brightdata';
await import(process.argv[1]);
const axios=(await import(process.argv[2])).default;
let calls=0;const adapter=async config=>{calls++;return {status:200,data:'offline',headers:{},config}};
const out=[];
for(const client of [axios,axios.create()]){
try{await client.post('https://api.example.org/',{url:'https://linkedin.com/in/p'},{adapter});out.push('allow')}catch{out.push('block')}
await client.post('https://api.example.org/',{url:'https://example.org/'},{adapter});
}
console.log(JSON.stringify({out,calls}));
})().catch(()=>process.exit(1));
"""
        p=subprocess.run(['node','-e',code,str(ROOT/'tools/web/managed_guard.mjs'),str(axios_path)],capture_output=True,text=True,check=True,timeout=10)
        self.assertEqual(json.loads(p.stdout),{'out':['block','block'],'calls':2})

    def test_index_transport_stays_disabled_without_audited_schema(self):
        import research
        with tempfile.TemporaryDirectory() as root:
            p=next(x for x in research.providers(root) if x.id=='agent_reach_discovery')
        self.assertFalse(p.available);self.assertFalse(p.enabled)

if __name__=='__main__':unittest.main()
