"""Cuttack Municipal Corporation (cmccuttack.odisha.gov.in, WordPress): the field staff of each of its 59 wards. One page per ward,
/index.php/ward/ward-<N>/ (the home page links wards 1-59; ward 41 has no link there but has the same URL form). Each page has a
block <div class="name_of _ward"> with one <p><strong>label:</strong> NAME, mobile</p> per post:
  Name of the Ward | Name of the Corporator | Name of the Ward Officer | Name of the Junior Engineer |
  Name of the Community Organiser (NULM) | Name of the MPHS (Multi Purpose Health Supervisor).
The corporator is an elected member (the councillors task reads those), so the reader keeps only the four staff posts. One officer
often holds two posts in a ward (ward officer and junior engineer): both records are kept. Names are in capitals, as on the page.
The pages show no "Last Updated" date.
India only: no answer from Germany (2026-11-11, connect timeout); answers from India over https. The server does not send its
intermediate certificate (Sectigo Public Server Authentication CA DV R36, in certs/): the family's trust() completes the chain.
Not in archive.s1d.me (only the home page, cut short). Sample: ward 1, live from India 2026-11-11.
Records: level "ward", wards = [N]. Record ids: dept:ward2s_cuttack:w<N>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_cuttack"
BODY, LGD, STATE, DISTRICT = "Cuttack Municipal Corporation", "250501", "OD", "Cuttack"
BASE = "https://cmccuttack.odisha.gov.in/index.php/ward/ward-{}/"
WARDS = 59
POSTS = (("ward officer", "Ward Officer"), ("junior engineer", "Junior Engineer"),
         ("community organi", "Community Organiser"), ("mphs", "Multi Purpose Health Supervisor (MPHS)"))
PHONE = re.compile(r"(?:\+?91[\s-]*)?\d[\d\s-]{8,}\d")


def items(get=None):
    return [{"key": f"{MODULE}-w{n}", "payload": {"reader": MODULE, "url": BASE.format(n), "ward": str(n), "state": STATE,
                                                   "india_only": True}} for n in range(1, WARDS + 1)]


def split(value):
    """'DILLIP KUMAR SWAIN, 7205023600' -> (name, phones)."""
    v = _esw.clean(value)
    phones = PHONE.findall(v)
    name = PHONE.sub(" ", v)
    name = re.sub(r"[\s,;/:-]+$", "", re.sub(r"^[\s,;/:-]+", "", re.sub(r"\s+", " ", name)))
    return name, ", ".join(p.strip() for p in phones)


def parse(html, p):
    soup = _esw.soup(html)
    box = soup.select_one("div.ward-details") or soup
    lines = {}
    for para in box.find_all("p"):
        st = para.find("strong")
        if not st:
            continue
        label = _esw.clean(st.get_text(" ")).rstrip(":").lower()
        lines[label] = _esw.clean(para.get_text(" ").replace(st.get_text(" "), "", 1)).lstrip(": ")
    m = re.search(r"\d+", next((v for k, v in lines.items() if "name of the ward" == k), "") or "")
    ward = str(int(m.group())) if m else str(p.get("ward") or "")
    if not ward:
        return []
    seen, recs = set(), []
    for word, post in POSTS:
        value = next((v for k, v in lines.items() if word in k), "")
        name, phone = split(value)
        if not (name or phone):
            continue
        recs.append(_ward.record(MODULE, f"w{ward}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="ward", area=f"Ward {ward}", post=post, name=name,
                                 phone=phone, wards=[ward], source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"ward-{p.get('ward', 'x')}", r.content)], "" if recs else "no ward staff block"
