"""Uttar Pradesh Home Guards: "Contact Details of UP HG Officials" (homeguard.up.gov.in/Downloads/ContactDetailsofUPHGOfficials.pdf,
4 pages, Hindi, linked from the department's home page; no login, no date). One PDF, one queue item.
Rows: serial | unit (इकाई) | mobile | e-mail, grouped by division (मण्डल). About 110 rows: Commandant General and Senior Staff
Officer (headquarters, Lucknow), Deputy Commandants General, Divisional Commandants (18 divisions), Divisional Training Centre
commandants, and one District Commandant per district (75). The PDF names posts, not people.
The PDF's Hindi text does not extract cleanly (its font maps some letters wrongly: "नजला कमाण् ड" for "जिला कमाण्डेंट"), so the
reader takes the post and the district from the official e-mail address, which follows one pattern: cmdhg<xx>-up@nic.in (District
Commandant), dchg<xx>-up@nic.in (Divisional Commandant), dtc-hg.<xx>@up.gov.in (Divisional Training Centre), dycg*-hg.<xx>@up.gov.in
(Deputy Commandant General), cghg-up (Commandant General), ssohg-up (Senior Staff Officer). <xx> -> district: CODES (from this PDF).
Record: dept police (the Home Guards organisation is under the Home department), layer emerg_hg, level state / division /
district, area (district or division headquarters), post, phone (mobile), email, state UP, source. Record ids:
dept:emerg_hg_up:<e-mail local part>.
"""
import re

from dforms import _emerg
from dforms._pdftext import layout_pages
from provenance import line_pos
import provenance

METHOD = "pdf text (pdftotext -layout, else pypdf layout): mobile + e-mail line; post and area from the e-mail name"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_hg_up"
URL = "https://homeguard.up.gov.in/Downloads/ContactDetailsofUPHGOfficials.pdf"
CODES = {
    "ag": "Agra", "ah": "Prayagraj", "al": "Aligarh", "am": "Amethi", "an": "Ambedkar Nagar", "au": "Auraiya", "az": "Azamgarh",
    "bb": "Bara Banki", "bd": "Budaun", "bg": "Baghpat", "bh": "Bahraich", "bi": "Bijnor", "bl": "Ballia", "bn": "Banda",
    "bp": "Balrampur", "br": "Bareilly", "bs": "Basti", "bu": "Bulandshahr", "cd": "Chandauli", "ct": "Chitrakoot", "de": "Deoria",
    "et": "Etah", "ew": "Etawah", "fi": "Firozabad", "fr": "Farrukhabad", "ft": "Fatehpur", "fz": "Ayodhya",
    "gb": "Gautam Buddha Nagar", "go": "Gonda", "gp": "Ghazipur", "gr": "Gorakhpur", "gz": "Ghaziabad", "hm": "Hamirpur",
    "hp": "Hapur", "hr": "Hardoi", "ht": "Hathras", "jh": "Jhansi", "jl": "Jalaun", "jp": "Amroha", "ju": "Jaunpur",
    "kd": "Kanpur Dehat", "kg": "Kasganj", "kj": "Kannauj", "kn": "Kanpur Nagar", "ks": "Kaushambi", "ku": "Kushinagar",
    "la": "Lalitpur", "lk": "Kheri", "lu": "Lucknow", "mb": "Mau", "me": "Meerut", "mg": "Mahrajganj", "mh": "Mahoba",
    "mi": "Mirzapur", "mo": "Moradabad", "mp": "Mainpuri", "mt": "Mathura", "mu": "Muzaffarnagar", "pi": "Pilibhit",
    "pr": "Pratapgarh", "ra": "Rampur", "rb": "Rae Bareli", "sa": "Saharanpur", "sb": "Sambhal", "si": "Sitapur",
    "sj": "Shahjahanpur", "sk": "Sant Kabir Nagar", "sm": "Shamli", "sn": "Siddharthnagar", "so": "Sonbhadra", "sr": "Bhadohi",
    "su": "Sultanpur", "sv": "Shrawasti", "un": "Unnao", "va": "Varanasi",
}
DIVISIONS = {"dp": "Devipatan", "kn": "Kanpur", "fz": "Ayodhya"}  # division names that differ from the district of the same code
TRAINING = {"pr": "Prayagraj"}  # dtc-hg.pr / dycg-hg.pr: Prayagraj (cmdhgpr is Pratapgarh)
LINE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)\s+([A-Za-z0-9._-]+(?:@[A-Za-z0-9.-]+)?)")


def unit(local):
    """(post, level, area code) from the e-mail local part ('cmdhglu-up', 'dtc-hg.lu', 'dycgcti-hg.lu' ...)."""
    m = re.fullmatch(r"cmdhg([a-z]{2})-up", local)
    if m:
        return "District Commandant, Home Guards", "district", m.group(1)
    m = re.fullmatch(r"dchg([a-z]{2})-up", local)
    if m:
        return "Divisional Commandant, Home Guards", "division", m.group(1)
    m = re.fullmatch(r"dtc-hg\.([a-z]{2})", local)
    if m:
        return "Divisional Commandant, Divisional Training Centre, Home Guards", "division", m.group(1)
    m = re.fullmatch(r"dycg(cti)?-hg\.([a-z]{2})", local)
    if m:
        return ("Deputy Commandant General, Central Training Institute, Home Guards" if m.group(1)
                else "Deputy Commandant General, Home Guards"), "division", m.group(2)
    if local == "cghg-up":
        return "Commandant General, Home Guards", "state", "lu"
    if local == "ssohg-up":
        return "Senior Staff Officer, Home Guards Headquarters", "state", "lu"
    return None


def records(pages, url=URL, engine=None):
    lines = [ln for pg in pages for ln in pg.split("\n")]
    at = [(pn, k) for pn, pg in enumerate(pages, 1) for k, _ in enumerate(pg.split("\n"), 1)]
    recs, seen = [], set()
    for i, ln in enumerate(lines):
        m = LINE.search(ln)
        if not m:
            provenance.skip_line(ln, 'skip: not m')
            continue
        mobile, mail = m.group(1), m.group(2)
        if "@" not in mail and i + 1 < len(lines):
            nxt = re.match(r"\s*(@[A-Za-z0-9.-]+)", lines[i + 1].strip() and lines[i + 1].split()[-1] or "")
            mail = mail + nxt.group(1) if nxt else mail
        local = mail.split("@")[0].lower()
        u = unit(local)
        if not u:
            provenance.skip_line(ln, 'skip: not u')
            continue
        post, level, code = u
        if local.startswith(("dtc", "dycg")) and code in TRAINING:
            code_name = TRAINING[code]
        else:
            code_name = DIVISIONS.get(code, CODES.get(code, "")) if level == "division" else CODES.get(code, "")
        area = code_name
        district = code_name if code_name in CODES.values() else None
        key = _emerg.unique(local, seen)
        recs.append(_emerg.record(
            MODULE, key, "hg", dept="police", level=level, area=area or "Uttar Pradesh", post=post, phone=mobile,
            email=mail.lower() if "@" in mail else "", district=district if level != "state" else None, state="UP",
            office_id=key, source=url, src_pos=line_pos(*at[i], ln),
            **({"method": f"pdf text ({engine}): mobile + e-mail line; post and area from the e-mail name"} if engine else {})))
    return recs


def items(get=None):
    return _emerg.seed(MODULE)


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a PDF"
    pages, engine = layout_pages(r.content)
    recs = records(pages, url, _emerg.ENGINE.get(engine))
    return recs, [_emerg.keep(MODULE, "contact-details-uphg", r.content, ext="pdf")], "" if recs else "no rows"
