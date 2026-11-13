"""Rajasthan: fair price shops (ration shops), their dealers and the dealers' mobiles from the Food & Civil Supplies Department site
https://food.rajasthan.gov.in, page FairPriceShop.aspx ("एफपीएस संपर्क सूची" = FPS contact list, "ग्रामीण और शहरी जिले वार एफपीएस दुकान
सूची"). ASP.NET form, no login, no captcha: the reader GETs the page and posts its own hidden fields back with one district
(ddl_All_District) and the Search button (txt_Search), as the browser does. The answer is one table (GridViewFPSRuralUrban) with every
shop of the district, rural and urban: FPS code, dealer name in Hindi and in English, shop name, address (mostly empty), town / village,
panchayat, block, municipality (nagar palika), tehsil and contact number (the dealer's mobile, in full; "0" = none). Kota gave 545 shops.
The select has no autopostback; posting the select itself as __EVENTTARGET fails (the site sends you to its error page).
No coordinates here: the site's GeoTag.aspx map has lat/lon but its page shows only the first 2,000 shops of the state and its filters
need the browser's map script (not used). One queue item per district (41, codes from the page's own list, saved 2026-11-11;
seeds/dept_civic_fps2_rj.json). Only reached from India so far (india_only). Record ids: dept:civic_fps2_rj:<FPS code>.
"""
import re

from dforms import _civic, _civic_fps, _esw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps2_rj"
STATE = "RJ"
BASE = "https://food.rajasthan.gov.in"
PAGE = BASE + "/FairPriceShop.aspx"
INDIA_ONLY = True
P = "ctl00$ContentPlaceHolder1$"


def districts(html):
    sel = _esw.soup(html).find("select", attrs={"name": P + "ddl_All_District"})
    return [(o.get("value"), _esw.clean(o.get_text())) for o in (sel.find_all("option") if sel else [])
            if (o.get("value") or "").strip() not in ("", "-1", "0")]


def items(get):
    page = get(PAGE)
    pay = {"reader": MODULE, "url": PAGE, "state": STATE, "india_only": INDIA_ONLY}
    return [{"key": f"{MODULE}-{c}", "payload": dict(pay, dist_code=c, district_regional=n)}
            for c, n in (districts(page.text) if page is not None else [])]


def form_fields(html):
    soup = _esw.soup(html)
    return {i.get("name"): i.get("value") or "" for i in soup.find_all("input", attrs={"type": "hidden"}) if i.get("name")}


def parse(html, district="", district_regional="", dist_code="", src=PAGE):
    soup = _esw.soup(html)
    table = soup.find("table", id=re.compile("GridViewFPS")) or soup.find("table", id=re.compile("GridView"))
    recs, seen = [], set()
    if table is None:
        return recs
    for tr in table.find_all("tr"):
        tds = [_esw.clean(td.get_text(" ")) for td in tr.find_all("td")]
        if len(tds) < 12 or not re.fullmatch(r"\d+", tds[1]):
            provenance.skip_row(tds, "no fps_id")
            continue
        fid, name_hi, name_en, shop, addr, place, panchayat, block, town, tehsil, phone = tds[1:12]
        name_hi, name_en = _civic_fps.name_of(name_hi), _civic_fps.name_of(name_en)
        name = name_en or name_hi
        if fid in seen or not name:
            provenance.skipped("repeated fps_id or no name")
            continue
        seen.add(fid)
        urban = bool(town) and not (panchayat or block)
        recs.append(_esw.record(
            MODULE, fid, dept="food_supplies", level="facility", layer="fps", area=place, post=_civic_fps.POST, name=name,
            name_regional=name_hi if name_hi != name else "", phone=_civic_fps.unmasked(phone), address=addr, shop_name=shop,
            state=STATE, district=district, district_regional=district_regional, dist_code=dist_code, village=place,
            panchayat=panchayat, block=block or town, municipality=town, subdistrict=tehsil, area_type="urban" if urban else "rural",
            fps_id=fid, office_id=fid, source=src, src_pos=_civic.tr_pos(tr)))
    return recs


def fetch(p, get):
    url = p.get("url") or PAGE
    page = get(url)
    if page is None:
        return [], [], "no page"
    dists = [(str(p["dist_code"]), p.get("district_regional", ""))] if p.get("dist_code") else districts(page.text)
    if not dists:
        return [], [], "no district list"
    base = form_fields(page.text)
    if "__VIEWSTATE" not in base:
        return [], [], "no form on the page"
    recs, files = [], []
    for code, dname in dists:
        form = dict(base)
        form.update({P + "ddl_All_District": code, P + "txtSearch": "", P + "txt_Search": "Search", P + "ddlAreaType": "-1"})
        r = get(url, method="POST", data=form, headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": url})
        if r is None:
            continue
        files.append(_esw.keep(MODULE, f"district-{code}", r.content))
        recs += _civic.tag(parse(r.text, p.get("district", "") if p.get("dist_code") else "", dname, code, url), r, url)
    return recs, files, "" if recs else "no rows"
