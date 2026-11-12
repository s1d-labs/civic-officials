"""Gujarat: fair price shops (ration shops) and their dealers from the state's iPDS portal https://ipds.gujarat.gov.in.
Source: the public "FPS Dealer List" report /FpsSale/frm_stateFPS.aspx (ASP.NET, no login, no captcha). A GET shows the first 5 rows and
a "Records to be display" select (ddlTopRows: 5, 10, 20, 0 = --ALL--); the reader posts the page's own hidden form fields back with
ddlTopRows=0 in the same run and gets every active shop of the state in one table (15,486 rows on 2026-11-11, ~32 MB answer; the GET is
~8 MB of ViewState). Columns: Sr No, FPSUID (shop id), FPS NAME (the dealer's name, in Gujarati), District, Taluka, Village, Status.
No phone, no address beyond the village, no coordinates. District names come in Gujarati; the English name is taken from the site's own
district list (codes 01-35 in the Social Audit page) and kept in "district", the Gujarati one in "district_regional". "Ahmedabad City"
(code 27, the city supply office) is kept as district "Ahmedabad" with supply_district "Ahmedabad City". Taluka and village stay in
Gujarati. Only reached from India so far (india_only). One queue item = the whole state (seeds/dept_civic_fps2_gj.json).
Record ids: dept:civic_fps2_gj:<FPSUID>. The bucket file keeps only the result table, not the ViewState.
"""
import re

from dforms import _civic_fps, _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps2_gj"
STATE = "GJ"
BASE = "https://ipds.gujarat.gov.in"
PAGE = BASE + "/FpsSale/frm_stateFPS.aspx"
INDIA_ONLY = True

# Gujarati district name (as the report writes it) -> English name, from the district list (codes 01-35) of the site's Social Audit page.
DISTRICTS = {
    "કચ્છ": "Kachchh", "બનાસકાંઠા": "Banaskantha", "પાટણ": "Patan", "મહેસાણા": "Mahesana", "સાબરકાંઠા": "Sabarkantha",
    "ગાંધીનગર": "Gandhinagar", "અમદાવાદ": "Ahmedabad", "સુરેન્દ્રનગર": "Surendranagar", "રાજકોટ": "Rajkot", "જામનગર": "Jamnagar",
    "પોરબંદર": "Porbandar", "જુનાગઢ": "Junagadh", "અમરેલી": "Amreli", "ભાવનગર": "Bhavnagar", "આણંદ": "Anand", "ખેડા": "Kheda",
    "પંચમહાલ": "Panchmahal", "દાહોદ": "Dahod", "વડોદરા": "Vadodara", "નર્મદા": "Narmada", "ભરૂચ": "Bharuch", "સુરત": "Surat",
    "ડાંગ": "Dang", "નવસારી": "Navsari", "વલસાડ": "Valsad", "તાપી": "Tapi", "અમદાવાદ શહર": "Ahmedabad", "મોરબી": "Morbi",
    "ગીર સોમનાથ": "Gir Somnath", "બોટાદ": "Botad", "અરવલ્લી": "Aravalli", "મહીસાગર": "Mahisagar", "છોટાઉદેપુર": "Chhota Udaipur",
    "દેવભુમિ દ્વારિકા": "Devbhumi Dwarka", "વાવ-થરાદ": "Vav-Tharad",
}
CITY = {"અમદાવાદ શહર": "Ahmedabad City"}


def items(get):
    return [{"key": MODULE + "-all", "payload": {"reader": MODULE, "url": PAGE, "state": STATE, "india_only": INDIA_ONLY}}]


def form_fields(html):
    """The page's own hidden ASP.NET fields (__VIEWSTATE, __EVENTVALIDATION ...), as the browser would post them back."""
    soup = _esw.soup(html)
    return {i.get("name"): i.get("value") or "" for i in soup.find_all("input", attrs={"type": "hidden"}) if i.get("name")}


def table_part(html):
    """The result table only (for the bucket file): from the dealer list fieldset to the end of its table."""
    i = html.find("FPS Dealers Details")
    if i < 0:
        return html
    j = html.find("</table>", i)
    return html[i:j + 8] if j > 0 else html[i:]


def parse(html, src=PAGE):
    recs, seen = [], set()
    soup = _esw.soup(html)
    for tr in soup.find_all("tr", class_="dg_Item"):
        tds = [_esw.clean(td.get_text(" ")) for td in tr.find_all("td")]
        if len(tds) < 7 or not re.fullmatch(r"\d+", tds[1]):
            continue
        fid, name, dist_gu, taluka, village, status = tds[1], _civic_fps.name_of(tds[2]), tds[3], tds[4], tds[5], tds[6]
        if fid in seen or not name:
            continue
        seen.add(fid)
        recs.append(_esw.record(
            MODULE, fid, dept="food_supplies", level="facility", layer="fps", area=taluka, area_regional=taluka,
            post=_civic_fps.POST, name=name, state=STATE, district=DISTRICTS.get(dist_gu, dist_gu), district_regional=dist_gu,
            supply_district=CITY.get(dist_gu, ""), subdistrict=taluka, block=taluka, village=village, fps_id=fid, office_id=fid,
            status=status, source=src))
    return recs


def fetch(p, get):
    url = p.get("url") or PAGE
    page = get(url)
    if page is None:
        return [], [], "no page"
    form = form_fields(page.text)
    if "__VIEWSTATE" not in form:
        return [], [], "no form on the page"
    form.update({"ddlTopRows": "0", "__EVENTTARGET": "ddlTopRows", "__EVENTARGUMENT": ""})
    r = get(url, method="POST", data=form, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r is None:
        return [], [], "no answer to the ALL request"
    table = table_part(r.text)                # the 32 MB answer is mostly ViewState: parse and keep the table only
    recs = parse(table, url)
    return recs, [_esw.keep(MODULE, "dealer-list", table)], "" if recs else "no rows"
