"""Haryana Police (India only: port 443 refuses connections from outside India). Two kinds of payload:
- default: statewide list haryanapolice.gov.in/static/DistrictTelephone (".aspx" redirects there), 413 rows: S. No. | Name of the
  Police Station | Telephone Nos. | Mobile No. (the SHO CUG) | E-mail. Header rows 'COMMISSIONERATE OF X' / 'DISTRICT X' /
  'POLICE DISTRICT X' give the district; 'WOMEN / TRAFFIC / CYBER CRIME POLICE STATIONS', 'POLICE STATIONS OF GRP.' and
  'Anti CORRUPTION BUREAU' open statewide sections. No names. Footer 'Updated on 01.04.2025'.
  Record id dept:police_hr:<district or section>:<station>.
- "kind": "sho": <district>.haryanapolice.gov.in/SHOContact.html, SHO name + rank per station (and police posts). Column
  order differs per district (Faridabad: SHO Name & Rank | Police Station | Office Tel. | Email | Mobile; Ambala, Hisar, Nuh:
  Name of Offices/Police Station/Police Post | Email | Name of Police Officers | Landline | Mobile; Jind: also MHC Contact and
  a police post table). Rows without a serial number (rowspan) are one cell short. Record id dept:police_hr:sho:<district>:<station>.
"""
import re

from bs4 import BeautifulSoup

from dforms import _civic
from dforms._police import ascii_digits, clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_hr"
URL = "https://haryanapolice.gov.in/static/DistrictTelephone"
DISTRICTS = ["ambala", "bhiwani", "charkhidadri", "dabwali", "faridabad", "fatehabad", "gurugram", "hansi", "hisar", "jhajjar",
             "jind", "kaithal", "karnal", "kurukshetra", "mahendergarh", "mewat", "palwal", "panchkula", "panipat", "rewari",
             "rohtak", "sirsa", "sonipat", "yamunanagar"]
STD = re.compile(r"(?<!\d)\(?(0\d{2,4})\)?(\s*-\s*|\s+|\)\s*)(\d{6,8})(?!\d)")
# the rank before the name: "SI Ram", "Insp.Parkash" (no blank after the dot), also after the post: "SHO INSP Manoj Kumar"
RANK = re.compile(r"^(?:SHO\b\s*[/,:-]?\s*)?((?:L/|P/|W/|LADY\s+|LADIES\s+)?(?:INSP(?:ECTOR)?|SUB\s+INSPECTOR|E?S\.?I|A\.?S\.?I|P\.?S\.?I|"
                  r"H\.?C|E/?ASI|E/?SI|DSP|CONST|CT)\.?)(?:(?<=\.)\s*|\s+)(?=\S)", re.I)
POST_FIRST = re.compile(r"^SHO\b\s*[/,:-]?\s*(?=\S)", re.I)    # "SHO Ram Kumar": the post, not part of the name


def ph(*cells):
    """phones(), but 'STD-number' with a separator stays a landline (_police.one_phone reads '01662-230011' right but
    '08372-278213' as a mobile)."""
    out = []
    for c in cells:
        c = ascii_digits(str(c or ""))
        pos = 0
        for m in list(STD.finditer(c)) + [None]:
            seg = c[pos:m.start()] if m else c[pos:]
            out += (phones(seg) or "").split(", ")
            if m:
                out.append(f"{m.group(1)}-{m.group(3)}")
                pos = m.end()
    out = [x for i, x in enumerate(out) if x and x not in out[:i]]
    return ", ".join(out) or None


def mail(s):
    return email(re.sub(r"\[\s*dash\s*\]", "-", s or "", flags=re.I))


def updated(html):
    m = re.search(r"Updated on\s*(\d{2})\.(\d{2})\.(\d{4})", html)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def parse_state(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    last = updated(html)
    recs, district, section = [], None, None
    for tr in soup.find_all("tr"):
        c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"], recursive=False)]
        filled = [x for x in c if x]
        if len(filled) == 1 and not filled[0][0].isdigit():
            h = filled[0]
            m = re.match(r"^(?:COMMISSIONERATE OF|POLICE DISTRICT|DISTRICT)\s+(.+)$", h, re.I)
            if m:
                district, section = m.group(1).title(), None
            elif re.search(r"POLICE STATIONS|BUREAU", h, re.I):
                district, section = None, h.title().rstrip(".")
            continue
        if len(c) != 5 or not re.match(r"^\d+\.?$", c[0] or "") or not c[1]:
            provenance.skip_row(tr, 'skip: len(c) != 5 or not re.match(r"^\\d+\\.?$", c[0] or "") or not c[1]')
            continue
        st = c[1]
        recs.append(rec(M, f"{slug(district or section or 'haryana')}:{slug(st)}", area=st, office_type=section, post="SHO (station CUG)",
                        phone=ph(c[3], c[2]), email=mail(c[4]), state="HR", district=district, last_updated=last, source=url,
                        src_pos=_civic.tr_pos(tr)))
    return uniq(recs)


def _col(head, *words):
    for i, h in enumerate(head):
        if any(w in h for w in words):
            return i
    return None


def parse_sho(html, district, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        if not trs:
            continue
        head = [clean(c.get_text(" ", strip=True)).lower() for c in trs[0].find_all(["th", "td"])]
        st_i = _col(head, "name of offices", "police station", "pp name")
        if st_i is None:
            continue
        name_i = _col(head, "name & rank", "name of police officers", "i/c name")
        tel_i = _col(head, "tel", "landline")
        mail_i = _col(head, "email", "e-mail")
        mob_i = _col(head, "mobile", "sho contact", "i/c contact")
        mhc_i = _col(head, "mhc")
        post_table = "pp name" in head[st_i]
        for tr in trs[1:]:
            c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
            if len(c) == len(head) - 1 and not re.match(r"^\d+\.?$", c[0] or ""):
                c = [""] + c
            if len(c) != len(head) or not c[st_i]:
                provenance.skip_row(tr, 'skip: len(c) != len(head) or not c[st_i]')
                continue
            cell = lambda i: c[i] if i is not None and c[i] not in ("-", "--") else None  # noqa: E731
            st, who = c[st_i], cell(name_i)
            rank = None
            if who:
                m = RANK.match(who)
                if m:
                    rank, who = clean(m.group(1)), clean(who[m.end():])
                else:
                    who = clean(POST_FIRST.sub("", who)) or None
            is_post = post_table or bool(re.match(r"^P\.?P\b", st, re.I))
            recs.append(rec(M, f"sho:{slug(district)}:{slug(st)}", area=st, office_type="police post" if is_post else "police station",
                            post="Officer in charge" if is_post else "SHO", name=who, rank=rank, phone=ph(cell(mob_i), cell(tel_i)),
                            mhc_mobile=ph(cell(mhc_i)), email=mail(cell(mail_i)), state="HR", district=district.title(), source=url,
                            src_pos=_civic.tr_pos(tr)))
    return uniq(recs)


def fetch(p, get):
    if p.get("kind") == "sho":
        d = p["district"]
        url = p.get("url") or f"https://{d}.haryanapolice.gov.in/SHOContact.html"
        r = get(url)
        if r is None:
            return [], [], "no answer"
        recs = parse_sho(r.text, p.get("district_name") or d, url)
        return recs, [gz(M, f"sho-{d}.html", r.content)], "" if recs else "no rows"
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse_state(r.text, url)
    return recs, [gz(M, "DistrictTelephone.html", r.content)], "" if recs else "no rows"
