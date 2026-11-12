"""Kerala: heads of the 87 municipalities and 6 corporations elected by the new councils after the December 2025 poll
(Chairperson / Vice Chairperson; Mayor / Deputy Mayor), as councillor records with their own ward.

Why: the SEC member pages (sec.kerala.gov.in/public/wyr/view/<id>, read by councillors.py kl-body) show a post only where the
body has entered it; on 2026-11-12, 71 of 93 bodies still showed every member as "Elected Member of Local Administration"
(we hold 22 chairpersons and 1 mayor from SEC). The bodies' own sites (Information Kerala Mission template, <site>/en) show them:
- /en/members (new KSMART template, most municipalities): one div.member-card per member, data-committee = the post in lower
  case; h5 = name; first p = post ("Chairperson", "Vice Chairperson & Chairman Standing Committee for Finance"); second p =
  "<ward no>, <ward name>"; link /en/member/<uuid>. Every member is shown; only heads become records here (the SEC holds the rest).
- else the home page, read with dforms/ulb_kl.py (team cards "post | name | mobile", or the older corporation name tables),
  which gives the head's name and mobile but no ward.
One queue item = one body: payload {"kind": "form-kl_heads", "state": "KL", "url" (https://<site>/en), "body", "body_type",
"code" (LSGD code M030100 / C...), "district", "lgd_code"}. The sites answer from outside India.
Record id councillor:KL:head:<code>:<post key> (chair, vice, mayor, deputy-mayor).
"""
import re

from bs4 import BeautifulSoup

from dforms import ulb_kl

METHOD = "html cards (div.member-card of /en/members) or the home page's head cards (dforms/ulb_kl)"

ELECTION = "Kerala 2025 (poll December 2025; heads elected by the councils), as listed on the body's website"
POSTS = [(r"deputy\s*mayor", "deputy-mayor", "Deputy Mayor"), (r"vice[\s-]*chair", "vice", "Vice Chairperson"),
         (r"\bmayor\b", "mayor", "Mayor"), (r"^\s*chair\s*(?:person|man)\b", "chair", "Chairperson")]


def post_of(text):
    t = " ".join((text or "").split())
    for rx, key, pos in POSTS:
        if re.search(rx, t, re.I):
            if key == "chair" and re.search(r"standing|committee", t, re.I) and not re.match(r"^\s*chairperson\s*$", t, re.I):
                return None
            return key, pos
    return None


def member_cards(html):
    """[(name, post text, ward no, ward name, member url, card index)] from /en/members."""
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    for i, card in enumerate(soup.select("div.member-card")):
        h = card.find("h5")
        ps = [" ".join(p.get_text(" ", strip=True).split()) for p in card.select("p.card-text")]
        a = card.find("a", href=re.compile(r"/member/"))
        post = ps[0] if ps else (card.get("data-committee") or "")
        wn, wname = None, None
        if len(ps) > 1:
            m = re.match(r"^\s*(\d+)\s*,?\s*(.*)$", ps[1])
            if m:
                wn, wname = m.group(1), m.group(2) or None
        out.append((" ".join(h.get_text(" ", strip=True).split()) if h else "", post, wn, wname, a["href"] if a else None, i))
    return out


def base_of(p):
    return {"type": "councillor", "state": "KL", "body": p.get("body_list") or p.get("name_list") or p.get("body"),
            "body_en": p.get("name_list") or p.get("body"), "body_type": p.get("body_type"), "district": p.get("district"),
            "lb_code": p.get("code"), "lgd_code": p.get("lgd_code"), "election": ELECTION, "indirect": True}


def from_members(html, p, url):
    recs = {}
    host = re.match(r"https?://[^/]+", url).group(0)
    for name, post, wn, wname, link, i in member_cards(html):
        hit = post_of(post)
        if not hit or not name:
            continue
        key, pos = hit
        if key == "chair" and p.get("code", "").startswith("C"):
            key, pos = "mayor", "Mayor"
        d = {**base_of(p), "ward_no": "chair" if key in ("chair", "mayor") else "vice", "position": pos, "position_local": post,
             "name": name, "own_ward": wn, "own_ward_name": wname, "url": host + link if link else url, "list_url": url,
             "src_url": url, "src_pos": {"selector": "div.member-card", "index": i}}
        recs.setdefault(f"councillor:KL:head:{p.get('code')}:{key}", {k: v for k, v in d.items() if v not in (None, "")})
    return recs


def from_home(html, p, url):
    recs = {}
    for _, o in ulb_kl.parse(html, dict(p, url=url), url):
        hit = post_of(o.get("post") or o.get("designation") or "")
        if not hit or not o.get("name"):
            continue
        key, pos = hit
        d = {**base_of(p), "ward_no": "chair" if key in ("chair", "mayor") else "vice", "position": pos,
             "position_local": o.get("post") or o.get("designation"), "name": o.get("name"), "phone": o.get("phone"),
             "office_phone": o.get("office_phone"), "office_email": o.get("office_email"), "last_updated": o.get("last_updated"),
             "url": url, "src_url": url, "src_pos": o.get("src_pos")}
        recs.setdefault(f"councillor:KL:head:{p.get('code')}:{key}", {k: v for k, v in d.items() if v not in (None, "")})
    return recs


def fetch(p, get):
    site = p["url"].rstrip("/")
    murl = site + "/members"
    recs = {}
    r = get(murl)
    if r is not None:
        recs = from_members(r.text, p, murl)
    if not any(k.endswith((":chair", ":mayor")) for k in recs):
        h = get(site)
        if h is not None:
            for k, d in from_home(h.text, p, site).items():
                recs.setdefault(k, d)
    elif recs:
        # the home page gives the heads' mobiles: add them to the member-card records
        h = get(site)
        if h is not None:
            for k, d in from_home(h.text, p, site).items():
                if k in recs and d.get("phone") and not recs[k].get("phone"):
                    recs[k]["phone"] = d["phone"]
                    recs[k]["phone_src_url"] = site
    out = list(recs.items())
    return out, [], "" if out else "no head on the members page or the home page"
