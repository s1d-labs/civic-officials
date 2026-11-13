"""Gujarat Police headquarters (Director General of Police, Gandhinagar): the org chart of the DGP office on the state police CMS,
https://police.gujarat.gov.in/dgp/CMS.aspx?orgchart=true (the same CMS as the unit sites that dforms/police_gj.py reads; its
orgchart() and contact() are imported, not changed). Checked 2026-11-13 from dev-vps-3: 79 designations (2026-11-13): the DGP,
ADGPs and IGPs of the HQ branches (administration, law and order, CID crime, intelligence, training, armed units, SCRB, traffic
...), the 4 Commissioners of Police (Ahmedabad, Vadodara, Surat, Rajkot), the 9 range IGs / DIGs and, under each range, the SPs
of its districts. Each designation page has the office contact table (name, designation, address, phone, mobile, fax, e-mail).
Text and digits are Gujarati; digits become ASCII, text stays Gujarati (post and name in Gujarati, post_en for the rank).

Records (dforms/_state.py): range IG / DIG -> level division (division = the range as written, districts = LGD codes of the SPs
under it in the chart, else dforms/st_div_gj.json); SP / CP -> level district (district + district_code from the Gujarati
district name); every other post -> level state (body "Police Headquarters, Gandhinagar"). dept police, body_kind police.
Route: India only (every *.gujarat.gov.in police host timed out from Germany, police_gj note); answers from Mumbai: direct or
proxy. One queue item = the org chart + one page per designation (~80 GETs). Record ids: dept:st_gj_police_hq:<designation id>.
"""
import re

from dforms import _police, _state
from dforms.police_gj import contact, norm, orgchart

METHOD = "html page (org chart + designation contact table)"

M = "st_gj_police_hq"
URL = "https://police.gujarat.gov.in/dgp/CMS.aspx?orgchart=true"
BODY = "Police Headquarters, Gandhinagar"

# Gujarati district names (letters as the chart writes them, spaces and hyphens dropped) -> LGD code
GJ = {"અમદાવાદ": "438", "અમરેલી": "439", "આણંદ": "440", "અરવલ્લી": "672", "બનાસકાંઠા": "441", "ભરૂચ": "442", "ભાવનગર": "443",
      "બોટાદ": "676", "છોટાઉદેપુર": "668", "દાહોદ": "445", "ડાંગ": "444", "દેવભૂમિદ્વારકા": "674", "ગાંધીનગર": "446",
      "ગીરસોમનાથ": "675", "જામનગર": "447", "જુનાગઢ": "448", "કચ્છ": "449", "ખેડા": "450", "મહેસાણા": "451", "મહીસાગર": "669",
      "મોરબી": "673", "નર્મદા": "452", "નવસારી": "453", "પંચમહાલ": "454", "પાટણ": "455", "પોરબંદર": "456", "રાજકોટ": "457",
      "સાબરકાંઠા": "458", "સુરત": "459", "સુરેન્દ્રનગર": "460", "તાપી": "641", "વડોદરા": "461", "વલસાડ": "462", "વાવથરાદ": "789"}
LGD_EN = {"438": "Ahmedabad", "439": "Amreli", "440": "Anand", "672": "Arvalli", "441": "Banas Kantha", "442": "Bharuch",
          "443": "Bhavnagar", "676": "Botad", "668": "Chhotaudepur", "445": "Dahod", "444": "Dangs", "674": "Devbhumi Dwarka",
          "446": "Gandhinagar", "675": "Gir Somnath", "447": "Jamnagar", "448": "Junagadh", "449": "Kachchh", "450": "Kheda",
          "451": "Mahesana", "669": "Mahisagar", "673": "Morbi", "452": "Narmada", "453": "Navsari", "454": "Panch Mahals",
          "455": "Patan", "456": "Porbandar", "457": "Rajkot", "458": "Sabar Kantha", "459": "Surat", "460": "Surendranagar",
          "641": "Tapi", "461": "Vadodara", "462": "Valsad", "789": "Vav-Tharad"}
# range word in the post -> the English range name of dforms/st_div_gj.json
RANGES = [("અમદાવાદ રેન્જ", "Ahmedabad Range"), ("ગાંધીનગર રેન્જ", "Gandhinagar Range"), ("વડોદરા રેન્જ", "Vadodara Range"),
          ("સુરત રેન્જ", "Surat Range"), ("જુનાગઢ રેન્જ", "Junagadh Range"), ("રાજકોટ રેન્જ", "Rajkot Range"),
          ("સરહદી રેન્જ", "Border Range"), ("ભાવનગર રેન્જ", "Bhavnagar Range"), ("ગોધરા રેન્જ", "Panchmahal-Godhra Range")]
RANK_EN = [(r"અધિક\s*પોલીસ\s*મહાનિદેશક", "Additional Director General of Police"),
           (r"નાયબ\s*પોલીસ\s*મહાનિ(રી|રિ)ક્ષક", "Deputy Inspector General of Police"),
           (r"પોલીસ\s*મહાનિદેશક", "Director General of Police"),
           (r"પોલીસ\s*મહાનિ(રી|રિ)ક્ષક", "Inspector General of Police"),
           (r"પોલીસ\s*કમિશ્?ન્?ર|પોલીસ\s*કમિશનર", "Commissioner of Police"),
           (r"નાયબ\s*પોલીસ\s*અધિક્ષક", "Deputy Superintendent of Police"),
           (r"પોલીસ\s*અધ(િ|ી)ક્ષક", "Superintendent of Police")]


# rank (English) -> _state post_kind; given here because _state.post_kind("Deputy Inspector General ...") answers "igp"
KIND = {"Director General of Police": "dgp", "Additional Director General of Police": "adgp",
        "Inspector General of Police": "igp", "Deputy Inspector General of Police": "dig", "Commissioner of Police": "cp",
        "Superintendent of Police": "sp", "Deputy Superintendent of Police": "dysp"}


def key(s):
    return re.sub(r"[\s\-‌‍,.()]", "", s or "")


def district_of(text):
    """LGD code of the Gujarati district name in a post ("પોલીસ અધિક્ષક, ગીર-સોમનાથ" -> 675), longest name first; ''."""
    k = key(text)
    for name in sorted(GJ, key=len, reverse=True):
        if name in k:
            return GJ[name]
    return ""


def rank_en(text):
    t = norm(text)
    for rx, en in RANK_EN:
        if re.search(rx, t):
            return en
    return ""


def range_of(text):
    t = norm(text)
    if "રેન્જ" not in t:
        return ""
    return next((en for gu, en in RANGES if key(gu) in key(t)), "")


def classify(text, parents):
    """(level, range English name, district code) of one org chart post."""
    en = rank_en(text)
    rng = range_of(text)
    if rng and en in ("Inspector General of Police", "Deputy Inspector General of Police"):
        return "division", rng, ""
    if en in ("Superintendent of Police", "Commissioner of Police"):
        code = district_of(text)
        if code and not re.search(r"સ્ટેટ|તકનિકી|મોટર|સ્ટાફ|SCRB", norm(text)):     # HQ branch SPs sit in Gandhinagar too
            return "district", "", code
    if en == "Deputy Inspector General of Police" and district_of(text) and "ગ્રામ્ય" in norm(text):
        return "district", "", district_of(text)      # "નાયબ પોલીસ મહાનિરીક્ષક, રાજકોટ ગ્રામ્ય": the rural SP post held by a DIG
    return "state", "", ""


def build(chart, pages, url=URL):
    """chart: orgchart() rows; pages: {designation id: (page url, contact dict)} -> records."""
    base = url.split("CMS.aspx")[0]
    kids = {}
    for did, text, depth, parents in chart:
        if parents:
            kids.setdefault(parents[-1], []).append(text)
    recs = []
    for n, (did, text, depth, parents) in enumerate(chart, 1):
        durl, c = pages.get(did, (f"{base}CMS.aspx?orgchart=true&designation_id={did}", None))
        c = c or {}
        post = c.get("designation") or text
        lv, rng, code = classify(text, parents)
        districts = [] if lv == "district" else None     # a district row: no range district list
        if lv == "division":
            districts = sorted({district_of(k) for k in kids.get(text, []) if district_of(k)}) or None
        mob, land = _police.phones(c.get("mobile") or ""), _police.phones(c.get("phone") or "")
        parent_range = next((range_of(p) for p in reversed(parents) if range_of(p)), "")
        recs.append(_state.rec(
            M, did, state="GJ", level=lv, post=post, post_en=rank_en(post) or None, name=c.get("name") or "",
            post_kind=KIND.get(rank_en(post)) or _state.post_kind(post) or None, body=BODY if lv == "state" else post, body_kind="police",
            dept="police", department="Home Department (Police)", division=rng or (parent_range if lv == "district" else ""),
            districts=districts, district=LGD_EN.get(code, ""), district_code=code, phone=_police.phones(mob, land), mobile=mob or None,
            landline=land or None, fax=_police.phones(c.get("fax") or "") or None, email=c.get("email") or "",
            address=re.sub(r"\s*,(\s*,)+", ",", c.get("address") or "").strip(" ,"), parents=parents or None,
            chart_depth=depth, office_id=did, src_url=durl, src_pos={"orgchart_row": n, "designation_id": did}))
    return recs


def items(get=None):
    return [{"key": f"{M}:dgp", "payload": {"reader": M, "url": URL, "state": "GJ", "india_only": True, "route": "direct"}}]


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_police.gz(M, "dgp/orgchart.html", r.content)]
    chart = orgchart(r.text)
    base = url.split("CMS.aspx")[0]
    pages = {}
    for did, *_ in chart:
        durl = f"{base}CMS.aspx?orgchart=true&designation_id={did}"
        x = get(durl)
        if x is None:
            continue
        files.append(_police.gz(M, f"dgp/designation-{did}.html", x.content))
        pages[did] = (durl, contact(x.text))
    recs = build(chart, pages, url)
    return recs, files, "" if recs else "empty org chart"
