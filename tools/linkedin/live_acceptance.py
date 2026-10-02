#!/usr/bin/env python3
"""Supervised live acceptance. Login is human-only; evidence is not written raw to disk."""
import argparse
import asyncio
import json
from fastmcp import Client
from mcp_gateway import build
from policy import begin_task

async def main(root):
    async with Client(build(root)) as client:
        print(json.dumps({'catalogue':[t.name for t in await client.list_tools()]}),flush=True)
        begin_task(root,onboarding=True)
        result=await client.call_tool('read_my_profile',{'stage':'experience'})
        print(json.dumps(result.data,ensure_ascii=False),flush=True)
        print('MANUAL_GATE: complete any login/verification in the dedicated browser. Commands: resume, profile, professional, interests, posts, feed, status, close. No credentials here.',flush=True)
        while True:
            cmd=(await asyncio.to_thread(input)).strip()
            if cmd=='close':
                await client.call_tool('close_session',{});break
            if cmd=='resume':
                begin_task(root,onboarding=True)
                print('Human-confirmed continuation; onboarding budget reset once after authentication.',flush=True)
                continue
            mapped={'profile':('read_my_profile',{'stage':'experience'}),
                    'professional':('read_my_profile',{'stage':'professional'}),
                    'interests':('read_my_profile',{'stage':'interests'}),
                    'posts':('read_my_posts',{'stage':'onboarding'}),
                    'feed':('read_feed',{'limit':10}), 'status':('connector_status',{})}
            if cmd in mapped:
                name,args=mapped[cmd];result=await client.call_tool(name,args)
                print(json.dumps(result.data,ensure_ascii=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True)
    asyncio.run(main(ap.parse_args().root))
