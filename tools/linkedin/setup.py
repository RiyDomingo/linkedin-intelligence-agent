#!/usr/bin/env python3
"""Install isolated pinned integration, verify gateway catalogue, preview/register it."""
import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

ROOT=Path(__file__).resolve().parents[2]
ENV=ROOT/'tools/linkedin/.venv'
NAME='linkedin_account'


def registration(root=ROOT):
    return '\n'.join(['[mcp_servers.linkedin_account]',
       'command = '+json.dumps(str(root/'tools/linkedin/.venv/bin/python')),
       'args = ['+json.dumps(str(root/'tools/linkedin/mcp_gateway.py'))+', "--root", '+json.dumps(str(root/'.linkedin-agent'))+']',
       'startup_timeout_sec = 30','tool_timeout_sec = 240','required = false',
       'enabled_tools = ["connector_status", "read_my_profile", "read_my_posts", "read_feed", "close_session"]',''])


def merge(existing, addition):
    old=tomllib.loads(existing)
    if NAME in old.get('mcp_servers',{}):
        if old['mcp_servers'][NAME]==tomllib.loads(addition)['mcp_servers'][NAME]: return existing
        raise ValueError('Existing linkedin_account registration preserved; review conflict')
    value=existing.rstrip()+'\n\n'+addition if existing.strip() else addition
    tomllib.loads(value)
    return value


def validate():
    script="""import asyncio,json,sys; sys.path.insert(0,sys.argv[1]); from mcp_gateway import build
async def check():
 s=build(sys.argv[2]); tools=await s.list_tools(); names=sorted(t.name for t in tools)
 assert names==sorted(['connector_status','read_my_profile','read_my_posts','read_feed','close_session']),names
 print(json.dumps({'gateway_catalogue':names}))
asyncio.run(check())"""
    subprocess.run([str(ENV/'bin/python'),'-c',script,str(ROOT/'tools/linkedin'),str(ROOT/'.linkedin-agent')],check=True,cwd=ROOT)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--install',action='store_true');ap.add_argument('--provision-browser',action='store_true');ap.add_argument('--write',action='store_true')
    a=ap.parse_args()
    try:
        for p in (ENV,*ENV.parents):
            if p.is_symlink(): raise ValueError('Symlinked environment refused')
        if a.install:
            uv=shutil.which('uv')
            if not uv: raise ValueError('uv required for optional connector setup')
            if not (ENV/'bin/python').exists():
                subprocess.run([uv,'venv','--python','3.12',str(ENV)],check=True,cwd=ROOT)
            subprocess.run([uv,'pip','sync','--python',str(ENV/'bin/python'),'--require-hashes',str(ROOT/'tools/linkedin/requirements.lock')],check=True,cwd=ROOT)
        if a.provision_browser:
            subprocess.run([str(ENV/'bin/python'),'-c','from linkedin_mcp_server.bootstrap import ensure_browser_installed; ensure_browser_installed()'],check=True,cwd=ROOT)
        validate()
        addition=registration();print(addition)
        target=ROOT/'.codex/config.toml'
        if target.is_symlink() or target.parent.is_symlink(): raise ValueError('Symlinked configuration refused')
        existing=target.read_text() if target.exists() else ''
        result=merge(existing,addition)
        if a.write:
            target.parent.mkdir(exist_ok=True)
            fd,name=tempfile.mkstemp(prefix='.linkedin-config-',dir=target.parent)
            try:
                with os.fdopen(fd,'w') as stream:
                    stream.write(result); stream.flush(); os.fsync(stream.fileno())
                if (target.read_text() if target.exists() else '')!=existing:
                    raise ValueError('Configuration changed during setup; preserved')
                os.replace(name,target)
            finally:
                if os.path.exists(name): os.unlink(name)
        print(json.dumps({'registered':a.write,'default_account_reads':'DISABLED until explicit local enable','auth':'manual dedicated browser, no cookie import'}))
    except (OSError,ValueError,subprocess.CalledProcessError):
        ap.exit(2,'Connector setup failed; existing registrations preserved. Inspect dependency/configuration availability.\n')


if __name__=='__main__':main()
