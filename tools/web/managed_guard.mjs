// Host-side guard for the pinned managed server, before its Axios requests.
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

export function blockedDestination(value) {
  const url = new URL(value);
  const host = url.hostname.toLowerCase().replace(/\.+$/, '');
  return !['http:', 'https:'].includes(url.protocol) || !!url.username || !!url.password ||
    (url.port && !['80', '443'].includes(url.port)) ||
    host === 'linkedin.com' || host.endsWith('.linkedin.com') || host === 'r.jina.ai';
}

export function inspectPayload(value, depth = 0) {
  if (depth > 8) throw new Error('Managed payload nesting refused');
  if (typeof value === 'string') {
    if (value.startsWith('{') || value.startsWith('[')) {
      try { return inspectPayload(JSON.parse(value), depth + 1); }
      catch { throw new Error('Managed payload refused'); }
    }
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) inspectPayload(item, depth + 1);
    return;
  }
  if (!value || typeof value !== 'object') return;
  for (const [key, item] of Object.entries(value)) {
    if (key === 'url' && (typeof item !== 'string' || blockedDestination(item)))
      throw new Error('LinkedIn/reader destinations are unavailable for managed retrieval');
    if (key === 'urls') {
      if (!Array.isArray(item) || item.some(x => typeof x !== 'string' || blockedDestination(x)))
        throw new Error('Managed destination list refused');
    }
    inspectPayload(item, depth + 1);
  }
}

export function install(axios) {
  const guard = config => {
    inspectPayload(config.data);
    inspectPayload(config.params);
    return config;
  };
  axios.interceptors.request.use(guard);
  const original = axios.create.bind(axios);
  axios.create = (...args) => {
    const instance = original(...args);
    instance.interceptors.request.use(guard);
    return instance;
  };
}

if (process.env.LINKEDIN_AGENT_GUARD_COMPONENT === 'brightdata') {
  const pkg = require('./node_modules/@brightdata/mcp/package.json');
  if (pkg.version !== '2.11.3') throw new Error('Review managed guard before changing pinned server');
  const axios = (await import('axios')).default;
  install(axios);
}
