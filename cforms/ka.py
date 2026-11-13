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
import time
import socket

import requests
from bs4 import BeautifulSoup

import provenance
from cforms.cp_common import Cells

METHOD = "html table (town site council page, en and kn; head's message page text when no member is listed)"     # source trail (provenance.py)

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
# "ನಾಮಿನಿ ಸದಸ್ಯರು" (nominee member, Channarayapatna), "Name Direction Member" (a machine translation of ನಾಮನಿರ್ದೇಶನ, Hosapete),
# "NOMINATTED MEMBERS DETAILS" (Kembhavi)
NOMINATED = re.compile(r"nominat|nominee|ನಾಮನಿರ್ದೇಶ|ನಾಮ ನಿರ್ದೇಶ|ನಾಮಿನಿ|name\s*direction", re.I)
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


def _ward_in_address(s):
    """(ward number, ward name) from an "Address & Ward Number" cell, else (None, None). Only a ward the cell clearly states:
    "Ward No 01", "ವಾರ್ಡ್ ನಂ 01 ...", a cell that is only "23" or "12 - Gandhi Nagar", or a ward written at the end of the
    address as "<no>-<ward name>" (Saligrama: "... ಮನೆ ನಂ: 2-12 ಹೊಳೆಕೆರೆ -ಚಿತ್ರಪಾಡಿ 6 -ಮಾರಿ ಗುಡಿ" = ward 6 Mari Gudi).
    A house number at the start of an address ("1-175 Hoigekere House, Kadaba") is no ward (2026-11-14: _ward() read it as ward 1)."""
    t = (s or "").translate(KN_DIGITS).strip()
    if not t or ALL_WARDS.search(t):
        return None, None
    if re.search(r"ward|ವಾರ್ಡ", t, re.I):
        return _ward(t), None
    m = re.fullmatch(r"(\d{1,3})(?:\s*[-.,:)]\s*([^\d]{2,40}))?", t)
    if not m:
        m = re.search(r"(?:^|[\s,.;'\"])(\d{1,3})\s*-\s*([^\d,;/()\-]{2,30}?)\s*$", t)
    if not m:
        return None, None
    return str(int(m.group(1))), (m.group(2) or "").strip(" .,-") or None


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
            if len([c for c in cells if c]) < 2:
                if NOMINATED.search(" ".join(cells)):     # a title row in the table: "TMC KEMBHAVI NOMINATTED MEMBERS DETAILS"
                    nominated = True
                provenance.skip_row(cells, 'skip: len(cells) < 2')
                continue
            if sum(1 for c in cells if _col(c) in ("sl", "name", "position", "phone", "ward_no", "ward_addr")) >= 3:
                provenance.skip_row(cells, 'skip: the header row again (second block of the table)')
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
                d["address"] = d.pop("ward_addr")
                w, wn = _ward_in_address(d["address"])
                if w:
                    d["ward_no"] = w
                    if wn:
                        d.setdefault("ward_name", wn)
                if re.fullmatch(r"(?:ward|ವಾರ್ಡ್?)\W*(?:no|ನಂ|ಸಂಖ್ಯೆ)?\W*[\d೦-೯]+", d["address"], re.I):
                    del d["address"]            # the cell holds only the ward number
            if EX_OFFICIO.search(d.get("position", "")):
                provenance.skip_row(cells, 'skip: EX_OFFICIO.search(d.get("position", ""))')
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


MSG_LINK = re.compile(r"administrat|mayor|president|ಆಡಳಿತಾಧಿಕಾರಿ|ಮಹಾಪೌರ|ಅಧ್ಯಕ್ಷ", re.I)


def message_links(html, base):
    """Links of the home page to the head's message page ("Mayor's Message" -> /en/administrator-message on Shivamogga): the
    template keeps one such page per body; when the council's term is over it names the Administrator."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        h, t = a["href"], _txt(a)
        if "message" in h.lower() and (MSG_LINK.search(h) or MSG_LINK.search(t)) and "commis" not in h.lower():
            u = h if h.startswith("http") else base + "/" + h.lstrip("/")
            if u not in out:
                out.append(u)
    return out[:2]


def admin_message(html):
    """The Administrator named on a head's message page ('Shri Hon'ble Administrator, Shivamogga City Corporation'): the
    sentence that holds the word, else None. A Mayor / President message gives None (the council may still be in office)."""
    soup = BeautifulSoup(html, "lxml")
    area = soup.find("article") or soup.select_one(".region-content") or soup.body or soup
    text = _txt(area)
    m = re.search(r"administrator|ಆಡಳಿತಾಧಿಕಾರಿ", text, re.I)
    if not m:
        return None
    s = text.rfind(".", 0, max(0, m.start() - 60))
    return text[s + 1: m.end() + 120].strip()


def _message_status(p, base, get, home_lang="en"):
    """(url, response, text) of a head's message page that names the Administrator, else None."""
    home = _get(get, f"{base}/{home_lang}")
    if home is None:
        return None
    for u in message_links(home.text, base):
        r = _get(get, u)
        if r is not None and (t := admin_message(r.text)):
            return u, r, t
    return None


def fetch(p, get):
    base, path, sl = _base(p), p.get("path", "council-members"), p["slug"]
    files, recs, admins, why, blank = [], [], [], "", 0
    seen = None            # (url, response) of the last page that answered: the source of a "no members listed" status
    for lang in ("en", "kn"):
        url = f"{base}/{lang}/{path}"
        r = _get(get, url)
        if r is None:
            why = why or f"{lang} page did not answer"
            continue
        seen = (url, r)
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
    if seen:
        # no member and no Administrator on the council page: the head's message page (linked from the home page) may name
        # the Administrator (Shivamogga: "Hon'ble Administrator, Shivamogga City Corporation" under "Mayor's Message")
        msg = _message_status(p, base, get)
        if msg:
            url, r, t = msg
            files.append((f"councillors/KA/{sl}-message.html.gz", gzip.compress(r.content), "application/gzip"))
            rec = {"type": "body_status", "state": "KA", "body": p.get("body"), "body_type": p.get("body_type"), "district": p.get("district"),
                   "lgd_code": p.get("lgd_code"), "status": "administrator", "administrator": t[:300],
                   "note": "no council members listed; the head's message page names the Administrator", "url": url, **provenance.at(r, url),
                   "src_pos": {"part": "message page text"}, "method": "html text (town site head's message page)"}
            return [(f"body_status:KA:{sl}", {k: v for k, v in rec.items() if v not in (None, "")})], files, ""
    if seen:        # the town's own site answered but lists no member: say so on the town page, with the page as source
        url, r = seen
        note = ("the town's website shows its ward table with empty names" if blank else "the town's website lists no council members")
        rec = {"type": "body_status", "state": "KA", "body": p.get("body"), "body_type": p.get("body_type"), "district": p.get("district"),
               "lgd_code": p.get("lgd_code"), "status": "no members listed", "note": note, "url": url, **provenance.at(r),
               "checked": time.strftime("%Y-%m-%d", time.gmtime())}
        return [(f"body_status:KA:{sl}", {k: v for k, v in rec.items() if v not in (None, "")})], files, ""
    if blank:
        return [], files, "no council members listed (ward table with empty names)"
    return [], files, why or "no council members listed"
