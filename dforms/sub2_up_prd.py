"""Uttar Pradesh: the Block Development Officer (BDO) and the Assistant Development Officer (Panchayat) (ADO) of every development
block, with mobile and WhatsApp numbers, from the Panchayati Raj Department's public "अधिकारी डायरेक्टरी" (officer directory)
prdfinance.up.gov.in/pr_officer_ado_bdo_gpdata_public (ASP.NET WebForms; answers from Germany too).

Structure: the page (about 140 KB) shows a state summary grid (table#gridEntry1): one row per district and per division total
(Division, District, Total No. of GP, Total no. of ADO, Total no. of BDO, details entered); on 2026-11-11: 824 ADO and 610 BDO rows
for 75 districts (826 blocks in LGD). Each district name is a postback link (__doPostBack('gridEntry1$ctlNN$ben_name','')); the
answer to that POST (the page's own hidden fields: __VIEWSTATE, __VIEWSTATEGENERATOR ...; no event validation) holds
table#gridEntryDist: Sno | District | Block | Post Name (ADO / BDO) | Name | Mobile No. | WhatsApp Mobile No. | Gender. Some rows have
the post written in the name column ("ADO-ETMADPUR"): the name is then left out and the phone kept. One person can hold two blocks
(two rows). Three districts are listed twice in the summary (SHRAVASTI, KUSHI NAGAR, PRAYAGRAJ: two data sets with different counts);
each link is its own queue item. The answer shows the time of the report ("Date:: 11/11/2026"), not a date of the data.

One queue item per district link (78 links): 1 GET (the summary page, for fresh hidden fields) + 1 POST. items(get) reads the summary.
Records: BDO -> dept rural_development, level block, post "Block Development Officer"; ADO -> rural_development, level block, post
"Assistant Development Officer (Panchayat)". Area = the block as written (title case), district = the LGD name (district()).
Record ids: dept:sub2_up_prd:UP-<district slug>:<block slug>:<bdo|ado>[:n].
"""
import re

import provenance
from dforms import _esw

METHOD = "html table (ASP.NET postback answer, table#gridEntryDist)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub2_up_prd"
URL = "https://prdfinance.up.gov.in/pr_officer_ado_bdo_gpdata_public"
LGD = ["Agra", "Aligarh", "Ambedkar Nagar", "Amethi", "Amroha", "Auraiya", "Ayodhya", "Azamgarh", "Baghpat", "Bahraich", "Ballia",
       "Balrampur", "Banda", "Bara Banki", "Bareilly", "Basti", "Bhadohi", "Bijnor", "Budaun", "Bulandshahr", "Chandauli", "Chitrakoot",
       "Deoria", "Etah", "Etawah", "Farrukhabad", "Fatehpur", "Firozabad", "Gautam Buddha Nagar", "Ghaziabad", "Ghazipur", "Gonda",
       "Gorakhpur", "Hamirpur", "Hapur", "Hardoi", "Hathras", "Jalaun", "Jaunpur", "Jhansi", "Kannauj", "Kanpur Dehat", "Kanpur Nagar",
       "Kasganj", "Kaushambi", "Kheri", "Kushinagar", "Lalitpur", "Lucknow", "Mahoba", "Mahrajganj", "Mainpuri", "Mathura", "Mau",
       "Meerut", "Mirzapur", "Moradabad", "Muzaffarnagar", "Pilibhit", "Pratapgarh", "Prayagraj", "Rae Bareli", "Rampur", "Saharanpur",
       "Sambhal", "Sant Kabir Nagar", "Shahjahanpur", "Shamli", "Shrawasti", "Siddharthnagar", "Sitapur", "Sonbhadra", "Sultanpur",
       "Unnao", "Varanasi"]
_KEY = {re.sub(r"[^a-z]", "", d.lower()): d for d in LGD}
ALIAS = {"santravidasnagarbhadohi": "Bhadohi", "santravidasnagar": "Bhadohi", "shravasti": "Shrawasti", "maharajganj": "Mahrajganj",
         "siddharthnagar": "Siddharthnagar", "barabanki": "Bara Banki", "raebareli": "Rae Bareli", "lakhimpurkheri": "Kheri",
         "santkabeernagar": "Sant Kabir Nagar", "allahabad": "Prayagraj", "faizabad": "Ayodhya", "badaun": "Budaun",
         "kanshiramnagar": "Kasganj", "jyotibaphulenagar": "Amroha", "kushinagar": "Kushinagar", "bulandshahar": "Bulandshahr"}
POSTS = {"BDO": "Block Development Officer", "ADO": "Assistant Development Officer (Panchayat)"}


def district(name):
    k = re.sub(r"[^a-z]", "", (name or "").lower())
    return _KEY.get(k) or ALIAS.get(k) or _esw.clean(name).title()


def form_fields(html):
    """The hidden fields and select values the page posts back."""
    soup = _esw.soup(html)
    form = soup.find("form")
    if form is None:
        return {}
    data = {i["name"]: i.get("value", "") for i in form.find_all("input") if i.get("name") and (i.get("type") or "").lower() == "hidden"}
    for s in form.find_all("select"):
        if not s.get("name"):
            continue
        o = s.find("option", selected=True) or s.find("option")
        data[s["name"]] = o.get("value", "") if o else ""
    return data


def district_links(html):
    """[(district as written, event target, n-th time this name appears)] from the summary grid; division totals are left out."""
    out, count = [], {}
    grid = _esw.soup(html).find("table", id="gridEntry1")
    for a in (grid.find_all("a", href=True) if grid is not None else []):
        m = re.search(r"__doPostBack\(\s*['\"](gridEntry1\$ctl\d+\$ben_name)['\"]", a["href"])
        name = _esw.clean(a.get_text(" "))
        if not m or not name or re.search(r"(?i)division", name):
            continue
        count[name] = count.get(name, 0) + 1
        out.append((name, m.group(1), count[name]))
    return out


def items(get=None):
    if get is None:
        return []
    r = get(URL)
    if r is None:
        return []
    out = []
    for name, target, n in district_links(r.text):
        key = f"sub2_up_prd-{_esw.slug(name)}" + (f"-{n}" if n > 1 else "")
        out.append({"key": key, "payload": {"reader": MODULE, "url": URL, "state": "UP", "district_as_written": name, "nth": n,
                                            "district": district(name), "target": target}})
    return out


def rows(html, where=None):
    """[{district, block, post, name, mobile, whatsapp, gender}] of table#gridEntryDist. where: a list; when given, it gets each
    row's src_pos."""
    t = _esw.soup(html).find("table", id="gridEntryDist")
    if t is None:
        return []
    tp = []
    g = _esw.grid(t, pos=tp)
    out = []
    for r, pos in zip(g[1:], tp[1:]):
        if len(r) < 7 or not re.fullmatch(r"\d+", r[0].strip()):
            continue
        if where is not None:
            where.append(pos)
        out.append({"district": r[1], "block": r[2], "post": r[3].strip().upper(), "name": r[4], "mobile": r[5], "whatsapp": r[6],
                    "gender": r[7] if len(r) > 7 else ""})
    return out


def _person(name, block):
    n = _esw.clean(name)
    if not re.search(r"[A-Za-zऀ-ॿ]{2}", n) or re.match(r"(?i)^(ado|bdo|b\.d\.o|a\.d\.o)\b", n) or \
            re.search(r"(?i)vacant|rikt|रिक्त", n):
        return ""
    return n


def build(found, dist, seen, source, where=None, src=None):
    """where: src_pos per row of found; src: provenance.at() of the answer (GET and POST of one url)."""
    recs = []
    for r, pos in zip(found, where or [None] * len(found)):
        post = POSTS.get(r["post"])
        if not post or not r["block"].strip():
            continue
        area = _esw.clean(r["block"]).title()
        base = f"UP-{_esw.slug(dist)}:{_esw.slug(area)}:{r['post'].lower()}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="rural_development", level="block", area=area, post=post,
                                name=_person(r["name"], r["block"]), phone=_esw.phones(r["mobile"], r["whatsapp"]),
                                whatsapp=_esw.phones(r["whatsapp"]), district=dist, state="UP", source=source, src_pos=pos,
                                **(src or {})))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    links = district_links(r.text)
    want = p.get("district_as_written", "")
    target = next((t for name, t, n in links if name == want and n == int(p.get("nth", 1))), None) or p.get("target")
    if not target:
        return [], [], "district link not found"
    data = form_fields(r.text)
    data.update({"__EVENTTARGET": target, "__EVENTARGUMENT": ""})
    a = get(url, method="POST", data=data)
    if a is None:
        return [], [], "no answer to the district link"
    tag = _esw.slug(want) + (f"-{p['nth']}" if int(p.get("nth", 1)) > 1 else "")
    files = [_esw.keep(MODULE, f"district-{tag}", a.content)]
    dist = p.get("district") or district(want)
    where = []
    recs = build(rows(a.text, where), dist, set(), url, where, provenance.at(a, url))
    return recs, files, "" if recs else "no rows"
