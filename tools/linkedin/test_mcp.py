"""Optional-environment tests exercise actual MCP transport/catalogue with a fake server."""
import asyncio
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch
from fastmcp.client.transports import StdioTransport
from fastmcp import FastMCP, Client
from mcp_gateway import build, Upstream
from policy import set_enabled, begin_task, TOOLS

class FakeServer:
    def __init__(self):
        self.calls=[];self.server=FastMCP('Fake upstream, no browser or network')
        @self.server.tool
        async def get_my_profile(sections:str|None=None,max_scrolls:int|None=None):
            self.calls.append(('get_my_profile',{'sections':sections,'max_scrolls':max_scrolls}))
            return {'url':'https://linkedin.com/in/example/','sections':{'main_profile':'Example professional','posts':'Example post'}}
        @self.server.tool
        async def get_feed(num_posts:int=10):
            self.calls.append(('get_feed',num_posts));return {'url':'https://linkedin.com/feed/','sections':{'feed':'Example feed'}}
        @self.server.tool
        async def send_message(text:str):
            self.calls.append(('send_message',text));return {'sent':True}
        @self.server.tool
        async def close_session():return {'closed':True}
    async def call(self,name,arguments):
        async with Client(self.server) as client:
            result=await client.call_tool(name,arguments)
            return result.data
    async def close(self):pass

class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        set_enabled(self.root,True);begin_task(self.root)
        self.up=FakeServer();self.server=build(self.root,self.up)
    async def asyncTearDown(self):self.temp.cleanup()
    async def test_exact_mcp_catalogue(self):
        async with Client(self.server) as client:self.assertEqual(sorted(t.name for t in await client.list_tools()),sorted(TOOLS))
    async def test_write_and_raw_upstream_absent(self):
        async with Client(self.server) as client:
            for name in ('send_message','get_my_profile','get_inbox','raw_passthrough','post'):
                result=await client.call_tool(name,{},raise_on_error=False);self.assertTrue(result.is_error)
        self.assertEqual(self.up.calls,[])
    async def test_real_read_mapping(self):
        async with Client(self.server) as client:
            result=await client.call_tool('read_my_posts',{})
            self.assertIn('posts',result.data['evidence_sections'])
        self.assertEqual(self.up.calls,[('get_my_profile',{'sections':'posts','max_scrolls':2})])
    async def test_invalid_limit_never_reaches_fake(self):
        async with Client(self.server) as client:
            result=await client.call_tool('read_feed',{'limit':21},raise_on_error=False);self.assertTrue(result.is_error)
        self.assertEqual(self.up.calls,[])
    async def test_malformed_limits_never_coerce(self):
        async with Client(self.server) as client:
            for value in ('10',True,1.5,None):
                result=await client.call_tool('read_feed',{'limit':value},raise_on_error=False)
                self.assertTrue(result.is_error)
        self.assertEqual(self.up.calls,[])

    async def test_unexpected_arguments_rejected(self):
        async with Client(self.server) as client:
            for name,args in [('read_feed',{'limit':10,'url':'https://linkedin.com/in/other/'}),('read_my_profile',{'sections':'contact_info'}),('connector_status',{'token':'fake-fixture'})]:
                result=await client.call_tool(name,args,raise_on_error=False)
                self.assertTrue(result.is_error)
        self.assertEqual(self.up.calls,[])

    async def test_kill_switch_never_reaches_fake(self):
        set_enabled(self.root,False)
        async with Client(self.server) as client:
            result=await client.call_tool('read_feed',{});self.assertEqual(result.data['state'],'DISABLED')
        self.assertEqual(self.up.calls,[])
    async def test_real_stdio_transport(self):
        script=self.root/'fake_server.py'
        script.write_text("from fastmcp import FastMCP\ns=FastMCP('fake')\n@s.tool\nasync def get_my_profile(sections:str,max_scrolls:int): return {'sections':{'main_profile':'Fake observed profile'}}\n@s.tool\nasync def close_session(): return {'closed':True}\ns.run(transport='stdio',show_banner=False)\n")
        def transport(**kw):
            kw['command']=sys.executable;kw['args']=[str(script)]
            return StdioTransport(**kw)
        up=Upstream()
        with patch('mcp_gateway.StdioTransport',side_effect=transport):
            result=await up.call('get_my_profile',{'sections':'experience','max_scrolls':2})
            self.assertIn('main_profile',result['sections'])
            await up.close()

    async def test_upstream_direct_writes_blocked(self):
        up=Upstream()
        with self.assertRaises(ValueError):await up.call('send_message',{'text':'No'})
        self.assertIsNone(up.client)

if __name__=='__main__':unittest.main()
