// Fixed host-side MCP initPage hook: page content never supplies executable code.
const dns = require('node:dns').promises;
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const python = path.resolve(__dirname, '../../.venv/bin/python');
const globalIPs = 'import ipaddress,json,sys; xs=json.load(sys.stdin); sys.exit(0 if xs and all(ipaddress.ip_address(x).is_global for x in xs) else 1)';
module.exports.default = async ({ page }) => {
  const context = page.context();
  if (context.routeWebSocket) await context.routeWebSocket('**/*', socket => socket.close());
  await context.route('**/*', async route => {
    try {
      const request = route.request();
      const url = new URL(request.url());
      const hostname = url.hostname.toLowerCase().replace(/\.+$/, '');
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
          (url.port && !['80', '443'].includes(url.port)) ||
          !['GET', 'HEAD'].includes(request.method()) ||
          (hostname === 'linkedin.com' || hostname.endsWith('.linkedin.com') || hostname === 'r.jina.ai') ||
          /(^|\.)(localhost|local|internal)\.?$/i.test(url.hostname)) throw new Error('boundary');
      const addresses = await dns.lookup(url.hostname, { all: true });
      execFileSync(python, ['-c', globalIPs], {
        input: JSON.stringify(addresses.map(x => x.address)), timeout: 3000, stdio: ['pipe', 'ignore', 'ignore']
      });
      // Playwright routing may omit later redirect hops: never pass redirects through.
      const response = await route.fetch({ maxRedirects: 0, timeout: 20000 });
      if (response.status() >= 300 && response.status() < 400) throw new Error('redirect');
      await route.fulfill({ response });
    } catch {
      await route.abort('blockedbyclient');
    }
  });
};
