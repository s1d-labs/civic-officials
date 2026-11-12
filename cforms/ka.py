"""Karnataka: council members of urban local bodies, from each body's own site on *.mrc.gov.in (KMDS Drupal template,
"Know Your Members > Council Members"). India only. Most of these sites serve plain http (port 443 refused): fetch() asks port 443
first and uses https when it answers (certificate checks stay on), http only when the connection is refused.
One queue item = one body: payload {"kind": "form-ka", "state": "KA", "url": "<scheme>://<host>/en/<path>", "host", "path",
"body", "body_type", "district", "lgd_code", "slug"}. The English page comes first; when it has no member table (some bodies
fill only the Kannada side), the same path under /kn/ is read. Tables differ per body: ward number, name, designation, address,
phone, party or reservation, in English or Kannada. A table that lists only the Administrator (council term over) gives one
record body_status:KA:<slug> (type body_status, status "administrator", the administrator's name and post); a template with ward rows but empty names, or notices
in the name column ("Election Not Held", "Stay in High Court"), gives "... (ward table with empty names)". MP/MLA/MLC rows
(ex-officio) are left out. Record id councillor:KA:<slug>:<ward no>; nominated members get nominated-<n>, and members on a page
without ward numbers sl-<serial no>. Seeds: seeds/councillors_ka.json."""
import gzip
import re
import socket

import requests
from bs4 import BeautifulSoup

import provenance
from cforms.cp_common import Cells

METHOD = "html table (town site council page, en and kn)"     # source trail (provenance.py): how this reader reads its sources

KN_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")

# column header -> field; checked in this order, first match wins (English and Kannada headers)
COLS = [
    ("sl", r"^(s[li]\.?\s*no|sl\b|si\b|sr\.?\s*no|serial|ಕ್ರಮ)"),
    ("ward_noname", r"ward\s*(?:no|number)\W.*name|ವಾರ್ಡ್?\s*ಸಂಖ್ಯೆ.*ಹೆಸರು"),
    ("ward_name", r"ward\s*name|ವಾರ್ಡ್?\s*ಹೆಸರು"),
    ("ward_addr", r"address.*ward|ward.*address|ವಿಳಾಸ.*ವಾರ್ಡ|ವಾರ್ಡ.*ವಿಳಾಸ"),
    ("ward_no", r"ward|ವಾರ್ಡ"),
    ("addr_phone", r"address.*(?:contact|mobile|phone)|(?:contact|mobile|phone).*address|ವಿಳಾಸ.*ಸಂಪರ್ಕ"),
    ("phone", r"contact|mobile|phone|ph\.?\s*no|ಸಂಪರ್ಕ|ಮೊಬೈಲ್|ದೂರವಾಣಿ"),
    ("name", r"name|ಹೆಸರು"),
    ("position", r"designation|post\b|position|ಹುದ್ದೆ|ಪದನಾಮ"),
    ("party", r"party|ಪಕ್ಷ"),
    ("reservation", r"reserv|category|ಮೀಸಲಾತಿ|ಪ್ರವರ್ಗ"),
    ("address", r"address|ವಿಳಾಸ"),
    ("photo", r"photo|ಫೋಟೋ|ಭಾವಚಿತ್ರ"),
]
# the official in charge when the council's term is over: Administrator, Deputy/Assistant Commissioner, an IAS/KAS officer
ADMIN = re.compile(r"administrator|administrative officer|ಆಡಳಿತಾಧಿಕಾರಿ|ಆಡಳಿತ ಅಧಿಕಾರಿ|deputy commissioner|assistant commissioner|\bI\.?\s?A\.?\s?S\b|\bK\.?\s?A\.?\s?S\b"
                   r"|ಜಿಲ್ಲಾಧಿಕಾರಿ|ಉಪ ?ವಿಭಾಗಾಧಿಕಾರಿ|ಸಹಾಯಕ ಆಯುಕ್ತ|ಅಡಳಿತಾಧಿಕಾರಿ|ಭಾ\.\s?[ಆಅ]\.\s?ಸೇ", re.I)
# MP / MLA / MLC rows: ex-officio members, not elected for a ward (they are in the legislator records)
EX_OFFICIO = re.compile(r"\bM\.?\s?P\b|\bM\.?\s?L\.?\s?[AC]\b|member of parliament|legislative|ಸಂಸದ|ಶಾಸಕ|ವಿಧಾನ ?ಪರಿಷತ್", re.I)
# a row that holds no person: honorific only, "vacant", "Ending its current term", "Election Not Held ..."
PLACEHOLDER = re.compile(r"vacant|ಖಾಲಿ|\bterm\b|election|not held|ಚುನಾವಣೆ|ಅವಧಿ|\bstay\b|\bcourt\b|conduct|upgraded|\bclosed\b|council members|ನ್ಯಾಯಾಲಯ|ಇರುವುದಿಲ್ಲ|ಮೇಲ್ದ", re.I)
HONORIFIC = re.compile(r"^(?:(?:shri|sri|smt|mrs?|ms|dr|kum|ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ|ಡಾ)(?=[\s.,]|$)\.?\s*)+", re.I)
ALL_WARDS = re.compile(r"^\s*all\b|ಎಲ್ಲಾ", re.I)
# "ನಾಮಿನಿ ಸದಸ್ಯರು" (nominee member, Channarayapatna), "Name Direction Member" (a machine translation of ನಾಮನಿರ್ದೇಶನ, Hosapete)
NOMINATED = re.compile(r"nominated|nominee|ನಾಮನಿರ್ದೇಶ|ನಾಮ ನಿರ್ದೇಶ|ನಾಮಿನಿ|name\s*direction", re.I)
HONBLE = re.compile(r"\bHon'?ble\b|\bHonourable\b|ಮಾನ್ಯ|ಪೂಜ್ಯ", re.I)
TERM = re.compile(r"(?:term|ಅವಧಿ)\D{0,20}((?:19|20)\d\d\s*(?:-|–|to|ರಿಂದ)\s*(?:19|20)\d\d)", re.I)


def _txt(el):
    return " ".join(el.get_text(" ", strip=True).split())


def _col(head):
    h = head.lower()
    for key, rx in COLS:
        if re.search(rx, h):
            return key
    return None


def _ward(s):
    """Ward number from 'Ward No.69', '69 ನೇ ವಾರ್ಡ', 'ವಾರ್ಡ್ ನಂ 04', '23'; None for 'All 31 Wards' or text without a number."""
    s = (s or "").translate(KN_DIGITS)
    if re.search(r"\ball\b|ಎಲ್ಲಾ", s, re.I):
        return None
    m = re.search(r"(?:ward|ವಾರ್ಡ್?)\D{0,12}?(\d{1,3})\b", s, re.I) or re.search(r"\b(\d{1,3})\s*(?:ನೇ|st|nd|rd|th)?\s*(?:ward|ವಾರ್ಡ)", s, re.I)
    if not m:                       # a ward cell: "23", "12 - Gandhi Nagar"
        m = re.match(r"\s*(\d{1,3})(?:\s*[-.,:)]|\s*$|\s+\D)", s)
    return str(int(m.group(1))) if m else None


def _phone(s):
    s = re.sub(r"[\u2010-\u2015]", "-", (s or "").translate(KN_DIGITS).replace("\xa0", " "))
    nums = re.findall(r"(?:\+91[\s-]?)?\d[\d\s-]{6,}\d", s)
    nums = [re.sub(r"[\s-]", "", n) for n in nums]
    return ", ".join(n for n in nums if len(n) >= 8) or None


def tables(html):
    """Member tables in the page's content area: [(heading text before it, [header], [[cells]])]."""
    soup = BeautifulSoup(html, "lxml")
    area = soup.find("article") or soup.select_one(".region-content") or soup.body or soup
    out = []
    for t in area.find_all("table"):
        if t.find_parent("table") is not None:
            continue
        trs = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
        hi = next((i for i, tr in enumerate(trs[:4])
                   if sum(1 for c in tr.find_all(["th", "td"]) if _col(_txt(c)) in ("name", "ward_no", "position", "phone", "sl")) >= 2), None)
        if hi is None:
            continue
        head = [_txt(c) for c in trs[hi].find_all(["th", "td"])]
        tno = len(t.find_all_previous("table")) + 1
        rows = []
        for ri, tr in enumerate(trs[hi + 1:], hi + 2):     # source trail: table place on the page, <tr> number in it
            row = Cells(_txt(c) for c in tr.find_all(["td", "th"]))
            row.pos = {"table": tno, "row": ri}
            rows.append(row)
        prev = t.find_previous(["h1", "h2", "h3", "h4", "h5", "p", "strong"])
        heading = " ".join([_txt(prev) if prev else ""] + [_txt(tr) for tr in trs[:hi]])     # title rows inside the table count too
        out.append((heading, head, [r for r in rows if any(r)]))
    return out


def members(html):
    """Rows as dicts with fields named as in COLS; plus the Administrator rows seen, and a term if the page states one."""
    rows, admins, blank = [], [], 0
    for heading, head, body in tables(html):
        cols = [_col(h) for h in head]
        nominated = bool(NOMINATED.search(heading)) or "ward_no" not in cols and "ward_addr" not in cols and bool(NOMINATED.search(" ".join(head)))
        for cells in body:
            if len(cells) < 2:
                continue
            d = {"_pos": getattr(cells, "pos", None)}
            for c, v in zip(cols, cells):
                if c and v and v not in ("-", "--", "NA", "N/A") and c not in d:
                    d[c] = v
            bare = re.sub(r"[\s\d.,_/()\-]", "", HONORIFIC.sub("", d.get("name") or ""))     # Kannada vowel signs count
            if len(bare) < 2 or len(d["name"]) > 90 or PLACEHOLDER.search(d["name"]):     # a name of 2 letters or a sentence is no name
                blank += 1                     # a ward row of the template with the name left empty
                continue
            if ADMIN.search(" ".join((d.get("position", ""), " ".join(head), d.get("name", "")))) \
                    or ALL_WARDS.search(d.get("ward_no") or d.get("ward_addr") or ""):
                admins.append(d)
                continue
            if "ward_addr" in d:
                d["ward_no"] = d["address"] = d.pop("ward_addr")
                if re.fullmatch(r"(?:ward|ವಾರ್ಡ್?)\W*(?:no|ನಂ|ಸಂಖ್ಯೆ)?\W*[\d೦-೯]+", d["address"], re.I):
                    del d["address"]            # the cell holds only the ward number
            if EX_OFFICIO.search(d.get("position", "")):
                continue
            if "addr_phone" in d:            # one cell with the address and the phone number
                d["address"] = d["phone_raw"] = d.pop("addr_phone")
                d.setdefault("phone", d["phone_raw"])
                del d["phone_raw"]
            # "Councillor Ward No.13", "Ward Mo.11, Chandapura Village": the ward written elsewhere. The post first: an address can
            # name the ward the member lives in (Chandapura: post "Ward No.13", address "Ward No.10, #134 ...")
            for src in ("position", "address"):
                v = d.get(src) or ""
                if "ward_no" not in d and re.search(r"ward|ವಾರ್ಡ", v, re.I) and (src == "address" or re.search(r"[\d೦-೯]", v)):
                    d["ward_no"] = v
            if "ward_noname" in d:          # "12 - Gandhi Nagar", "Ward No 12 Gandhi Nagar"
                v = d.pop("ward_noname")
                d["ward_no"] = v
                nm = re.sub(r"^\W*(?:ward|ವಾರ್ಡ್?)?\W*(?:no|number|ನಂ|ಸಂಖ್ಯೆ)?\W*[\d೦-೯]+\W*", "", v, flags=re.I).strip()
                if nm and nm != v:
                    d.setdefault("ward_name", nm)
            m = HONBLE.search(d["name"])         # "Smt. X Hon'ble Mayor": the post written after the name
            if m and m.start() > 0:
                d.setdefault("position", d["name"][m.start():].strip())
                d["name"] = d["name"][:m.start()].strip(" ,")
            d["nominated"] = nominated or bool(NOMINATED.search(d.get("position", "")))
            rows.append(d)
    soup = BeautifulSoup(html, "lxml")
    text = _txt(soup.find("article") or soup)
    if not rows and not admins and ADMIN.search(text):     # "... have taken charge as the Administrator" written as text
        admins.append({"text": text[:300]})
    m = TERM.search(text)
    return rows, admins, (re.sub(r"\s+", " ", m.group(1)) if m else None), blank


def _base(p):
    """https when port 443 accepts a connection, http when it is refused; otherwise the scheme the seed found."""
    host = p["host"]
    try:
        socket.create_connection((host, 443), timeout=10).close()
        return "https://" + host
    except ConnectionRefusedError:
        return "http://" + host
    except OSError:
        return p["url"].split("://", 1)[0] + "://" + host


def _get(get, url):
    try:
        return get(url)
    except requests.exceptions.ConnectionError as e:     # --local mode raises: a refused https connection -> same page over http
        if url.startswith("https://") and "refused" in str(e).lower():
            return get("http://" + url[len("https://"):])
        raise


def fetch(p, get):
    base, path, sl = _base(p), p.get("path", "council-members"), p["slug"]
    files, recs, admins, why, blank = [], [], [], "", 0
    for lang in ("en", "kn"):
        url = f"{base}/{lang}/{path}"
        r = _get(get, url)
        if r is None:
            why = why or f"{lang} page did not answer"
            continue
        files.append((f"councillors/KA/{sl}-{lang}.html.gz", gzip.compress(r.content), "application/gzip"))
        rows, adm, term, nb = members(r.text)
        admins += [(a, url, r) for a in adm]
        blank += nb
        if not rows:
            continue
        used, n_nom = set(), 0
        for d in rows:
            ward = None if d["nominated"] else _ward(d.get("ward_no"))
            if d["nominated"]:
                n_nom += 1
                key = f"nominated-{n_nom}"
            elif ward is None:              # the page gives no ward: the row's serial number
                serial = re.sub(r"\D", "", (d.get("sl") or "").translate(KN_DIGITS))
                key = f"sl-{int(serial)}" if serial else f"row-{len(used) + 1}"
            else:
                key = ward
            k, n = key, 1
            while k in used:                # two members on one ward number (or a repeated serial): -2, -3 ...
                n += 1
                k = f"{key}-{n}"
            used.add(k)
            key = k
            rec = {"type": "councillor", "state": "KA", "body": p.get("body"), "body_type": p.get("body_type"), "district": p.get("district"),
                   "lgd_code": p.get("lgd_code"), "ward_no": ward, "ward_name": d.get("ward_name"), "name": d.get("name"),
                   "position": d.get("position"), "party": d.get("party"), "reservation": d.get("reservation"), "phone": _phone(d.get("phone")),
                   "address": d.get("address"), "nominated": d["nominated"] or None, "election": term or "as listed on the body's website (term not stated)", "lang": lang, "url": url,
                   **provenance.at(r), "src_pos": d.get("_pos")}
            recs.append((f"councillor:KA:{sl}:{key}", {k: v for k, v in rec.items() if v not in (None, "")}))
        return recs, files, ""
    if admins:      # the council's term is over: one body_status record (sql/73 of civic-india shows it on the town page)
        a, url, r = admins[0]
        who = "; ".join(dict.fromkeys(" · ".join(x for x in (d.get("name"), d.get("position")) if x) or d.get("text", "")
                                      for d, _, _ in admins))
        rec = {"type": "body_status", "state": "KA", "body": p.get("body"), "body_type": p.get("body_type"), "district": p.get("district"),
               "lgd_code": p.get("lgd_code"), "status": "administrator", "administrator": who[:300],
               "note": "no council members listed (administrator only)", "url": url, **provenance.at(r), "src_pos": a.get("_pos")}
        return [(f"body_status:KA:{sl}", {k: v for k, v in rec.items() if v not in (None, "")})], files, ""
    if blank:
        return [], files, "no council members listed (ward table with empty names)"
    return [], files, why or "no council members listed"
