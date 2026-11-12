"""Puducherry Police: police.py.gov.in. get_station.php = JSON list of all 57 police stations and units of the UT
(Puducherry, Karaikal, Mahe, Yanam: id, district, ps_code, ps_name), then one page station.php?id=<id> per station with the
'Officer In Charge' card (name and rank), phone and official email. Works from outside India. One queue item = the whole UT
(58 requests). Kept: the list and the station card of every page. Record id dept:police_py:<ps_code>."""
import json
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, uniq

METHOD = "json api + html page"     # source trail (provenance.py): how this reader reads its sources

M = "police_py"
BASE = "https://police.py.gov.in/"
RANK = re.compile(r"\b(Inspector|Sub[- ]Inspector|Superintendent|Dy\.? ?S\.?P|Assistant Sub|SI\b|ASI\b|Head Constable)", re.I)


def station(html):
    soup = BeautifulSoup(html, "lxml")
    box = soup.select_one(".station-page") or soup
    d = {}
    t = box.select_one(".station-title")
    d["title"] = clean(t.get_text(" ", strip=True)) if t else None
    o = box.select_one(".officer-name")
    officer = clean(o.get_text(" ", strip=True)).rstrip(".") if o else None
    if officer:
        name, _, rank = officer.rpartition(",")
        if name and RANK.search(rank):
            d["name"], d["rank"] = name.strip(), rank.strip()
        else:
            d["name"] = officer
    text = box.get_text("\n", strip=True)
    m = re.search(r"Phone:\s*\n?([^\n]*)", text)
    d["phone"] = phones(m.group(1)) if m else None
    m = re.search(r"Email:\s*\n?([^\n]*)", text)
    d["email"] = email(m.group(1)) if m else None
    return d, str(box)


def fetch(p, get):
    r = get(p.get("url", BASE + "get_station.php"))
    if r is None:
        return [], [], "no answer"
    files = [gz(M, "get_station.json", r.content)]
    try:
        rows = r.json()
    except ValueError:
        return [], files, "not json"
    recs, cards, missed = [], [], 0
    for x in rows:
        url = f"{BASE}station.php?id={x['id']}"
        s = get(url)
        d = {}
        if s is not None:
            d, card = station(s.text)
            cards.append(f"<section data-id=\"{x['id']}\">{card}</section>")
        else:
            missed += 1
        recs.append(rec(M, x.get("ps_code") or f"id{x['id']}", area=x.get("ps_name"), post="Officer in charge",
                        name=d.get("name"), rank=d.get("rank"), phone=d.get("phone"), email=d.get("email"), state="PY",
                        district=(x.get("district") or "").title() or None, office_id=x.get("ps_code"), source=url))
    files.append(gz(M, "stations.html", "<html><body>" + "\n".join(cards) + "</body></html>"))
    recs = uniq(recs)
    return recs, files, "" if recs and missed < len(rows) else "station pages did not answer"
