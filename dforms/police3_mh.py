"""Maharashtra district police sites that left the state Next.js template (police2s_mh) for their own static HTML site, e.g.
Jalna (jalnapolice.gov.in, 2026-11): impcon.html "Important Contact" has three tables: district officers (SP, Addl. SP, Home
DySP, SDPOs: "Police Officer's Name | Post | Mobile No | Landline No | Email Address"), the station in-charges ("Police Officer's
Name | Police Station | Mobile No | Landline No | Email Address", PI / API with name and mobile, plus the cyber police station)
and the branch in-charges ("Police Officer's Name | Branch | Mobile No | post": LCB, EOW, city and rural traffic, Bharosa cell,
AHTU, control room ...). The old /en/about/police-station-incharge path answers 404 there. Parsing: police3_tab.tables.
Payload "kind": "raigad" = Raigad (www.raigadpolice.gov.in, own CMS): one page per station, /en/police-station-details/<name>
(28 links on the home page; items(get) lists them). Each page: <h2> station, <h4> officer name, <h6> rank, "single-item" blocks
"Landline No. | Mobile No. | Email | Address"; the page head "Contact Info" lists the district numbers ("Sp. Raigad : 02141 222093",
"Add. Sp. Raigad", "DYSP HQ", "Control Room", "Emergency No.", "WhatsApp No.", "Email"): read on the item with "contacts": true.
Answers from Mumbai (2026-11-13); abroad unchecked. One queue item = one page. Record id dept:police3_mh:<district>:<place>.
"""
import re
from urllib.parse import unquote

from bs4 import BeautifulSoup

from dforms import police3_tab
from dforms._police import clean, email, gz, phones, rec, slug, uniq

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police3_mh"


RAIGAD = "https://www.raigadpolice.gov.in/"
HEAD_POSTS = [("Sp. Raigad", "Superintendent of Police", "district", "office"), ("Add. Sp. Raigad", "Addl. Superintendent of Police",
              "district", "office"), ("DYSP HQ", "DySP HQ", "district", "unit"), ("Control Room", "Control Room", "district",
              "control_room"), ("Emergency No.", "Emergency number", "district", "control_room"), ("WhatsApp No.",
              "WhatsApp number", "district", "control_room")]


def items(get):
    r = get(RAIGAD)
    if r is None:
        return []
    names = sorted(set(re.findall(r'href="/(?:mr|en)/police-station-details/([^"]+)"', r.text)))
    return [{"key": f"{M}:raigad:{slug(unquote(n))}", "payload": {"reader": M, "kind": "raigad", "state": "MH", "district": "Raigad",
             "url": f"{RAIGAD}en/police-station-details/{n}", "contacts": i == 0}} for i, n in enumerate(names)]


def raigad(html, url, contacts=False):
    soup = BeautifulSoup(html, "lxml")
    out = []
    h2 = soup.find("h2")
    station = clean(h2.get_text(" ", strip=True)) if h2 else None
    box = soup.find("div", class_="content_block_6")
    if station and box:
        name = box.find("h4")
        rank = box.find("h6")
        f = {}
        for it in box.find_all("div", class_="single-item"):
            lab, val = it.find("h6"), it.find("h4")
            if lab and val:
                f[clean(lab.get_text(" ", strip=True)).lower().strip(" .:")] = clean(val.get_text(" ", strip=True))
        out.append(rec(M, f"raigad:{slug(station)}", level="police_station", office_type="police station", area=station,
                       post="SHO", rank=clean(rank.get_text(" ", strip=True)) if rank else None,
                       name=clean(name.get_text(" ", strip=True)) if name else None,
                       phone=phones(f.get("mobile no"), f.get("landline no")), email=email(f.get("email") or ""),
                       address=f.get("address"), district="Raigad", state="MH", source=url, src_url=url,
                       src_pos={"block": "station", "h2": station}))
    if contacts:
        text = soup.get_text(" | ", strip=True)
        for label, post, level, otype in HEAD_POSTS:
            m = re.search(re.escape(label) + r"\s*:\s*([+\d][\d\s+-]{6,})", text)
            if m:
                out.append(rec(M, f"raigad:{slug(post)}", level=level, office_type=otype, area="Raigad", post=post,
                               phone=phones(m.group(1).strip()), district="Raigad", state="MH", source=url, src_url=url,
                               src_pos={"block": "contact info", "label": label}))
    return uniq(out)


def fetch(p, get):
    url = p["url"]
    if p.get("kind") == "raigad":
        r = get(url)
        if r is None:
            return [], [], "no answer"
        recs = raigad(r.text, url, p.get("contacts"))
        return recs, [gz(M, "raigad-" + slug(unquote(url.rsplit("/", 1)[-1])), r.content)], "" if recs else "no rows"
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = police3_tab.tables(r.text, url, M, p["district"], p.get("state", "MH"))
    return recs, [gz(M, slug(p["district"]) + "-" + slug(url.rstrip("/").rsplit("/", 1)[-1]), r.content)], "" if recs else "no rows"
