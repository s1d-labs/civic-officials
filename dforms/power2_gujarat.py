"""Gujarat: the four GUVNL discoms' officer pages (one queue item each). Two card layouts:
- MGVCL (www.mgvcl.com/key-officials.php) and, by the same GUVNL template, DGVCL / PGVCL (www.dgvcl.com, www.pgvcl.com
  /key-officials.php): one card per officer: <h4> name, <p> qualification, <p><i fa-file> post (with "(Baroda City Circle)" for the
  circle SEs), <p><i fa-phone> phone, <p><i fa-envelope> e-mail. MGVCL: 31 officers (MD, CEs, ACEs, GMs, SEs of the 6 circles).
- UGVCL (www.ugvcl.com/senioroff, /keyofficials): one "team-item" card per officer: <h6> name, <span> post, e-mail; no phones.
  About 25 senior officers.
Level: a post naming a circle -> circle (area = the circle), a division -> division; else state (head office). No officer lists
below circle are public on these sites (division / sub-division offices are in the GUVNL consumer app only).
TLS: www.ugvcl.com sends no intermediate certificate: certs/sectigo_public_server_ov_r36.pem completes it. www.dgvcl.com and
www.pgvcl.com closed the TLS handshake from Germany and from India on 2026-11-11 (SSL_ERROR_SYSCALL): their items may fail.
Records "dept:power2_gujarat:<discom>:<post>:<name>".
"""
import re

from bs4 import BeautifulSoup

from dforms import _power, _util2

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "power2_gujarat"
PAGES = {
    "mgvcl": ("MGVCL", "https://www.mgvcl.com/key-officials.php", "Vadodara"),
    "dgvcl": ("DGVCL", "https://www.dgvcl.com/key-officials.php", "Surat"),
    "pgvcl": ("PGVCL", "https://www.pgvcl.com/key-officials.php", "Rajkot"),
    "ugvcl": ("UGVCL", "https://www.ugvcl.com/senioroff", "Mahesana"),
    "ugvcl-key": ("UGVCL", "https://www.ugvcl.com/keyofficials", "Mahesana"),
}


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "page": k, "url": u, "state": "GJ", "india_only": True}}
            for k, (_, u, _) in PAGES.items()]


def cards(soup):
    """(name, post, phone, email) for each officer card of either layout."""
    for box in soup.select("div.item-experts, div.team-item"):
        h = box.find(["h4", "h6", "h5"])
        name = h.get_text(" ", strip=True) if h else None
        post = phone = mail = None
        for el in box.find_all(["p", "span"]):
            icon = el.find("i")
            cls = " ".join(icon.get("class", [])) if icon else ""
            txt = " ".join(el.get_text(" ", strip=True).split())
            if "fa-phone" in cls:
                phone = txt
            elif "fa-envelope" in cls:
                mail = txt
            elif "fa-file" in cls or (el.name == "span" and not post and not icon and txt and "@" not in txt):
                post = post or txt
        if not post:   # MGVCL cards without an icon on the post line: the last <p> before the phone
            ps = [" ".join(p.get_text(" ", strip=True).split()) for p in box.find_all("p")]
            post = next((p for p in ps if re.search(r"engineer|manager|director|officer|controller|secretary", p, re.I)), None)
        yield name, post, phone, mail


def parse(html, page, url):
    discom, _, district = PAGES.get(page, (page.upper(), url, None))
    out = _power.Out(MODULE, "GJ", url, discom=discom)
    for name, post, phone, mail in cards(BeautifulSoup(html, "lxml")):
        name = _util2.person(name)
        if not (name or post):
            continue
        m = re.search(r"\(([^()]*(circle|division)[^()]*)\)", post or "", re.I)
        if m:
            area = re.sub(r"\s+", " ", m.group(1)).strip()
            level = "circle" if re.search("circle", area, re.I) else "division"
        else:
            area, level = f"{discom} Corporate Office", "state"
        out.add(f"{discom}:{post}:{name}", level, area, post=_power.clean(post), name=name, phone_=_util2.tel(phone or ""),
                email_=_power.email(mail), district=district if level == "state" else None)
    return out.recs


def fetch(p, get):
    page = p.get("page", "mgvcl")
    url = p.get("url") or PAGES[page][1]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, page, url)
    return recs, [_power.raw(MODULE, page, r.content, "html")], "" if recs else "no rows"
