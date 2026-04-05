export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let path = url.pathname;
    if (path === '/') path = '/index.html';
    if (!path.includes('.')) path = path + '.html';
    return env.ASSETS.fetch(new Request(new URL(path, url), request));
  }
};
