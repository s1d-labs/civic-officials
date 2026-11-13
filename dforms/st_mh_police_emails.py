"""Maharashtra Police: the official e-mail lists of the DGP office, https://www.mahapolice.gov.in/contact-and-emails/ (7 PDFs
under /uploads/contact_email/, text PDFs of 1-2 pages, 16-45 KB, Nitro Pro; checked 2026-11-13 from dev-vps-3; the archive copies
of 2026-11-05 are broken 7.9 KB files, so the items fetch the live file):
- 68668baee3e1e673247df6ca88ac5e67.pdf "Director General of Police office e-mail IDs" (DGP, ADGs and IGs of the HQ, Mumbai)
- igcontact3.pdf (range IGs: Amravati, Aurangabad, Kolhapur, Konkan, Nagpur, Nanded, Nashik; DIG Gadchiroli)
- opcontact5.pdf (other units: ACB, SID, CID crime, wireless, railways, SRPF, traffic, MPA, cyber, MT ...)
- spcontact4.pdf, dd35bfea..., 743f2f0a..., aa6513ff... (SP / CP units and the rest; same two columns, not opened here)
Columns: Sr. No. | DESIGNATION | EMAIL-ID. A row may run over several lines (designation or extra e-mails with notes in
brackets). The lists give posts and e-mails, no names, no phones.
Records (dforms/_state.py): a "RANGE" post -> level division (division "<Name> Range", districts from st_div_mh.json
"police_ranges"); "SP" / "SUPERINTENDENT" / "COMMISSIONER OF POLICE" posts naming a district or city -> level district;
everything else -> level state. dept police, body_kind police. Route: answers from Mumbai (direct); abroad not checked.
One queue item = one PDF (1 GET). Record ids: dept:st_mh_police_emails:<file stem>:<sr no> (second and later sections: <file stem>:s<k>:<sr no>).
"""
import json
import re

import provenance
from dforms import _esw, _field, _state

METHOD = "pdf text (pdftotext -layout, else pypdf layout)"

M = "st_mh_police_emails"
BASE = "https://www.mahapolice.gov.in/uploads/contact_email/"
FILES = ["68668baee3e1e673247df6ca88ac5e67.pdf", "igcontact3.pdf", "opcontact5.pdf", "spcontact4.pdf",
         "dd35bfea79f9781e930f648165ed7a08.pdf", "743f2f0a6891748aca453b5432a98ce2.pdf", "aa6513ff8e34502a6614651b36920f5e.pdf"]
ROW = re.compile(r"^\s{0,12}(\d{1,3})\.?\s{1,}(.*)$")
_RANGES = None


def police_ranges():
    global _RANGES
    if _RANGES is None:
        _RANGES = json.loads((_state.HERE / "st_div_mh.json").read_text()).get("police_ranges", {})
    return _RANGES


def rows(text):
    """[{sn, designation, email, notes, section, sec_no, pos}] of the layout text (pages split by form feeds). A designation that
    runs over two lines often starts on the line ABOVE its numbered line (the number and the e-mail are centred): a text line
    without number and e-mail is held and goes to the next numbered row; held text that no numbered row takes goes to the row
    above. A heading line ("DGP'S OFFICE DESK E-MAIL ID'S") starts a new section (the numbers start again)."""
    out, cur, held, section, sec_no = [], None, [], "", 1
    for pg, ptext in enumerate(text.split("\f"), 1):
        for n, raw in enumerate(ptext.split("\n"), 1):
            if not raw.strip() or re.search(r"(?i)designation\s+e-?mail|desk name\s+e-?mail|^\s*sr\.?\s*(no\.?)?\s*$|^\s*no\.\s*$", raw):
                provenance.skip_line(raw, 'skip: not raw.strip() or re.search(r"(?i)designation\\s+e-?mail|desk name\\...')
                continue
            em = _esw.emails(raw)
            rest = _esw.clean(_esw.EMAIL.sub(" ", _esw.deob(raw)))
            if not em and re.search(r"(?i)e-?m(ai|ia)l[- ]?id", raw):
                if out:
                    sec_no += 1
                section, held = rest, []
                continue
            m = ROW.match(raw)
            if m and (em or re.search(r"[A-Za-z]{2,}", m.group(2))):
                desig = _esw.clean(" ".join(held + [_esw.EMAIL.sub(" ", m.group(2))]))
                cur = {"sn": m.group(1), "designation": re.sub(r"\s*\((for [^)]*)\)?\s*$", "", desig, flags=re.I).strip(),
                       "email": em, "notes": [], "section": section, "sec_no": sec_no,
                       "pos": provenance.line_pos(pg, n, raw)}
                held = []
                out.append(cur)
                continue
            if cur is None:
                provenance.skip_line(raw, 'skip: cur is None')
                continue
            if em:
                if held:
                    cur["designation"] = _esw.clean(cur["designation"] + " " + " ".join(held))
                    held = []
                cur["email"] = ", ".join(dict.fromkeys([e for e in (cur["email"] + ", " + em).split(", ") if e]))
                if rest:
                    cur["notes"].append(rest)
            elif rest.startswith("(") or re.search(r"(?i)\bfor\b", rest):
                cur["notes"].append(rest)
            elif re.search(r"[A-Za-z]", rest):
                held.append(rest)
        if held and cur is not None:
            cur["designation"] = _esw.clean(cur["designation"] + " " + " ".join(held))
            held = []
    return out


def _range(desig):
    m = re.search(r"(?i)\b([A-Z][A-Za-z]+)\s+RANGE\b", desig)
    if not m:
        return "", []
    name = m.group(1).title() + " Range"
    return name, police_ranges().get(name, [])


def parse(text, url):
    stem = url.rsplit("/", 1)[-1].rsplit(".", 1)[0][:12]
    from dforms.st_mh_divcom import MH, district_in
    recs = []
    for r in rows(text):
        d = r["designation"]
        rng, codes = _range(d)
        lv, code = "state", ""
        if rng:
            lv = "division"
        elif re.search(r"(?i)^(SP|S\.P\.|SUPDT|SUPERINTENDENT OF POLICE|CP|COMMISSIONER OF POLICE)\b", d):
            code = district_in(d, [])
            left = re.sub(r"(?i)^(SP|S\.P\.|SUPDT\.?|SUPERINTENDENT OF POLICE|CP|COMMISSIONER OF POLICE)\b|\b(CITY|RURAL|"
                          r"COMMISSIONERATE)\b|[^A-Za-z]", " ", d)
            left = re.sub(r"[^a-z]", "", left.lower()).replace(re.sub(r"[^a-z]", "", MH.get(code, "-").lower()), "", 1)
            lv = "district" if code and not left else "state"     # "SP, DG CONTROL ROOM, MUMBAI": a HQ post, not the district
            code = code if lv == "district" else ""
        sid = f"{stem}:{r['sn']}" if r["sec_no"] == 1 else f"{stem}:s{r['sec_no']}:{r['sn']}"
        recs.append(_state.rec(M, sid, state="MH", level=lv, post=d, division=rng, districts=codes if rng else [],
                               district=MH.get(code, ""), district_code=code, email=r["email"], body="Maharashtra Police",
                               body_kind="police", dept="police", department="Home Department (Police)",
                               notes=" ".join(r["notes"]) or None, section=r["section"] or None, list_no=r["sn"], src_url=url, src_pos=r["pos"]))
    return recs


def items(get=None):
    return [{"key": f"{M}:{f.rsplit('.', 1)[0][:12]}", "payload": {"reader": M, "url": BASE + f, "state": "MH",
                                                                   "india_only": True, "route": "direct"}} for f in FILES]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a pdf"
    stem = p["url"].rsplit("/", 1)[-1]
    recs = parse(_field.pdf_text(r.content), p["url"])
    return recs, [(f"depts/{M}/{stem}", r.content, "application/pdf")], "" if recs else "no rows"
