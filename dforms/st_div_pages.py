"""Division-level officers from division pages that are not read by st_div_s3waas (2026-11-13): commissioner portals on
other platforms (Karnataka's karnataka.gov.in CMS: rckalaburagi / rcbelagavi; Bihar's magadhdivision.bihar.gov.in PHP site),
S3WaaS portals with Marathi or Hindi headers (divcomkonkan.gov.in), and state police "range" telephone pages (Haryana Police
/static/TelephoneDirectory_<range>.aspx: IGP of the range and the SPs of its districts).

One queue item = one division (or range): payload {"reader": "st_div_pages", "key", "state", "division", "urls": [...],
"office": [{"url", "post"}], "kind": "revenue" | "police", "district_names": {LGD code: [names as the pages write them]},
"body"}. Each url is read for tables (officials.tables: header row by its words, the caption kept as "section"); the S3WaaS
pager (ww_pages / dir_pages, with the nonce the page carries) is followed as whoswho.py does. An "office" page gives one
record for the office itself (post from the payload, phone and e-mail from the page's contact text, e.g. karnataka.gov.in
"Contact us": "Phone No : 0831-2404007 ... Email: rcbelagavi@gmail.com").

Header words (English, Hindi, Marathi): Name / नाम / नाव, Designation / पद / पदनाम, Phone / दूरभाष / दूरध्वनी, Mobile /
मोबाइल / भ्रमणध्वनी, E-mail / ई-मेल / ईमेल, Fax, Address / पता / पत्ता, "Name & Designation" (split at the first post word).
A second header row ("Code | Office | Residence | Mobile No.", Haryana Police) is skipped; its phone columns are read as
phones. Rows without name and post (notes such as "Updated on 21.10.2026") are skipped.

Records (_state.rec, type dept_office): level division (division = the payload's, districts from dforms/st_div_<st>.json);
a row whose post or section names a district head (Collector / District Magistrate / Deputy Commissioner / SP / SSP / ZP CEO /
Municipal Commissioner / Commissioner of Police, in English, Hindi or Marathi) and a district of the payload's
district_names gets level district with the LGD code. dept: police for police posts and items of kind police (body
"<division>, <state> Police"), else from the post and section words (_state.dept_key), revenue for the commissioner's office.
post_kind divisional_commissioner for the head of the office ("Divisional Commissioner", "Regional Commissioner",
"विभागीय आयुक्त", "Commissioner" in the commissioner's own table). Every cell is kept in "cells". src_pos {"table", "row"}
(pager answers: {"category", "paged", "item"}). Ids: dept:st_div_pages:<key>:<page slug>:<table>:<row>,
dept:st_div_pages:<key>:<action>:<category>:<paged>:<item>, dept:st_div_pages:<key>:office:<n>.
"""
import json
import re
from urllib.parse import unquote, urlparse

import officials
import provenance
from dforms import _esw, _state
from dforms.st_html_tables import split_name_post

METHOD = "html table (division pages: header row by its words) + json api (S3WaaS ww_pages / dir_pages pager) + contact text"
MODULE = "st_div_pages"
MAX_AJAX = 40

FIELDS = [
    ("name_post", r"(?i)name\s*(and|&|/)\s*designation|नाम\s*(एवं|व|और|/)\s*पद"),
    ("post", r"(?i)designation|^post$|^rank|^पद|पदनाम|हुद्दा"),
    ("name", r"(?i)^(officer\s+)?name\b|name of|^नाम|^नाव"),
    ("email", r"(?i)e-?\s*mail|mail id|ई-?\s*मेल|ईमेल"),
    ("mobile", r"(?i)mobile|मोबाइल|भ्रमणध्वनी"),
    ("fax", r"(?i)\bfax|फैक्स"),
    ("address", r"(?i)address|पता|पत्ता"),
    ("phone", r"(?i)telephone|phone|contact|landline|office\s*no|resident|code|दूरभाष|दूरध्वनी|फोन|^col\d+$"),
    ("sno", r"(?i)^s\.?\s*no|^sl|^sr|क्र"),
    ("photo", r"(?i)photo|image|picture|फोटो"),
]
HEADER_WORD = re.compile(r"(?i)^\W*(code|office|residence|mobile( no\.?)?|phones?|fax|e-?mail|name|designation|s\.?\s*no\.?)\W*$")
HEAD_OF_OFFICE = re.compile(r"(?i)^\W*((divisional|regional|revenue divisional)\s+)?commis+ioner\b(?!.*\b(police|tax|excise|"
                            r"labour|food|state|municipal|zila|cooperative)\b)|विभागीय\s+आयुक्त|प्रमंडलीय\s+आयुक्त|संभागीय\s+आयुक्त|"
                            r"मंडलायुक्त|^\W*आयुक्त\W*$")
NOT_HEAD = re.compile(r"(?i)\b(additional|addl|joint|jt|deputy|dy|assistant|asst|special)\b|अपर|अतिरिक्त|सह\b|उप\b|सहाय्यक")
DISTRICT_HEAD = re.compile(
    r"(?i)\b(collector|district magistrate|deputy commissioner(?! of police)|dy\.? commissioner(?! of police)|\bD\.?M\.?\b|"
    r"superintendent of police|\bS\.?S\.?P\b|\bS\.?P\b|zilla parishad|zila parishad|chief executive officer|\bceo\b|"
    r"municipal commissioner|commissioner of police|police commissioner|district (administration|directory))\b|"
    r"जिल्हाधिकारी|जिलाधिकारी|जिला पदाधिकारी|पोलीस अधीक्षक|पुलिस अधीक्षक|जिल्हा परिषद|महानगरपालिका आयुक्त|पोलीस आयुक्त|"
    r"वरिष्ठ पुलिस अधीक्षक")
POLICE = re.compile(r"(?i)\b(police|\bIGP?\b|\bDIGP?\b|\bS\.?S\.?P\b|\bS\.?P\b|range|zone|\bIPS\b)\b|पोलीस|पुलिस|भापोसे")


def kind(h):
    h = _esw.clean(h)
    for k, rx in FIELDS:
        if re.search(rx, h):
            return k
    return ""


def slug(url):
    p = unquote(urlparse(url).path + ("?" + urlparse(url).query if urlparse(url).query else "")).lower()
    s = re.sub(r"[^a-z0-9]+", "-", p).strip("-")
    return s or "home"


def district_in(text, names):
    """(LGD code, first name) of the district a text names, from the payload's {code: [names]}; ("", "") if none. The longest
    name wins ("Mumbai Suburban" before "Mumbai")."""
    t = _esw.clean(text).lower()
    best = ("", "", 0)
    for code, ns in (names or {}).items():
        for n in ([ns] if isinstance(ns, str) else ns):
            k = n.lower().strip()
            if len(k) >= 3 and re.search(r"(?<![a-zऀ-ॿ])" + re.escape(k) + r"(?![a-z])", t) and len(k) > best[2]:
                best = (code, ([ns] if isinstance(ns, str) else ns)[0], len(k))
    return best[0], best[1]


SERVICE_END = re.compile(r"^(.{3,80}?[-,(\s]\s*(?:IAS|IPS|IFS|KAS|JKAS|JKPS|HCS|PCS|RAS|BAS|OAS|WBCS|MCS)\)?)\s*[,-]?\s+(.+)$")
RANK_START = re.compile(r"(?i)\b(DIGP?|IGP?|ADGP?|SSP|SP|DGP|Inspector General|Deputy Inspector General|Superintendent)\b")


def name_post(s):
    """"Sh. Sandeep Wazir -IPS, DIG Rajouri Poonch Range" -> ("Sh. Sandeep Wazir -IPS", "DIG Rajouri Poonch Range");
    "Sh. Vikas Kundal, IAS Divisional Commissioner Jammu" -> ("Sh. Vikas Kundal, IAS", "Divisional Commissioner Jammu")."""
    s = _esw.clean(s)
    m = SERVICE_END.match(s)
    if m:
        return m.group(1).strip(" ,-"), m.group(2).strip(" ,-")
    n, p = split_name_post(s)
    if p:
        return n, p
    m = RANK_START.search(s)
    if m and len(s[: m.start()].split()) >= 2:
        return s[: m.start()].strip(" ,-"), s[m.start():].strip(" ,-")
    return s, ""


def fields(row):
    """{name, post, email, phone, mobile, fax, address} of one {header: cell} row."""
    f, phones = {}, []
    for h, v in row.items():
        v = _esw.clean(v)
        if not v:
            continue
        k = kind(h)
        if k == "phone":
            phones.append(v)
        elif k and k not in f:
            f[k] = v
    if "name_post" in f:
        f["name"], f["post"] = name_post(f.pop("name_post"))
    f["phone_raw"] = phones
    return f


REGIONAL_DEPT = [("town_body", r"महानगरपालिका|नगर\s*निगम|नगर परिषद|नगरपालिका"), ("rural_development", r"जिल्हा परिषद|जिला परिषद|पंचायत"),
                 ("excise_tax", r"राज्यकर|वाणिज्य कर|करमणूक कर|उत्पादन शुल्क"), ("education", r"शिक्षण|शिक्षा"),
                 ("health", r"आरोग्य|स्वास्थ्य"), ("agriculture", r"कृषी|कृषि"), ("treasury", r"लेखा|कोषागार")]


def dept_of(post, section):
    t = " ".join([post, section])
    for k, rx in REGIONAL_DEPT:
        if re.search(rx, t):
            return k
    return _state.dept_key(post, section)


def is_head(p, post):
    """The head of the division office: "Divisional Commissioner", "Regional Commissioner", "Magadh Commissioner",
    "Commissioner, Jammu Division", "विभागीय आयुक्त"; not Additional / Deputy / Joint ones."""
    t = _esw.clean(post)
    for w in re.split(r"[\s-]+", p.get("division", "")):
        if len(w) >= 3:
            t = re.sub(r"(?i)\b" + re.escape(w) + r"\b", " ", t)
    t = re.sub(r"(?i)[,\s]*\b(division|divisional office)\b\W*$", "", t).strip(" ,")
    return bool(HEAD_OF_OFFICE.search(t)) and not NOT_HEAD.search(post)


def classify(p, post, name, section, address, email):
    """(level, district code, district name, dept, body_kind, post_kind) of one row."""
    police_item = p.get("kind") == "police"
    text = " ".join([post, section])
    level, code, dname = "division", "", ""
    if DISTRICT_HEAD.search(post) or (DISTRICT_HEAD.search(section) and not HEAD_OF_OFFICE.search(post)):
        code, dname = district_in(" ".join([post, section, address]), p.get("district_names"))
        if not code and email:
            code, dname = district_in(email.split("@")[0].replace(".", " ").replace("-", " "), p.get("district_names"))
        if code:
            level = "district"
    police = police_item or bool(POLICE.search(text + " " + name))
    if police:
        dept, body_kind = "police", "police"
    elif level == "district":
        dept = "administration" if re.search(r"(?i)collector|magistrate|deputy commissioner|जिल्हाधिकारी|जिलाधिकारी", post) else dept_of(post, section)
        body_kind = "department"
    elif dept_of(post, section) not in ("administration", "revenue") and not re.search(r"(?i)\bcommissioner\b(?!.*(tax|labour|food))|विभागीय|अपर आयुक्त|उपायुक्त", post):
        dept, body_kind = dept_of(post, section), "department"
    else:
        dept, body_kind = "revenue", "division"
    pk = _state.post_kind(post) or None
    if pk == "divisional_commissioner" and NOT_HEAD.search(post):
        pk = "officer"
    if level == "division" and not police and is_head(p, post):
        pk = "divisional_commissioner"
    elif level == "division" and not police and re.fullmatch(r"(?i)\W*commissioner\W*", section or "") and not post and name:
        pk = "divisional_commissioner"
    return level, code, dname, dept, body_kind, pk


def rows_records(p, rows, section, ids, poss, url, src=None):
    out = []
    st, div = p["state"], p["division"]
    for row, rid, pos in zip(rows, ids, poss):
        vals = [_esw.clean(v) for v in row.values() if _esw.clean(v)]
        if vals and all(HEADER_WORD.match(v) for v in vals):
            continue                                    # a second header row ("Code | Office | Residence | Mobile No.")
        f = fields(row)
        name, post = f.get("name", ""), f.get("post", "")
        if not (name or post) or re.fullmatch(r"(?i)name|नाम|नाव|designation", name or ""):
            continue
        email = _esw.emails(" ".join([f.get("email", "")] + f["phone_raw"]))
        phone = _esw.phones(*f["phone_raw"])
        mobile = _esw.phones(f.get("mobile", ""))
        address = f.get("address", "")
        level, code, dname, dept, body_kind, pk = classify(p, post, name, section or "", address, email)
        if body_kind == "police":
            body = p.get("body") if p.get("kind") == "police" else (section or f"Police, {div}")
        elif body_kind == "division":
            body = p.get("body") or f"Office of the Divisional Commissioner, {div}"
        else:
            body = section or p.get("body") or ""
        tdiv = (p.get("table_divisions") or {}).get(str((pos or {}).get("table", "")))
        kw = {"division": tdiv or div}
        if p.get("police_unit_rx"):
            u = re.search(p["police_unit_rx"], post + " " + address)
            kw["police_unit"] = _esw.clean(u.group(0)) if u else None
        if level == "division" and p.get("districts") and not tdiv:
            kw["districts"] = p["districts"]
        if level == "district":
            kw.update(district=dname, district_code=code, districts=[code])
        out.append(_state.rec(
            MODULE, f"{p['key']}:{rid}", state=st, level=level, post=post, post_kind=pk, name=name, body=body,
            body_kind=body_kind, department=section or None, dept=dept, phone=", ".join(x for x in (phone, mobile) if x),
            mobile=mobile or None, fax=f.get("fax") or None, email=email, address=address, section=section or None,
            host=urlparse(url).netloc, division_kind=p.get("kind") or "revenue", cells={k: v for k, v in row.items() if _esw.clean(v)},
            source=url, src_url=url, src_pos=pos, **{k: v for k, v in (src or {}).items() if k != "src_url"}, **kw))
    return out


def parse_page(p, html, url):
    out = []
    for t in officials.tables(html):
        heads = [kind(h) for h in t.get("headers", [])]
        if not ({"name", "post", "name_post"} & set(heads)):
            continue                                    # accessibility / file format tables of the CMS
        n = len(t["rows"])
        poss = t.get("pos") or [{} for _ in range(n)]
        ids = [f"{slug(url)}:{ps.get('table', 0)}:{ps.get('row', i + 1)}" for i, ps in enumerate(poss)]
        out += rows_records(p, t["rows"], t.get("caption", ""), ids, poss, url)
    return out


def pager(p, html, url, get):
    out, calls = [], 0
    for k in ("ww", "dir"):
        pg = officials.pager_blocks(html, k)
        if not pg:
            continue
        for b in pg["blocks"]:
            n = 1
            while n < b["pages"] and calls < MAX_AJAX:
                r = get(pg["ajaxurl"], "POST", {"action": pg["action"], "paged": n, "tax_slug": b["slug"], "type": "next",
                                                "profile_image": pg["profile"], "filter": pg["filter"], "security": pg["nonce"]})
                calls += 1
                if r is None:
                    break
                rows = officials.ajax_rows(r.text)
                if not rows:
                    break
                ids = [f"{pg['action']}:{b['slug']}:{n}:{i}" for i in range(1, len(rows) + 1)]
                poss = [{"category": b["slug"], "paged": n, "item": i} for i in range(1, len(rows) + 1)]
                out += rows_records(p, rows, b["name"], ids, poss, pg["ajaxurl"], provenance.at(r, pg["ajaxurl"]))
                try:
                    if str(json.loads(r.text).get("last")) == "1":
                        break
                except ValueError:
                    break
                n += 1
    return out


STOP = re.compile(r"(?i)district informatics|national informatics|screen reader|website (is )?(designed|content)")


def office_record(p, html, url, n, o):
    """One record for an office from contact text on the page: o = {"post", "anchor" (regex where the text starts; default
    the first of Office Address / Postal Address / Contact Us / Address), "division" (default the payload's)}. Phone = the
    numbers after "Phone", e-mail = the first address; a line "<name>-IPS, IGP Jammu Zone" (name with service, then the post)
    gives name and post."""
    post = o.get("post", "")
    soup = _esw.soup(html)
    for x in soup(["script", "style", "nav", "header", "footer"]):
        x.decompose()
    text = soup.get_text("\n", strip=True)
    m = None
    for rx in ([o["anchor"]] if o.get("anchor") else []) + [r"(?i)office address", r"(?i)postal address", r"(?i)contact us",
                                                            r"(?i)address", r"संपर्क"]:
        m = re.search(rx, text)
        if m or o.get("anchor"):
            break
    if o.get("anchor") and not m:
        return []
    chunk = text[m.start():] if m else text
    s = STOP.search(chunk)
    chunk = chunk[: s.start()] if s else chunk
    chunk = chunk[: int(o.get("chars", 800))]
    email = _esw.emails(chunk).split(", ")[0] if _esw.emails(chunk) else ""
    ph = re.search(r"(?i)(phone|tel|telephone|दूरध्वनी|दूरभाष)[^:\d]*:?\s*([\d\s,()/+-]{6,})", chunk)
    phone = _esw.phones(ph.group(2)) if ph else ""
    if not (email or phone):
        return []
    name = ""
    nm = re.search(r"(?m)^(.{3,60}?\b(?:IPS|IAS))\W+(.{3,80})$", chunk)
    if nm:
        name, post = nm.group(1).strip(" -,"), _esw.clean(nm.group(2))
    fax = re.search(r"(?i)fax\W*([\d\s,()/-]{6,})", chunk)
    lines = [x for x in chunk.split("\n")[1:] if not re.search(r"(?i)phone|e-?mail|website|tel\b|fax|share on|share of|contact us|"
                                                             r"^\W*or\W*$|\[|\b(IPS|IAS)\b|^address\W*$", x)]
    police = p.get("kind") == "police"
    div = o.get("division") or p["division"]
    return [_state.rec(MODULE, f"{p['key']}:office:{n}", state=p["state"], level="division", post=post,
                       post_kind=("divisional_commissioner" if is_head(p, post) else None) if not police else None, name=name,
                       body=p.get("body") or f"Office of the Divisional Commissioner, {div}",
                       body_kind="police" if police else "division", dept="police" if police else "revenue", division=div,
                       districts=p.get("districts") if o.get("division") in (None, p["division"]) else None,
                       police_unit=o.get("police_unit"), phone=phone, email=email, fax=_esw.phones(fax.group(1)) if fax else None,
                       address=", ".join(lines[:5]).strip(", "), office_contact=True, division_kind=p.get("kind") or "revenue",
                       host=urlparse(url).netloc, source=url, src_url=url,
                       src_pos={"text": "contact", "chars": [m.start() if m else 0, (m.start() if m else 0) + len(chunk)]})]


def fetch(p, get):
    recs, files, seen, cache = [], [], set(), {}
    pages = [(u, None) for u in p.get("urls", [])] + [(o["url"], o) for o in p.get("office", [])]
    for n, (url, o) in enumerate(pages):
        if url not in cache:
            r = get(url)
            if r is not None and getattr(r, "status_code", 200) < 400:
                if not r.encoding or r.encoding.lower() == "iso-8859-1":
                    r.encoding = "utf-8"
                files.append(_esw.keep(MODULE, f"{p['key']}/{slug(url)}", r.content))
                cache[url] = r.text
            else:
                cache[url] = None
        html = cache[url]
        if html is None:
            continue
        got = office_record(p, html, url, n, o) if o is not None else parse_page(p, html, url) + pager(p, html, url, get)
        for rid, d in got:
            if rid not in seen:
                seen.add(rid)
                recs.append((rid, d))
    return recs, files, "" if recs else "no rows"
