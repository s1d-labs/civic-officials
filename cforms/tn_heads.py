"""Tamil Nadu: heads of the municipal corporations and municipalities (Mayor, Deputy Mayor, Chairman/Chairperson, Vice-Chairman),
elected indirectly by the councils on 04.03.2022 (and later by casual elections), from each body's own site on the state
platform www.tnurbantree.tn.gov.in/<site>/ (WordPress multisite, 155 sites). TNSEC publishes no indirect-election results.
The "Who's Who" pages have no common address (whos-who/mayor, chairman, vice-chairman, deputy-mayor ...), so the reader asks
the site's public WordPress API: <site>/wp-json/wp/v2/pages?search=<term> for "chair", "mayor" and "தலைவர்" (page content and
"modified" date included), and keeps the pages whose title names a head post. A page is a label | value table (Name, Name of
the Party, Address, Office / Residence Address, Mobile No / Contact No., Email ID), sometimes inside an outer table with the photo.
The body's sites show no term dates: each record keeps the page's last change ("page_modified"); a page last changed before the
2022 indirect election (04.03.2022) can show the head of the 2011-2016 council: such records get "old_page": true.
One queue item = one site. Payload {"kind": "form-tn_heads", "state": "TN", "url" (the site), "site", "name_en", "lgd_code"}.
Record id councillor:TN:head:<site>:<post key> (mayor, deputy-mayor, chair, vice-chair).
The platform answers from outside India.
"""
import json
import re
from urllib.parse import quote

from bs4 import BeautifulSoup
import provenance

METHOD = "html table (in a WordPress search answer: json api)"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://www.tnurbantree.tn.gov.in/"
TERMS = ("chair", "mayor", "தலைவர்")
ELECTION = "Tamil Nadu 2022 indirect election of heads (04.03.2022), as listed on the body's website"
# title -> (post key, position); first match wins, so "Vice" / "Deputy" come before the plain post
POSTS = [(r"deputy\s*mayor|துணை\s*மேயர்|துணை\s*மாநகர", "deputy-mayor", "Deputy Mayor"),
         (r"vice[\s-]*chair|துணைத்?\s*தலைவர்", "vice-chair", "Vice Chairperson"),
         (r"\bmayor\b|மேயர்|மாமன்ற\s*தலைவர்", "mayor", "Mayor"),
         (r"\bchair\s*(?:man|person|woman)?\b|^\s*(?:நகர்மன்றத்?\s*)?தலைவர்", "chair", "Chairperson")]
NOT_HEAD = re.compile(r"committee|commission|standing|ward|council(?:lor|or|ar)s?\b|charter|disclosure|engineer|officer|staff|"
                      r"குழு|உறுப்பினர்", re.I)
LABELS = [("name", r"^name$|^name of the (chair|mayor|vice|deputy)|பெயர்"), ("party", r"party|கட்சி"),
          ("office_address", r"office\s*address"), ("address", r"address|முகவரி"),
          ("phone", r"mobile|contact|phone|cell|தொலைபேசி|கைபேசி|அலைபேசி"), ("email", r"e-?mail|மின்னஞ்சல்"),
          ("ward_no", r"^ward|வார்டு")]
OLD_BEFORE = "2022-03-04"


def search_url(site, term):
    return f"{BASE}{site}/wp-json/wp/v2/pages?search={quote(term)}&_fields=id,link,title,content,modified&per_page=50"


def text(el):
    return " ".join(el.get_text(" ", strip=True).split()).strip(" :-")


def post_of(title):
    t = BeautifulSoup(title or "", "lxml").get_text(" ", strip=True)
    if not t or NOT_HEAD.search(t):
        return None
    for rx, key, pos in POSTS:
        if re.search(rx, t, re.I):
            return key, pos, t
    return None


def label_key(label):
    lab = label.lower().strip(" :.-")
    for key, rx in LABELS:
        if re.search(rx, lab, re.I):
            return key
    return None


def pairs(html):
    """(label key, value, table no, row no) from label | value rows; text lines 'Label : value' when no table holds a name."""
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    for ti, tbl in enumerate(soup.find_all("table")):
        for ri, tr in enumerate(tbl.find_all("tr", recursive=False) or tbl.select(":scope > tbody > tr")):
            tds = [td for td in tr.find_all(["td", "th"], recursive=False) if not td.find("table")]
            cells = [text(td) for td in tds]
            cells = [c for c in cells if c]
            if len(cells) >= 2:
                key = label_key(cells[0])
                if key:
                    out.append((key, cells[1], ti, ri))
    if not any(k == "name" for k, *_ in out):
        for li, line in enumerate(soup.get_text("\n").split("\n")):
            m = re.match(r"\s*([^:]{2,40}?)\s*[:：-]\s*(.+)$", line)
            if m and label_key(m.group(1)):
                out.append((label_key(m.group(1)), " ".join(m.group(2).split()), None, li))
    return out


def phones(s):
    d = re.sub(r"\D", "", s or "")
    d = d[2:] if len(d) == 12 and d.startswith("91") else d
    if len(d) >= 20 and len(d) % 10 == 0 and all(d[i] in "6789" for i in range(0, len(d), 10)):
        return [d[i:i + 10] for i in range(0, len(d), 10)]          # "7305712227 9363042912": two mobiles
    out = []
    for m in re.findall(r"(?:\+?91[\s-]*)?(?:0?\d[\d\s-]{8,13}\d)", s or ""):
        d = re.sub(r"\D", "", m)
        d = d[2:] if len(d) == 12 and d.startswith("91") else d
        if len(d) >= 10 and d not in out:
            out.append(d)
    return out


def party_short(s):
    m = re.search(r"\(([A-Z][A-Z.()\- ]{1,15})\)\s*$", s or "")
    return m.group(1).replace(".", "").strip() if m else s


def name_clean(s):
    s = re.sub(r"^(thiru|tmt|selvi|thirumathi|mr|mrs|ms|dr|adv|திரு|திருமதி|செல்வி)\b\.?\s*", "", s or "", flags=re.I)
    s = re.sub(r"[\s,(-]*\b(vice[\s-]*)?(chair\s*(man|person|woman)?|mayor|deputy\s+mayor)\b[\s.)]*$", "", s, flags=re.I)
    return s.strip(" .")


def parse(answers, p):
    """answers: [(search url, json text)] -> records (one per head page; the same page from two searches once)."""
    site = p.get("site")
    seen, recs = set(), []
    for ai, (url, body) in enumerate(answers):
        try:
            pages = json.loads(body)
        except (ValueError, TypeError):
            continue
        if not isinstance(pages, list):
            continue
        for pi, pg in enumerate(pages):
            if not isinstance(pg, dict):
                continue
            hit = post_of((pg.get("title") or {}).get("rendered"))
            if not hit or pg.get("id") in seen:
                continue
            key, pos, title = hit
            got = {}
            rows = []
            for k, v, ti, ri in pairs((pg.get("content") or {}).get("rendered")):
                if k not in got and v:
                    got[k] = v
                    rows.append({"label": k, "table": ti, "row": ri})
            name = name_clean(got.get("name"))
            if not name or len(name) < 3:
                continue
            seen.add(pg.get("id"))
            mod = (pg.get("modified") or "")[:10]
            ph = phones(got.get("phone"))
            d = {"type": "councillor", "state": "TN", "body": p.get("name_en") or site, "body_en": p.get("name_en"),
                 "lgd_code": p.get("lgd_code"), "site": site, "position": pos, "position_local": title,
                 "ward_no": "chair" if key in ("mayor", "chair") else "vice", "name": name, "name_as_listed": got.get("name"),
                 "party": party_short(got.get("party")), "party_as_listed": got.get("party"),
                 "address": got.get("address"), "office_address": got.get("office_address"),
                 "phone": ph[0] if ph else None, "phones": ph or None, "phone_as_listed": got.get("phone"),
                 "email": got.get("email"), "own_ward": got.get("ward_no"),
                 "election": ELECTION, "indirect": True, "page_modified": pg.get("modified"),
                 "in_charge": bool(re.search(r"in\s*-?\s*charge|i/c", title, re.I)) or None,
                 "old_page": bool(mod and mod < OLD_BEFORE) or None,
                 "url": pg.get("link"), "list_url": url, "src_url": url,
                 "src_pos": {"index": pi, "id": pg.get("id"), "page": pg.get("link"), "rows": rows}}
            recs.append((f"councillor:TN:head:{site}:{key}", {k: v for k, v in d.items() if v not in (None, "", [])}))
    out, n = [], {}
    for rid, d in recs:          # two pages for one post (an old and a new one): keep both, the newer first
        n[rid] = n.get(rid, 0) + 1
        out.append((rid if n[rid] == 1 else f"{rid}-{n[rid]}", d))
    return out


def fetch(p, get):
    site = p["site"]
    answers, files = [], []
    for term in TERMS:
        url = search_url(site, term)
        r = get(url)
        if r is None:
            continue
        answers.append((url, r.text))
    if not answers:
        return [], [], "no answer"
    recs = parse(answers, p)
    # newest page first for each post, so the plain id holds the current head
    by = {}
    for rid, d in recs:
        by.setdefault(rid.rsplit("-", 1)[0] if re.search(r"-\d+$", rid) else rid, []).append(d)
    out = []
    for base, ds in by.items():
        ds.sort(key=lambda d: d.get("page_modified") or "", reverse=True)
        for i, d in enumerate(ds):
            out.append((base if i == 0 else f"{base}-{i + 1}", d))
    return out, files, "" if out else "no head page"


def items(get=None):
    """Queue items from platform_sites.csv (tnurbantree sites) with the LGD codes in seeds/tn_heads_lgd.json."""
    import csv
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lgd = json.load(open(os.path.join(here, "seeds", "tn_heads_lgd.json"), encoding="utf-8"))
    out = []
    with open(os.path.join(here, "platform_sites.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["state_code"] != "TN" or "tnurbantree" not in row["domain"]:
                continue
            site = row["name"]
            if site.startswith("wpfc-"):          # a cache plugin folder, not a body
                provenance.skip_row(row, 'skip: site.startswith("wpfc-")')
                continue
            info = lgd.get(site) or {}
            out.append({"key": f"tn-heads-{site}", "payload": {"kind": "form-tn_heads", "state": "TN", "url": row["url"],
                        "site": site, "name_en": info.get("name") or site.replace("-", " ").title(),
                        "lgd_code": info.get("lgd_code")}})
    return out
