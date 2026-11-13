"""Kerala: elected members of the 941 grama, 152 block and 14 district panchayats (December 2025 poll) as pri_member records
(cforms/_pri.py), heads (President, Vice President) first.

Sources (measured 2026-11-13 from dev-vps-3, Mumbai; no captcha, no login):
- State Election Commission, sec.kerala.gov.in/public/wyrlb/<d>/<type>: d = 1..14 is the district in REVERSE LSGD order
  (14 = Thiruvananthapuram = code 01, 1 = Kasaragod = code 14); type G = grama panchayats, B = block panchayats (a list:
  "# | G01001 - <name in Malayalam> | wards | members", link /public/wyrw/<lb id>), D = the district panchayat itself (its ward
  table), C = corporation (councillors.py). /public/wyrw/<lb id> = one body's ward table: ward no | ward name | member (link
  /public/wyr/view/<member id>) | post (Malayalam, blank where the body has not entered it) | party | reservation. The member
  page (English) gives name, position, age, front, party, votes, margin, ward code, phone, email, address (councillors.kl_member).
- The body's own site (Information Kerala Mission template, <site>.lsgkerala.gov.in/en): "profile-card" blocks h5 = name,
  p.member-title = post ("President", "Vice President & Chairman Standing Committee for finance") on the home page. Used for the
  heads only, where the SEC table has no post. Sites are listed at lsgkerala.gov.in/en/website/web (60 pages; the seed item
  walks it on the hub). The site codes (G020105) are not the SEC codes (G02005): the two meet by name (+ district).

Payloads (kind "form-pri_kl"):
- part "sec": url (wyrw/<id> or wyrlb/<d>/D), lb_id, sec_code, level, district, body, lgd_code. 1 GET of the ward table and 1 GET
  per member (about 18 per grama panchayat). Records pri:KL:<level>:<lgd_code or names>:w<ward no>; the President / Vice
  President rows also get head=True (head_rank 1 / 2).
- part "site": url (https://<site>/en), site_code, level, district, body, lgd_code. 1 GET. Records ...:head-site / vice-site.
- {"kind": "seed", "module": "pri_kl"} (councillors.py seed): items(get) walks the site index and lists the "site" items.
"""
import re

from bs4 import BeautifulSoup
from urllib.parse import urljoin

import councillors
import provenance
from cforms import _pri

METHOD = "html table (SEC ward table) + html labels (SEC member page); body site profile cards for heads"
# reader audit (audit.py): the SEC member page has no table; its repeated blocks are the site menus ("Know SEC | Commissioner |
# Who is who ...", "Voter Service | ...") and the empty dialogs ("Modal title | Close"); the newer member page (2026) splits the
# one member into sections ("Governance Profile", "Election Records", "Official Bio & Tenure", "Contact Details"). The blocks hold
# no other person. The member's record takes the member page as its source and names the ward table in list_url, so the ward
# table's rows are checked against those records (seeds/build_audit.py).
AUDIT_LEAVES_OUT = (r"^(Know SEC|Acts & Rules|Voter Service|Delimitation|RTI Officials|Modal title|Governance Profile|Election Records|"
                    r"Official Bio|Contact Details)\b")

STATE = "KL"
ELECTION = "Kerala 2025 (poll December 2025)"
BASE = "https://sec.kerala.gov.in"
INDEX = "https://lsgkerala.gov.in/en/website/web"
DISTRICTS = {"01": "Thiruvananthapuram", "02": "Kollam", "03": "Pathanamthitta", "04": "Alappuzha", "05": "Kottayam",
             "06": "Idukki", "07": "Ernakulam", "08": "Thrissur", "09": "Palakkad", "10": "Malappuram", "11": "Kozhikode",
             "12": "Wayanad", "13": "Kannur", "14": "Kasaragod"}
LEVEL = {"G": "gp", "B": "ps", "D": "zp"}
TYPE_EN = {"gp": "Grama Panchayat", "ps": "Block Panchayat", "zp": "District Panchayat"}
# Malayalam posts in the SEC ward table
ML_VICE = re.compile(r"വൈസ്\s*പ്രസിഡ")
ML_PRES = re.compile(r"പ്രസിഡ")


def sec_district(d):
    """URL district number (1..14) -> LSGD district code (14 -> 01)."""
    return f"{15 - int(d):02d}" if str(d).isdigit() and 1 <= int(d) <= 14 else ""


def head_of(post_ml="", post_en=""):
    """1 = President, 2 = Vice President, 0 = other member."""
    en = " ".join((post_en or "").split()).lower()
    if re.match(r"^vice[\s-]*president", en) or ML_VICE.search(post_ml or ""):
        return 2
    if re.match(r"^president\b", en) or (ML_PRES.search(post_ml or "") and not ML_VICE.search(post_ml or "")):
        return 1
    return 0


def body_list(html):
    """SEC list page (wyrlb/<d>/G or B): [(sec code, Malayalam name, lb id, wards text, members text, row no)]."""
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    for n, tr in enumerate(soup.select("table tr"), 1):
        a = tr.find("a", href=re.compile(r"/public/wyrw/\d+"))
        tds = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]
        if not a or len(tds) < 4:
            provenance.skip_row(tr, 'skip: not a or len(tds) < 4')
            continue
        m = re.match(r"^([GBD]\d{5})\s*-\s*(.*)$", " ".join(a.get_text(" ", strip=True).split()))
        if not m:
            provenance.skip_row(tr, 'skip: not m')
            continue
        out.append((m.group(1), m.group(2), a["href"].rsplit("/", 1)[1], tds[2], tds[3], n))
    return out


def ward_rows(html, url):
    """SEC ward table: [(row no, ward no, ward name, member name, post, party, reservation, member url)]."""
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    for n, tr in enumerate(soup.select("table tr"), 1):
        tds = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]
        if len(tds) < 6:
            provenance.skip_row(tr, 'skip: len(tds) < 6')
            continue
        a = tr.find("a", href=re.compile(r"wyr/view/\d+"))
        out.append((n, tds[0], tds[1], tds[2], tds[3], tds[4], tds[5], urljoin(url, a["href"]) if a else None))
    return out


def base(p):
    return {"lgd_code": p.get("lgd_code") or "", "body": p.get("body") or "", "body_regional": p.get("body_ml") or None,
            "body_type": TYPE_EN.get(p.get("level")), "district": p.get("district") or "", "block": p.get("block") or None,
            "election": ELECTION, "sec_code": p.get("sec_code") or None, "lb_id": p.get("lb_id") or None}


def fetch_sec(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    rows = ward_rows(r.text, p["url"])
    recs = []
    for n, wno, wname, mname, post_ml, party, resv, murl in rows:
        if councillors.stop:
            break
        d = {**base(p), "ward_no": wno, "ward_name_regional": wname, "name_regional": mname, "post_regional": post_ml or None,
             "party": party, "reservation_regional": resv, "list_url": p["url"]}
        src = {**provenance.at(r, p["url"]), "src_pos": {"table": 0, "row": n}}
        m = get(murl) if murl else None
        if m is not None:
            md = councillors.kl_member(m.text)
            d.update({"name": md.get("name"), "post": md.get("position"), "party": md.get("party") or party, "front": md.get("front"),
                      "age": md.get("age"), "votes": md.get("votes"), "margin": md.get("margin"), "ward_name": md.get("ward_name"),
                      "ward_code": md.get("ward_code"), "reservation": md.get("reservation"), "phone": md.get("phone"),
                      "email": md.get("email"), "address": md.get("address"), "serving_since": md.get("serving_since"),
                      "election_code": md.get("election"), "body_sec": md.get("body"), "url": murl})
            if not d["body"] and md.get("body"):      # English name of the body from the member page ("Parassala Grama Panchayath")
                d["body"] = re.sub(r"(?i)\s+(grama|block|district)\s+panchayath?\s*$", "", md["body"]).strip().title()
            src = {**provenance.at(m, murl), "src_pos": {"selector": "detail page labels", "list_row": n}}
        else:
            d["url"] = murl or p["url"]
            d["member_page"] = "no answer" if murl else "no link"
        rank = head_of(post_ml, d.get("post"))
        if rank:
            d.update({"head": True, "head_rank": rank})
        d["post"] = d.get("post") or {1: "President", 2: "Vice President"}.get(rank) or "Member"
        rid, data = _pri.record(STATE, p["level"], pkey=_pri.post_key(ward_no=wno), **d, **src)
        recs.append((rid, data))
    return recs, [], "" if recs else "no members"


def profile_cards(html):
    """Body site home page: [(index, name, post)] of div.profile-card + .card-body (h5 name, p.member-title post)."""
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    for i, card in enumerate(soup.select("div.profile-card")):
        body = card.find_next_sibling("div", class_="card-body") or card.parent.find("div", class_="card-body")
        if body is None:
            continue
        h, t = body.find("h5"), body.find(class_="member-title")
        if h and t:
            out.append((i, " ".join(h.get_text(" ", strip=True).split()), " ".join(t.get_text(" ", strip=True).split())))
    return out


def fetch_site(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = []
    for i, name, post in profile_cards(r.text):
        rank = head_of("", post)
        if not rank or not name:
            provenance.skipped('skip: not rank or not name')
            continue
        d = {**base(p), "name": name, "post": post, "head": True, "head_rank": rank, "url": p["url"], "site_code": p.get("site_code"),
             "source_kind": "body website", **provenance.at(r, p["url"]), "src_pos": {"selector": "div.profile-card", "index": i}}
        rid, data = _pri.record(STATE, p["level"], pkey=("head" if rank == 1 else "vice") + "-site", **d)
        recs.append((rid, data))
    return recs, [], "" if recs else "no head cards"


def fetch(p, get):
    return fetch_site(p, get) if p.get("part") == "site" else fetch_sec(p, get)


# ---- seed side ----------------------------------------------------------------------------------------------------------

def sec_items(lists, lgd=None):
    """Queue items from the SEC list pages: lists = {(d, type letter): html}; district panchayats from wyrlb/<d>/D directly."""
    lgd = lgd or _pri.Lgd(STATE)
    ml = MlIndex(lgd)
    out = []
    for d in range(1, 15):
        code = sec_district(d)
        dist = DISTRICTS[code]
        out.append(item_sec(f"{BASE}/public/wyrlb/{d}/D", f"D{code}", "zp", dist, dist, "", lgd.match("zp", dist), f"D{code}"))
        for t in ("B", "G"):
            for sec_code, name_ml, lb_id, wards, members, _ in body_list(lists.get((d, t), "")):
                lc = ml.match(LEVEL[t], dist, name_ml)
                out.append(item_sec(f"{BASE}/public/wyrw/{lb_id}", lb_id, LEVEL[t], dist, ml.name(lc), name_ml, lc, sec_code,
                                    expected=members))
    return out


def ml_key(s):
    """Malayalam name key: joiners (ZWJ / ZWNJ, also as &zwj; text), spaces, brackets and punctuation removed."""
    s = re.sub(r"&zwn?j;", "", s or "")
    return re.sub(r"[\s​-‍()\[\].,\-–/]+", "", s)


class MlIndex:
    """LGD bodies of Kerala by (level, district, Malayalam name key); the LGD extract carries local_body_name_local."""

    def __init__(self, lgd):
        self.lgd, self.idx = lgd, {}
        for code, lev, name, local, parent in lgd.rows:
            dist = next((lgd.by_code[c][2] for c in lgd.chain(code) if lgd.by_code[c][1] == "zp"), "")
            self.idx.setdefault((lev, _pri.norm(dist), ml_key(local)), set()).add(code)

    def match(self, level, district, name_ml):
        c = self.idx.get((level, _pri.norm(district), ml_key(name_ml)))
        return next(iter(c)) if c and len(c) == 1 else ""

    def name(self, code):
        r = self.lgd.by_code.get(code)
        return r[2] if r else ""


def item_sec(url, lb_id, level, district, body, body_ml, lgd_code, sec_code, expected=""):
    p = {"kind": "form-pri_kl", "part": "sec", "state": STATE, "url": url, "lb_id": lb_id, "sec_code": sec_code, "level": level,
         "district": district, "body": body, "body_ml": body_ml, "lgd_code": lgd_code, "election": ELECTION, "route": "direct",
         "india_only": "unchecked"}
    if _pri.digits(expected):
        p["expected"] = int(expected)
    return {"key": f"pri-kl-{sec_code.lower()}", "payload": {k: v for k, v in p.items() if v != ""}}


SITE_KIND = re.compile(r"\s+(Grama|Block|District)\s+Panchayat\s*$", re.I)


def index_rows(html):
    """lsgkerala.gov.in/en/website/web: [(name, site code, site, row)] of panchayat rows, and whether a next page exists."""
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    for t in soup.find_all("table"):
        for n, tr in enumerate(t.find_all("tr")):
            td = tr.find_all("td")
            if len(td) < 4:
                provenance.skip_row(tr, 'skip: len(td) < 4')
                continue
            name = " ".join(td[1].get_text(" ", strip=True).split())
            code = " ".join(td[2].get_text(" ", strip=True).split())
            a = td[3].find("a", href=True)
            site = (a["href"] if a else td[3].get_text(" ", strip=True)).strip()
            if re.fullmatch(r"[GBD]\d{6}", code) and site:
                out.append((name, code, site, n))
    more = soup.find("a", attrs={"rel": "next"}) is not None or soup.select_one("li.pager__item--next") is not None
    return out, more


def item_site(name, code, site, lgd):
    level = LEVEL[code[0]]
    dist = DISTRICTS.get(code[1:3], "")
    body = SITE_KIND.sub("", name).strip()
    host = re.sub(r"^https?://", "", site).strip("/")
    p = {"kind": "form-pri_kl", "part": "site", "state": STATE, "url": f"https://{host}/en", "site_code": code, "level": level,
         "district": dist, "body": body, "name_list": name, "lgd_code": lgd.match(level, dist if level == "zp" else body, district=dist),
         "election": ELECTION, "route": "abroad"}
    return {"key": f"pri-kl-site-{code.lower()}", "payload": {k: v for k, v in p.items() if v != ""}}


def seed_item():
    return {"key": "pri-kl-seed-sites", "payload": {"kind": "seed", "module": "pri_kl", "url": INDEX, "state": STATE, "route": "abroad"}}


def items(get):
    """On the hub: one "site" item per grama / block / district panchayat site in the lsgkerala.gov.in index."""
    lgd = _pri.Lgd(STATE)
    out, seen = [], set()
    for n in range(80):
        r = get(INDEX if n == 0 else f"{INDEX}?page=%2C%2C%2C{n}")
        if r is None:
            break
        rows, more = index_rows(r.text)
        for name, code, site, _ in rows:
            if code not in seen:
                seen.add(code)
                out.append(item_site(name, code, site, lgd))
        if not more:
            break
    return out
