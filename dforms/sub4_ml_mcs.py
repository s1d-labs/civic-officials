"""Meghalaya: Block Development Officers (C&RD blocks), Sub-Divisional Officers (Civil) / ADCs in charge of civil sub-divisions and
Assistant Commissioners of civil sub-divisions, from the state portal's "MCS List" (meghalaya.gov.in/mcs; Meghalaya Civil Service
officers, Personnel department). An HTML table, 51 rows a page, ?page=0..3 on 2026-11-13 (163 officers): Name | Present Post |
Assets. "Present Post" lists every charge of the officer with the date of the charge report: "Assistant Commissioner, Ri-Bhoi
District, Nongpoh - 16.01.2023, BDO, Umsning C&RD Block - 27.06.2024" ("- Charge report not yet received" when the order is new).
The list gives no phone numbers or emails. The portal answered from dev-vps-3 (Mumbai); route abroad not checked.

Kept charges: "BDO, <block> C&RD Block" -> dept rural_development, level block, post Block Development Officer, area = block,
lgd_block_code (lgd.blocks, state 17; the list spells some names differently: ALIAS); "SDO, <x> Civil Sub-Division" and
"ADC, i/c <x> Civil Sub-Division" -> dept administration, level subdivision, post Sub-Divisional Officer (Civil) (in_charge for an
ADC); "Assistant Commissioner, <x> Civil Sub-Division" -> level subdivision, post Assistant Commissioner. District: the block's
LGD district, else the district named in the officer's other charges ("..., East Khasi Hills District, Shillong").
charge_date = the date of the charge report (ISO), or charge_report_pending = true.
One queue item reads all pages (1 GET each, page 0, 1, ... until a page has no rows; at most 15).
Record ids: dept:sub4_ml_mcs:<post key>:<area slug>[:n] (an officer holding two blocks gives two records).
"""
import re

from dforms import _esw

METHOD = "html table rows (BeautifulSoup), charges split from the Present Post cell by regex"     # source trail

MODULE = "sub4_ml_mcs"
URL = "https://meghalaya.gov.in/mcs"
MAX_PAGES = 15
BLOCKS = {'adokgre': ('7522', '656'), 'amlarem': ('2463', '275'), 'baghmara': ('2471', '277'), 'bajengdoba': ('7184', '656'),
          'batabari': ('7527', '278'), 'betasing': ('2475', '663'), 'bhoirymbong': ('7182', '276'), 'chokpot': ('2472', '277'),
          'dadenggiri': ('2476', '278'), 'dalu': ('2477', '278'), 'damborongjeng': ('2450', '273'), 'demdema': ('7181', '278'),
          'gambegre': ('2478', '278'), 'gasuapara': ('2473', '277'), 'jirang': ('2468', '276'),
          'khadarshnonglaitkroh': ('2455', '274'), 'kharkutta': ('2451', '656'), 'laskein': ('2465', '275'),
          'lumshnong': ('7525', '657'), 'mairang': ('2483', '740'), 'mawhati': ('7596', '276'), 'mawkynrew': ('2456', '274'),
          'mawkyrwat': ('2484', '658'), 'mawlai': ('7185', '274'), 'mawpat': ('7186', '274'), 'mawphlang': ('2457', '274'),
          'mawryngkneng': ('2458', '274'), 'mawshynrut': ('2485', '279'), 'mawsynram': ('2459', '274'),
          'mawthadraishan': ('2486', '740'), 'mylliem': ('2460', '274'), 'namdong': ('7523', '275'), 'nongstoin': ('2487', '279'),
          'purakhasia': ('7563', '663'), 'pynursla': ('2461', '274'), 'rambrai': ('7521', '279'), 'ranikor': ('2488', '658'),
          'rerapara': ('7180', '663'), 'resubelpara': ('2452', '656'), 'rimuliang': ('7524', '279'), 'rongara': ('2474', '277'),
          'rongram': ('2479', '278'), 'saipung': ('2466', '657'), 'salsella': ('2480', '278'), 'samanda': ('2453', '273'),
          'shallang': ('7526', '279'), 'shellabholaganj': ('2462', '274'), 'siju': ('7520', '277'), 'sohiong': ('7183', '274'),
          'songsak': ('2454', '273'), 'thadlaskein': ('2467', '275'), 'tikrikilla': ('2481', '278'), 'umling': ('2469', '276'),
          'umsning': ('2470', '276'), 'wapung': ('2464', '657'), 'zikzak': ('2482', '663')}
ALIAS = {"selsella": "salsella", "betabari": "batabari", "dadenggre": "dadenggiri", "khatarshnonglaitkroh": "khadarshnonglaitkroh",
         "thadlaskein": "thadlaskein", "dambo": "damborongjeng"}
DISTRICTS = {'eastgarohills': '273', 'eastkhasihills': '274', 'westjaintiahills': '275', 'ribhoi': '276', 'southgarohills': '277',
             'westgarohills': '278', 'westkhasihills': '279', 'northgarohills': '656', 'eastjaintiahills': '657',
             'southwestkhasihills': '658', 'southwestgarohills': '663', 'easternwestkhasihills': '740'}
DNAME = {'273': 'East Garo Hills', '274': 'East Khasi Hills', '275': 'West Jaintia Hills', '276': 'Ri Bhoi', '277': 'South Garo Hills',
         '278': 'West Garo Hills', '279': 'West Khasi Hills', '656': 'North Garo Hills', '657': 'East Jaintia Hills',
         '658': 'South West Khasi Hills', '663': 'South West Garo Hills', '740': 'Eastern West Khasi Hills'}
# civil sub-divisions -> district (LGD code); the list names the district only in some rows
SUBDIVS = {"sohra": "274", "pynursla": "274", "dalu": "278", "dadenggre": "278", "jengjal": "278", "raksamgre": "278",
           "ranikor": "658", "mawshynrut": "279", "amlarem": "275", "patharkhmah": "276", "chokpot": "277", "rongjeng": "273",
           "bajengdoba": "656"}
CHARGE = re.compile(r"\s*(.+?)\s+-\s+(\d{1,2}\.\d{1,2}\.\d{4}|charge\s+report\s+not\s+yet\s+received)\s*(?:,|$)", re.I)
TITLE = re.compile(r"^(?:shri|smti|smt|dr|mr|ms|kumari)\.?\s+", re.I)
SUBDIV = r"\(?civil\)?\s*sub[\s-]*division"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "ML", "india_only": False}}]


def key(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def block(name):
    k = key(name)
    k = ALIAS.get(k, k)
    if k not in BLOCKS:
        k = next((a for a in ALIAS if k.startswith(a)), k)
        k = ALIAS.get(k, k)
    return BLOCKS.get(k, ("", ""))


def charges(text):
    """[(charge text, date ISO or '', pending)] from a Present Post cell."""
    out = []
    for m in CHARGE.finditer(re.sub(r"\s*\|\s*", " ", text or "")):
        when = m.group(2)
        if re.match(r"\d", when):
            d, mo, y = when.split(".")
            out.append((m.group(1).strip(" ,"), f"{y}-{int(mo):02d}-{int(d):02d}", False))
        else:
            out.append((m.group(1).strip(" ,"), "", True))
    return out


def kind(charge):
    """(post key, post, level, dept, area, in_charge) or None."""
    m = re.match(r"(?i)BDO\s*,\s*(.+?)\s*,?\s*C\s*&\s*RD\s+Block$", charge)
    if m:
        return ("bdo", "Block Development Officer", "block", "rural_development", m.group(1), False)
    m = re.match(rf"(?i)(SDO|ADC)\s*,\s*(i/c\s+)?(.+?)\s+{SUBDIV}$", charge)
    if m:
        return ("sdo", "Sub-Divisional Officer (Civil)", "subdivision", "administration", m.group(3),
                bool(m.group(2)) or m.group(1).upper() == "ADC")
    m = re.match(rf"(?i)Assistant\s+Commissioner\s*,\s*(.+?)\s+{SUBDIV}$", charge)
    if m:
        return ("ac", "Assistant Commissioner", "subdivision", "administration", m.group(1), False)
    return None


def build(pages):
    """pages: [(url, html)]."""
    recs, seen = [], set()
    for url, html in pages:
        soup = _esw.soup(html)
        for table in soup.find_all("table"):
            pos = []
            rows = _esw.grid(table, pos=pos)
            for row, sp in zip(rows, pos):
                if len(row) < 2 or re.search(r"(?i)present\s+post", row[1]):
                    continue
                name = re.sub(r",?\s*\bMCS\b\.?$", "", row[0]).strip(" ,")
                name = TITLE.sub("", name).strip()
                cs = charges(row[1])
                home = ""
                for c, _, _ in cs:
                    m = re.search(r"(?i),\s*([A-Za-z\- ]+?)\s+District\b", c)
                    if m and key(m.group(1)) in DISTRICTS:
                        home = DISTRICTS[key(m.group(1))]
                        break
                for c, when, pending in cs:
                    k = kind(c)
                    if not k:
                        continue
                    pk, post, level, dept, area, ic = k
                    area = area.strip(" ,")
                    bc, bdc = block(area) if pk == "bdo" else ("", "")
                    dc = bdc or (SUBDIVS.get(key(area), "") if level == "subdivision" else "") or home
                    rid = f"{pk}:{_esw.slug(area)}"
                    while rid in seen:
                        rid += ":2"
                    seen.add(rid)
                    recs.append(_esw.record(MODULE, rid, dept=dept, level=level, post=post, designation=c, area=area,
                                            lgd_block_code=bc, district=DNAME.get(dc, ""), district_code=dc, state="ML",
                                            name=name, cadre="MCS", in_charge=True if ic else None, charge_date=when,
                                            charge_report_pending=True if pending else None, source=url, src_url=url,
                                            src_pos=sp))
    return recs


def officers(html):
    """Number of officer rows on a page (a cell that starts with Shri / Smti / Dr ... and ends with MCS)."""
    return len(re.findall(r"(?is)<td[^>]*>\s*(?:<[^>]+>\s*)*(?:shri|smti|smt|dr|kumari)\.?\s[^<]{2,80}?MCS\s*<", html or ""))


def fetch(p, get):
    base = p.get("url") or URL
    pages, files = [], []
    for n in range(MAX_PAGES):
        url = base if n == 0 else f"{base}?page={n}"
        r = get(url)
        if r is None:
            if n == 0:
                return [], [], "no answer"
            break
        if not officers(r.text):
            break
        files.append(_esw.keep(MODULE, f"mcs-page-{n}", r.content))
        pages.append((url, r.text))
    recs = build(pages)
    return recs, files, "" if recs else "no rows"
