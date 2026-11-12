"""Goa: MLAs of the 8th Goa Legislative Assembly (2022-) from goavidhansabha.gov.in. Answers from Germany too.

The list page (mlas.php) names the sitting members (section "MLA's"; section "Expired" = members who died: left out) with their
member page member_detail.php?mem_id=<id>. Each member page gives: name, "Constituency No/Name: 06 - Siolim", party (symbol
alt text), designation (Chief Minister, Speaker ...), date of birth, email, fax, phones "Official", "Residence", "Personal",
and addresses "Office", "Permanent", "Present". "-NA-" means empty. Some emails are shown only as images: their URLs go in
"email_images" (no OCR here). One queue item = one member page.
items(get) reads the live list page when get is given; items() without get gives the 38 members of the list saved on 2026-11-05.
"""
import re

from dforms import _leg

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_ga"
BASE = "https://www.goavidhansabha.gov.in/"
LIST = BASE + "mlas.php"
PAGE = BASE + "member_detail.php?mem_id={}"
# mlas.php, archive copy of 2026-11-05: sitting members (mem_id)
MEM_IDS = [250, 251, 252, 70, 249, 253, 254, 51, 38, 255, 29, 256, 257, 258, 259, 54, 260, 32, 243, 94, 43, 261, 262, 26, 263,
           68, 39, 33, 25, 264, 265, 266, 267, 268, 56, 36, 40, 34]


def list_ids(html):
    """mem_ids of the sitting members on mlas.php (before the "Expired" heading)."""
    i = html.find('id="E"')
    part = html[html.find('id="A"'):i if i > 0 else None]
    out = []
    for m in re.findall(r"member_detail\.php\?mem_id=(\d+)", part):
        if int(m) not in out:
            out.append(int(m))
    return out


def items(get=None):
    ids = MEM_IDS
    if get is not None:
        r = get(LIST)
        live = list_ids(r.content.decode("utf-8", "replace")) if r is not None else []
        ids = live or ids
    return [{"key": f"leg_ga-mem-{i}", "payload": {"reader": MODULE, "url": PAGE.format(i), "state": "GA", "india_only": False,
                                                    "mem_id": i}} for i in ids]


def _na(s):
    s = _leg.clean(s)
    return "" if s.strip("- ").upper() in ("NA", "N/A", "") else s


def parse(html, url):
    from bs4 import BeautifulSoup
    html = html.replace("\u200d", "").replace("\u200c", "")   # _esw.clean turns ZWJ/ZWNJ into spaces inside Devanagari words
    soup = BeautifulSoup(html, "lxml")
    box = soup.select_one(".mla-info-bx")
    if box is None or box.find("h3") is None:
        return []
    name = _leg.clean(box.find("h3").get_text(" "))
    desig = box.select_one("p.desig")
    cp = next((p for p in box.find_all("p") if "Constituency" in p.get_text()), None)
    m = re.search(r"Constituency No/Name:\s*(\d+)\s*-\s*(.+)", _leg.clean(cp.get_text(" ")) if cp else "")
    no, cons = (m.group(1), _leg.clean(m.group(2))) if m else (None, "")
    party = soup.select_one(".party-sysmbol-bx img")
    f, email_images = {}, []
    for tr in soup.select(".personal-detail tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2:
            k = _leg.clean(tds[0].get_text(" ")).rstrip(": ").lower()
            f[k] = _na(tds[1].get_text(" "))
            if k == "email":            # some members' addresses are shown only as images
                email_images = [i["src"] for i in tds[1].find_all("img") if i.get("src")]
    seat, note = _leg.ac_seat("GA", no, cons)
    return [_leg.member(MODULE, "GA", "AC", seat, name, constituency=cons, party=party.get("alt", "") if party else "",
                        source=url, email=f.get("email", ""), phone_office=f.get("official", ""),
                        phone_residence=f.get("residence", ""), mobile=f.get("personal", ""), fax=f.get("fax", ""),
                        office_address=f.get("office", ""), permanent_address=f.get("permanent", ""),
                        residence_address=f.get("present", ""), designation=_leg.clean(desig.get_text(" ")) if desig else "",
                        seat_no=int(no) if no else None, note=note, email_images=", ".join(email_images))]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, f"mem-{p.get('mem_id', 'x')}", r.content, "html")]
    recs = parse(r.content.decode("utf-8", "replace"), p["url"])
    return recs, files, "" if recs else "no member on the page"
