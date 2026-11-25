/* =====================
   inflasjonskalkulator.no – nav.js
   Håndterer mobilmeny og søk (nav HTML er inline i hver side)
   ===================== */

(function () {
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

  markActive();
})();
