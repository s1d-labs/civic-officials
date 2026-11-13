"""Tripura: Sub-Divisional Magistrates (23 sub-divisions) and Block Development Officers (58 blocks), from the state portal's
"Contact Directory" (tripura.gov.in/contact-directory, section "District Administration"). Each list is one ruled PDF with a
text layer: SDMs "Sub_Divisional_Magistrates_05_11_2026.pdf" (2 pages; Sl.No | sub-division | name of the SDM, cadre | office
phone (O), mobile (M), email), BDOs "Block_Development_Officers_27_10_2026.pdf" (5 pages; Sl. No | block, post office, district |
name of the BDO | phones and email). The portal answered from dev-vps-3 (Mumbai) on 2026-11-13; route abroad not checked.

One queue item per list (payload "kind": "sdm" or "bdo"): 1 GET of the directory page, which gives the newest file of that title
(a new upload has a new name), + 1 GET of the PDF (the payload url when the page does not answer). The PDF is kept in the bucket.
Records: SDM -> dept administration, level subdivision, area = sub-division, subdistrict_code = the code of the sub-division in
civic.subdistrict (LGD sub-district code); BDO -> dept rural_development, level block, area = block, lgd_block_code (LGD), the post
office address. The district: for BDOs from the block cell ("Dhalai District"), for SDMs from the sub-division.
Record ids: dept:sub4_tr:<kind>:<slug of area>.
"""
import re

from dforms import _esw, _sub4_ruled as ruled

METHOD = "pdf text pieces by position in the ruled table (pypdf)"     # source trail (provenance.py)

MODULE = "sub4_tr"
PAGE = "https://tripura.gov.in/contact-directory"
BASE = "https://tripura.gov.in"
LISTS = {"sdm": ("Sub-Divisional Magistrates", BASE + "/sites/default/files/2026-11/Sub_Divisional_Magistrates_05_11_2026.pdf",
                 "2026-11-05"),
         "bdo": ("Block Development Officers", BASE + "/sites/default/files/2026-10/Block_Development_Officers_27_10_2026.pdf",
                 "2026-10-27")}
DISTRICTS = {"dhalai": ("269", "Dhalai"), "north": ("270", "North Tripura"), "south": ("271", "South Tripura"),
             "west": ("272", "West Tripura"), "khowai": ("652", "Khowai"), "sepahijala": ("653", "Sepahijala"),
             "gomati": ("654", "Gomati"), "unakoti": ("655", "Unakoti"), "unokoti": ("655", "Unakoti")}
DNAME = {c: n for c, n in DISTRICTS.values()}
# lgd.blocks of state 16: name key -> (block code, district code)
BLOCKS = {'amarpur': ('2423', '654'), 'ambassa': ('2410', '269'), 'bamutia': ('6791', '272'), 'belbari': ('6792', '272'),
          'bharatchandranagar': ('6789', '271'), 'bishalgarh': ('2434', '653'), 'bokafa': ('2424', '271'),
          'boxanagar': ('2435', '653'), 'chandipur': ('6785', '655'), 'charilam': ('6786', '653'), 'chawmanu': ('2411', '269'),
          'damcherra': ('2415', '270'), 'dasda': ('2416', '270'), 'dukli': ('2436', '272'), 'dumburnagar': ('2412', '269'),
          'durgachowmuhani': ('6729', '269'), 'ganganagar': ('6781', '269'), 'gournagar': ('2417', '655'),
          'hezamara': ('2437', '272'), 'hrishyamukh': ('2425', '271'), 'jampuihills': ('2418', '270'),
          'jampuijala': ('2438', '653'), 'jirania': ('2439', '272'), 'jolaibari': ('6723', '271'), 'jubarajnagar': ('6727', '270'),
          'kadamtala': ('2419', '270'), 'kakraban': ('2426', '654'), 'kalacherra': ('6783', '270'), 'kalyanpur': ('2440', '652'),
          'karbook': ('2427', '654'), 'kathalia': ('2441', '653'), 'khowai': ('2442', '652'), 'killa': ('2428', '654'),
          'kumarghat': ('2420', '655'), 'laljuri': ('6784', '270'), 'lefunga': ('6721', '272'), 'mandwai': ('2443', '272'),
          'mandai': ('2443', '272'), 'manu': ('2413', '269'), 'matabari': ('2429', '654'), 'mohanbhog': ('6787', '653'),
          'mohanpur': ('2445', '272'), 'mungiakami': ('2446', '652'), 'nalchar': ('2444', '653'), 'oldagartala': ('6790', '272'),
          'ompi': ('2430', '654'), 'padmabil': ('2447', '652'), 'panisagar': ('2421', '270'), 'pecharthal': ('2422', '655'),
          'poangbari': ('6788', '271'), 'poyangbari': ('6788', '271'), 'raishyabari': ('6780', '269'), 'rajnagar': ('2431', '271'),
          'rupaichari': ('2432', '271'), 'salema': ('2414', '269'), 'satchand': ('2433', '271'), 'silachari': ('6725', '654'),
          'teliamura': ('2448', '652'), 'tepania': ('6782', '654'), 'tulashikhar': ('2449', '652')}
# civic.subdistrict of Tripura (the 23 sub-divisions): name key -> (sc, district code); the list spells some names differently
SUBDIVS = {'amarpur': ('6695', '654'), 'ambassa': ('6697', '269'), 'belonia': ('6687', '271'), 'bishalgarh': ('6699', '653'),
           'dharmanagar': ('6691', '270'), 'darmanagar': ('6691', '270'), 'gandacherra': ('6686', '269'),
           'gondatwisa': ('6686', '269'), 'jampuijala': ('6677', '653'), 'jirania': ('6679', '272'), 'kailashahar': ('6682', '655'),
           'kamalpur': ('6681', '269'), 'kanchanpur': ('6685', '270'), 'karbook': ('6690', '654'), 'khowai': ('6684', '652'),
           'kumarghat': ('6694', '655'), 'longtharaivalley': ('6692', '269'), 'ltvalley': ('6692', '269'),
           'mohanpur': ('6689', '272'), 'panisagar': ('6678', '270'), 'sabroom': ('6688', '271'), 'sadar': ('6696', '272'),
           'santirbazar': ('6683', '271'), 'sonamura': ('6680', '653'), 'teliamura': ('6698', '652'), 'udaipur': ('6693', '654')}
NAME = re.compile(r"^((?:Shri|Smt|Sri|Ms|Mr|Mrs|Dr|Kumari)\.?\s*)", re.I)


def items(get=None):
    return [{"key": f"{MODULE}_{k}", "payload": {"reader": MODULE, "kind": k, "url": u, "page": PAGE, "state": "TR",
                                                  "india_only": False}} for k, (_, u, _) in LISTS.items()]


def key(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def current_url(html, title):
    """The PDF link of the row titled `title` on the contact directory page (absolute), else None."""
    soup = _esw.soup(html)
    for a in soup.find_all("a", href=True):
        if (a.get("title") or "").strip().lower() == title.lower() and a["href"].lower().endswith(".pdf"):
            h = a["href"]
            return h if h.startswith("http") else BASE + h
    return None


def contacts(t):
    """(phones, emails) from the contact cell: '03821 263 226 (O), 9436454678 (M), sdmofficesonamura@gmail. c om'."""
    mail_part = re.sub(r"\s*([@.])\s*", r"\1", re.sub(r"(\w)\s*-\s+(?=\w+@)", r"\1-", t))          # the print breaks addresses: "po_abs@yahoo .co.in", "gmail. c om"
    mail_part = re.sub(r"(?<=\.)c om\b", "com", mail_part)
    emails = re.findall(r"[\w.\-]+@[\w\-]+(?:\.[\w\-]+)+", mail_part)
    emails = [e.rstrip(".") for e in emails]
    rest = re.sub(r"[\w.\-]+@\S+", " ", t)
    phones = []
    for m in re.finditer(r"(?<!\d)(0\d{2,4})\s?(\d{3})\s?(\d{3,4})(?!\d)(\s*\(F\))?|(?<!\d)([6-9]\d{9})(?!\d)", rest):
        if m.group(5):
            phones.append(m.group(5))
        elif not m.group(4):                               # fax numbers left out
            phones.append(f"{m.group(1)}-{m.group(2)}{m.group(3)}")
    return ", ".join(dict.fromkeys(phones)), ", ".join(dict.fromkeys(e.lower() for e in emails))


def person(t):
    """('Anupam Chakrabory', 'TCS-I') from 'Shri. Anupam Chakrabory, TCS - I'; the name keeps no title."""
    t = re.sub(r"\s+([,.])", r"\1", t).strip(" ,")
    cadre = ""
    m = re.search(r",?\s*\b(IAS|TCS[\w\s\-.]*|TRDS[\w\s\-.]*)$", t)
    if m:
        cadre = re.sub(r"\s*-\s*", "-", m.group(1)).strip(" ,.")
        t = t[:m.start()].strip(" ,")
    return NAME.sub("", t).strip(" .,"), cadre


def build(kind, rs, source, listed):
    recs, seen = [], set()
    for r in rs:
        c = [ruled.text(x) for x in r["cells"]]
        if len(c) < 4:
            continue
        name, cadre = person(c[2])
        phone, email = contacts(c[3])
        if kind == "sdm":
            area = c[1].strip(" ,.")
            sc, dc = SUBDIVS.get(key(area), ("", ""))
            f = dict(dept="administration", level="subdivision", post="Sub-Divisional Magistrate", subdistrict_code=sc)
        else:
            cell = c[1]
            area = re.split(r"[.,]", cell, 1)[0].strip()
            m = re.search(r"(\w+)\s+District", cell)
            dc = DISTRICTS.get(key(m.group(1)), ("", ""))[0] if m else ""
            bc, bdc = BLOCKS.get(key(area), ("", ""))
            dc = dc or bdc
            address = re.sub(r"\s*-\s*", "-", cell[len(area):].strip(" .,"))
            f = dict(dept="rural_development", level="block", post="Block Development Officer", lgd_block_code=bc,
                     address=address)
        if not area:
            continue
        k = f"{kind}:{_esw.slug(area)}"
        while k in seen:
            k += ":2"
        seen.add(k)
        recs.append(_esw.record(MODULE, k, area=area, district=DNAME.get(dc, ""), district_code=dc, state="TR", name=name,
                                cadre=cadre, phone=phone, email=email, source=source, src_url=source, last_updated=listed,
                                list_no=r["_pos"]["sn"], src_pos=r["_pos"], **f))
    return recs


def fetch(p, get):
    kind = p.get("kind", "bdo")
    title, url, listed = LISTS[kind]
    url = p.get("url") or url
    files = []
    page = get(p.get("page") or PAGE)
    if page is not None and page.content:
        found = current_url(page.text, title)
        if found:
            url = found
        files.append(_esw.keep(MODULE, "contact-directory", page.content))
    m = re.search(r"_(\d\d)_(\d\d)_(20\d\d)\.pdf$", url)
    if m:
        listed = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    r = get(url)
    if r is None:
        return [], files, "no answer"
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    files.append((f"depts/{MODULE}/{kind}.pdf", r.content, "application/pdf"))
    recs = build(kind, ruled.rows(r.content), url, listed)
    return recs, files, "" if recs else "no rows"
