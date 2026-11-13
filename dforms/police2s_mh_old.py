"""Maharashtra police unit sites that are NOT (yet) on the state Next.js template that police2s_mh reads. police2s_mh.fetch calls
fetch() here when /en/about/<section> has no officer cards, with the same payload ({"key", "url": .../en/about/<section>}), so the
queue keys stay the same. <section> is "senior-officers" or "police-station-incharge". Records keep module police2s_mh
(dept:police2s_mh:<site key>:<slug>), next to the new-template records.

Layouts (all seen 2026-11-13 from dev-vps-3, Mumbai):
- "nextapi": the older static Next.js export (Nashik Rural; the same build was on Gondia, Nandurbar, Dharashiv in the archive,
  2026-11-05). https://<host>/<section> has no data in the HTML; its page script /_next/static/chunks/pages/<section>-<hash>.js
  calls fetch("".concat("https://<api host>","/api/<name>")) with a plain GET and no key (Nashik Rural: nrbkapi.neuronexdevelopers.com,
  /api/get-senior-officer -> {"Data": [{sr_no, name, name_in_marathi, designation, designation_in_marathi, phone, email}]},
  /api/officers-admin -> {"Officers": [{psId: {name, name_in_marathi}, name, name_in_marathi, post, post_in_marathi, mobile,
  contact_no, email}]}). The reader reads the page, then the script, then the API the script names (3 requests).
- Solapur City (own PHP site): /senior_officers (div.officer-card, lang-en / lang-mr spans); stations: the "Select Police
  Station" list on the same page -> /police-station/<slug> (one officer card per page; 7 stations, 1 + 7 requests).
- Jalna (static HTML): /seniorofficers.html (div.card-seniorofficers: h3 name, p designation, tel: links); stations: ps*.html
  links on the home page (19), each "Station Name: | Contact Number: | Email Id: | Division:" with the incharge's name, rank, mobile.
- Hingoli (Marathi only): /Officers (h3 name, h4 post: no phones on the page); stations: /PoliceStation?ps=<n> (GET form, 13
  stations): "पोलीस ठाणे प्रभारी | name | rank | पत्ता | दूरध्वनी क्रमांक | मोबाइल नंबर | ई-मेल | विभाग".
- Nagpur Railway: https://nagpurrailwaypolice.gov.in/en/officerslist ("OFFICER NAME | DESIGNATION | BRANCH | MOBILE NUMBER |
  EMAIL ID", emails written x[at]y[dot]z). No station incharge list found on the site.
Not readable here (why text): a page that says "No records yet" (Gadchiroli stations), Nashik City (Next.js app router, data by
script from an API not found in the page scripts), sites that time out from Mumbai or answer an empty page."""
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import provenance
from dforms._police import ascii_digits, clean, email, gz, phones, rec, slug, uniq
from officials import deobfuscate

METHOD = "html cards / label blocks; json api named by the page script"     # source trail (provenance.py)

M = "police2s_mh"
DEV = re.compile(r"[ऀ-ॿ]")
API = re.compile(r"""fetch\(\s*(?:""\.concat\(\s*"(https?://[^"]+)"\s*,\s*"(/[^"]+)"\s*\)|"(https?://[^"]+)")""")
SKIP_API = re.compile(r"visitor|count|banner|news|gallery|notice|slider|login", re.I)
ACP = re.compile(r"\bACP\b|Assistant Commissioner|SDPO|Sub[- ]?Divisional|DY\.?\s?SP|Deputy Superintendent|उपविभागीय|पोलीस उपअधीक्षक|सहाय्यक पोलीस आयुक्त", re.I)
DCP = re.compile(r"\bDCP\b|Deputy Commissioner|पोलीस उपायुक्त|पोलीस उप आयुक्त", re.I)
TOP = re.compile(r"Commissioner of Police|Superintendent of Police|\bS\.?P\b|Addl|Additional|पोलीस अधीक्षक|पोलीस आयुक्त", re.I)
HQ = re.compile(r"\(HQ\)|\bHQ\b|Home|Crime|Special|Traffic|Control|Admin|Cyber|Branch|मुख्यालय|गुन्हे|वाहतूक|शाखा", re.I)


def level_of(post):
    p = post or ""
    if ACP.search(p) and not HQ.search(p):
        return "subdivision", "office"
    if DCP.search(p) and not HQ.search(p):
        return "zone", "office"
    if TOP.search(p) or ACP.search(p) or DCP.search(p):
        return "district", "office" if not HQ.search(p) else "unit"
    return "district", "unit"


def _t(node):
    return clean(ascii_digits(node.get_text(" ", strip=True))) if node is not None else None


def _record(p, section, key, *, post, name, area=None, phone=None, mail=None, r=None, url=None, pos=None, **more):
    if section == "police-station-incharge":
        level, otype = "police_station", "police station"
        area = area or post
    else:
        level, otype = level_of(post)
        area = area or post
    en = lambda s: None if s and DEV.search(s) else s        # noqa: E731
    return rec(M, f"{slug(p.get('key') or urlparse(p['url']).hostname.split('.')[0])}:{slug(key)}", level=level, office_type=otype,
               area=area, post=post, name=name, phone=phone, email=email(mail), state="MH", district=p.get("district"),
               source=url, **more, **provenance.at(r, url), src_pos=pos,
               name_is_regional=True if name and DEV.search(name) and not en(name) else None)


# ---- the older static Next.js export: page -> page script -> JSON API ---------------------------------------------------------

def page_script(html, section):
    m = re.search(r'src="(/_next/static/chunks/pages/' + re.escape(section) + r'-[0-9a-f]+\.js)"', html or "")
    return m.group(1) if m else None


def api_urls(js):
    out = []
    for m in API.finditer(js or ""):
        u = (m.group(1) + m.group(2)) if m.group(1) else m.group(3)
        if not SKIP_API.search(u) and u not in out:
            out.append(u)
    return out


def rows_of(data):
    """The first list of dicts in an API answer ({"Data": [...]}, {"Officers": [...]}, or a bare list)."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        for v in data.values():
            if isinstance(v, dict):
                got = rows_of(v)
                if got:
                    return got
    return []


def from_api(p, section, items, r, url):
    recs = []
    for i, o in enumerate(items):
        st = o.get("psId") if isinstance(o.get("psId"), dict) else {}
        post = clean(o.get("designation") or o.get("post") or o.get("rank"))
        post_mr = clean(o.get("designation_in_marathi") or o.get("post_in_marathi"))
        name = clean(o.get("name"))
        if not name:
            provenance.skip_row(o, 'skip: not name')
            continue
        area = clean(st.get("name")) if section == "police-station-incharge" else None
        if area and not re.search(r"(?i)police|station|\bps\b", area):
            area = f"{area} Police Station"
        oid = clean(str(o.get("_id") or o.get("id") or i))
        recs.append(_record(p, section, oid, post=post, name=name, area=area, phone=phones(o.get("mobile"), o.get("phone"),
                            o.get("contact_no")), mail=o.get("email"), r=r, url=url, pos={"index": i, "id": oid},
                            name_regional=clean(o.get("name_in_marathi")), post_regional=post_mr,
                            area_regional=clean(st.get("name_in_marathi")) or None, sr_no=o.get("sr_no"), office_id=oid,
                            updated=clean(o.get("updatedAt"))))
    return recs


def nextapi(p, section, get, files):
    host = urlparse(p["url"]).hostname
    page = f"https://{host}/{section}"
    r = get(page)
    if r is None:
        return [], f"no answer from {page}"
    files.append(gz(M, f"{slug(host)}-{section}.html", r.content))
    js_path = page_script(r.text, section)
    if not js_path:
        return [], "no page script on the old page"
    js = get(urljoin(page, js_path))
    if js is None:
        return [], "page script did not answer"
    urls = api_urls(js.text)
    if not urls:
        return [], "page script names no API"
    for u in urls:
        a = get(u)
        if a is None:
            continue
        try:
            data = a.json()
        except ValueError:
            continue
        files.append(gz(M, f"{slug(host)}-{section}-api.json", a.content))
        recs = from_api(p, section, rows_of(data), a, u)
        if recs:
            return recs, ""
    return [], "API gave no officers"


# ---- Solapur City -------------------------------------------------------------------------------------------------------------

def _lang(node, cls=""):
    """(English, Marathi) texts of a node's span.lang-en / span.lang-mr."""
    if node is None:
        return None, None
    return _t(node.select_one(".lang-en")), _t(node.select_one(".lang-mr"))


def solapur_senior(html, p, r, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for i, c in enumerate(soup.select("div.officer-card")):
        name, name_mr = _lang(c.select_one("h2"), "")
        post, post_mr = _lang(c.select_one(".officer-designation"), "")
        items = [_t(x) for x in c.select(".contact-item")]
        mail = next((x for x in items if x and "@" in x), None)
        if not name:
            continue
        recs.append(_record(p, "senior-officers", post or name, post=post, name=name, phone=phones(*[x for x in items if x and "@" not in x]),
                            mail=mail, r=r, url=url, pos={"card": i}, name_regional=name_mr, post_regional=post_mr))
    return recs


def solapur_stations(html, base):
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    for o in soup.select("option[value]"):
        v = o["value"]
        if "/police-station/" in v:
            u = urljoin(base, v)
            if u not in out:
                out.append(u)
    return out


def solapur_station(html, p, r, url):
    soup = BeautifulSoup(html, "lxml")
    st, st_mr = _lang(soup.select_one(".ps-header h1") or soup.select_one("h1"), "")
    c = soup.select_one("div.officer-card")
    if c is None or not st:
        return []
    name, name_mr = _lang(c.select_one(".officer-name"), "")
    post, post_mr = _lang(c.select_one(".officer-post"), "")
    tels = [a["href"][4:] for a in c.select('a[href^="tel:"]') if not DEV.search(a["href"])]
    mail = next((a["href"][7:] for a in c.select('a[href^="mailto:"]')), None)
    addr = next((_t(x.select_one(".lang-en")) for x in c.select("p") if x.select_one(".fa-location-dot")), None)
    about = soup.find(string=re.compile("serves the citizens of"))
    sub = _t(about.find_next("strong")) if about else None
    if not name:
        return []
    return [_record(p, "police-station-incharge", st, post=post, name=name, area=st, phone=phones(*tels), mail=mail, r=r, url=url,
                    pos={"card": 0, "station": st}, name_regional=name_mr, post_regional=post_mr, area_regional=st_mr, address=addr,
                    subdivision=sub)]


# ---- Jalna --------------------------------------------------------------------------------------------------------------------

def jalna_senior(html, p, r, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for i, c in enumerate(soup.select("div.card-seniorofficers")):
        name, post = _t(c.find("h3")), _t(c.select_one(".designation-seniorofficers, .designation") or c.find("p"))
        if not name:
            continue
        tels = [a["href"][4:] for a in c.select('a[href^="tel:"]')]
        recs.append(_record(p, "senior-officers", post or name, post=post, name=name, phone=phones(*tels), r=r, url=url, pos={"card": i}))
    return recs


def jalna_stations(html, base):
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    for a in soup.find_all("a", href=re.compile(r"^ps[a-z]+\.html$", re.I)):
        u = urljoin(base, a["href"])
        if u not in out:
            out.append(u)
    return out


LABELS_EN = {"station name:": "station", "contact number:": "office", "email id:": "email", "division:": "division", "address:": "address"}


def jalna_station(html, p, r, url):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    toks = [clean(s) for s in soup.stripped_strings]
    toks = [t for t in toks if t]
    f = {}
    for i, t in enumerate(toks[:-1]):
        k = LABELS_EN.get(t.lower())
        if k and k not in f:
            f[k] = toks[i + 1]
    st = f.get("station")
    if not st or st not in toks:
        return []
    i = toks.index(st)                       # the first time the station's name shows: heading, then name, rank, mobile
    name, post = (toks[i + 1], toks[i + 2]) if i + 2 < len(toks) else (None, None)
    mob = toks[i + 3] if i + 3 < len(toks) and re.search(r"\d{6}", toks[i + 3]) else None
    if not name or not re.match(r"(?i)(shri|smt|kum|mr|ms|dr)\b", name):
        return []
    return [_record(p, "police-station-incharge", st, post=post, name=name, area=st, phone=phones(re.sub(r"^[^\d+]+", "", mob or ""), f.get("office")),
                    mail=f.get("email"), r=r, url=url, pos={"station": st, "token": i + 1}, subdivision=f.get("division"),
                    address=f.get("address"))]


# ---- Hingoli (Marathi) --------------------------------------------------------------------------------------------------------

def hingoli_senior(html, p, r, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for i, h in enumerate(soup.select("div.i_contact h3")):
        name, post = _t(h), _t(h.find_next_sibling("h4"))
        if not name or not post:
            continue
        joined = next((_t(x) for x in h.find_parent("div", class_="i_contact").select("h4") if "रुजू" in (_t(x) or "")), None)
        recs.append(_record(p, "senior-officers", post, post=post, name=name, r=r, url=url, pos={"card": i}, joined=joined))
    return recs


def hingoli_stations(html, base):
    soup = BeautifulSoup(html or "", "lxml")
    sel = soup.find("select", attrs={"name": "ps"})
    if sel is None:
        return []
    return [urljoin(base, f"/PoliceStation?ps={o['value']}") for o in sel.find_all("option") if (o.get("value") or "").isdigit()]


HI = {"पोलीस ठाणे प्रभारी": "name", "पत्ता": "address", "दूरध्वनी क्रमांक": "office", "मोबाइल नंबर": "mobile", "ई-मेल": "email",
      "विभाग": "division"}


def hingoli_station(html, p, r, url):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "nav", "header", "footer", "select", "option"]):
        t.decompose()
    toks = [clean(ascii_digits(s)) for s in soup.stripped_strings]
    toks = [t for t in toks if t]
    if "पोलीस ठाणे प्रभारी" not in toks:
        return []
    i = toks.index("पोलीस ठाणे प्रभारी")
    st = toks[i - 1] if i else None
    f = {"name": toks[i + 1] if i + 1 < len(toks) else None, "post": toks[i + 2] if i + 2 < len(toks) else None}
    for j in range(i + 3, min(len(toks) - 1, i + 16)):
        k = HI.get(toks[j])
        if k and k != "name":
            nxt = toks[j + 1]
            f[k] = None if nxt in HI else nxt
    if not f["name"] or f["name"] in HI:
        return []
    area = f"{st} पोलीस ठाणे" if st else None
    return [_record(p, "police-station-incharge", st or f["name"], post=f["post"], name=f["name"], area=area,
                    phone=phones(f.get("mobile"), f.get("office")), mail=f.get("email"), r=r, url=url, pos={"station": st, "token": i},
                    area_regional=area, name_regional=f["name"], post_regional=f["post"], subdivision=f.get("division"),
                    address=f.get("address") if f.get("address") and not re.fullmatch(r"[\d\s,-]+", f["address"]) else None)]


# ---- Nagpur Railway -----------------------------------------------------------------------------------------------------------

NR = {"OFFICER NAME": "name", "DESIGNATION": "post", "BRANCH": "branch", "MOBILE NUMBER": "mobile", "EMAIL ID": "email"}


def label_list(html, p, r, url, section):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    toks = [clean(s) for s in soup.stripped_strings]
    toks = [t for t in toks if t]
    blocks, cur = [], None
    for i, t in enumerate(toks[:-1]):
        k = NR.get(t.upper())
        if not k:
            continue
        if k == "name":
            cur = {"_i": i}
            blocks.append(cur)
        if cur is not None and k not in cur:
            nxt = toks[i + 1]
            cur[k] = None if nxt.upper() in NR else nxt
    recs = []
    for b in blocks:
        if not b.get("name"):
            provenance.skip_row(b, 'skip: not b.get("name")')
            continue
        post = b.get("post") if (b.get("branch") or "") == (b.get("post") or "") else f"{b.get('post')}, {b.get('branch')}"
        recs.append(_record(p, section, b.get("branch") or post, post=post, name=b["name"], area=b.get("branch"),
                            phone=phones(b.get("mobile")), mail=deobfuscate(b.get("email") or ""), r=r, url=url,
                            pos={"token": b["_i"]}, branch=b.get("branch")))
    return recs


# ---- dispatch ------------------------------------------------------------------------------------------------------------------

def _one(p, get, files, url, parse, name):
    r = get(url)
    if r is None:
        return [], f"no answer from {url}"
    files.append(gz(M, name, r.content))
    return parse(r.text, p, r, url), ""


def _list(p, get, files, list_url, finder, parse, tag, limit=40):
    r = get(list_url)
    if r is None:
        return [], f"no answer from {list_url}"
    urls = finder(r.text, list_url)
    if not urls:
        return [], "no station list on the page"
    recs = []
    for u in urls[:limit]:
        x = get(u)
        if x is None:
            continue
        files.append(gz(M, f"{tag}-{slug(u.rsplit('/', 1)[-1])}"[:90] + ".html", x.content))
        recs += parse(x.text, p, x, u)
    return recs, "" if recs else f"no officer on {len(urls)} station pages"


def fetch(p, get, first=None):
    """(records, files, why) for a police2s_mh item whose /en/about/ page had no cards. first = that page's answer (or None)."""
    url = p["url"]
    host = urlparse(url).hostname or ""
    section = "police-station-incharge" if "police-station-incharge" in url else "senior-officers"
    files = []
    if first is not None and re.search(r"No records yet", first.text or ""):
        return [], files, "the site's page says 'No records yet'"
    base = f"https://{host}"
    if host.endswith("solapurcitypolice.gov.in"):
        if section == "senior-officers":
            recs, why = _one(p, get, files, base + "/senior_officers", solapur_senior, "solapurcity-senior.html")
        else:
            recs, why = _list(p, get, files, base + "/senior_officers", solapur_stations, solapur_station, "solapurcity-ps")
    elif host.endswith("jalnapolice.gov.in"):
        if section == "senior-officers":
            recs, why = _one(p, get, files, base + "/seniorofficers.html", jalna_senior, "jalna-senior.html")
        else:
            recs, why = _list(p, get, files, base + "/", jalna_stations, jalna_station, "jalna")
    elif host.endswith("hingolipolice.gov.in"):
        if section == "senior-officers":
            recs, why = _one(p, get, files, base + "/Officers", hingoli_senior, "hingoli-officers.html")
        else:
            recs, why = _list(p, get, files, base + "/PoliceStation", hingoli_stations, hingoli_station, "hingoli")
    elif host.endswith("nagpurrailwaypolice.gov.in"):
        if section != "senior-officers":
            return [], files, "no station incharge list on the site (officers list only)"
        recs, why = _one(p, get, files, "https://nagpurrailwaypolice.gov.in/en/officerslist",
                         lambda h, pp, r, u: label_list(h, pp, r, u, section), "nagpurrailway-officerslist.html")
    else:
        recs, why = nextapi(p, section, get, files)
    recs = uniq(recs)
    for _, d in recs:
        d["layout"] = "old site"
    return recs, files, "" if recs else (why or "no officers")
