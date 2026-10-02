#!/usr/bin/env python3
"""Expose five project-owned tools, never the upstream catalogue."""
import argparse
from contextlib import AsyncExitStack, asynccontextmanager
from importlib.metadata import version
import os
from pathlib import Path
import sys
import asyncio
from typing import Literal
from pydantic import StrictInt
from fastmcp import FastMCP, Client
from fastmcp.client.transports import StdioTransport
from gateway import Gateway
from policy import VERSION


class Upstream:
    def __init__(self):
        self.client = None
        self.stack = None

    async def call(self, name, arguments):
        if name not in ('get_my_profile', 'get_feed'):
            raise ValueError('Upstream operation denied')
        if self.client is None:
            env = {k:v for k,v in os.environ.items() if k in ('HOME','PATH','TMPDIR','LANG','LC_ALL','SYSTEMROOT')}
            env.update({'AUTO_IMPORT_FROM_BROWSER':'false', 'LOG_LEVEL':'WARNING', 'LINKEDIN_MCP_CHECK_FOR_UPDATES':'off'})
            self.stack = AsyncExitStack()
            transport = StdioTransport(command=str(Path(sys.executable).with_name('mcp-server-linkedin')),
                args=['--transport','stdio','--no-auto-import','--no-daemon','--login-inline-wait','0'], env=env, cwd='/private/tmp', keep_alive=False, log_file=Path(os.devnull))
            try:
                self.client = await self.stack.enter_async_context(Client(transport))
            except BaseException:
                await self.stack.aclose()
                self.stack = None
                raise
        result = await self.client.call_tool(name, arguments, raise_on_error=False)
        if result.is_error:
            # Never forward raw upstream exceptions/diagnostics to the model or disk.
            from gateway import error_category
            text = ' '.join(c.text for c in result.content if hasattr(c,'text'))
            return {'error': error_category(text)}
        if isinstance(result.data, dict): return result.data
        import json
        for block in result.content:
            if hasattr(block,'text'):
                try: return json.loads(block.text)
                except (ValueError, TypeError): pass
        raise ValueError('MALFORMED_RESPONSE')

    async def close(self):
        if self.client:
            try:
                await self.client.call_tool('close_session', {}, raise_on_error=False)
            finally:
                await self.stack.aclose()
                self.client, self.stack = None, None


def build(root, upstream=None):
    gateway = Gateway(root, upstream or Upstream(), installed=version('mcp-server-linkedin') == VERSION)
    @asynccontextmanager
    async def lifespan(_):
        try:
            yield {}
        finally:
            await gateway.upstream.close()
    server = FastMCP('LinkedIn Intelligence Account Reader', lifespan=lifespan,
                     strict_input_validation=True, mask_error_details=True)
    @server.tool
    async def connector_status() -> dict:
        """Passive installed/enabled and last observed per-capability status; no auth probe."""
        return await gateway.dispatch('connector_status')
    @server.tool
    async def read_my_profile(stage: Literal['routine','experience','professional','interests']='routine') -> dict:
        """Bounded own professional profile. Onboarding stages require a local onboarding task."""
        return await gateway.dispatch('read_my_profile', {'stage':stage})
    @server.tool
    async def read_my_posts(stage: Literal['routine','onboarding']='routine') -> dict:
        """Read a bounded own-post sample. Observed posts are not confirmed local history."""
        return await gateway.dispatch('read_my_posts', {'stage':stage})
    @server.tool
    async def read_feed(limit: StrictInt=10) -> dict:
        """Read a small feed sample, target 1–20; references are never positional post URLs."""
        return await gateway.dispatch('read_feed', {'limit':limit})
    @server.tool
    async def close_session() -> dict:
        """Close the connector browser/process, preserving dedicated saved authentication."""
        return await gateway.dispatch('close_session')
    return server


if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True)
    build(ap.parse_args().root).run(transport='stdio', show_banner=False)
