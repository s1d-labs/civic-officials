"""Maharashtra: MSEDCL (Mahavitaran) field offices from the company's telephone diary, "Mahavitaran_Index_Diary-Updated-2026-V-07.pdf"
(www.mahadiscom.in/wp-content/uploads/2026/06/, 216 pages, June 2026). One queue item = the PDF. The archive holds copies
(2026-11-07 .. 11-12); www.mahadiscom.in answers from Germany (power_msedcl items run abroad).

The diary was made in InDesign. Each page has two text columns ("Office | Name" twice); the text flows down the left column,
then down the right column, then on to the next page. The PDF also carries an invisible OCR layer (font Arial, text render
mode 3) with errors ("AE (Recovery-Il)"); only the visible text (Helvetica) is read. Pieces in Devanagari or stray marks are
left out.
In each column, line by line:
- bold office heading: "LATUR ZONE" (after "CHIEF ENGINEER"), "BEED O&M CIRCLE", "Ambajogai O&M Dn.", "Kaij Sub Dn.",
  "Ardhapur S/Dn.", "<X> REGION" (level state). A heading can wrap over two or three lines. STD, CONTROL ROOM, PIN and address
  lines and "Email:" lines after it belong to that office. A phone on the heading line is the office phone.
- bold name, then the phone lines ("7875762111 (M)") and the designation (oblique): one named officer of that office.
- phone + text: a post of the office ("AE (Dist.)", "Dy. Ex. Engineer") or a field office below it ("Babhalgaon Unit",
  "Bori Unit", "Kolpa 33 KV Sub Stn.", "Ambulga sec JE"): the latter = level section (the section offices ("Unit") and the
  33/11 kV sub-stations of a sub-division), area = that text.
- a line without phone continues the text above it (wrapped words), or, when the text above is complete, is an office of its
  own without phone. A line with only a phone adds a phone to the entry above.
Only the distribution field offices are kept: zone, circle, division ("Dn."), sub-division ("Sub Dn.", "S/Dn.", "SDn."),
their posts and section offices, and the regions. The head office pages and the departments (infra plan, testing, civil,
IT, store, cells ...) are not kept; their lines are counted as skipped.
Parents: the last region, zone, circle, division and sub-division heading above the line in the text flow.
Some sub-division lists are printed twice (one with mobile and one with landline numbers): the same office (same parents,
area, post and name) is one record with the phones of both.
On the June 2026 file: 9,541 records; offices: 4 regions, 16 zones, 44 circles, 152 divisions, 659 sub-divisions;
5,229 section offices and sub-stations; the other records are posts and named officers of these offices.
Record id dept:power3_msedcl:<level>:<sub-division or office>:<area>:<post>:<name>.
"""
import html
import io
import re

import provenance
from dforms._power import Out, clean, email, phone, raw

METHOD = "pdf text (pypdf text positions, visible text layer only)"     # source trail (provenance.py)

MOD = "power3_msedcl"
URL = "https://www.mahadiscom.in/wp-content/uploads/2026/06/Mahavitaran_Index_Diary-Updated-2026-V-07.pdf"
HALF = 178.0                       # x of the gap between the two text columns (page width 354)
PHONE_W = 50.0                     # phone sub-column: x < column start + 50
PHONE_PIECE = re.compile(r"^[\d\s()/,+\-–.]*\d[\d\s()/,+\-–.]*(\((M|O|P|R)\))?$|^\((M|O|P|R)\)$")
LEVEL_RX = re.compile(r"(?i)(sub\.?\s*-?\s*dn|s\s*/\s*dn|\bs\.?\s*dn\b|sdn\b|sub\s*div|\bdn\b|\bdn\.|division|circle|\bzone\b|region)")
POST_START = re.compile(r"(?i)^(AE\b|A\.?\s*E\.?\b|JE\b|J\.?\s*E\b|Jr\b|Sr\b|Astt|Asstt|Asst|Add|Addl|Dy\b|Dy\.|Deputy|Ex\.|Ex\b|Exe|"
                        r"Executive|Manager|Maintenance|Lineman|Tech|Supdt|Suptdg|Chief|Programmer|System|Accounts|Law|Legal|"
                        r"Upper|Lower|Office|Vacant|Flying|Control|Asst\.)")
SECTION_RX = re.compile(r"(?i)(\bunit\b|\bsec\b|section|sub\s*\.?\s*/?\s*stn|s\s*/\s*stn|s/\s*s\b|sub-?station|\bf\.?\s*c\.?\s*c\b|"
                        r"profit\s*cent|\bk\.?\s*v\b\.?|\bccc\b)")
COMPLETE = re.compile(r"(?i)(stn\.?|s/s\.?|unit(\s*(no\.?)?\s*[-\d ivx]+)?|section|sec|centre|center|c\.c\.?|office|\d)\s*$")
ADDRESS = re.compile(r"(?i)(\d{3}|^std\b|std\s*[:\-]|fax|pin\b|control\s*room|road|marg|near|plot|building|bhavan|bhawan|complex|"
                     r"chowk|premises|floor|campus|colony|opp\.|behind|m\.?i\.?d\.?c|^at\b|post\b|tal\.|dist\.|mumbai\s*-|\bpbx\b|"
                     r"in\s*front|\bmill\b|\bpo\b|\bp\.o\.)")
START = re.compile(r"JT\.?\s*MANAGING\s*DIRECTOR.*REGION")          # upper case: the field part; the summary page is mixed case
# the field part ends at page 184 ("EXECUTIVE DIRECTOR / CORPORATE OFFICE, / SECURITY & ENFORCEMENT"); a zone has its own
# "SECURITY & ENFORCEMENT" cell, so that word alone does not end it
STOP = re.compile(r"(?i)^corporate\s*office|consumer\s*grievances|police|collectors")
NOT_FIELD = re.compile(r"(?i)infra|plan|testing|civil|store|project|vigilance|training|quality|\bit\b|account|legal|\bcell\b|"
                       r"construction|solar|software|recruit|medical|dept|department|committee|holiday|board|corporate|"
                       r"enforcement|purchase|material|renewable|ht\b|h\.t\.|meter|workshop|security|finance|billing\s*&|commercial")
TITLE = re.compile(r"(?i)^(\*?\s*)?(jt\.?\s*managing\s*director|chief\s*engineer|regional\s*director|suptdg\.?\s*engineer|"
                   r"superintending\s*engineer|executive\s*engineer)\s*[,\-]?\s*")
NAME_BAD = re.compile(r"(?i)engineer|manager|officer|\bae\b|\bje\b|maintenance|nsc|recovery|\bsec\b|wing|dist|team|unit|stn|kv\b|"
                      r"o\s*&\s*m|b\s*&\s*r|urban|rural|sub\b|division|circle|zone|region|office|email|std|control")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def _mul(a, b):
    return [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]


def page_lines(page):
    """[(column 0/1, y, [(x relative to the column, kind B/I/r, text)])] of one page, left column then right, top down."""
    ps = []

    def vt(text, cm, tm, fd, fs):
        f = str((fd or {}).get("/BaseFont", "") or "")
        t = html.unescape(" ".join((text or "").split()))
        if not t or "Arial" in f:              # the invisible OCR layer
            return
        m = _mul(tm, cm)
        ps.append((m[4], m[5], "B" if "Bold" in f else ("I" if "Oblique" in f or "Italic" in f else "r"), t))
    try:
        page.extract_text(visitor_text=vt)
    except Exception:
        return []
    out = []
    for col in (0, 1):
        hp = sorted([p for p in ps if (p[0] >= HALF) == bool(col)], key=lambda p: -p[1])
        x0 = HALF + 5 if col else 37.0
        lines = []
        for x, y, k, t in hp:
            if lines and abs(lines[-1][1] - y) <= 2.5:
                lines[-1][2].append((x - x0, k, t))
            else:
                lines.append([col, y, [(x - x0, k, t)]])
        for ln in lines:
            ln[2].sort()
            out.append((ln[0], round(ln[1], 1), ln[2]))
    return out


def classify(pieces):
    """(kind, text, phones, bold) of one line. kind: head, name, post, entry, cont, phone, email, info, noise."""
    pieces = [p for p in pieces if not DEVANAGARI.search(p[2]) and p[2].strip("*•· ")]
    if not pieces:
        return "noise", "", [], False
    ph = [t for x, k, t in pieces if x < PHONE_W and PHONE_PIECE.match(t)]
    tx = [(x, k, t) for x, k, t in pieces if not (x < PHONE_W and PHONE_PIECE.match(t))]
    text = " ".join(t for _, _, t in tx)
    bold = bool(tx) and all(k == "B" for _, k, _ in tx)
    obl = bool(tx) and any(k == "I" for _, k, _ in tx)
    phones = []
    for t in ph:                               # "(M)" belongs to the number before it
        if re.fullmatch(r"\((M|O|P|R)\)", t) and phones:
            phones[-1] += " " + t
        else:
            phones.append(t)
    if not text:
        return ("phone" if phones else "noise"), "", phones, False
    if "@" in text or re.match(r"(?i)e-?mail", text):
        return "email", text, phones, bold
    if re.match(r"(?i)(std|fax|pin|control\s*room|pbx)\b", text):
        return "info", text, phones, bold
    if obl:
        return "post", text, phones, bold
    if bold:
        if text.lower() in ("office name office name", "office name", "office", "name", "name residence"):
            return "noise", text, phones, bold
        if TITLE.match(text) and not phones:
            return "head", text, phones, bold          # "CHIEF ENGINEER" above "LATUR ZONE,"
        if POST_START.match(text):
            return ("name" if re.fullmatch(r"(?i)vacant", text) else "entry"), text, phones, bold
        if ADDRESS.search(text) and not LEVEL_RX.search(re.sub(r"(?i)control\s*room.*", "", text)):
            return "info", text, phones, bold
        if LEVEL_RX.search(text) or TITLE.match(text) or (len(re.sub(r"[^A-Za-z]", "", text)) > 4 and text.upper() == text):
            return "head", text, phones, bold
        if not re.search(r"\d", text) and len(text.split()) <= 5 and not NAME_BAD.search(text):
            return "name", text, phones, bold
        return "entry", text, phones, bold
    if not phones and re.search(r"(?i)(sub\.?\s*dn|s\s*/\s*dn)\.?\s*$", text) and not POST_START.match(text):
        return "head", text, phones, bold              # a sub-division heading printed in regular type
    return ("entry" if phones else "cont"), text, phones, bold


def stream(reader):
    """Every line of the PDF in text-flow order: (page, column, y, pieces, classify(pieces)). A heading wrapped over two or
    three bold lines ("Chhatrapati" / "Sambhajinagar Rural" / "Sub Dn.1") is joined into one "head" line first."""
    lines = []
    for pno, page in enumerate(reader.pages, 1):
        for col, y, pieces in page_lines(page):
            lines.append([pno, col, y, pieces, classify(pieces)])
    out, i = [], 0
    while i < len(lines):
        pno, col, y, pieces, c = lines[i]
        merged = False
        if c[3] and c[0] in ("name", "head", "entry") and not LEVEL_RX.search(c[1]) and not POST_START.match(c[1]):
            for n in (1, 2):
                nxt = lines[i + 1:i + 1 + n]
                if len(nxt) < n or any(l[0] != pno or l[1] != col or not l[4][3] or l[4][0] in ("email", "info")
                                       or POST_START.match(l[4][1]) for l in nxt):
                    break
                if any(abs(a[2] - b[2]) > 10.5 for a, b in zip([lines[i]] + nxt, nxt)):
                    break
                if LEVEL_RX.search(nxt[-1][4][1]):
                    joined = " ".join([c[1]] + [l[4][1] for l in nxt])
                    ph = c[2] + [p for l in nxt for p in l[4][2]]
                    out.append((pno, col, y, pieces + [p for l in nxt for p in l[3]], ("head", joined, ph, True)))
                    provenance.used(n)          # the lines joined into the heading (the heading line counts itself)
                    i += 1 + n
                    merged = True
                    break
        if not merged:
            out.append(tuple(lines[i]))
            i += 1
    return out


def _continues(entry, text):
    """Does a line without phone continue the entry above (wrapped words), or is it an office / post of its own?"""
    if POST_START.match(text):
        return False
    if entry["kind"] == "post":
        return True
    if text[:1].islower() or re.match(r"(?i)^(\(|&|/|-|sub\b|s\s*/|stn|33|22|11|kv|k\.v|no\.|\d)", text):
        return True
    return not COMPLETE.search(entry["text"]) or bool(re.search(r"[&,/(-]\s*$", entry["text"]))


def level_of(head):
    """Most specific first: "Kolhapur O & M East Zone Sub Dn" is a sub-division."""
    h = TITLE.sub("", head)
    if re.search(r"(?i)(sub\.?\s*-?\s*dn|s\s*/\s*dn|\bs\.?\s*dn\b|sdn\b|sub\s*div)", h):
        return "subdivision"
    if re.search(r"(?i)(\bdn\b|\bdn\.|division)", h):
        return "division"
    if re.search(r"(?i)circle", h):
        return "circle"
    if re.search(r"(?i)\bzone\b", h):
        return "zone"
    if re.search(r"(?i)region", h):
        return "state"
    return None


def parse(content, url=URL):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    out = Out(MOD, "MH", url, discom="MSEDCL", last_updated="2026-06-10")
    recs = {}                     # key -> record fields (merged), in order
    order = []
    par = {"state": None, "zone": None, "circle": None, "division": None, "subdivision": None}
    block = None                  # {"level", "area", "field", "email", "address", "phones", "key", "head_open"}
    officer = None                # the named officer being read
    entry = None                  # the last post / office entry
    name_open = False

    def rec(key, **f):
        if key in recs:
            r = recs[key]
            for ph in (f.get("phones") or []):
                if ph not in r["phones"]:
                    r["phones"].append(ph)
            for k in ("name", "post", "email", "address"):
                if f.get(k) and not r.get(k):
                    r[k] = f[k]
            r["n"] += 1
            return r
        r = {"phones": list(f.pop("phones", None) or []), "n": 1, **f}
        recs[key] = r
        order.append(key)
        return r

    def parents_for(level):
        up = {"state": [], "zone": ["state"], "circle": ["state", "zone"], "division": ["state", "zone", "circle"],
              "subdivision": ["state", "zone", "circle", "division"],
              "section": ["state", "zone", "circle", "division", "subdivision"]}[level]
        p = {("region" if k == "state" else k): par[k] for k in up if par.get(k)}
        return p

    def office_key(level, area):
        chain = [par[k] or "" for k in ("zone", "circle", "division", "subdivision")]
        return "|".join([level] + chain + [area])

    part = "before"              # before the field part, in it, after it
    last_kind = None
    lines = stream(reader)
    toc = {ln[0] for ln in lines if re.search(r"\.{6,}\s*\d+\s*$", ln[4][1])}       # contents pages ("PUNE REGION ....131")
    for pno, col, y, pieces, (kind, text, phones, bold) in lines:
        pos = {"page": pno, "column": col + 1, "y": y, "line_text": " | ".join(t for _, _, t in pieces)}
        if kind == "head" and part == "before" and START.search(text) and pno not in toc:
            part = "field"
        elif kind == "head" and part == "field" and STOP.search(text):
            part = "after"
        if part != "field":
            provenance.skipped("header" if kind == "noise" else ("head office pages" if part == "before"
                                                                 else "pages after the field offices"))
            continue
        prev_kind, last_kind = last_kind, kind
        if kind == "noise":
            last_kind = prev_kind
            provenance.skipped("header" if text else "empty")
            continue
        if kind == "head":
            if block and prev_kind == "head" and not LEVEL_RX.search(block["raw"]):
                block["raw"] += " " + text           # "CHIEF ENGINEER" + "LATUR ZONE,"; "Garkheda B&R Urban" + "Sub Dn."
                if phones:
                    block["phones"] += phones
                _settle(block, par, rec, office_key, parents_for)
                if block["field"]:
                    provenance.used()
                else:
                    provenance.skipped("not a field office")
                continue
            if block and prev_kind in ("head", "info", "email") and re.sub(r"\W", "", text.lower()) in re.sub(r"\W", "", block["raw"].lower()):
                provenance.skipped("heading printed twice")
                continue
            block = {"raw": text, "phones": list(phones), "head_open": True, "pos": pos, "field": False}
            officer = entry = None
            name_open = False
            _settle(block, par, rec, office_key, parents_for)
            if block["field"]:
                provenance.used()
            else:
                provenance.skipped("not a field office")
            continue
        if block is None or not block["field"]:
            provenance.skipped("not a field office" if block else "head office pages")
            continue
        if kind == "info" or (kind == "email" and block.get("head_open")):
            block["info"] = True
            r = recs[block["key"]]
            if kind == "email":
                m = email(text)
                if m:
                    r["email"] = ", ".join(x for x in (r.get("email"), m) if x)
                elif re.search(r"[A-Za-z0-9]\.(in|com)\b", text) and r.get("email") and r["email"].endswith("/"):
                    r["email"] += text
            else:
                if text not in (r.get("address") or ""):
                    r["address"] = " ".join(x for x in (r.get("address"), text) if x)
                tel = re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", text)
                for t in tel:
                    if t not in r["phones"]:
                        r["phones"].append(t)
            for ph in phones:
                if ph not in r["phones"]:
                    r["phones"].append(ph)
            provenance.used()
            continue
        if kind == "email":
            # a bare address continuing the line above ("mahadiscom.in", "eejalna1@gmail.com")
            r = recs[block["key"]]
            m = email(text)
            if m and m not in (r.get("email") or ""):
                r["email"] = ", ".join(x for x in (r.get("email"), m) if x)
            provenance.used()
            continue
        block["head_open"] = False
        lvl, area = block["level"], block["area"]
        if kind == "name":
            if name_open and officer is not None and not officer["phones"] and not officer.get("post"):
                officer["name"] = f"{officer['name']} {text}".strip()        # a name wrapped onto a second line
            else:
                officer = rec(f"{office_key(lvl, area)}|officer|{text}|{pno}:{y}", level=lvl, area=area, name=clean(text),
                              parents=parents_for(lvl), src_pos=pos, phones=phones)
                entry = None
            name_open = True
            provenance.used()
            continue
        name_open = False
        if officer is not None and (kind == "post" or (kind == "entry" and prev_kind == "name" and not officer.get("post"))):
            # the designation under a name, oblique or (some zones) regular type: "7875762002 (M) | (Admn. & Safety)"
            officer["post"] = " ".join(x for x in (officer.get("post"), text) if x)
            for ph in phones:
                if ph not in officer["phones"]:
                    officer["phones"].append(ph)
            provenance.used()
            continue
        if kind == "phone":
            tgt = entry if entry is not None else officer
            if tgt is None:
                tgt = recs[block["key"]]
            for ph in phones:
                if ph not in tgt["phones"]:
                    tgt["phones"].append(ph)
            provenance.used()
            continue
        if kind == "cont" and entry is not None and _continues(entry, text):
            entry["text"] = f"{entry['text']} {text}"
            entry["pos"]["line_text"] += "\n" + pos["line_text"]
            provenance.used()
            continue
        if kind in ("entry", "cont", "post"):
            officer = None
            ek = "office" if SECTION_RX.search(text) and not POST_START.match(text) else "post"
            entry = {"kind": ek, "text": text, "phones": list(phones), "pos": pos, "lvl": lvl, "area": area,
                     "okey": office_key(lvl, area), "parents": parents_for(lvl), "sub": par.get("subdivision")}
            block.setdefault("entries", []).append(entry)
            _entry_rec(entry, rec, par)
            provenance.used()
            continue
        provenance.skipped(f"line kind {kind}")
    # entries were registered as they came; their text may have grown by continuation lines: build the records now
    for key in order:
        r = recs[key]
        if r.get("entry"):
            e = r["entry"]
            if e["kind"] == "office":
                r["area"] = clean(e["text"])
            else:
                r["post"] = clean(e["text"])
            for ph in e["phones"]:
                if ph not in r["phones"]:
                    r["phones"].append(ph)
    final = {}
    for key in order:
        r = recs[key]
        if r.get("entry"):
            e = r["entry"]
            k2 = (r["level"], tuple(sorted((r.get("parents") or {}).items())), r.get("area"), r.get("post"))
            if k2 in final:                                   # a list printed twice: one office, the phones of both
                f = final[k2]
                for ph in r["phones"]:
                    if ph not in f["phones"]:
                        f["phones"].append(ph)
                continue
            final[k2] = r
        else:
            final[("o", key)] = r
    for k2, r in final.items():
        if not r.get("area"):
            provenance.skipped("no office name")
            continue
        sub = (r.get("parents") or {}).get("subdivision") or (r.get("parents") or {}).get("division") or ""
        key = f"{r['level']}:{sub}:{r['area']}:{r.get('post') or ''}:{r.get('name') or ''}"
        out.add(key, r["level"], r["area"], post=r.get("post"), name=r.get("name"), phone_=phone(*r["phones"]) if r["phones"] else None,
                email_=r.get("email"), address=r.get("address"), parents=r.get("parents"), src_pos=r.get("src_pos"),
                method="pdf text")
    return out.recs


def _settle(block, par, rec, office_key, parents_for):
    """Level, area and record of a (possibly wrapped) heading; updates the parents chain."""
    raw_ = " ".join(block["raw"].split())
    area = clean(TITLE.sub("", raw_).strip(" ,.-*")) or raw_
    lvl = level_of(raw_)
    block["field"] = bool(lvl) and not NOT_FIELD.search(raw_)
    if not block["field"]:
        block["level"], block["area"] = lvl, area
        return
    order = ["state", "zone", "circle", "division", "subdivision"]
    for k in order[order.index(lvl):]:
        par[k] = None
    block["level"], block["area"] = lvl, area
    block["key"] = office_key(lvl, area) + "|office"
    r = rec(block["key"], level=lvl, area=area, parents=parents_for(lvl), src_pos=block["pos"], phones=block["phones"])
    par[lvl] = area
    r["parents"] = parents_for(lvl)
    r["phones"] = list(dict.fromkeys(r["phones"] + block["phones"]))


def _entry_rec(e, rec, par):
    if e["kind"] == "office":
        p = dict(e["parents"])
        if e["lvl"] != "state":
            p[e["lvl"]] = e["area"]
        r = rec(f"{e['okey']}|entry|{id(e)}", level="section", area=e["text"], parents=p, src_pos=e["pos"], phones=[])
    else:
        r = rec(f"{e['okey']}|entry|{id(e)}", level=e["lvl"], area=e["area"], post=e["text"], parents=e["parents"],
                src_pos=e["pos"], phones=[])
    r["entry"] = e


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MOD, "Mahavitaran_Index_Diary", r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    recs = parse(r.content, url)
    return recs, files, "" if recs else "no rows"
