"""Kerala: chairperson / mayor, vice chairperson / deputy mayor and secretary of every municipality and corporation, from the
home page of each body's own site (Information Kerala Mission template "lsgwebnew", one template for all local bodies).

Kerala has no statewide list of municipal secretaries that is open: the Directorate of Urban Affairs "Directory" page
(urban.lsgkerala.gov.in/en/directory/50, /ml/directory/69) is empty, and the State Election Commission's member and officer
search (sec.kerala.gov.in) needs a captcha. The statewide index of body sites is lsgkerala.gov.in/en/website/web: one HTML table
per page (Slno, Localbody Name, Localbody Code, Website), about 26 rows per page and 60 pages (?page=%2C%2C%2C<n>), all 1,200
local bodies in name order. The body code gives the district: M030100 = municipality (M; C = corporation) of district 03.

Two kinds of queue item:
- {"kind": "seed", "module": "ulb_kl"} (seeds/dept_ulb_kl.json): items(get) walks the index on the hub and lists one item per
  municipality and corporation (about 93).
- {"reader": "ulb_kl", "kind": "body", "url": "https://<site>/en", "body", "code", "district"}: fetch() reads the home page. Its
  "team" cards give post + name + mobile ("Chairperson | MAYA RAHUL | 9526968579", "Vice Chairperson", "Secretary"; corporations:
  "Mayor", "Deputy Mayor"); the footer "Contact" block gives the office phone and email (kept on the Secretary record as
  office_phone / office_email, and as a record of its own when no Secretary card is shown). "Last reviewed and updated on
  28-Oct-2026 16:50:33" -> last_updated. Answers from outside India (checked from Germany, 2026-11-11). Older template
  (corporations, e.g. Kochi): small tables "photo | post | name" without phones, the office phone in the "block-address" block.
  Some sites (Angamaly, Maradu in the archive copy) show only the office email and phone: one "Secretary (office)" record.
"""
import re
from datetime import datetime

from dforms import _esw, _ulb
import provenance

METHOD = "html cards (div.team-card) or name tables, home page of the body"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_kl"
INDEX = "https://lsgkerala.gov.in/en/website/web"
PAGES = 80                     # safety stop; the index has about 60 pages
DISTRICTS = {"01": "Thiruvananthapuram", "02": "Kollam", "03": "Pathanamthitta", "04": "Alappuzha", "05": "Kottayam", "06": "Idukki",
             "07": "Ernakulam", "08": "Thrissur", "09": "Palakkad", "10": "Malappuram", "11": "Kozhikode", "12": "Wayanad",
             "13": "Kannur", "14": "Kasaragod"}
KIND = re.compile(r"\s+(Municipality|Municipal Corporation|Corporation)\s*$", re.I)


def seed_item():
    return {"key": "ulb_kl-seed", "payload": {"kind": "seed", "module": MODULE, "url": INDEX, "state": "KL", "india_only": False}}


def index_rows(html):
    """(name, code, site) of each municipality / corporation row of one index page, and whether a next page exists."""
    soup = _esw.soup(html)
    out = []
    for t in soup.find_all("table"):
        for tr in t.find_all("tr"):
            td = tr.find_all("td")
            if len(td) < 4:
                provenance.skip_row(tr, 'skip: len(td) < 4')
                continue
            name, code = _esw.clean(td[1].get_text(" ")), _esw.clean(td[2].get_text(" "))
            a = td[3].find("a", href=True)
            site = (a["href"] if a else _esw.clean(td[3].get_text(" "))).strip()
            if not KIND.search(name) or not re.fullmatch(r"[MC]\d{6}", code) or not site:
                provenance.skip_row(tr, 'skip: not KIND.search(name) or not re.fullmatch(r"[MC]\\d{6}", code) or no...')
                continue
            out.append((name, code, site))
    more = soup.find("a", attrs={"rel": "next"}) is not None or soup.select_one("li.pager__item--next") is not None
    return out, more


def body_item(name, code, site):
    host = re.sub(r"^https?://", "", site).strip("/")
    return {"key": f"{MODULE}-{code.lower()}", "payload": {
        "reader": MODULE, "kind": "body", "url": f"https://{host}/en", "state": "KL", "india_only": False,
        "body": KIND.sub("", name), "body_type": "Corporation" if code.startswith("C") else "Municipality", "code": code,
        "district": DISTRICTS.get(code[1:3]), "name_list": name}}


def items(get=None):
    """Without get: the seed item. With get (on the hub): one item per municipality and corporation from the index."""
    if get is None:
        return [seed_item()]
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


def _txt(el):
    return _esw.clean(el.get_text(" ")) if el is not None else ""


def last_updated(soup):
    m = re.search(r"(?i)last reviewed and updated on\s*(\d{1,2}-[A-Za-z]{3}-\d{4})", soup.get_text(" "))
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%d-%b-%Y").date().isoformat()
    except ValueError:
        return None


def parse(html, p, url=None):
    url = url or p.get("url")
    soup = _esw.soup(html)
    body, district, btype = p.get("body"), p.get("district"), p.get("body_type")
    extra = {"lb_code": p.get("code"), "last_updated": last_updated(soup)}
    office_phone, office_email = office(soup)
    where = []
    people = cards(soup, where)
    if not people:
        where = []
        people = name_tables(soup, where)
    recs, seen, roles = [], set(), set()
    for (post, name, phone), pos in zip(people, where):
        more = {}
        if _ulb.role_of(post) == "head":
            more = {"office_phone": office_phone or None, "office_email": office_email or None}
        roles.add(_ulb.role_of(post))
        recs.append(_ulb.record(MODULE, "KL", body, post, seen, name=name, phone=phone, district=district, body_type=btype,
                                source=url, src_pos=pos, **extra, **more))
    if "head" not in roles and (office_phone or office_email):
        # the body's office line: in Kerala bodies the secretary's office (the email is "secretary<town>@...")
        recs.append(_ulb.record(MODULE, "KL", body, "Secretary (office)", seen, phone=office_phone, email=office_email,
                                district=district, body_type=btype, source=url, src_pos={"selector": "contact block"}, **extra))
    return recs


POST = re.compile(r"(?i)^(chair\s*(person|man|woman)|vice\s*chair\s*(person|man|woman)|mayor|deputy\s*mayor|secretary|additional\s*secretary)$")


def cards(soup, where=None):
    """lsgwebnew template: div.team-card with .team-name (post) and .team-position spans (name, mobile)."""
    out = []
    for k, card in enumerate(soup.select("div.team-card"), 1):
        post = _txt(card.select_one(".team-name"))
        pos = [_txt(s) for s in card.select(".team-position")]
        name = next((x for x in pos if x and not re.search(r"\d{6,}", x)), "")
        phone = _esw.phones(" ".join(x for x in pos if re.search(r"\d{6,}", x)))
        if post and (name or phone):
            out.append((post, name, phone))
            if where is not None:
                where.append({"selector": "div.team-card", "card": k})
    return out


def name_tables(soup, where=None):
    """Older template (corporations, e.g. Kochi): small tables "photo | post | name", one per person; no phones."""
    out = []
    for t in soup.find_all("table"):
        cells = [own_text(td) for td in t.find_all("td")]
        cells = [c for c in cells if c]
        for i, c in enumerate(cells[:-1]):
            if POST.match(c) and not POST.match(cells[i + 1]) and not re.search(r"\d{5,}", cells[i + 1]):
                if (c, cells[i + 1], "") not in out:
                    out.append((c, cells[i + 1], ""))
                    if where is not None:       # cell = the post cell's place among the table's non-empty <td>
                        where.append({"table": _esw.table_no(t), "cell": i + 1})
    return out


def own_text(td):
    """Cell text without the text of tables nested in it (the Mayor's cell holds the photo table and "<p>Mayor</p>")."""
    t = _txt(td)
    for inner in td.find_all("table"):
        it = _txt(inner)
        if it:
            t = _esw.clean(t.replace(it, " "))
    return t


def office(soup):
    """(phone, email) of the body's office: the footer "Contact" block, else the top bar, else a "Phone:" address block."""
    for h in soup.find_all(["h4", "h5"]):
        if _txt(h).lower() == "contact":
            box = h.find_parent("div")
            phone = _esw.phones(" ".join(_txt(x) for x in box.find_all("p") if x.find("i", class_=re.compile("phone"))))
            return phone, _esw.emails(_txt(box))
    bar = [s for s in soup.find_all("small") if s.find("i", class_=re.compile(r"fa-(envelope|phone)"))]
    if bar:
        return (_esw.phones(" ".join(_txt(s) for s in bar if s.find("i", class_=re.compile("phone")))),
                _esw.emails(" ".join(_txt(s) for s in bar)))
    blk = soup.find(id="block-address")
    if blk is not None:
        t = _txt(blk)
        m = re.search(r"(?i)phone\s*:?\s*([\d\s,/+-]{6,})", t)
        return (_esw.phones(m.group(1)) if m else ""), _esw.emails(t)
    return "", ""


def fetch(p, get):
    if p.get("kind") != "body":
        return [], [], "not a body item"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, (p.get("code") or _esw.slug(p.get("body"))).lower(), r.content)]
    recs = parse(r.text, p)
    return recs, files, "" if recs else "no officials on the home page"
