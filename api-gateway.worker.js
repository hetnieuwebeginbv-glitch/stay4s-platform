// api-gateway.worker.js
// Stay4S API Gateway - Cloudflare Worker
// Env: API_KEYS (KV), RATE_LIMIT (KV), USAGE_LOG (D1), BACKEND_ORIGIN

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/v1/')) {
      return new Response('Not Found', { status: 404 });
    }
    const apiKey = request.headers.get('X-API-Key');
    if (!apiKey) return jsonError(401, 'Missing API key');
    const ownerId = await env.API_KEYS.get(apiKey);
    if (!ownerId) return jsonError(403, 'Invalid API key');
    const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
    const rateKey = `rl:${ownerId}:${clientIP}:${Math.floor(Date.now() / 60000)}`;
    const current = parseInt((await env.RATE_LIMIT.get(rateKey)) || '0', 10);
    if (current >= 100) return jsonError(429, 'Rate limit exceeded');
    await env.RATE_LIMIT.put(rateKey, String(current + 1), { expirationTtl: 120 });
    const backendPath = url.pathname.replace(/^\/v1/, '');
    const backendUrl = `https://backend.stay4s.com${backendPath}${url.search}`;
    const proxyReq = new Request(backendUrl, {
      method: request.method,
      headers: request.headers,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : undefined,
    });
    proxyReq.headers.delete('X-API-Key');
    const response = await fetch(proxyReq);
    const status = response.status;
    ctx.waitUntil(
      env.USAGE_LOG.prepare(
        'INSERT INTO api_usage (owner_id, ip, method, path, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)'
      ).bind(ownerId, clientIP, request.method, url.pathname, status, new Date().toISOString()).run()
    );
    const dayKey = `usage:${ownerId}:${new Date().toISOString().slice(0, 10)}`;
    const dayCount = parseInt((await env.RATE_LIMIT.get(dayKey)) || '0', 10);
    await env.RATE_LIMIT.put(dayKey, String(dayCount + 1), { expirationTtl: 86400 });
    return response;
  },
};

function jsonError(status, message) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
