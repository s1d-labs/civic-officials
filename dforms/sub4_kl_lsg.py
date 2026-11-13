"""Kerala: the staff of every block panchayat (Secretary = Block Development Officer), grama panchayat (Secretary = panchayat
secretary) and district panchayat, from each body's own site on the Information Kerala Mission template
(<body>.lsgkerala.gov.in, Drupal theme "lsgdgrama"; one template for all 1,200 local bodies).

Index: lsgkerala.gov.in/en/website/web (the same state index as dforms/ulb_kl.py: Slno | Localbody Name | Localbody Code |
Website, about 26 rows per page, ?page=%2C%2C%2C<n>). Code letter: B = block panchayat (152), G = grama panchayat (941),
D = district panchayat (14), M / C = towns (read by ulb_kl). Code digits 1-2 = district (01 Thiruvananthapuram ... 14 Kasaragod).

Body site (measured 2026-11-13 from Mumbai on Adimaly block panchayat B060100, Adat G080601, Adimaly G060101, Alangad B070200):
- /en (home): the menu links a staff page whose title differs per body: "Officials and Employees" (Adimaly block), "Staff
  Details" (Adat, Adimaly GP), "Block Panchayath Staffs" (Alangad: empty page on 2026-11-13). The reader follows menu links of
  the same host whose text names officials / staff / employees (not "Implementing Officers" / "നിർവ്വഹണ ഉദ്യോഗസ്ഥർ", "Official Web
  Portals", elected members or "Employees of Constituent Institutions"), at most 2. Some staff pages are empty (Alangad,
  Agali G090601 "ജീവനക്കാർ" on 2026-11-13): the office record still comes from /en/emails.
- the staff page: an HTML table (Sl. No. | Full Name | Designation | Seat | Date of Joining | Mobile Number; headers carry
  emoji on some sites) or cards (article.employee-card: div.name, div.designation, "Section" / "Responsibility" values,
  div.phone). Every row is kept: Secretary, Assistant Secretary, JBDOs, clerks, VEOs, engineers, drivers.
- /en/emails: "District: Idukki Pincode: 685561 Phone: 04864222671 Email: bdoadimali@gmail.com" = the office of the body,
  then a table of the offices under it (office -> email). The office phone and email go on the Secretary record
  (office_phone, office_email); with no Secretary row a record "Secretary (office)" carries them alone. The office list
  rows are kept as level "office" records (post = the office as written, email).

Records (dept rural_development; level block / gram_panchayat / district for the body's staff): area = the body name without
"Block Panchayat" / "Grama Panchayat", district = LGD name + district_code, lb_code, body_type, post = "Block Development
Officer (Secretary, Block Panchayat)" / "Panchayat Secretary" / "Secretary, District Panchayat" for the Secretary, else the
designation as written; designation, section, responsibility, seat, joined (as written), phone, is_head; a row named "Vacant" ("Vaccant") keeps
post and phone with vacant=true and no name. Answers from abroad
(same template as ulb_kl, checked from Germany 2026-11-11 for towns): route abroad (civic-officials-depts).
Queue: {"kind": "seed", "module": "sub4_kl_lsg"} lists one item per body; item = 3-4 GETs.
Ids: dept:sub4_kl_lsg:<code lower>:<n> (n = row on the staff page, 1-based, in page order) / :office / :sub:<n>.
"""
import re
from urllib.parse import urljoin, urlparse

from dforms import _esw

METHOD = "html table or cards (staff page of the body site) + office block of /en/emails"     # source trail (provenance.py)

MODULE = "sub4_kl_lsg"
INDEX = "https://lsgkerala.gov.in/en/website/web"
PAGES = 80
DISTRICTS = {"01": ("Thiruvananthapuram", "565"), "02": ("Kollam", "559"), "03": ("Pathanamthitta", "564"),
             "04": ("Alappuzha", "554"), "05": ("Kottayam", "560"), "06": ("Idukki", "556"), "07": ("Ernakulam", "555"),
             "08": ("Thrissur", "566"), "09": ("Palakkad", "563"), "10": ("Malappuram", "562"), "11": ("Kozhikode", "561"),
             "12": ("Wayanad", "567"), "13": ("Kannur", "557"), "14": ("Kasaragod", "558")}
TYPES = {"B": ("Block Panchayat", "block", "Block Development Officer (Secretary, Block Panchayat)"),
         "G": ("Grama Panchayat", "gram_panchayat", "Panchayat Secretary"),
         "D": ("District Panchayat", "district", "Secretary, District Panchayat")}
SUFFIX = re.compile(r"\s+(Block Panchayath?|Grama Panchayath?|Gram Panchayath?|District Panchayath?)\s*$", re.I)
STAFF_LINK = re.compile(r"(?i)officials?\s*(and|&)\s*employees|staff|employees|\bofficials\b|ജീവനക്കാർ|ഉദ്യോഗസ്ഥ")
NOT_LINK = re.compile(r"(?i)implementing|web\s*portal|elected|member|constituent|institution|rti|right\s*to\s*information|"
                      r"order|transfer|asha|anganwadi|kudumbashree|നിർവ്വഹണ|നിർവഹണ|ജനപ്രതിനിധി")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")
NAME_H = re.compile(r"(?i)name|പേര്")
DESIG_H = re.compile(r"(?i)designation|post\b|position|ഉദ്യോഗപ്പേര്|തസ്തിക")
PHONE_H = re.compile(r"(?i)phone|mobile|contact|ഫോൺ|മൊബൈൽ")
EMAIL_H = re.compile(r"(?i)e-?mail")
SECT_H = re.compile(r"(?i)section|seat|department|responsib|duty|duties|charge|subject")
DATE_H = re.compile(r"(?i)joining|date")
SNO_H = re.compile(r"(?i)^(sl\.?\s*no|s\.?\s*no|no\.?$|ക്രമ)")
SECRETARY = re.compile(r"(?i)^\s*(the\s+)?secretary\b(?!.*assistant)|^\s*bdo\b|block\s+development\s+officer")


def txt(s):
    return _esw.clean(EMOJI.sub(" ", s or ""))


def body_item(name, code, site):
    host = re.sub(r"^https?://", "", site).strip().strip("/").split("/")[0].lower()
    btype, _, _ = TYPES[code[0]]
    district, dc = DISTRICTS.get(code[1:3], ("", ""))
    return {"key": f"{MODULE}-{code.lower()}", "payload": {
        "reader": MODULE, "kind": "body", "url": f"https://{host}/en", "host": host, "state": "KL", "india_only": False,
        "route": "abroad", "body": SUFFIX.sub("", name), "name_list": name, "body_type": btype, "code": code,
        "district": district, "district_code": dc}}


def index_rows(html):
    """(name, code, site) of each block / grama / district panchayat row of one index page, and whether a next page exists."""
    soup = _esw.soup(html)
    out = []
    for t in soup.find_all("table"):
        for tr in t.find_all("tr"):
            td = tr.find_all("td")
            if len(td) < 4:
                continue
            name, code = _esw.clean(td[1].get_text(" ")), _esw.clean(td[2].get_text(" "))
            a = td[3].find("a", href=True)
            site = (a["href"] if a else _esw.clean(td[3].get_text(" "))).strip()
            if re.fullmatch(r"[BGD]\d{6}", code) and site:
                out.append((name, code, site))
    more = soup.find("a", attrs={"rel": "next"}) is not None or soup.select_one("li.pager__item--next") is not None
    return out, more


def items(get=None):
    """Without get: the seed item. With get (on the hub): one item per block, grama and district panchayat from the index."""
    if get is None:
        return [{"key": f"{MODULE}-seed", "payload": {"kind": "seed", "module": MODULE, "url": INDEX, "state": "KL",
                                                      "india_only": False, "route": "abroad"}}]
    out, seen = [], set()
    for n in range(PAGES):
        r = get(INDEX if n == 0 else f"{INDEX}?page=%2C%2C%2C{n}")
        if r is None:
            break
        rows, more = index_rows(r.text)
        for name, code, site in rows:
            if code not in seen:
                seen.add(code)
                out.append(body_item(name, code, site))
        if not more:
            break
    return out


def staff_links(html, base, host):
    out = []
    for a in _esw.soup(html).find_all("a", href=True):
        href, label = a["href"].strip(), txt(a.get_text(" "))
        if href.startswith("#") or not label:
            continue
        u = urljoin(base, href)
        pu = urlparse(u)
        if (pu.hostname or "").lower() != host or pu.query or "/ml/" in pu.path:
            continue
        if not STAFF_LINK.search(label) or NOT_LINK.search(label) or NOT_LINK.search(pu.path):
            continue
        if u not in out:
            out.append(u)
    return out[:2]


def roles(header):
    out = {}
    for i, h in enumerate(header):
        h = txt(h)
        if not h:
            continue
        if SNO_H.match(h):
            out[i] = "sno"
        elif EMAIL_H.search(h):
            out[i] = "email"
        elif PHONE_H.search(h):
            out[i] = "phone"
        elif DESIG_H.search(h):
            out[i] = "designation"
        elif NAME_H.search(h):
            out[i] = "name"
        elif DATE_H.search(h):
            out[i] = "joined"
        elif SECT_H.search(h):
            out[i] = "section" if "section" not in out.values() else "responsibility"
    return out


def table_people(soup):
    """[(fields, src_pos)] from tables whose header (first 2 rows) names a name and a designation or phone column."""
    out = []
    for t in soup.find_all("table"):
        pos = []
        g = _esw.grid(t, pos=pos)
        hi = next((i for i, r in enumerate(g[:2]) if any(NAME_H.search(txt(c)) for c in r)
                   and any(DESIG_H.search(txt(c)) or PHONE_H.search(txt(c)) for c in r)), None)
        if hi is None:
            continue
        header = [txt(c) for c in g[hi]]
        rl = roles(header)
        if "name" not in rl.values():
            continue
        for r, sp in zip(g[hi + 1:], pos[hi + 1:]):
            v = {}
            for i, c in enumerate(r):
                c = txt(c)
                if rl.get(i) and c and c not in v.get(rl[i], []):
                    v.setdefault(rl[i], []).append(c)
            f = {k: " | ".join(x) for k, x in v.items()}
            if not f.get("name") or [txt(c) for c in r] == header:
                continue
            f["cells"] = {header[i] or f"col{i + 1}": txt(c) for i, c in enumerate(r) if txt(c) and i < len(header)}
            out.append((f, sp))
    return out


def card_people(soup):
    """[(fields, src_pos)] from cards: an element with class "name" and one with class "designation" in the same card."""
    out, seen = [], set()
    for n, nm in enumerate(soup.select(".name"), 1):
        card = nm.find_parent("article") or nm.find_parent(class_=re.compile(r"card"))
        if card is None:                                              # no card element: the nearest box with a designation
            card = nm
            for _ in range(4):
                card = card.parent
                if card is None or card.select_one(".designation") is not None:
                    break
        if card is None or card.select_one(".designation") is None or id(card) in seen:
            continue
        seen.add(id(card))
        f = {"name": txt(nm.get_text(" ")), "designation": txt(card.select_one(".designation").get_text(" "))}
        for row in card.select(".detail-row, .detail-content"):
            lab, val = row.select_one(".label"), row.select_one(".value")
            if lab is not None and val is not None:
                k = txt(lab.get_text(" ")).lower()
                f["section" if "section" in k else "responsibility" if "respons" in k else re.sub(r"\W+", "_", k)] = \
                    txt(val.get_text(" "))
        ph = card.select_one(".phone")
        if ph is not None:
            f["phone"] = txt(ph.get_text(" "))
        if f["name"]:
            out.append((f, {"card": len(out) + 1}))
    return out


def office(html):
    """{"district", "pincode", "phone", "email"} of the body's office and [(office, email, src_pos)] of the offices under it,
    from /en/emails."""
    soup = _esw.soup(html)
    for t in soup(["script", "style"]):
        t.decompose()
    text = txt(soup.get_text(" "))
    o = {}
    for k, pat in (("district", r"District:\s*([A-Za-z ]+?)\s+Pincode"), ("pincode", r"Pincode:\s*(\d{6})"),
                   ("phone", r"Phone:\s*([\d\s,/+-]{6,}?)\s*(?:Email|$)"), ("email", r"Email:\s*(\S+@\S+)")):
        m = re.search(pat, text)
        if m:
            o[k] = m.group(1).strip()
    if o.get("phone"):
        o["phone"] = _esw.phones(o["phone"])
    if o.get("email"):
        o["email"] = _esw.emails(o["email"])
    subs = []
    for n, box in enumerate(soup.select("div.mail-address"), 1):         # one div per office: name div, email div
        parts = [txt(d.get_text(" ")) for d in box.find_all("div", recursive=False)]
        em = _esw.emails(" ".join(parts))
        name = next((x for x in parts if x and "@" not in x), "")
        if em and name:
            subs.append((name, em, {"mail_row": n}))
    return o, subs


def people(html):
    soup = _esw.soup(html)
    for t in soup(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    return table_people(soup) or card_people(soup)


def build(p, staff, off, subs, emails_url):
    """staff: [(fields, src_pos, url)]; off/subs from office()."""
    code = p["code"]
    _, level, head_post = TYPES[code[0]]
    base = dict(dept="rural_development", area=p["body"], district=p.get("district"), district_code=p.get("district_code"),
                state="KL", lb_code=code, body_type=p.get("body_type"))
    recs, head = [], False
    for n, (f, sp, url) in enumerate(staff, 1):
        desig = f.get("designation") or ""
        vacant = bool(re.fullmatch(r"(?i)va+c+a+nt|-+|nil", f.get("name") or ""))
        is_head = bool(SECRETARY.search(desig)) and not head
        more = {}
        if is_head:
            head = True
            more = {"office_phone": off.get("phone"), "office_email": off.get("email"), "pincode": off.get("pincode")}
        recs.append(_esw.record(MODULE, f"{code.lower()}:{n}", level=level, post=head_post if is_head else (desig or "Staff"),
                                designation=desig or None, name=None if vacant else f.get("name"),
                                vacant=True if vacant else None, phone=_esw.phones(f.get("phone") or ""),
                                email=_esw.emails(f.get("email") or ""), section=f.get("section"),
                                responsibility=f.get("responsibility"), joined=f.get("joined"), list_no=f.get("sno"),
                                is_head=True if is_head else None, kind="staff", cells=f.get("cells"),
                                source=url, src_url=url, page=url, src_pos=sp, **more, **base))
    if not head and (off.get("phone") or off.get("email")):
        recs.append(_esw.record(MODULE, f"{code.lower()}:office", level=level, post=head_post, designation="Secretary (office)",
                                phone=off.get("phone"), email=off.get("email"), pincode=off.get("pincode"), is_head=True,
                                kind="office", source=emails_url, src_url=emails_url, page=emails_url,
                                src_pos={"block": "office"}, **base))
    for n, (name, em, sp) in enumerate(subs, 1):
        recs.append(_esw.record(MODULE, f"{code.lower()}:sub:{n}", level="office", post=name, email=em, kind="office_under_body",
                                parent_body=p["body"], source=emails_url, src_url=emails_url, page=emails_url, src_pos=sp,
                                **{k: v for k, v in base.items() if k != "area"}, area=name))
    return recs


def fetch(p, get):
    host = p.get("host") or urlparse(p["url"]).hostname
    files = []
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    home = r.text
    files.append(_esw.keep(MODULE, f"{p['code'].lower()}-home", home))
    staff = []
    for u in staff_links(home, p["url"], host):
        s = get(u)
        if s is None:
            continue
        files.append(_esw.keep(MODULE, f"{p['code'].lower()}-{_esw.slug(urlparse(u).path)}", s.text))
        staff += [(f, sp, u) for f, sp in people(s.text)]
    emails_url = f"https://{host}/en/emails"
    e = get(emails_url)
    off, subs = ({}, [])
    if e is not None:
        files.append(_esw.keep(MODULE, f"{p['code'].lower()}-emails", e.text))
        off, subs = office(e.text)
    recs = build(p, staff, off, subs, emails_url)
    return recs, files, "" if recs else "no staff rows"
