export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let path = url.pathname;

    // Fjern trailing slash (unntatt root)
    if (path.endsWith('/') && path !== '/') {
      path = path.slice(0, -1);
    }

    // Prøv å hente filen direkte
    let response = await env.ASSETS.fetch(new Request(url.toString(), request));
    
    // Hvis 404, prøv med .html
    if (response.status === 404) {
      const htmlUrl = new URL(url.toString());
      htmlUrl.pathname = path + '.html';
      response = await env.ASSETS.fetch(new Request(htmlUrl.toString(), request));
    }

    // Hvis fortsatt 404, prøv index.html i mappen
    if (response.status === 404) {
      const indexUrl = new URL(url.toString());
      indexUrl.pathname = path + '/index.html';
      response = await env.ASSETS.fetch(new Request(indexUrl.toString(), request));
    }

    return response;
  }
}