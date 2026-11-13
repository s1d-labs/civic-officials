"""West Bengal: district and block officers from the Chief Electoral Officer's site (ceowestbengal.wb.gov.in, "Officials" page).

Files (text PDFs printed from spreadsheets, 90-400 KB, checked 2026-11-12 from dev-vps-3, Mumbai):
- Downloads/Officials/<DISTRICT>.pdf, one per district (24, Google Sheets): sections "Additional District Magistrate",
  "Sub-Divisional Officer", "Returning Officer" (per assembly constituency: the officer and his regular post), "Block Development
  Officer", "Cell In-Charge" (election cells: Name of the Cell, ADM In-Charge + phones + e-mail, Officer In-Charge + phones +
  e-mail; one record per cell row for its Officer In-Charge, the ADM in adm_in_charge; the ADM alone when the row has no
  officer). Returning Officer rows that name no AC (Purulia, Alipurduar) are kept with the district as area. Columns: District (or "<AC no>-<AC name>"), Name, Designation, Office
  Telephone No., Mobile No., Email ID, Residential Contact No.
- Downloads/EROlist/ERO.pdf ("ERO of West Bengal as on <date>", 294 ACs, Excel) and EROlist/RO_2024.pdf (an older ERO list with
  the same columns in another order): AC No, District, Assembly, Name, Office Address, Mobile No., Landline, E-mail.
- Downloads/DMList/DMDEO.pdf: District Magistrate & District Election Officer per district.
- Downloads/CEOOffice/CEO_Office.pdf: the CEO's own office (name, designation, land line, fax).

Route: the host needs TLS legacy renegotiation (councillors.get() retries with LegacyTLS). From abroad it did not answer
(2026-11-11); from Mumbai (dev-vps-3) it answers: project civic-officials-depts-direct.
Cells: dforms/_pdfcells.py (poppler pdftotext -raw -bbox + pypdf grid lines). Google Sheets cells mix: a row's AC or district
can stand in the name cell, a phone can stick to the e-mail. The reader reads the person's name up to the service tag (IAS,
WBCS (Exe.), ...) and takes phones and e-mails from the whole row. Phones as written; mobile = the 10-digit numbers.
One queue item = one PDF; the PDF is kept in the bucket (depts/sub3_wb/<file>.pdf.gz).
Record ids: dept:sub3_wb:<file slug>:<section>:<area slug or AC no>[:n].
"""
import re
from urllib.parse import quote

from dforms import _esw
from dforms import _pdfcells
import provenance

METHOD = 'pdf table cells (pdftotext -raw -bbox, else pypdf)'     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub3_wb"
BASE = "https://ceowestbengal.wb.gov.in/Downloads/"
DISTRICTS = ["ALIPURDUAR", "BANKURA", "BIRBHUM", "COOCHBEHAR", "DAKSHIN DINAJPUR", "DARJEELING", "HOOGHLY", "HOWRAH", "JALPAIGURI",
             "JHARGRAM", "KALIMPONG", "KOLKATA NORTH", "KOLKATA SOUTH", "MALDA", "MURSHIDABAD", "NADIA", "NORTH 24 PARGANAS",
             "PASCHIM BARDHAMAN", "PASCHIM MEDINIPUR", "PURBA BARDHAMAN", "PURBA MEDINIPUR", "PURULIA", "SOUTH 24 PARGANAS",
             "UTTAR DINAJPUR"]
LISTS = [("ero", "EROlist/ERO.pdf"), ("ero2024", "EROlist/RO_2024.pdf"), ("dm", "DMList/DMDEO.pdf"), ("ceo", "CEOOffice/CEO_Office.pdf")]
# section title -> (key, post, dept, level)
SECTIONS = (
    (r"additional\s+district\s+magistrate", ("adm", "Additional District Magistrate", "administration", "district")),
    (r"sub[\s-]*divisional\s+officer", ("sdo", "Sub-Divisional Officer", "administration", "subdivision")),
    (r"returning\s+officer", ("ro", "Returning Officer", "elections", "ac")),
    (r"block\s+development\s+officer", ("bdo", "Block Development Officer", "rural_development", "block")),
    (r"cell\s+in[\s-]*charge", ("cell", None, None, None)),
    (r"^\s*AEO\s*$|assistant\s+election\s+officer", ("aeo", "Assistant Election Officer", "elections", "district")),
    (r"district\s+magistrate\s*&\s*district\s+election", ("dm", "District Magistrate & District Election Officer", "administration",
                                                          "district")),
    (r"\bERO\s+of\s+west\s+bengal", ("ero", "Electoral Registration Officer", "elections", "ac")),
)
SERVICE = re.compile(r",?\s*\b(?:I\.?\s?A\.?\s?S\.?|lAS|I\.?P\.?S\.?|W\.?\s?B\.?\s?C\.?\s?S\.?\s*\(?\s*Exe(?:c|cutive)?\.?\s*\)?|WBCS|WBA\s*&\s*AS|WBSS|"
                     r"WBFS|WBIS|IRS|IFS)(?![\w])\.?", re.I)
MOBILE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")


def items(get=None):
    out = [{"key": f"sub3_wb_{_esw.slug(d)}", "payload": {"reader": MODULE, "url": BASE + "Officials/" + quote(d) + ".pdf",
                                                          "file": _esw.slug(d), "district": d.title(), "state": "WB",
                                                          "india_only": True, "route": "direct"}}
           for d in DISTRICTS]
    out += [{"key": f"sub3_wb_{k}", "payload": {"reader": MODULE, "url": BASE + path, "file": k, "state": "WB",
                                                "india_only": True, "route": "direct"}} for k, path in LISTS]
    return out


def fix_emails(s):
    """E-mails as the cell wraps them ("sdo.sadar.cbrelection@gmail. com", "ero25matigaranaxalbari@gm ail.com", "dm- ali@nic.in"),
    a phone stuck in front ("9231847777admghoog@gmail.com") cut off."""
    s = re.sub(r"(\d{10})(?=[a-z])", r"\1 ", s or "", flags=re.I)
    s = re.sub(r"(@[\w.-]*?)\s+(?=[\w.-]*\.(?:com|in|org|net)\b)", r"\1", s)    # break inside the domain
    s = re.sub(r"(@[\w-]+\.)\s+(?=(?:com|in|org|net|co|gov|nic)\b)", r"\1", s)
    s = re.sub(r"(\.co)\s+(m)\b", r"\1\2", s)
    s = re.sub(r"\b([\w.]+-)\s+(?=[\w.-]+@)", r"\1", s)                            # break after a hyphen in the local part
    return s


def split_phones(text):
    """(mobiles, other phones) in a text, as written."""
    t = re.sub(r"\s*/\s*", " / ", text or "")
    mob = [m.group(1) for m in MOBILE.finditer(t)]
    rest = MOBILE.sub(" ", t)
    other = [p for p in _esw.phones(rest).split(", ") if p and len(re.sub(r"\D", "", p)) >= 6]
    return mob, other


def section_of(text):
    for rx, sec in SECTIONS:
        if re.search(rx, text, re.I):
            return sec
    return None


def _role(label):
    l = label.lower()
    for role, rx in (("acno", r"^ac\s*no"), ("assembly", r"assembly"), ("district", r"district"), ("cell", r"name of the cell"),
                     ("name", r"name"), ("designation", r"designation"), ("address", r"address"), ("office_phone", r"office|land"),
                     ("mobile", r"mobile"), ("email", r"e-?mail"), ("residential", r"residential"), ("fax", r"fax")):
        if re.search(rx, l):
            return role
    return None


def split_name(text):
    """(name, service, rest) from "Tarun Bhattacharyya, WBCS (Exe.) Additional District Magistrate ..."."""
    m = SERVICE.search(text or "")
    if not m:
        return _esw.clean(text), "", ""
    svc = re.sub(r"^[,\s]+", "", m.group(0))
    return _esw.clean(text[:m.start()]).strip(" ,"), _esw.clean(svc), _esw.clean(text[m.end():]).strip(" ,")


AC_HEAD = re.compile(r"^\s*(\d{1,3})\s*-\s*")


def strip_ac(text):
    """("185", "Uttarpara", rest) when the text starts with "<no>-<AC name>", else (None, None, text). The AC name ends where the
    WB AC list says (dforms/ac_no.json), else after one word; "(SC)" / "(ST)" go with it."""
    m = AC_HEAD.match(text or "")
    if not m:
        return None, None, text
    no, rest = m.group(1), text[m.end():]
    words = rest.split()
    names = [k for k, v in _esw._AC.get("WB", {}).items() if str(v) == no] if _esw._AC else []
    take = 1
    if names:
        target = names[0].split("@")[0]
        for i in range(1, min(5, len(words)) + 1):
            if len(_esw.norm_ac(" ".join(words[:i]))) >= len(target) - 2:
                take = i
                break
    while take < len(words) and re.fullmatch(r"\((sc|st)\)", words[take], re.I):
        take += 1
    return no, " ".join(words[:take]), " ".join(words[take:])


def area_of(sec, designation, district):
    """Block / sub-division from the designation: "BLOCK DEVELOPMENT OFFICER, ARAMBAGH, HOOGHLY." -> "Arambagh"."""
    d = re.sub(r"\s+", " ", designation or "").strip(" .")
    if sec == "bdo":
        m = re.search(r"(?:develope?ment\s+officer|\bB\.?\s?D\.?\s?O\b\.?)\s*,?\s*(?:of\s+)?(.+)", d, re.I)
    elif sec == "sdo":
        m = re.search(r"officer\s*,?\s*(.+)", d, re.I)
    else:
        return None
    if not m:
        return None
    parts = [p.strip(" .") for p in m.group(1).split(",") if p.strip(" .")]
    if len(parts) > 1 and district and _esw.norm_ac(parts[-1]) == _esw.norm_ac(district):
        parts = parts[:-1]
    a = ", ".join(parts)
    if a.isupper():
        a = re.sub(r"\b(i{1,3}|iv|vi{0,3})\b", lambda m: m.group(1).upper(), a.title(), flags=re.I)
    return a


def parse(content, p):
    """Records from one PDF."""
    _esw.ac_no("WB", "")                                    # loads ac_no.json
    url, file = p.get("url", ""), p.get("file") or "x"
    district0 = p.get("district")
    recs, seen = [], {}
    sec, roles, as_on, cell_cols = None, None, None, None
    for pg in _pdfcells.pages(content):
        for row, text in zip(pg["rows"], pg["texts"]):
            filled = [c for c in row if c]
            low = text.lower()
            if len(filled) == 1 and not re.search(r"\d{5}|@", text) and len(text) < 80 and not re.search(r"not\s+applicable", text, re.I):
                if section_of(text):
                    sec = section_of(text)
                elif re.search(r"officer|magistrate|\b(aeo|ero|deo|sdo|bdo|aero)\b|in[\s-]*charge", text, re.I):
                    sec = (_esw.slug(text)[:30], _esw.clean(text), "elections", "district")
                else:
                    continue
                m = re.search(r"as\s+on\s+([\d.\-/]+)", text, re.I)
                as_on = m.group(1) if m else as_on
                continue
            if sec and sec[0] == "cell":
                if re.search(r"officer\s+in[\s-]*charge", low) and not re.search(r"@", text):
                    cell_cols = (row.index(next(c for c in row if re.search(r"(?i)officer\s+in", c or ""))),
                                 next((i for i, c in enumerate(row) if re.search(r"(?i)adm\s+in", c or "")), 2))
                    continue
                if cell_cols and re.search(r"[A-Za-z]{3}", text) and re.search(r"\d{6}|\d{5} \d{5}|@", text):
                    rec = build_cell(row, cell_cols, district0, url, pg["page"])
                    if rec is not None:
                        base = f"{file}:cell:{rec.pop('_key')}"
                        seen[base] = seen.get(base, 0) + 1
                        recs.append(_esw.record(MODULE, base if seen[base] == 1 else f"{base}:{seen[base]}", **rec))
                        continue
            if re.search(r"\bname\b", low) and re.search(r"designation|mobile|address|land", low) and not re.search(r"@", text):
                roles = [_role(c) if c else None for c in row]
                if sec is None and re.search(r"designation", low) and file == "ceo":
                    sec = ("ceo", None, "elections", "state")
                continue
            text_na = re.sub(r"not\s+applicable", " ", text, flags=re.I)
            if file == "ceo":
                sec = ("ceo", None, "elections", "state")
            if not roles or not sec or sec[0] == "cell" or not re.search(r"[A-Za-z]{3}", text_na):
                provenance.skip_line(row, 'skip: not roles or not sec or sec[0] == "cell" or not re.search(r"[A-Za-z...')
                continue
            cells = {}
            for role, c in zip(roles, row):
                if c:
                    c = re.sub(r"(?i)\bnot\s+applicable\b", " ", c).strip()
                    if c:
                        cells[role] = (cells.get(role, "") + " " + c).strip()
            rec = build(sec, cells, district0, url, as_on, pg["page"])
            if rec is None:
                provenance.skip_line(row, 'skip: rec is None')
                continue
            base = f"{file}:{sec[0]}:{rec.pop('_key')}"
            seen[base] = seen.get(base, 0) + 1
            key = base if seen[base] == 1 else f"{base}:{seen[base]}"
            recs.append(_esw.record(MODULE, key, **rec))
    return recs


def _parts(text):
    """(name, service, rest) of one person's text with phones and e-mails taken out."""
    t = _esw.EMAIL.sub(" ", text)
    t = re.sub(r"(?<![\w-])(?:\+?91[\s-]?)?0?\d[\d\s-]{7,}\d(?![\w])", " ", t)
    name, service, rest = split_name(_esw.clean(t))
    if not service and "," in (name or ""):            # "Lopsang Tamang, PD, DRDC": the name ends at the first comma
        name, rest = name.split(",", 1)
    return _esw.clean(name).strip(" ,&"), service, _esw.clean(rest).strip(" ,")


def _contacts(text):
    mob, other = split_phones(_esw.EMAIL.sub(" ", text))
    return mob, other, _esw.emails(text)


def build_cell(row, cols, district0, url, page):
    """One row of the "Cell In-Charge" table: the cell, its ADM in charge and its Officer In-Charge (the person of the record;
    the ADM when no officer is named). The sheets often draw the officer into the ADM's e-mail cell and the ADM into the cell
    name ("9231847777materialmanagementcell2026@gmail.com Ajoy Kumar Bose, WBCS (Exe.), DM&DC"): the officer is the text of
    the officer columns, else the person written after the ADM's e-mail."""
    oi, ai = cols
    na = lambda c: re.sub(r"(?i)\bnot\s+applicable\b", " ", c or "").strip()
    cell = _esw.clean(na(row[1]) if len(row) > 1 else "")
    if SERVICE.search(cell) or re.search(r"\d{6}|@", cell):
        cell = ""
    adm_t = fix_emails(" ".join(na(c) for c in row[1 if not cell else ai:oi] if na(c)))
    off_t = fix_emails(" ".join(na(c) for c in row[oi:] if na(c)))
    if not re.search(r"[A-Za-z]{3}", _esw.EMAIL.sub(" ", off_t)):
        # the officer written after the ADM's e-mail in the ADM part
        m = list(_esw.EMAIL.finditer(adm_t))
        if m and re.search(r"[A-Z][a-z]+\s+[A-Z]", adm_t[m[-1].end():]):
            adm_t, off_t = adm_t[:m[-1].end()], adm_t[m[-1].end():] + " " + off_t
    else:
        m = list(_esw.EMAIL.finditer(adm_t))
        if m and re.search(r"[A-Z][a-z]+\.?\s+[A-Z][a-z]+.*?(?:" + SERVICE.pattern + ")", adm_t[m[-1].end():] + " " + off_t):
            adm_t, off_t = adm_t[:m[-1].end()], adm_t[m[-1].end():] + " " + off_t
    lead = re.match(r"^[\s\d/,-]*(?:\S+@\S+\s*)*", off_t)     # phones and e-mails before the officer's name (with an e-mail): the ADM's
    if lead and "@" in lead.group(0) and re.search(r"[A-Za-z]{3}", off_t[lead.end():]):
        adm_t, off_t = adm_t + " " + lead.group(0), off_t[lead.end():]
    adm_name, adm_svc, adm_rest = _parts(adm_t)
    adm_mob, adm_other, adm_mail = _contacts(adm_t)
    name, svc, rest = _parts(off_t)
    mob, other, mail = _contacts(off_t)
    who = "Officer In-Charge"
    if not name or not re.search(r"[A-Za-z]{3}", name):
        name, svc, rest, mob, other, mail, who = adm_name, adm_svc, adm_rest, adm_mob, adm_other, adm_mail or mail, "ADM In-Charge"
    if not name or not re.search(r"[A-Za-z]{3}", name):
        return None
    adm = who != "ADM In-Charge"
    return {"_key": _esw.slug(cell or name)[:60], "dept": "elections", "level": "district", "area": district0,
            "post": f"{who}, {cell}" if cell else who, "name": name, "service": svc or None, "designation": rest or None,
            "cell": cell or None, "phone": ", ".join(dict.fromkeys(mob + other)), "mobile": ", ".join(mob), "email": mail,
            "adm_in_charge": _esw.clean(" ".join(x for x in (adm_name, adm_svc, adm_rest) if x)) if adm else None,
            "adm_phone": ", ".join(dict.fromkeys(adm_mob + adm_other)) if adm else None, "adm_email": adm_mail if adm else None,
            "state": "WB", "district": district0, "source": url, "page": page}


def build(sec, cells, district0, url, as_on, page):
    key, post, dept, level = sec
    allt = " ".join(v for k, v in cells.items() if k not in ("address", "fax"))
    email = _esw.emails(fix_emails(cells.get("email", "") + " " + allt))
    mail_free = _esw.EMAIL.sub(" ", fix_emails(allt))
    ac_no = ac_name = None
    district = district0
    if key == "ero":
        ac_no = (re.sub(r"\D", "", cells.get("acno", "")) or None)
        ac_name = cells.get("assembly")
        district = (cells.get("district") or "").title() or district0
        name, service, _ = split_name(cells.get("name", ""))
        designation = None
        address = cells.get("address", "").strip('" ')
        mob, other = split_phones(cells.get("mobile", ""))
        mob2, land = split_phones(cells.get("office_phone", ""))
        mob += [m for m in mob2 if m not in mob]
        land = other + land
        if not ac_no or not name:
            return None
        area = f"{ac_no} - {ac_name}" if ac_name else ac_no
        rkey = ac_no
    else:
        address = None
        lead = " ".join(cells.get(k, "") for k in ("district", "name", "designation")).strip()
        lead = _esw.EMAIL.sub(" ", fix_emails(lead))
        lead = re.sub(r"(?<![\w-])(?:\+?91[\s-]?)?0?\d[\d\s-]{7,}\d(?![\w])", " ", lead)   # phones that fell into the text cells
        no, acn, rest = strip_ac(lead)
        if no:
            ac_no, ac_name = no, acn
        elif key not in ("ceo",):
            d = cells.get("district", "")
            if d and _esw.norm_ac(rest).startswith(_esw.norm_ac(d)) and not re.match(r"\d", d):
                rest = rest[len(d):].strip() if rest.lower().startswith(d.lower()) else rest
                if key == "dm":
                    district = d.title()
            for dn in filter(None, [district0]):
                if rest.lower().startswith(dn.lower() + " "):
                    rest = rest[len(dn):].strip()
        name, service, designation = split_name(rest)
        if not service:                         # no service tag: the cells as the PDF splits them
            name = _esw.clean(cells.get("name", "")) if not no else name
            designation = _esw.clean(cells.get("designation", ""))
            if no and not cells.get("designation"):
                name, designation = rest, ""
            if not designation:                 # an overflowing designation drawn in the next column
                designation = next((v for k, v in cells.items() if k not in ("district", "name") and
                                    re.search(r"officer|magistrate|\bB\.?D\.?O\b|\bS\.?D\.?O\b", v, re.I)), "")
                designation = _esw.EMAIL.sub(" ", re.sub(r"[\d/()-]{6,}", " ", designation)).strip()
        m = re.match(r"^\((SC|ST)\)\s*", name or "", re.I)
        if m:                                   # "(SC)" of the AC name printed in the name cell
            name = name[m.end():]
            if ac_name and "(" not in ac_name:
                ac_name += f" ({m.group(1).upper()})"
        if service and "(" in service and ")" not in service and (designation or "").startswith(")"):
            service, designation = service + ")", designation[1:].strip()
        if not name or not re.search(r"[A-Za-z]{2}", name):
            return None
        if key == "ro" and not ac_no:           # Kolkata: "RO, 162 - Chowrangee AC, AEO Kolkata North"
            m = re.search(r"\b(\d{1,3})\s*-\s*([A-Za-z][A-Za-z .()-]*?)\s+AC\b", designation or "")
            # South 24 Parganas: "RO 127-Gosaba(SC) & PD, DRDC"; Malda: "Returning Officer, 43-Habibpur (ST) A.C."
            m = m or re.search(r"\b(\d{1,3})\s*-\s*([A-Za-z][A-Za-z .]*?(?:\s*\((?:SC|ST)\))?)\s*(?=&|,|A\.?\s?C\b|$)",
                               designation or "")
            if m:
                ac_no, ac_name = m.group(1), m.group(2).strip()
        mob, land = split_phones(re.sub(r"(?<!\d)\d{1,3}\s*-\s*[A-Za-z]", " ", mail_free))
        if key == "ro" and ac_no:
            area, rkey = f"{ac_no} - {ac_name}", ac_no
        elif key == "ro":                       # Purulia, Alipurduar: the row names no AC; the officer is kept all the same
            area, rkey = district0, _esw.slug(name)
        elif key in ("bdo", "sdo"):
            area = area_of(key, designation, district0) or district0
            rkey = _esw.slug(area or name)
        elif key == "dm":
            area, rkey = district, _esw.slug(district or name)
        elif key == "ceo":
            area, rkey = "West Bengal", _esw.slug(designation + " " + name)
        else:
            area, rkey = district, _esw.slug(designation or name)
    phone = ", ".join(dict.fromkeys(mob + land))
    return {"_key": rkey, "dept": dept, "level": level, "area": area, "post": post or designation, "name": name,
            "service": service or None, "designation": designation or None, "phone": phone, "mobile": ", ".join(dict.fromkeys(mob)),
            "email": email, "address": address, "state": "WB", "district": district, "ac_no": ac_no, "ac_name": ac_name,
            "fax": cells.get("fax"), "source": url, "last_updated": as_on if key == "ero" else None, "page": page}


def fetch(p, get):
    if not _pdfcells.ensure_poppler():
        return [], [], "poppler (pdftotext) not available"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.status_code != 200 or r.content[:5] != b"%PDF-":
        return [], [], f"HTTP {r.status_code}, not a PDF"
    files = [_esw.keep(MODULE, p.get("file") or "x", r.content, "pdf")]
    recs = parse(r.content, p)
    return recs, files, "" if recs else "no rows"
