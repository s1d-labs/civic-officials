"""Nagar Palik Nigam Korba (korbamunicipal.in/mck/): the officers of each branch and of each of its 7 zones (Korba, Transport Nagar
(परिवहन नगर), Kosabadi, Pt. Ravishankar Shukla Nagar, Balco, Sarvamangla Nagar, Darri). One PDF, "Zonal Information" on the home
page (/mck/docs/Zonal Information List 06122024.pdf, an Excel print of 2024-12-06, 2 pages, 71 rows, set in Kruti Dev: converted with
dforms/_ward_kd.py). Live sample from Mumbai on 2026-11-13 (plain http; https does not answer), not in archive.s1d.me; route
unchecked from abroad. Not read (scans, need OCR from a saved copy): /mck/docs/Staff_List_2025.pdf (83 pages) and
/mck/docs/Placement_Labour.pdf (the sanitation branch staff, 16 pages).
Columns: क्र. | शाखा / जोन का नाम | अधिकारी का नाम | पदनाम | मोबाइल नंबर. The branch / zone cell is merged over the rows below it in the
sheet, so an empty cell repeats the cell of the row above; a long branch cell wraps onto the lines below its row. Column starts are
taken from each page's heading line; a name that starts left of its column (row 15: "श्री एन.के.नाथ") is moved back from the
branch cell when the name cell does not start with श्री / श्रीमती / डॉ. itself.
Records: a row whose branch names a zone ("कोरबा जोन", "राजस्व (दर्री जोन)", "बालको जोन एवं प्रधानमंत्री आवास योजना") -> level "zone",
area = the zone in English, area_regional the Hindi, zone the same; every other row -> level "body" (charge = the branch). The PDF
gives no ward list per zone (wards_note). Names and posts are Hindi: name without श्री / श्रीमती / डॉ., name_regional as converted,
post English (dforms/_ward3_central.post_en), post_regional as converted. Record ids: dept:ward3_korba:<row n>.
"""
import re

import provenance
from dforms import _esw, _ward, _ward3_central as c3, _ward_kd as kd

METHOD = "pdf text (pdftotext -layout) + Kruti Dev map + heading columns"     # source trail (provenance.py)

MODULE = "ward3_korba"
BODY, LGD, STATE, DISTRICT = "Nagar Palik Nigam Korba", "250598", "CG", "Korba"
URL = "http://korbamunicipal.in/mck/docs/Zonal%20Information%20List%2006122024.pdf"
ZONES = (("परिवहन नगर", "Transport Nagar Zone"), ("कोसाबाड", "Kosabadi Zone"), ("रविशंकर", "Pt. Ravishankar Shukla Nagar Zone"),
         ("बालको", "Balco Zone"), ("सर्वमंगला", "Sarvamangla Nagar Zone"), ("दर्री", "Darri Zone"), ("कोरबा", "Korba Zone"))
HEAD = re.compile(r"vf/kdkjh\s+dk\s+uke")
NUM = re.compile(r"\s*(\d{1,3})(?=\s{2,}|\s+\S)")


def items(get=None):
    return [{"key": f"{MODULE}-zonal-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE, "route": "abroad"}}]


def hi(t):
    """Kruti Dev text -> Devanagari, with ¼ ½ as brackets, "]" as a comma and the matras that the font map leaves apart joined."""
    u = kd.convert(t).replace("¼", "(").replace("½", ")").replace("]", ",")
    u = re.sub(r"\s+(?=[ऀ-ःऺ-ॏॢॣ])", "", u)
    return _esw.clean(u)


def zone_of(branch):
    """(English zone, Hindi zone words) of a branch cell that names a zone, else (None, None)."""
    if "जोन" not in branch:
        return None, None
    m = re.search(r"([^(),]*?जोन)", branch)
    hz = _esw.clean(m.group(1)) if m else branch
    hz = re.sub(r"^\s*राजस्व\s*", "", hz)
    for key, en in ZONES:
        if key in hz:
            return en, hz
    return None, None


def rows(pages):
    """[{"n", "branch", "name", "post", "phone", "pos"}] in Kruti Dev text (branch already carried down)."""
    out = []
    for pn, pg in enumerate(pages, 1):
        cols = None
        for lno, ln in enumerate(pg.splitlines(), 1):
            if HEAD.search(ln):
                cols = (ln.index("'kk[kk") if "'kk[kk" in ln else 5, HEAD.search(ln).start(), ln.index("inuke"),
                        ln.index("eksckbZy"))
                continue
            if cols is None or not ln.strip():
                provenance.skip_line(ln, 'skip: cols is None or not ln.strip()')
                continue
            m = NUM.match(ln)
            b0, c_name, c_post, c_mob = cols
            if m and int(m.group(1)) <= 500:
                cut = lambda a, z: ln[a:z] if len(ln) > a else ""
                branch = ln[m.end():c_name - 1]
                name = ln[c_name - 1:c_post - 1].strip() if len(ln) > c_name - 1 else ""
                sp = re.search(r"\s(Jh|Jherh|MkW-)\s+\S+$", branch)
                if sp and not re.match(r"(Jh|Jherh|MkW-)\s", name):     # the name ran into the branch column
                    branch, name = branch[:sp.start()], branch[sp.start():].strip() + name
                out.append({"n": m.group(1), "branch": [branch.strip()] if branch.strip() else [],
                            "name": name, "post": cut(c_post - 1, c_mob - 2).strip(),
                            "phone": cut(c_mob - 2, len(ln) + 1).strip(), "pos": provenance.line_pos(pn, lno, ln)})
            elif out and ln[:c_name - 1].strip() and not ln[c_name - 1:].strip():
                out[-1]["branch"].append(ln.strip())      # a wrapped branch cell
    last = ""
    for r in out:
        r["branch"] = " ".join(r["branch"]) or last
        last = r["branch"]
    return out


def parse(pages, p):
    seen, recs = set(), []
    for r in rows(pages):
        name, post, branch = hi(r["name"]), hi(r["post"]), hi(r["branch"])
        phone = c3.phones_in(r["phone"])
        if not post or not (name or phone):
            continue
        en = c3.post_en(post)
        zen, zhi = zone_of(branch)
        base = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, post=en, post_regional=post, name=c3.strip_title(name),
                    name_regional=name, phone=phone, charge=branch or None, wing=c3.wing(branch + " " + post, en),
                    source=p["url"], src_pos=r["pos"])
        if zen:
            recs.append(_ward.record(MODULE, r["n"], seen, level="zone", area=zen, area_regional=zhi, zone=zen,
                                     wards_note="the list gives no ward list per zone", **base))
        else:
            recs.append(_ward.record(MODULE, r["n"], seen, level="body", area=BODY, **base))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "zonal-information", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no rows (pdftotext missing?)"
