export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let path = url.pathname;

    // Fjern trailing slash (unntatt root)
    if (path.endsWith('/') && path !== '/') {
      path = path.slice(0, -1);
    }

    // Prøv å hente filen direkte
    const directUrl = new URL(url.toString());
    directUrl.pathname = path;
    let response = await env.ASSETS.fetch(new Request(directUrl.toString(), request));
    if (response.status !== 404) return response;

    // Prøv med .html
    const htmlUrl = new URL(url.toString());
    htmlUrl.pathname = path + '.html';
    response = await env.ASSETS.fetch(new Request(htmlUrl.toString(), request));
    if (response.status !== 404) return response;

    // Prøv index.html i mappen
    const indexUrl = new URL(url.toString());
    indexUrl.pathname = path + '/index.html';
    response = await env.ASSETS.fetch(new Request(indexUrl.toString(), request));
    if (response.status !== 404) return response;

    // Prøv uten leading slash + .html (for undermapper som artikler/)
    const parts = path.split('/');
    if (parts.length >= 3) {
      const altUrl = new URL(url.toString());
      altUrl.pathname = parts.join('/') + '.html';
      response = await env.ASSETS.fetch(new Request(altUrl.toString(), request));
      if (response.status !== 404) return response;
    }

    // Fallback til 404
    return response;
  }
}