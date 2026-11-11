"""Nagar Nigam Bikaner (bikanermc.org; 80 wards): the sanitation staff of every ward and the corporation's officer contact list.
Two PDFs of the home page (same site software as kotamc.org / jaipurmc.org; answer from Germany; live sample 2026-11-11, not in
archive.s1d.me). One queue item reads both:
- "Ward Wise SI And Jamadar List 2026" (/PDF/Ward_Wise_List_Jamadar.pdf, 2 pages, Unicode Mangal text). Columns: जोन सं. (sanitation
  circle: EAST 1-5, WEST 1-5) | वार्ड न. | स्वच्छता प्रभारी का नाम | स्वच्छता प्रभारी का मो. न. | जमादार का नाम | जमादार का मो. न. |
  जमादार का मो. न. CUG. Records: one per circle for its sanitation in-charge (level "circle", wards = the circle's wards) and one per
  ward for its jamadar (level "ward"). The PDF's font has no Unicode value for some glyphs (श्र of श्री, half letters, some ि): the
  text layer loses or garbles them. A name with a garbled letter (a digit or a sign in the word) goes to name_text_layer only; a name
  that looks whole is kept as name, with name_note on every record. The in-charge's name comes from the contact list when his
  mobile is the same there (name_from).
- "Contact Us" (/PDF/ContactList.pdf?v1, 3 pages, Kruti Dev): 112 rows. Columns: क्र.सं. | नाम | पद | मोबाइल नम्बर (commissioner,
  deputy commissioners, XEN / AEN / JEN, revenue officers and inspectors, town planner, administrative officers, clerks, fire staff).
  No zone or ward: level "body", area "Head office". Rows are read with dforms/ward2n_kota.rows() (the same list layout).
Record ids: dept:ward2n_bikaner:<circle>:si, :ward-<n>:jamadar, :contact:<row>.
"""
import re

from dforms import _esw, _ward, ward2n_kota as kl

MODULE = "ward2n_bikaner"
BODY, LGD, STATE, DISTRICT = "Nagar Nigam Bikaner", "248667", "RJ", "Bikaner"
URL = "https://bikanermc.org/PDF/Ward_Wise_List_Jamadar.pdf?v1"
CONTACT_URL = "https://bikanermc.org/PDF/ContactList.pdf?v1"
ROW = re.compile(r"^\s*(EAST|WEST)\s+(\d)\s+(\d{1,3})\s+(.*)$")
PHONE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")
NOTE = "the PDF text layer loses some Devanagari letters (श्री, half letters, some ि): check the name against the PDF"


def items(get=None):
    return [{"key": f"{MODULE}-ward-sanitation", "payload": {"reader": MODULE, "url": URL, "contact_url": CONTACT_URL, "state": STATE}}]


def clean_name(t):
    """(name, text layer) of a name cell: the lost श्र of श्री leaves a lone "ी" in front; ि comes before its consonant in the text
    layer; pdftotext puts a space after an anusvara. name is "" when a letter of the text is garbled (a digit or a sign in it) or
    lost (a lone consonant between spaces: "क पल" for कपिल)."""
    t = _esw.clean(t)
    t = re.sub(r"^ी\s+", "", t)
    t = re.sub(r"ि([क-ह])", r"\1ि", t)
    t = re.sub(r"ं\s+(?=[क-ह])", "ं", t)
    t = _esw.clean(t)
    ok = bool(t) and re.fullmatch(r"[ऀ-ॿ ]+", t) is not None and not any(re.fullmatch(r"[क-ह]", w) for w in t.split())
    return (t if ok else ""), t


def sanitation_rows(pages):
    """[(circle "EAST 1", ward, si text, [si phones], jamadar text, [jamadar phones])] of the ward list."""
    out = []
    for pg in pages:
        for ln in pg.splitlines():
            m = ROW.match(ln)
            if not m:
                continue
            rest = m.group(4)
            ph = [(x.start(), x.group(1)) for x in PHONE.finditer(rest)]
            if not ph:
                continue
            si_name = rest[:ph[0][0]]
            si_ph = [ph[0][1]]
            k = 1
            if len(ph) > 1 and re.fullmatch(r"\s*/\s*", rest[ph[0][0] + 10:ph[1][0]]):
                si_ph.append(ph[1][1])
                k = 2
            start = ph[k - 1][0] + 10
            jam_name = rest[start:ph[k][0]] if len(ph) > k else rest[start:]
            out.append((f"{m.group(1)} {m.group(2)}", m.group(3), si_name, si_ph, jam_name, [p for _, p in ph[k:]]))
    return out


def parse_contacts(pages, p):
    seen, recs = set(), []
    for r in kl.rows(pages):
        if not (r["name"] or r["phones"] or r["post"]):
            continue
        recs.append(kl.record_of(MODULE, r, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, area="Head office",
                                 source=p.get("contact_url") or CONTACT_URL, key=f"contact:{r['n']}"))
    return recs


def parse(pages, p, contacts=()):
    """Records of the ward list; contacts: records of the contact list (their names fill in the in-charges by mobile number).
    pages may also be {"list": [page texts of the ward list], "contacts": [page texts of the contact list]} (the offline test):
    then the contact list records are given too."""
    if isinstance(pages, dict):
        contacts = parse_contacts(pages.get("contacts") or [], p)
        return parse(pages.get("list") or [], p, contacts) + contacts
    by_phone = {}
    for _, d in contacts:
        for x in PHONE.findall(d.get("phone", "")):
            if d.get("name"):
                by_phone.setdefault(x, d["name"])
    seen, recs, circles = set(), [], {}
    for circle, ward, si, si_ph, jam, jam_ph in sanitation_rows(pages):
        w = str(int(ward))
        c = circles.setdefault(circle, {"wards": [], "si": si, "ph": si_ph})
        if w not in c["wards"]:
            c["wards"].append(w)
        name, raw = clean_name(jam)
        recs.append(_ward.record(MODULE, f"ward-{w}:jamadar", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="ward",
                                 area=f"Ward {w}", zone=circle.title(), post="Sanitation Jamadar", post_regional="जमादार",
                                 name=name, name_regional=name or None, name_text_layer=raw if raw != name else None,
                                 name_note=NOTE, phone=", ".join(jam_ph), wards=[w], wing="sanitation",
                                 vacant=None if (raw or jam_ph) else True, source=p["url"]))
    for circle, c in circles.items():
        name, raw = clean_name(c["si"])
        found = next((by_phone[x] for x in c["ph"] if x in by_phone), None)
        recs.append(_ward.record(MODULE, f"{_esw.slug(circle)}:si", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="circle", area=f"{circle.title()} sanitation circle", zone=circle.title(),
                                 post="Sanitation In-charge (SI)", post_regional="स्वच्छता प्रभारी", name=found or name,
                                 name_regional=found or name or None, name_text_layer=raw if raw != (found or name) else None,
                                 name_from="ContactList.pdf (same mobile number)" if found else None,
                                 name_note=None if found else NOTE, phone=", ".join(c["ph"]), wards=c["wards"], wing="sanitation",
                                 source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "ward-sanitation", r.content, "pdf")]
    contacts = []
    rc = get(p["contact_url"]) if p.get("contact_url") else None
    if rc is not None and rc.content[:5] == b"%PDF-":
        files.append(_esw.keep(MODULE, "contact-list", rc.content, "pdf"))
        contacts = parse_contacts(_ward.layout_pages(rc.content), p)
    recs = parse(_ward.layout_pages(r.content), p, contacts) + contacts
    return recs, files, "" if recs else "no rows (pdftotext missing?)"
