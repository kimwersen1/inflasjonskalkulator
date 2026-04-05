export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let path = url.pathname;

    // Serve index.html for root
    if (path === '/') {
      return env.ASSETS.fetch(new Request(new URL('/index.html', url), request));
    }

    // Try the path as-is first (with .html extension already)
    if (path.endsWith('.html')) {
      return env.ASSETS.fetch(request);
    }

    // Try adding .html extension
    const withHtml = new Request(new URL(path + '.html', url), request);
    const response = await env.ASSETS.fetch(withHtml);
    if (response.status !== 404) {
      return response;
    }

    // Try index.html in directory
    const withIndex = new Request(new URL(path.replace(/\/$/, '') + '/index.html', url), request);
    const response2 = await env.ASSETS.fetch(withIndex);
    if (response2.status !== 404) {
      return response2;
    }

    // 404
    return new Response('Side ikke funnet', { status: 404 });
  }
};
