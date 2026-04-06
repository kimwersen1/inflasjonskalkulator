"""
Henter siste KPI-tall fra SSBs API og oppdaterer index.html automatisk.
Kjøres via GitHub Actions den 10. hver måned.

SSB API dokumentasjon: https://data.ssb.no/api/
Tabell 14700: Konsumprisindeks etter konsumgruppe (2015=100), fra 2026
Tabell 03014: Konsumprisindeks etter konsumgruppe (2015=100), historisk
"""

import requests
import json
import re
from datetime import datetime, timedelta

# ── SSB API KONFIGURASJON ─────────────────────────────────────────────────────

SSB_API_URL = "https://data.ssb.no/api/v0/no/table/14700"

# Konsumgruppe-koder i SSBs nye klassifisering (COICOP 2018)
# 00: KPI totalt, 011: Matvarer, 045: Elektrisitet, 041: Husleie,
# 072: Drivstoff, 083: Teletjenester
GRUPPER = {
    "00":  "kpi_total",
    "011": "matvarer",
    "045": "elektrisitet",
    "041": "husleie",
    "072": "drivstoff",
    "083": "teletjenester",
}

def hent_siste_kpi():
    """Henter siste 12-månedersendring per kategori fra SSB API."""

    # Finn forrige og nest forrige måned for 12-månedersendring
    i_dag = datetime.now()
    forrige_mnd = (i_dag.replace(day=1) - timedelta(days=1))
    samme_mnd_i_fjor = forrige_mnd.replace(year=forrige_mnd.year - 1)

    mnd_kode = forrige_mnd.strftime("%YM%m")
    fjor_kode = samme_mnd_i_fjor.strftime("%YM%m")

    print(f"Henter KPI for {mnd_kode} og {fjor_kode}...")

    query = {
        "query": [
            {
                "code": "Konsumgrp",
                "selection": {
                    "filter": "item",
                    "values": list(GRUPPER.keys())
                }
            },
            {
                "code": "ContentsCode",
                "selection": {
                    "filter": "item",
                    "values": ["KpiIndMnd"]
                }
            },
            {
                "code": "Tid",
                "selection": {
                    "filter": "item",
                    "values": [mnd_kode, fjor_kode]
                }
            }
        ],
        "response": {"format": "json-stat2"}
    }

    try:
        response = requests.post(SSB_API_URL, json=query, timeout=30)
        response.raise_for_status()
        data = response.json()
        print("SSB API svar mottatt!")
        return data, mnd_kode, fjor_kode, forrige_mnd
    except Exception as e:
        print(f"Feil ved API-kall: {e}")
        return None, None, None, None


def beregn_endringer(data, mnd_kode, fjor_kode):
    """Beregner 12-månedersendring per kategori."""
    if not data:
        return None

    verdier = data.get("value", [])
    dims = data.get("dimension", {})

    konsumgrp_ids = list(dims["Konsumgrp"]["category"]["index"].keys())
    tid_ids = list(dims["Tid"]["category"]["index"].keys())

    n_grp = len(konsumgrp_ids)
    n_tid = len(tid_ids)

    # Finn indekser for de to månedene
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

        idx_ny_val = i * n_tid + idx_ny
        idx_gammel_val = i * n_tid + idx_gammel

        ny_verdi = verdier[idx_ny_val]
        gammel_verdi = verdier[idx_gammel_val]

        if ny_verdi and gammel_verdi:
            endring = ((ny_verdi - gammel_verdi) / gammel_verdi) * 100
            endringer[navn] = round(endring, 1)
            print(f"  {navn}: {endring:.1f}%")

    return endringer


def formater_pst(verdi):
    """Formaterer prosentverdi med tegn."""
    if verdi >= 0:
        return f"+{verdi:.1f} %"
    else:
        return f"{verdi:.1f} %"


def oppdater_kpi_bar(html, endringer, mnd_label):
    """Oppdaterer KPI-baren øverst på siden."""
    kpi_total = endringer.get("kpi_total", 0)
    matvarer = endringer.get("matvarer", 0)
    elektrisitet = endringer.get("elektrisitet", 0)

    ny_bar = f'''  <div class="kpi-bar">
    <div class="kpi-bar-item">KPI {mnd_label}: <strong>{formater_pst(kpi_total)}</strong> <span class="arrow">{"↑" if kpi_total >= 0 else "↓"}</span></div>
    <div class="kpi-bar-item">Matvarer: <strong>{formater_pst(matvarer)}</strong> <span class="arrow">{"↑" if matvarer >= 0 else "↓"}</span></div>
    <div class="kpi-bar-item">Strøm: <strong>{formater_pst(elektrisitet)}</strong> <span class="arrow">{"↑" if elektrisitet >= 0 else "↓"}</span></div>
    <div class="kpi-bar-item hide-mobile">Kilde: <strong>SSB</strong></div>
  </div>'''

    html = re.sub(
        r'<div class="kpi-bar">.*?</div>\s*</div>',
        ny_bar,
        html,
        flags=re.DOTALL,
        count=1
    )
    return html


def oppdater_kategori_kort(html, endringer, mnd_label):
    """Oppdaterer kategori-kortene med nye tall."""
    mapping = {
        "kpi_total":    ("KPI totalt \\(alle varer\\)", "pos"),
        "matvarer":     ("Matvarer og alkoholfrie drikkevarer", "pos"),
        "elektrisitet": ("Elektrisitet inkl\\. nettleie", "pos"),
        "husleie":      ("Husleie", "pos"),
        "drivstoff":    ("Drivstoff og smøremidler", "pos"),
        "teletjenester":("Teletjenester", "pos"),
    }

    for key, (navn_pattern, _) in mapping.items():
        if key not in endringer:
            continue
        verdi = endringer[key]
        klasse = "pos" if verdi >= 0 else "neg"
        ny_pct = f'<div class="cat-pct {klasse}">{formater_pst(verdi)}</div>'

        # Finn og erstatt cat-pct for denne kategorien
        pattern = rf'(<div class="cat-name">{navn_pattern}</div>\s*<div class="cat-src">)[^<]*(</div>\s*</div>\s*<div class="cat-pct (?:pos|neg)">)[^<]*(</div>)'
        def erstatt(m):
            return m.group(1) + f'SSB KPI, {mnd_label}' + '</div>\n          </div>\n          ' + ny_pct
        html = re.sub(pattern, erstatt, html, flags=re.DOTALL)

    return html


def oppdater_highlight_box(html, endringer, mnd_label, forrige_mnd):
    """Oppdaterer highlight-boksen med siste tall."""
    kpi_total = endringer.get("kpi_total", 0)
    matvarer = endringer.get("matvarer", 0)

    mnd_navn = {
        1: "januar", 2: "februar", 3: "mars", 4: "april",
        5: "mai", 6: "juni", 7: "juli", 8: "august",
        9: "september", 10: "oktober", 11: "november", 12: "desember"
    }
    mnd_str = mnd_navn[forrige_mnd.month]
    aar = forrige_mnd.year
    aar_i_fjor = aar - 1

    ny_tekst = f'I {mnd_str} {aar} var den norske inflasjonen på <strong>{kpi_total:.1f} %</strong> sammenlignet med {mnd_str} {aar_i_fjor}. Matvarer steg med hele {matvarer:.1f} % i samme periode.'

    html = re.sub(
        r'(<div class="highlight-box">\s*)(.*?)(\s*</div>)',
        lambda m: m.group(1) + ny_tekst + m.group(3),
        html,
        flags=re.DOTALL,
        count=1
    )
    return html


def main():
    # Hent data
    data, mnd_kode, fjor_kode, forrige_mnd = hent_siste_kpi()

    if not data:
        print("Kunne ikke hente data fra SSB. Avbryter.")
        return

    # Beregn endringer
    endringer = beregn_endringer(data, mnd_kode, fjor_kode)

    if not endringer:
        print("Kunne ikke beregne endringer. Avbryter.")
        return

    # Lag månedsetikett
    mnd_navn = {
        1: "jan.", 2: "feb.", 3: "mars", 4: "apr.",
        5: "mai", 6: "juni", 7: "juli", 8: "aug.",
        9: "sep.", 10: "okt.", 11: "nov.", 12: "des."
    }
    mnd_label = f"{mnd_navn[forrige_mnd.month]} {forrige_mnd.year}"

    # Les index.html
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Oppdater HTML
    html = oppdater_kpi_bar(html, endringer, mnd_label)
    html = oppdater_kategori_kort(html, endringer, mnd_label)
    html = oppdater_highlight_box(html, endringer, mnd_label, forrige_mnd)

    # Skriv tilbake
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nindex.html oppdatert med KPI-tall for {mnd_label}!")


if __name__ == "__main__":
    main()
