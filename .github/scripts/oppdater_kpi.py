"""
Henter siste KPI-tall fra SSBs API og:
1. Oppdaterer index.html automatisk
2. Genererer en ny månedlig KPI-rapport HTML-side
3. Oppdaterer sitemap.xml

Kjøres via GitHub Actions den 10. hver måned.
"""

import requests
import re
import os
from datetime import datetime, timedelta

SSB_API_URL = "https://data.ssb.no/api/v0/no/table/14700"

GRUPPER = {
    "00":  "kpi_total",
    "011": "matvarer",
    "045": "elektrisitet",
    "041": "husleie",
    "072": "drivstoff",
    "083": "teletjenester",
}

MND_LANG = {1:"januar",2:"februar",3:"mars",4:"april",5:"mai",6:"juni",7:"juli",8:"august",9:"september",10:"oktober",11:"november",12:"desember"}
MND_KORT = {1:"jan.",2:"feb.",3:"mars",4:"apr.",5:"mai",6:"juni",7:"juli",8:"aug.",9:"sep.",10:"okt.",11:"nov.",12:"des."}
MND_SLUG = {1:"januar",2:"februar",3:"mars",4:"april",5:"mai",6:"juni",7:"juli",8:"august",9:"september",10:"oktober",11:"november",12:"desember"}


def hent_siste_kpi():
    i_dag = datetime.now()
    forrige_mnd = (i_dag.replace(day=1) - timedelta(days=1))
    samme_mnd_i_fjor = forrige_mnd.replace(year=forrige_mnd.year - 1)
    mnd_kode = forrige_mnd.strftime("%YM%m")
    fjor_kode = samme_mnd_i_fjor.strftime("%YM%m")
    print(f"Henter KPI for {mnd_kode} og {fjor_kode}...")
    query = {
        "query": [
            {"code": "Konsumgrp", "selection": {"filter": "item", "values": list(GRUPPER.keys())}},
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["KpiIndMnd"]}},
            {"code": "Tid", "selection": {"filter": "item", "values": [mnd_kode, fjor_kode]}}
        ],
        "response": {"format": "json-stat2"}
    }
    try:
        response = requests.post(SSB_API_URL, json=query, timeout=30)
        response.raise_for_status()
        print("SSB API svar mottatt!")
        return response.json(), mnd_kode, fjor_kode, forrige_mnd
    except Exception as e:
        print(f"Feil ved API-kall: {e}")
        return None, None, None, None


def beregn_endringer(data, mnd_kode, fjor_kode):
    if not data:
        return None
    verdier = data.get("value", [])
    dims = data.get("dimension", {})
    konsumgrp_ids = list(dims["Konsumgrp"]["category"]["index"].keys())
    tid_ids = list(dims["Tid"]["category"]["index"].keys())
    n_tid = len(tid_ids)
    try:
        idx_ny = tid_ids.index(mnd_kode)
        idx_gammel = tid_ids.index(fjor_kode)
    except ValueError:
        print("Fant ikke begge månedene i data")
        return None
    endringer = {}
    for i, grp_kode in enumerate(konsumgrp_ids):
        navn = GRUPPER.get(grp_kode)
        if not navn:
            continue
        ny_v = verdier[i * n_tid + idx_ny]
        gl_v = verdier[i * n_tid + idx_gammel]
        if ny_v and gl_v:
            e = ((ny_v - gl_v) / gl_v) * 100
            endringer[navn] = round(e, 1)
            print(f"  {navn}: {e:.1f}%")
    return endringer


def fp(v):
    return f"+{v:.1f} %" if v >= 0 else f"{v:.1f} %"

def farge(v):
    return "pos" if v >= 0 else "neg"

def pil(v):
    return "up" if v >= 0 else "down"


def oppdater_kpi_bar(html, e, mnd_label):
    kpi = e.get("kpi_total", 0)
    mat = e.get("matvarer", 0)
    strom = e.get("elektrisitet", 0)
    ny_bar = f'''  <div class="kpi-bar">
    <div class="kpi-bar-item">KPI {mnd_label}: <strong>{fp(kpi)}</strong> <span class="arrow">{chr(8593) if kpi >= 0 else chr(8595)}</span></div>
    <div class="kpi-bar-item">Matvarer: <strong>{fp(mat)}</strong> <span class="arrow">{chr(8593) if mat >= 0 else chr(8595)}</span></div>
    <div class="kpi-bar-item">Str&#248;m: <strong>{fp(strom)}</strong> <span class="arrow">{chr(8593) if strom >= 0 else chr(8595)}</span></div>
    <div class="kpi-bar-item hide-mobile">Kilde: <strong>SSB</strong></div>
  </div>'''
    return re.sub(r'<div class="kpi-bar">.*?</div>\s*</div>', ny_bar, html, flags=re.DOTALL, count=1)


def oppdater_kategori_kort(html, e, mnd_label):
    mapping = {
        "kpi_total": "KPI totalt \\(alle varer\\)",
        "matvarer": "Matvarer og alkoholfrie drikkevarer",
        "elektrisitet": "Elektrisitet inkl\\. nettleie",
        "husleie": "Husleie",
        "drivstoff": "Drivstoff og sm\\xf8remidler",
        "teletjenester": "Teletjenester",
    }
    for key, pattern in mapping.items():
        if key not in e:
            continue
        v = e[key]
        klasse = "pos" if v >= 0 else "neg"
        ny_pct = f'<div class="cat-pct {klasse}">{fp(v)}</div>'
        p = rf'(<div class="cat-name">{pattern}</div>\s*<div class="cat-src">)[^<]*(</div>\s*</div>\s*<div class="cat-pct (?:pos|neg)">)[^<]*(</div>)'
        def erstatt(m, lbl=mnd_label, pct=ny_pct):
            return m.group(1) + f'SSB KPI, {lbl}' + '</div>\n          </div>\n          ' + pct
        html = re.sub(p, erstatt, html, flags=re.DOTALL)
    return html


def oppdater_highlight_box(html, e, forrige_mnd):
    kpi = e.get("kpi_total", 0)
    mat = e.get("matvarer", 0)
    mnd_str = MND_LANG[forrige_mnd.month]
    aar = forrige_mnd.year
    tekst = f'I {mnd_str} {aar} var den norske inflasjonen p\xe5 <strong>{kpi:.1f} %</strong> sammenlignet med {mnd_str} {aar-1}. Matvarer steg med hele {mat:.1f} % i samme periode.'
    return re.sub(
        r'(<div class="highlight-box">\s*)(.*?)(\s*</div>)',
        lambda m: m.group(1) + tekst + m.group(3),
        html, flags=re.DOTALL, count=1
    )


def generer_kpi_rapport(e, forrige_mnd, pub_dato):
    mnd_str = MND_LANG[forrige_mnd.month]
    mnd_kort = MND_KORT[forrige_mnd.month]
    slug = MND_SLUG[forrige_mnd.month]
    aar = forrige_mnd.year
    aar_fjor = aar - 1

    kpi = e.get("kpi_total", 0)
    mat = e.get("matvarer", 0)
    strom = e.get("elektrisitet", 0)
    husleie = e.get("husleie", 0)
    drivstoff = e.get("drivstoff", 0)
    tele = e.get("teletjenester", 0)
    pris_10k = int(10000 * (1 + kpi/100))

    html = f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KPI {mnd_str} {aar} – Norsk inflasjon {mnd_str} {aar} | inflasjonskalkulator.no</title>
<meta name="description" content="Norsk inflasjon i {mnd_str} {aar}: KPI {fp(kpi)} fra {mnd_str} {aar_fjor} til {mnd_str} {aar}. Se alle tall og hva det betyr for din økonomi.">
<link rel="canonical" href="https://inflasjonskalkulator.no/kpi-rapport/{slug}-{aar}">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"NewsArticle","headline":"KPI {mnd_str} {aar} – Norsk inflasjon","datePublished":"{pub_dato}","dateModified":"{pub_dato}","publisher":{{"@type":"Organization","name":"inflasjonskalkulator.no","url":"https://inflasjonskalkulator.no"}}}}
</script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--green:#1a7a4a;--green-light:#e8f5ee;--green-mid:#2a9d60;--green-dark:#114d2e;--red:#c0392b;--text:#1a1a1a;--text-muted:#5a6472;--bg:#f7f8f5;--white:#ffffff;--border:#dde3d8;--fh:'Syne',sans-serif;--fb:'DM Sans',sans-serif;--r:12px;--rs:8px}}
body{{font-family:var(--fb);background:var(--bg);color:var(--text);font-size:17px;line-height:1.7}}
nav{{background:var(--green-dark);padding:0 1.5rem;display:flex;align-items:center;justify-content:space-between;height:60px;position:sticky;top:0;z-index:100}}
.nav-logo{{font-family:var(--fh);font-weight:800;font-size:1.2rem;color:#fff;text-decoration:none;letter-spacing:-0.02em}}
.nav-logo span{{color:#6ee09e}}
nav ul{{display:flex;gap:1.5rem;list-style:none}}
nav ul a{{color:rgba(255,255,255,0.75);text-decoration:none;font-size:0.9rem}}
@media(max-width:640px){{nav ul{{display:none}}}}
.hero{{background:var(--green-dark);padding:3rem 1.5rem 3.5rem}}
.wrap{{max-width:760px;margin:0 auto;padding:0 1.5rem}}
.bc{{font-size:0.82rem;color:rgba(255,255,255,0.5);margin-bottom:1rem}}
.bc a{{color:rgba(255,255,255,0.6);text-decoration:none}}
.bc span{{margin:0 6px}}
.tag{{display:inline-block;background:rgba(110,224,158,0.15);border:1px solid rgba(110,224,158,0.3);color:#6ee09e;font-size:0.78rem;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;padding:4px 14px;border-radius:99px;margin-bottom:1rem}}
h1{{font-family:var(--fh);font-weight:800;font-size:clamp(1.8rem,5vw,2.8rem);color:#fff;letter-spacing:-0.03em;line-height:1.1;margin-bottom:0.75rem}}
.meta{{color:rgba(255,255,255,0.5);font-size:0.85rem}}
.sg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;margin:2rem 0}}
.sc{{background:var(--white);border:1px solid var(--border);border-radius:var(--r);padding:1.25rem;text-align:center}}
.sv{{font-family:var(--fh);font-weight:800;font-size:2rem;color:var(--green-dark);letter-spacing:-0.03em;display:block}}
.sv.r{{color:var(--red)}}
.sl{{font-size:0.78rem;color:var(--text-muted);margin-top:4px}}
.ab{{padding:2rem 0 3rem}}
.ab h2{{font-family:var(--fh);font-weight:700;font-size:1.35rem;color:var(--green-dark);margin:2rem 0 0.75rem;letter-spacing:-0.02em}}
.ab p{{margin-bottom:1.1rem;font-size:0.97rem}}
.hb{{background:var(--green-light);border-left:4px solid var(--green);border-radius:0 var(--rs) var(--rs) 0;padding:1rem 1.25rem;margin:1.5rem 0;font-size:0.95rem}}
.kg{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:0.75rem;margin:1.25rem 0}}
.kc{{background:var(--white);border:1px solid var(--border);border-radius:var(--r);padding:0.9rem 1rem;display:flex;align-items:center;gap:0.75rem}}
.ki{{font-size:1.35rem;flex-shrink:0;width:26px;text-align:center}}
.kinfo{{flex:1;min-width:0}}
.kn{{font-weight:500;font-size:0.85rem;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.ks{{font-size:0.68rem;color:var(--text-muted)}}
.kp{{font-family:var(--fh);font-weight:800;font-size:1.2rem;letter-spacing:-0.02em;flex-shrink:0;white-space:nowrap}}
.kp.pos{{color:var(--red)}}.kp.neg{{color:var(--green)}}
.cta{{background:var(--green-dark);border-radius:var(--r);padding:1.75rem 2rem;margin:2rem 0;display:flex;align-items:center;justify-content:space-between;gap:1.5rem;flex-wrap:wrap}}
.cta p{{color:rgba(255,255,255,0.8);font-size:0.95rem;margin:0}}
.cta strong{{color:#fff;display:block;font-family:var(--fh);font-size:1.1rem;margin-bottom:4px}}
.cta-btn{{background:#6ee09e;color:var(--green-dark);text-decoration:none;font-family:var(--fh);font-weight:800;font-size:0.95rem;padding:10px 20px;border-radius:var(--rs);white-space:nowrap;flex-shrink:0}}
.back{{display:inline-flex;align-items:center;gap:8px;color:var(--green);text-decoration:none;font-weight:500;font-size:0.95rem;margin-top:1rem}}
footer{{background:var(--green-dark);color:rgba(255,255,255,0.6);padding:2rem 1.5rem;text-align:center;font-size:0.88rem}}
footer a{{color:rgba(255,255,255,0.8);text-decoration:none}}
.fl{{display:flex;justify-content:center;gap:2rem;margin-bottom:0.75rem;flex-wrap:wrap}}
</style>
</head>
<body>
<nav>
  <a class="nav-logo" href="/">inflasjonskalkulator<span>.no</span></a>
  <ul>
    <li><a href="/">Inflasjonskalkulator</a></li>
    <li><a href="/husleiekalkulator">Husleie</a></li>
    <li><a href="/lønnskalkulator">Lønn</a></li>
    <li><a href="/ressurser">Ressurser</a></li>
  </ul>
</nav>
<div class="hero">
  <div class="wrap">
    <div class="bc"><a href="/">Hjem</a><span>›</span><a href="/kpi-rapport">KPI-rapporter</a><span>›</span>{mnd_str.capitalize()} {aar}</div>
    <div class="tag">Månedlig KPI-rapport</div>
    <h1>KPI {mnd_str} {aar} – Norsk inflasjon</h1>
    <div class="meta">Publisert {pub_dato} &nbsp;·&nbsp; Kilde: SSB</div>
  </div>
</div>
<div class="wrap">
  <div class="sg">
    <div class="sc"><span class="sv r">{fp(kpi)}</span><div class="sl">KPI totalt (12 mnd.)</div></div>
    <div class="sc"><span class="sv r">{fp(mat)}</span><div class="sl">Matvarer</div></div>
    <div class="sc"><span class="sv">{fp(strom)}</span><div class="sl">Strøm</div></div>
    <div class="sc"><span class="sv">{fp(husleie)}</span><div class="sl">Husleie</div></div>
  </div>
  <div class="ab">
    <p>Konsumprisindeksen (KPI) steg <strong>{kpi:.1f} prosent</strong> fra {mnd_str} {aar_fjor} til {mnd_str} {aar}, viser nye tall fra SSB. Matvarer steg {mat:.1f} %, mens strømprisene endret seg med {strom:.1f} %.</p>
    <div class="hb"><strong>Kort oppsummert:</strong> Norsk inflasjon var {fp(kpi)} i {mnd_str} {aar}. Det som kostet 10 000 kr i {mnd_str} {aar_fjor} koster nå {pris_10k} kr.</div>
    <h2>Inflasjon per kategori – {mnd_str} {aar}</h2>
    <div class="kg">
      <div class="kc"><div class="ki">🛒</div><div class="kinfo"><div class="kn">Matvarer</div><div class="ks">SSB KPI, {mnd_kort} {aar}</div></div><div class="kp {farge(mat)}">{fp(mat)}</div></div>
      <div class="kc"><div class="ki">⚡</div><div class="kinfo"><div class="kn">Elektrisitet</div><div class="ks">SSB KPI, {mnd_kort} {aar}</div></div><div class="kp {farge(strom)}">{fp(strom)}</div></div>
      <div class="kc"><div class="ki">🏠</div><div class="kinfo"><div class="kn">Husleie</div><div class="ks">SSB KPI, {mnd_kort} {aar}</div></div><div class="kp {farge(husleie)}">{fp(husleie)}</div></div>
      <div class="kc"><div class="ki">⛽</div><div class="kinfo"><div class="kn">Drivstoff</div><div class="ks">SSB KPI, {mnd_kort} {aar}</div></div><div class="kp {farge(drivstoff)}">{fp(drivstoff)}</div></div>
      <div class="kc"><div class="ki">📱</div><div class="kinfo"><div class="kn">Teletjenester</div><div class="ks">SSB KPI, {mnd_kort} {aar}</div></div><div class="kp {farge(tele)}">{fp(tele)}</div></div>
      <div class="kc"><div class="ki">📊</div><div class="kinfo"><div class="kn">KPI totalt</div><div class="ks">SSB KPI, {mnd_kort} {aar}</div></div><div class="kp {farge(kpi)}">{fp(kpi)}</div></div>
    </div>
    <h2>Hva betyr dette for deg?</h2>
    <p>En inflasjon på {kpi:.1f} % betyr at det som kostet 10 000 kr i {mnd_str} {aar_fjor} nå koster {pris_10k} kr. Bruk vår <a href="/" style="color:var(--green);">inflasjonskalkulator</a> for å beregne hva dine konkrete beløp er verdt etter prisvekst.</p>
    <p>Skal du regulere husleie? Bruk <a href="/husleiekalkulator" style="color:var(--green);">husleiekalkulatoren</a>. Vil du vite om du har fått realLønnsvekst? Sjekk <a href="/lønnskalkulator" style="color:var(--green);">lønnskalkulatoren</a>.</p>
    <div class="cta">
      <div><strong>Beregn din kjøpekraft</strong><p>Se hva pengene dine er verdt etter {kpi:.1f} % prisvekst.</p></div>
      <a href="/" class="cta-btn">Åpne inflasjonskalkulator →</a>
    </div>
    <a href="/" class="back">← Tilbake til inflasjonskalkulator.no</a>
  </div>
</div>
<footer>
  <div class="wrap">
    <div class="fl">
      <a href="/">Hjem</a><a href="/#kalkulator">Inflasjonskalkulator</a>
      <a href="/husleiekalkulator">Husleiekalkulator</a>
      <a href="/lønnskalkulator">Lønnskalkulator</a>
      <a href="/ressurser">Ressurser</a>
    </div>
    <p>Tall basert på <a href="https://www.ssb.no" target="_blank" rel="noopener">SSBs Konsumprisindeks</a>. Informasjonen er kun veiledende.</p>
    <p style="margin-top:0.5rem;">&copy; {aar} inflasjonskalkulator.no</p>
  </div>
</footer>
</body>
</html>"""

    return html, slug, aar


def oppdater_sitemap(slug, aar, pub_dato):
    ny_url = f"""  <url>
    <loc>https://inflasjonskalkulator.no/kpi-rapport/{slug}-{aar}</loc>
    <lastmod>{pub_dato}</lastmod>
    <changefreq>never</changefreq>
    <priority>0.8</priority>
  </url>"""
    with open("sitemap.xml", "r", encoding="utf-8") as f:
        sitemap = f.read()
    if f"kpi-rapport/{slug}-{aar}" not in sitemap:
        sitemap = sitemap.replace("</urlset>", ny_url + "\n</urlset>")
        with open("sitemap.xml", "w", encoding="utf-8") as f:
            f.write(sitemap)
        print(f"Sitemap oppdatert: kpi-rapport/{slug}-{aar}")
    else:
        print("Allerede i sitemap.")



# ── HENT JANUAR KPI FOR HUSLEIEREGULERING ────────────────────────────────────

def hent_januar_kpi():
    aar = datetime.now().year
    jan_i_aar = f"{aar}M01"
    jan_i_fjor = f"{aar-1}M01"
    query = {
        "query": [
            {"code": "Konsumgrp", "selection": {"filter": "item", "values": ["00"]}},
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["KpiIndMnd"]}},
            {"code": "Tid", "selection": {"filter": "item", "values": [jan_i_aar, jan_i_fjor]}}
        ],
        "response": {"format": "json-stat2"}
    }
    try:
        r = requests.post(SSB_API_URL, json=query, timeout=30)
        r.raise_for_status()
        data = r.json()
        verdier = data["value"]
        tid_ids = list(data["dimension"]["Tid"]["category"]["index"].keys())
        idx_aar = tid_ids.index(jan_i_aar)
        idx_fjor = tid_ids.index(jan_i_fjor)
        ny = verdier[idx_aar]
        gammel = verdier[idx_fjor]
        if ny and gammel:
            vekst = round(((ny - gammel) / gammel) * 100, 1)
            print(f"Januar KPI-vekst {aar}: {vekst}%")
            return vekst, aar
    except Exception as e:
        print(f"Feil ved henting av januar KPI: {e}")
    return None, None


def hent_aarlig_kpi_snitt():
    aar = datetime.now().year
    forrige_aar = aar - 1
    maaneder = [f"{forrige_aar}M{str(m).zfill(2)}" for m in range(1, 13)]
    query = {
        "query": [
            {"code": "Konsumgrp", "selection": {"filter": "item", "values": ["00"]}},
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["KpiIndMnd"]}},
            {"code": "Tid", "selection": {"filter": "item", "values": maaneder}}
        ],
        "response": {"format": "json-stat2"}
    }
    try:
        r = requests.post(SSB_API_URL, json=query, timeout=30)
        r.raise_for_status()
        data = r.json()
        verdier = [v for v in data["value"] if v is not None]
        if len(verdier) == 12:
            snitt = round(sum(verdier) / 12, 1)
            print(f"Aarlig KPI-snitt {forrige_aar}: {snitt}")
            return snitt, forrige_aar
    except Exception as e:
        print(f"Feil ved henting av arsgjennomsnitt: {e}")
    return None, None


# ── OPPDATER HUSLEIEKALKULATOR ────────────────────────────────────────────────

def oppdater_husleiekalkulator(jan_vekst, aar):
    fil = "husleiekalkulator.html"
    if not os.path.exists(fil):
        print(f"{fil} ikke funnet, hopper over.")
        return
    with open(fil, "r", encoding="utf-8") as f:
        html = f.read()

    # Oppdater tittel og meta
    html = re.sub(r"Husleiekalkulator \d{4}", f"Husleiekalkulator {aar}", html)
    html = re.sub(r"Gyldig for \d{4}", f"Gyldig for {aar}", html)

    # Oppdater highlight-boks
    html = re.sub(
        r"Husleieøkning i \d{4} kan maksimalt være <strong>[^<]+</strong>[^.]+\.",
        f"Husleieøkning i {aar} kan maksimalt v\u00e6re <strong>{jan_vekst} %</strong>, basert p\u00e5 KPI-veksten fra januar {aar-1} til januar {aar} (SSB).",
        html
    )

    # Legg til nytt år i kpiVekst hvis ikke finnes
    if f"{aar}:" not in html:
        html = html.replace(
            "const kpiVekst = {",
            f"const kpiVekst = {{ {aar}: {jan_vekst},"
        ).replace("= {{ ", "= { ")

    # Legg til nytt år i dropdown hvis ikke finnes
    ny_option = f'<option value="{aar}">{aar} (KPI jan. {aar-1}\u2013jan. {aar}: +{jan_vekst} %)</option>'
    if f'value="{aar}"' not in html:
        html = html.replace(
            '<select id="reg-ar">',
            f'<select id="reg-ar">\n          {ny_option}'
        )

    # Legg til i historikk-listen
    ny_linje = f"<li><strong>{aar}:</strong> KPI jan. {aar-1}\u2013jan. {aar} = +{jan_vekst} %</li>"
    if f"<strong>{aar}:</strong>" not in html:
        forrige = f"<li><strong>{aar-1}:</strong>"
        if forrige in html:
            html = html.replace(forrige, ny_linje + "\n        " + forrige)

    with open(fil, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"husleiekalkulator.html oppdatert for {aar}!")


# ── OPPDATER LØNNSKALKULATOR ──────────────────────────────────────────────────

def oppdater_lonnskalkulator(kpi_snitt, forrige_aar):
    fil = "l\u00f8nnskalkulator.html"
    if not os.path.exists(fil):
        print(f"{fil} ikke funnet, hopper over.")
        return
    with open(fil, "r", encoding="utf-8") as f:
        html = f.read()

    # Legg til nytt ar i kpiData hvis ikke finnes
    if f"{forrige_aar}:" not in html:
        # Finn siste verdi og legg til
        match = re.search(r"(\d{4}):([\d.]+)\s*\}", html)
        if match:
            siste_aar = match.group(1)
            html = html.replace(
                f"{siste_aar}:{match.group(2)}",
                f"{siste_aar}:{match.group(2)},{forrige_aar}:{kpi_snitt}"
            )

    # Oppdater default arsvalgene
    aar = forrige_aar + 1
    html = re.sub(r"fraEl\.value = \d+", f"fraEl.value = {forrige_aar}", html)
    html = re.sub(r"tilEl\.value = \d+", f"tilEl.value = {aar}", html)

    with open(fil, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"lonnskalkulator.html oppdatert med {forrige_aar} (snitt {kpi_snitt})!")


def main():
    data, mnd_kode, fjor_kode, forrige_mnd = hent_siste_kpi()
    if not data:
        print("Kunne ikke hente data fra SSB. Avbryter.")
        return
    endringer = beregn_endringer(data, mnd_kode, fjor_kode)
    if not endringer:
        print("Kunne ikke beregne endringer. Avbryter.")
        return

    mnd_label = f"{MND_KORT[forrige_mnd.month]} {forrige_mnd.year}"
    pub_dato = datetime.now().strftime("%Y-%m-%d")

    # 1. Oppdater index.html
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    html = oppdater_kpi_bar(html, endringer, mnd_label)
    html = oppdater_kategori_kort(html, endringer, mnd_label)
    html = oppdater_highlight_box(html, endringer, forrige_mnd)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html oppdatert!")

    # 2. Generer KPI-rapport
    rapport_html, slug, aar = generer_kpi_rapport(endringer, forrige_mnd, pub_dato)
    os.makedirs("kpi-rapport", exist_ok=True)
    with open(f"kpi-rapport/{slug}-{aar}.html", "w", encoding="utf-8") as f:
        f.write(rapport_html)
    print(f"KPI-rapport generert: kpi-rapport/{slug}-{aar}.html")

    # 3. Oppdater sitemap
    oppdater_sitemap(slug, aar, pub_dato)

    # 4. Oppdater husleie- og lonnskalkulator kun i februar
    if datetime.now().month == 2:
        jan_vekst, jan_aar = hent_januar_kpi()
        if jan_vekst:
            oppdater_husleiekalkulator(jan_vekst, jan_aar)
        kpi_snitt, snitt_aar = hent_aarlig_kpi_snitt()
        if kpi_snitt:
            oppdater_lonnskalkulator(kpi_snitt, snitt_aar)

    print("\nAlt ferdig!")


if __name__ == "__main__":
    main()
