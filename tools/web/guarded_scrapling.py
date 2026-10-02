"""Pinned Scrapling MCP bootstrap with repository HTTP/browser destination guards."""
import functools
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/web'))


def guard_options(options):
    # Do not reuse accounts, private proxies or another browser's logged-in context.
    for name in ('cookies', 'auth', 'proxy_auth', 'proxy', 'proxies', 'cdp_url', 'real_chrome', 'user_data_dir', 'storage_state', 'solve_cloudflare'):
        if options.get(name):
            raise ValueError('Authenticated/session/proxy settings are not supported by this public reader')
    if options.get('additional_args'):
        guard_options(options['additional_args'])
    if options.get('executable_path'):
        from run_mcp import browser_path
        if options['executable_path'] != browser_path():
            raise ValueError('Only the installed local browser executable is allowed')


async def page_guard(page):
    from research import network_url
    async def guard(route):
        try:
            if route.request.method not in ('GET', 'HEAD'):
                raise ValueError('Public read-only browser')
            network_url(route.request.url)
            response = await route.fetch(max_redirects=0, timeout=20000)
            if 300 <= response.status < 400:
                raise ValueError('Redirect unavailable; use an inspected canonical URL')
            await route.fulfill(response=response)
        except Exception:
            await route.abort('blockedbyclient')
    try:
        await page.context.route('**/*', guard)
        await page.context.route_web_socket('**/*', lambda ws: ws.close())
    except Exception:
        # The upstream library logs setup exceptions and proceeds. Close first so
        # it cannot navigate without an installed guard.
        await page.close()
        raise


def guarded_http(original, method):
    @functools.wraps(original)
    async def call(self, url, **kwargs):
        from research import network_url
        if method != 'get':
            raise ValueError('Only GET is exposed by this public research server')
        guard_options(kwargs)
        url = network_url(url)
        kwargs['follow_redirects'] = False
        kwargs['max_redirects'] = 0
        return await original(self, url, **kwargs)
    return call


def guarded_browser_fetch(original):
    @functools.wraps(original)
    async def call(self, url, **kwargs):
        from research import network_url
        guard_options(kwargs)
        url = network_url(url)
        kwargs['page_setup'] = page_guard
        kwargs['google_search'] = False
        return await original(self, url, **kwargs)
    return call


def guarded_browser_init(original):
    @functools.wraps(original)
    def call(self, **kwargs):
        guard_options(kwargs)
        args = dict(kwargs.get('additional_args') or {})
        args['service_workers'] = 'block'
        kwargs['additional_args'] = args
        return original(self, **kwargs)
    return call


def install_guards():
    import scrapling
    if scrapling.__version__ != '0.4.15':
        raise ValueError('Review the guarded bootstrap before changing pinned Scrapling')
    from scrapling.engines.static import _ASyncSessionLogic
    from scrapling.fetchers import AsyncDynamicSession, AsyncStealthySession
    for method in ('get', 'post', 'put', 'delete', 'patch', 'head', 'options'):
        original = getattr(_ASyncSessionLogic, method, None)
        if original is not None:
            setattr(_ASyncSessionLogic, method, guarded_http(original, method))
    for cls in (AsyncDynamicSession, AsyncStealthySession):
        cls.__init__ = guarded_browser_init(cls.__init__)
        cls.fetch = guarded_browser_fetch(cls.fetch)


def main():
    install_guards()
    entrypoint = ROOT/'.venv/bin/scrapling-mcp'
    sys.argv[0] = str(entrypoint)
    runpy.run_path(str(entrypoint), run_name='__main__')


if __name__ == '__main__':
    main()
