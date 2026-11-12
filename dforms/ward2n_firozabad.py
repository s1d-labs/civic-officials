"""Firozabad Nagar Nigam (firozabadnagarnigam.com): the sanitation officers of each of its 70 wards. One page per ward,
/SafaiKaramcharis.aspx?ctid=<ward no> ("Safai Karamcharis List", ctid 1-70; saved in archive.s1d.me 2026-11-11). The heading
"वार्ड - <ward name>" names the ward; ctid is the ward number (checked: ctid 1 = सैलई = ward 1 Salai, ctid 2 = विजय नगर = ward 2
Vijay Nagar in the ward map layer). Table gvData1: पदनाम | नाम | मोबाइल नं, three rows: सेनेटरी एवं फ़ूड इंस्पेक्टर (sanitary and
food inspector), जोनल सेनेटरी ऑफिसर (zonal sanitary officer), सफाई नायक (sanitation supervisor). Table gvData (the sweepers of the
ward, with place and kind of work) is not read: it lists workers, not officers. The page shows no date.
Records: one per post per ward, level "ward", wards [n], area_regional = the ward name. Names are Hindi: name and name_regional
carry the same text. Record ids: dept:ward2n_firozabad:ward-<n>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_firozabad"
BODY, LGD, STATE, DISTRICT = "Firozabad Nagar Nigam", "249079", "UP", "Firozabad"
URL = "http://firozabadnagarnigam.com/SafaiKaramcharis.aspx?ctid={}"
WARDS = 70
POSTS = (("जोनल", "Zonal Sanitary Officer"), ("फूड|इंस्पेक्टर", "Sanitary and Food Inspector"), ("नायक", "Sanitation Supervisor"))


def items(get=None):
    return [{"key": f"{MODULE}-ward-{n}", "payload": {"reader": MODULE, "url": URL.format(n), "state": STATE, "ward": str(n)}}
            for n in range(1, WARDS + 1)]


def parse(html, p):
    soup = _esw.soup(html)
    ward = p.get("ward") or re.search(r"ctid=(\d+)", p["url"]).group(1)
    lbl = soup.find(id="lblwardname")
    wname = _esw.clean(re.sub(r"^\s*वार्ड\s*-\s*", "", lbl.get_text(" "))) if lbl else ""
    t = soup.find("table", id="gvData1")
    seen, recs = set(), []
    for tr in (t.find_all("tr") if t else []):
        tds = [_esw.clean(td.get_text(" ")) for td in tr.find_all("td")]
        if len(tds) < 4:
            continue
        post_hi, name, mob = tds[1], tds[2], tds[3]
        en = next((e for rx, e in POSTS if re.search(rx, _ward.hi_norm(post_hi))), None) or _ward.hi_post(post_hi)
        recs.append(_ward.record(MODULE, f"ward-{ward}:{_esw.slug(en)}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="ward", area=f"Ward {ward}", area_regional=wname or None, post=en,
                                 post_regional=re.sub(r"\s*का\s*नाम$", "", post_hi), name=name, name_regional=name or None,
                                 phone=mob, wards=[ward], wing="sanitation", source=p["url"], src_pos=_ward.tr_pos(tr)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"ward-{p.get('ward', '')}", r.content)], "" if recs else "no officer table"
