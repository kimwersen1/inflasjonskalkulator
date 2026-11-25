/* =====================
   inflasjonskalkulator.no – nav.js
   Delt nav-struktur: injiserer nav-HTML i alle sider
   ===================== */

(function () {
  /* ---- Legg til ny nav-HTML på plass ---- */
  const NAV_HTML = `
<nav>
  <a href="/" class="nav-logo">inflasjonskalkulator<span>.no</span></a>
  <ul class="nav-links">
    <li><a href="/kalkulatorer">Kalkulatorer</a></li>
    <li><a href="/artikler">Artikler</a></li>
    <li><a href="/kpi-rapport">KPI-rapport</a></li>
    <li><a href="/ressurser">Ressurser</a></li>
  </ul>
  <button class="nav-search-btn" onclick="openSearch()" aria-label="Søk">
    <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <span class="nav-search-label">Søk</span>
  </button>
  <button class="nav-burger" id="nav-burger" onclick="toggleMenu()" aria-label="Åpne meny" aria-expanded="false">
    <span></span><span></span><span></span>
  </button>
</nav>
<div class="nav-mobile" id="nav-mobile">
  <div class="nav-section">Kalkulatorer</div>
  <a href="/">📊 Inflasjonskalkulator</a>
  <a href="/husleiekalkulator">🏠 Husleiekalkulator</a>
  <a href="/lønnskalkulator">💼 Lønnskalkulator</a>
  <a href="/boliglånskalkulator">🏡 Boliglånskalkulator</a>
  <a href="/renters-rente-kalkulator">📈 Renters rente</a>
  <a href="/nettolønn-kalkulator">💰 Nettolønnskalkulator</a>
  <a href="/pensjonskalkulator">🏦 Pensjonskalkulator</a>
  <a href="/kalkulatorer" class="nav-mobile-alle">→ Se alle kalkulatorer</a>
  <div class="nav-section">Artikler & mer</div>
  <a href="/artikler">📰 Artikler</a>
  <a href="/kpi-rapport">📋 KPI-rapport</a>
  <a href="/ressurser">🔗 Ressurser</a>
</div>`;

  /* Merk aktiv lenke */
  function markActive() {
    const path = window.location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('.nav-links a, .nav-mobile a').forEach(a => {
      const href = a.getAttribute('href').replace(/\/$/, '') || '/';
      if (href === path) a.classList.add('active');
    });
  }

  /* Toggle mobilmeny */
  window.toggleMenu = function () {
    const m = document.getElementById('nav-mobile');
    const b = document.getElementById('nav-burger');
    if (!m || !b) return;
    const open = m.classList.toggle('open');
    b.classList.toggle('open', open);
    b.setAttribute('aria-expanded', open);
  };

  /* Lukk meny ved klikk utenfor */
  document.addEventListener('click', function (e) {
    const m = document.getElementById('nav-mobile');
    const b = document.getElementById('nav-burger');
    if (!m || !m.classList.contains('open')) return;
    if (!m.contains(e.target) && !b.contains(e.target)) {
      m.classList.remove('open');
      b.classList.remove('open');
      b.setAttribute('aria-expanded', 'false');
    }
  });

  /* Lukk meny ved Escape */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      const m = document.getElementById('nav-mobile');
      const b = document.getElementById('nav-burger');
      if (m) { m.classList.remove('open'); }
      if (b) { b.classList.remove('open'); b.setAttribute('aria-expanded', 'false'); }
    }
  });

  /* Injiser nav hvis siden ikke allerede har en <nav> med nav-burger */
  if (!document.getElementById('nav-burger')) {
    document.body.insertAdjacentHTML('afterbegin', NAV_HTML);
  }

  markActive();
})();
