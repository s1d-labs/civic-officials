"""Kerala: Akshaya centres (Kerala's Common Service Centres, run by an entrepreneur under the Akshaya State Project Office, KSITM),
from akshaya.kerala.gov.in "Locate Akshaya Centers". About 2,800 centres.
- List pages https://akshaya.kerala.gov.in/centers/<page> (page 0, 1, 2 ...; 42 cards a page, page 80 is empty): per card the centre
  code ("KNR267"), the place and district ("19 Th Mile, Kannur"), the centre phone and a link /centerstest/<id>/<slug>.
- Centre pages https://akshaya.kerala.gov.in/centers/<id>/<slug>: "Office Contact Details" (centre address, phone, email written as
  HTML character references), "Staff in Charge Contact Details" (the entrepreneur / staff: name, place, phone, email) and the map
  point (Maplace locations: lat, lon). The archive (archive.s1d.me) holds about 1,990 of these pages, saved 2026-11-10.
One queue item = one list page and the centre pages of its cards (43 requests). Answers from anywhere.
Record ids: dept:civic_csc_kl:<centre code> (or the site id when a card has no code).
The site writes some values run together; the reader splits them: two mobiles with no separator ("90202773999446680882" ->
9020277399, 9446680882), two emails with no separator ("sajnaboban@gmail.comsajna_magfil@yahoo.co.in"), and puts back the
leading 0 of an STD code that the site lost ("4872998822" -> 04872998822: 10 digits, first digit 1-5, is not a mobile).
"""
import re

import provenance
from dforms import _civic, _esw

METHOD = "html page (list card + detail page blocks)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_csc_kl"
BASE = "https://akshaya.kerala.gov.in"
PAGES = 80


def items(get=None):
    return [{"key": f"{MODULE}-p{n:03d}", "payload": {"reader": MODULE, "url": f"{BASE}/centers/{n}", "state": "KL",
                                                      "india_only": False, "page": n, "details": True, "expected": 42}}
            for n in range(PAGES)]


TLD = r"(?:co\.in|gov\.in|nic\.in|ac\.in|org\.in|net\.in|com|org|net|in)"


def split_emails(t):
    """'a@gmail.comb_c@yahoo.co.in' -> 'a@gmail.com b_c@yahoo.co.in': a domain end that runs into the next address."""
    return re.sub(r"(@[\w-]+(?:\.[\w-]+)*?\." + TLD + r")(?=[\w.+-]+@)", r"\1 ", _esw.deob(t or ""), flags=re.I)


def split_numbers(t):
    """Digit runs of 20 or more digits split into numbers: 0 + 10 digits is a landline, a first digit 6-9 starts a mobile
    (10 digits), 1-5 a landline that lost its 0 (10 digits)."""
    def cut(m):
        d, out = m.group(), []
        while len(d) >= 10:
            n = 11 if d[0] == "0" else 10
            out.append(d[:n])
            d = d[n:]
        return ", ".join(out + ([d] if d else []))
    return re.sub(r"(?<!\d)\d{20,}(?!\d)", cut, t or "")


def fix_phones(t):
    """_esw.phones() of the text after split_numbers(), with the lost STD 0 put back."""
    out = []
    for x in filter(None, _esw.phones(split_numbers(t)).split(", ")):
        if re.fullmatch(r"[1-5]\d{9}", x):
            x = "0" + x
        if x not in out:
            out.append(x)
    return ", ".join(out)


def cards(html):
    """[{"id", "slug", "url", "code", "place", "district", "phone"}] from one list page."""
    soup = _esw.soup(html)
    out = []
    for a in soup.select("a[href]"):
        m = re.match(r"^/centers(?:test)?/(\d+)/([^/?#]+)", a["href"])
        if not m or not a.select_one(".center-tl-head"):
            continue
        h5 = a.select_one("h5")
        small = h5.select_one("small") if h5 else None
        district = _esw.clean(small.get_text(" ")) if small else ""
        if small:
            small.extract()
        code = a.select_one(".tx small")
        ph = a.select_one("h4")
        out.append({"id": m.group(1), "slug": m.group(2), "url": f"{BASE}/centers/{m.group(1)}/{m.group(2)}",
                    "code": _esw.clean(code.get_text(" ")) if code else "",
                    "place": _esw.clean(h5.get_text(" ")).strip(" ,") if h5 else "", "district": district,
                    "phone": fix_phones(ph.get_text(" ")) if ph else ""})
    return out


def block(soup, title):
    """The column under <h2 class="title">title</h2>."""
    for h in soup.select("h2.title"):
        if _esw.clean(h.get_text(" ")).lower().startswith(title.lower()):
            return h.parent
    return None


def detail(html):
    """Centre page -> {"name", "address", "phone", "email", "staff", "staff_place", "staff_phone", "staff_email", "lat", "lon"}."""
    soup = _esw.soup(html)
    d = {}
    h = soup.select_one("h2.title.text-uppercase") or soup.find("h1")
    office = block(soup, "Office Contact Details")
    if office:
        adr = office.find("address")
        d["address"] = _esw.clean(adr.get_text(" ")).rstrip(" -") if adr else ""
        lis = office.find_all("li")
        d["phone"] = fix_phones(lis[1].get_text(" ")) if len(lis) > 1 else ""
        d["email"] = _esw.emails(split_emails(lis[2].get_text(" "))) if len(lis) > 2 else ""
    staff = block(soup, "Staff in Charge")
    if staff:
        staff.find("h2").extract()
        for br in staff.find_all("br"):
            br.replace_with("\n")
        lines = [_esw.clean(x) for x in staff.get_text().split("\n")]
        lines = [x for x in lines if x]
        mail = [x for x in lines if "@" in x]
        tel = [x for x in lines if re.fullmatch(r"[\d\s,+-]+", x) and len(re.sub(r"\D", "", x)) >= 6]
        rest = [x for x in lines if x not in mail and not re.fullmatch(r"[\d\s,+-]+", x)]
        d["staff"] = rest[0] if rest else ""
        d["staff_place"] = ", ".join(rest[1:])
        d["staff_phone"] = fix_phones(" ".join(tel))
        d["staff_email"] = _esw.emails(split_emails(" ".join(mail)))
    m = re.search(r"lat\s*:\s*(-?[\d.]+)\s*,\s*lon\s*:\s*(-?[\d.]+)", html)
    if m:
        d["lat"], d["lon"] = _civic.lat(m.group(1)), _civic.lon(m.group(2))
    t = re.search(r"title\s*:\s*'([^']+)'", html)
    d["name"] = _esw.clean(t.group(1)) if t else (_esw.clean(h.get_text(" ")) if h else "")
    return d


def record(c, d, list_url):
    key = c.get("code") or f"id{c['id']}"
    phone = ", ".join(x for x in dict.fromkeys(p for p in (d.get("phone"), c.get("phone"), d.get("staff_phone")) if p))
    email = ", ".join(x for x in dict.fromkeys(e for e in (d.get("email"), d.get("staff_email")) if e))
    return _civic.record(
        MODULE, key, "csc", dept="digital_services", level="facility", area=c.get("place") or d.get("name"),
        office=d.get("name") or f"Akshaya Centre {c.get('place')}", post="Staff in Charge (Akshaya entrepreneur)",
        name=d.get("staff"), staff_place=d.get("staff_place"), phone=fix_phones(phone), email=email, address=d.get("address"),
        district=c.get("district"), state="KL", office_id=key, site_id=c.get("id"), lat=d.get("lat"), lon=d.get("lon"),
        source=c["url"] if d else list_url, list_source=list_url, scheme="Akshaya (Common Service Centre, Kerala)")


def fetch(p, get):
    url = p.get("url") or f"{BASE}/centers/{p.get('page', 0)}"
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"list-{p.get('page', 0):03d}", r.content)]
    cs = cards(r.text)
    if not cs:
        return [], files, "" if "center-tl-head" not in r.text else "cards not read"   # past the last page: done, no rows
    recs = []
    for ci, c in enumerate(cs, 1):
        d = {}
        if p.get("details", True):
            m = get(c["url"])
            if m is not None:
                files.append(_esw.keep(MODULE, f"centre-{c['id']}", m.content))
                d = detail(m.text)
        rec = record(c, d, url)
        # the centre's fields come from its detail page when it answered, else from its card on the list page
        rec[1].update(provenance.at(m, c["url"]) if d else provenance.at(r, url))
        rec[1]["src_pos"] = {"list_card": ci, **({"detail": "labelled blocks (h2.title)"} if d else {})}
        rec[1]["method"] = "html page (list card + detail page blocks)" if d else "html page (list card)"
        recs.append(rec)
    return recs, files, ""
