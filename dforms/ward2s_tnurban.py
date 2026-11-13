"""Tamil Nadu city corporations on the state's urban local body WordPress platform (www.tnurbantree.tn.gov.in/<city>/): the
officer list on each corporation's "Office Staffs" / "Officers Details" page, /<city>/office-staffs/ (Tambaram: /tambaram/officers-detail/,
"Public Grievances and Officers who can be approached"). Madurai has its own reader
(ward2s_madurai: its page gives the ward of every engineer and inspector). The pages show no "last updated" date.
Samples: archive.s1d.me copies of 2026-11-11 (Tirunelveli, Hosur, Karaikudi, Kancheepuram) and one request from India (vpsin) on
2026-11-11 (Vellore, Dindigul, Tambaram; Tambaram is also in the archive, saved 2026-11-11). The platform answers slowly or not at all from Germany (time-outs on 2026-11-11): India only.
Each page is one HTML table; its form differs by city:
  tirunelveli   Sl. No. | Sanctioned Post Name | Name of the Persons currently employed (the state's 2025-26 staff template;
                the whole staff: Assistant Commissioners (Ward), revenue inspectors, tax collectors, sanitary officers and
                inspectors, conservancy inspectors, medical officers, engineers, town planning).
  hosur         Sl.no | Name | Designation | MOBILE, with section rows (General Administration, Revenue, Public Health,
                Engineering, Town Planning).
  karaikudi     Sl.No | HOD's | Name | Office | Mobile No. (one row per post; several names and phones in one cell).
  dindigul      Sl. No | Name of the Officer | Designation | Contact Number | Entrusted Responsibility (heads of sections and
                the assistant revenue officers).
  kancheepuram  Designation | Mobile No. (posts and phones, no names).
  vellore       Designation | CUG Number, in blocks "Main Office - Officers" and "Zone N - Officers" (zone AEE / AE / JE,
                assistant revenue officer, special revenue inspector, sanitary officer and inspector, fitter, sanitation
                supervisors; no names). The page does not give the wards of each zone.
  tambaram      Sl.No | Details of Municipal Services | Section | Officers | Ward nos | Contact Numbers: the zone Executive
                Engineers, Sanitary Officers and Assistant Revenue Officers of the 5 zones with the wards of each zone (one row per
                service; the rows of one officer become one record with the extra key "services"). "Jan-70" in the ward cell is
                "1-70" turned into a date by the spreadsheet: all 70 wards.
Except Tambaram, none of these pages ties a post to a ward. So the records are level "body" (area = the corporation: body-wide lists with field
posts: engineers, sanitary inspectors, revenue inspectors, tax collectors), and level "zone" for Vellore's zone blocks
(area "Zone N", no wards) and Tambaram's zone officers (level "zone", wards from the page). Clerical and support posts (junior assistants, assistants, typists, record clerks, drivers, office
assistants, watchmen, nurses, pharmacists) are left out. "Vacant" posts are kept with vacant = true.
Checked and left out (2026-11-11, one request each from India): Kumbakonam (general section clerks only), Karur (Tamil text list
of general section clerks, no table), Cuddalore (5 heads of sections, no field posts), Thoothukudi (links to section pages
that time out), Thanjavur and Erode (the page holds a wrong PDF link / no link), Sivakasi (empty page), Nagercoil and Pudukkottai
(404, and no staff page in the menu), Tiruppur and Avadi (time-out from India too).
One queue item = one city page. Record ids: dept:ward2s_tnurban:<city>:<zone or body>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_tnurban"
STATE = "TN"
BASE = "https://www.tnurbantree.tn.gov.in"
# city slug -> (body, LGD code, district)
BODIES = {
    "tirunelveli": ("Tirunelveli City Municipal Corporation", "253011", "Tirunelveli"),
    "vellore": ("Vellore City Municipal Corporation", "252381", "Vellore"),
    "dindigul": ("Dindigul City Municipal Corporation", "252707", "Dindigul"),
    "kancheepuram": ("Kancheepuram City Municipal Corporation", "252336", "Kancheepuram"),
    "hosur": ("Hosur City Municipal Corporation", "252399", "Krishnagiri"),
    "karaikudi": ("Karaikudi City Municipal Corporation", "252863", "Sivaganga"),
    "tambaram": ("Tambaram City Municipal Corporation", "252319", "Chengalpattu"),
}
PAGES = {"tambaram": "officers-detail"}  # the page name where it is not office-staffs
SKIP = re.compile(r"(?i)^(junior\s+assistants?|assistants?|steno[\s-]*typist|typist|record\s*(clerks?|assistants?)(\s*/\s*record\s*clerk)?|"
                  r"drivers?|office\s*assistants?|watchm[ae]n|staff\s*nurses?|pharmacist|shn|uhn|anm|manager|data\s*entry.*|"
                  r"cashier|computer\s*operator|assistant\s*programmer|skilled\s*ass(is)?t\.?\s*grade.*)$")
ABBR = (  # Vellore writes abbreviations: expand them, keep the abbreviation in brackets
    (r"^AEE\b", "Assistant Executive Engineer (AEE)"), (r"^AE\b", "Assistant Engineer (AE)"), (r"^JE\b", "Junior Engineer (JE)"),
    (r"^ARO\b", "Assistant Revenue Officer (ARO)"), (r"^E\.E\.\s*", "Executive Engineer "), (r"^E\.E\.\(UGS\)", "Executive Engineer (UGSS)"),
)


def items(get=None):
    return [{"key": f"{MODULE}-{c}", "payload": {"reader": MODULE, "url": f"{BASE}/{c}/{PAGES.get(c, 'office-staffs')}/", "state": STATE,
                                                 "city": c, "india_only": True}} for c in BODIES]


def city_of(p):
    c = p.get("city") or re.search(r"tnurbantree\.tn\.gov\.in/([^/]+)/", p["url"]).group(1)
    return c


def _heading(row):
    cells = [c for c in row if c]
    return cells[0] if cells and len(set(cells)) == 1 and not re.fullmatch(r"[\d\s,/|+-]+", cells[0]) else None


def _post_cell(post):
    return re.sub(r"\s*\|\s*", " ", post)


def _cols(head):
    low = [c.lower() for c in head]

    def find(*words):
        for w in words:  # the first word that any heading holds wins
            for i, c in enumerate(low):
                if w in c:
                    return i
        return None
    post = find("designation", "sanctioned post", "hod", "officers")
    name = find("name of the person", "name of the officer", "name")
    if name == post:
        name = None
    phone = find("mobile", "contact", "cug", "phone")
    return post, name, phone, find("ward"), find("services"), find("section")


def _wards(txt):
    """Ward numbers of a cell; "Jan-70" is "1-70" turned into a date by the spreadsheet the page was made from (all wards)."""
    m = re.fullmatch(r"(?i)\s*[a-z]{3}-(\d{1,3})\s*", txt or "")
    if m:
        return [str(w) for w in range(1, int(m.group(1)) + 1)]
    return _ward.wards_of(txt or "")


def _post(p):
    p = _esw.clean(p).strip(" ,-")
    if p.isupper() and len(p) > 4:
        p = p.title()
    for rx, full in ABBR:
        if re.search(rx, p):
            p = re.sub(rx, full, p, count=1).strip()
            break
    return p


ZONE_IN_POST = re.compile(r"(?i)\s*[–-]?\s*\b(zone\s*[–-]?\s*(\d+)(\s*(&|and)\s*\d+)?|z(\d+))\b\s*")


def _people(name, phone):
    """[(name, phone)] of one cell pair: names split on " | " and on "Thiru." / "Tmt." / "Dr." starts; phones paired in order when
    the counts match, else every name gets all phones."""
    names = [n for n in re.split(r"\s*\|\s*|\s+(?=(?:Thiru|Tmt|Selvi|Dr)\.)|(?<=\))\s+(?=[A-Z])", _esw.clean(name)) if n.strip(" .")]
    ph = [x for x in re.split(r",\s*", _esw.phones(phone)) if x] if phone else []
    if not names:
        return [("", ", ".join(ph))]
    if len(names) == len(ph):
        return list(zip(names, ph))
    return [(n, ", ".join(ph)) for n in names]


def parse(html, p):
    city = city_of(p)
    body, lgd, district = BODIES[city]
    seen, recs, byk = set(), [], {}
    for t in _esw.soup(html).find_all("table"):
        gp = []
        g = _esw.grid(t, pos=gp)
        if not g or len(g[0]) < 2:
            continue
        cols, section, zone = None, "", None
        for r, rp in zip(g, gp):
            h = _heading(r)
            if h and re.fullmatch(r"[\d\s-]+", h):
                provenance.skip_row(r, 'skip: h and re.fullmatch(r"[\\d\\s-]+", h)')
                continue
            if h:
                m = re.search(r"(?i)\bzone\s*(\d+)", h)
                if m:
                    zone = f"Zone {m.group(1)}"
                elif re.search(r"(?i)main\s*office", h):
                    zone = None
                if not re.search(r"(?i)corporation", h):
                    section = re.sub(r"(?i)\s*[–-]\s*officers$", "", h)
                continue
            if cols is None or any(re.fullmatch(r"(?i)(designation|sanctioned post name|hod.s)", c) for c in r):
                c = _cols(r)
                if c[0] is not None:
                    cols = c
                continue
            pi, ni, phi, wi, svi, sci = cols
            cell = lambda i: r[i] if i is not None and i < len(r) else ""  # noqa: E731
            wards, service = _wards(cell(wi)) if wi is not None else None, cell(svi)
            if sci is not None and cell(sci):
                section = cell(sci)
            post = r[pi] if pi < len(r) else ""
            name = r[ni] if ni is not None and ni < len(r) else ""
            phone = r[phi] if phi is not None and phi < len(r) else ""
            if not re.search(r"\d{6}", phone or ""):
                phone = ""
            post = _post_cell(post)
            if not post or re.fullmatch(r"[\d.]+", post) or SKIP.search(_esw.clean(post)):
                provenance.skip_row(r, 'skip: not post or re.fullmatch(r"[\\d.]+", post) or SKIP.search(_esw.clean...')
                continue
            z = zone
            mz = ZONE_IN_POST.search(post)
            if mz:
                z = z or f"Zone {mz.group(2) or mz.group(5)}"
                post = ZONE_IN_POST.sub(" ", post).strip(" –-")
                post = re.sub(r"\s+\(", " (", post)
            post = _post(post)
            if not post:
                provenance.skip_row(r, 'skip: not post')
                continue
            note = None
            mrest = re.search(r"\s*\|\s*(Deputy Collector.*)$", name)
            if mrest:
                name, note = name[:mrest.start()], mrest.group(1)
            for nm, ph in _people(name, phone):
                nm = re.sub(r"(?i)^(thiru|tmt|selvi)\s*\.+\s*", "", nm).strip(" .,")
                if not nm and not ph:  # a post with no one and no phone on the page (Tirunelveli: City Health Officer)
                    continue
                k = (post, z, nm, ph)
                if svi is not None and k in byk:  # Tambaram: the same officer on one row per service
                    if service and service not in byk[k].setdefault("services", []):
                        byk[k]["services"].append(service)
                    continue
                level, area = ("zone", z) if z else ("body", body)
                key = f"{city}:{_esw.slug(z) if z else 'body'}:{_esw.slug(post)}:{_esw.slug(nm) or 'post'}"
                recs.append(_ward.record(MODULE, key, seen, body=body, lgd=lgd, state=STATE, district=district, level=level,
                                         area=area, zone=z, post=post, name=nm, phone=ph, section=section or None,
                                         notes=note, wards=wards if z else None, services=[service] if service else None,
                                         source=p["url"], src_pos=rp))
                byk[k] = recs[-1][1]
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, city_of(p), r.content)], "" if recs else "no staff table"
