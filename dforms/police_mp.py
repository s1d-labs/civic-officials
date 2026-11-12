"""Madhya Pradesh: district police sites <district>.mppolice.gov.in. The home page section "Know your police station" (#KYPS)
embeds a Google My Maps map (google.com/maps/d/u/0/embed?mid=<mid>) that the district police keep; its KML export
(www.google.com/maps/d/kml?mid=<mid>&forcekml=1) has one Placemark per station: name, description "Mobile: ..<br>Telephone:
..<br>Email: ..", ExtendedData, Point coordinates; Folder = zone. Mobiles are the station CUG numbers (Bhopal 9479990xxx); no
SHO names. Works from outside India. One queue item = one district site (2 requests).
Record id dept:police_mp:<district>:<station>."""
import html as htmlmod
import re
from xml.etree import ElementTree as ET

from dforms._police import clean, email, gz, phones, rec, slug, uniq

METHOD = "kml (Google My Maps export)"     # source trail (provenance.py): how this reader reads its sources

M = "police_mp"
KML = "https://www.google.com/maps/d/kml?mid={mid}&forcekml=1"
NS = "{http://www.opengis.net/kml/2.2}"
MID = re.compile(r"google\.com/maps/d/(?:u/\d+/)?(?:embed|viewer|edit)\?mid=([\w-]+)")


def find_mid(html):
    m = MID.search(html or "")
    return m.group(1) if m else None


def _num(v):
    """ExtendedData keeps numbers as floats: 9.479990444E9 -> 9479990444."""
    v = clean(v) or ""
    if re.fullmatch(r"\d\.\d+E\d+", v, re.I):
        return str(int(float(v)))
    return v


def parse_kml(text, district, url):
    root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    doc = root.find(f"{NS}Document")
    title = clean(doc.findtext(f"{NS}name")) if doc is not None else None
    recs = []

    def walk(node, zone):
        for el in node:
            tag = el.tag.replace(NS, "")
            if tag == "Folder":
                walk(el, clean(el.findtext(f"{NS}name")) or zone)
            elif tag == "Placemark":
                name = clean(el.findtext(f"{NS}name"))
                if not name:
                    continue
                desc = el.findtext(f"{NS}description") or ""
                desc_t = clean(htmlmod.unescape(re.sub(r"<br\s*/?>", "\n", desc, flags=re.I)).replace("\n", " | "))
                desc_t = re.sub(r"<[^>]+>", " ", desc_t or "")
                ext = {clean(d.get("name") or "").lower(): _num(d.findtext(f"{NS}value")) for d in el.iter(f"{NS}Data")}
                mob = ext.get("mobile") or ext.get("mobile no") or ""
                tel = ext.get("telephone") or ext.get("phone") or ""
                mail = ext.get("email") or ext.get("e-mail") or ""
                for lab, val in re.findall(r"(Mobile|Telephone|Phone|Email|E-mail)\s*(?:No\.?)?\s*:\s*([^|]*)", desc_t, re.I):
                    lab = lab.lower()
                    if lab == "mobile":
                        mob = mob or val
                    elif lab in ("telephone", "phone"):
                        tel = tel or val
                    else:
                        mail = mail or val
                if not (mob or tel or mail):
                    tel = desc_t
                lat = lon = None
                co = clean(el.findtext(f".//{NS}coordinates"))
                if co:
                    parts = co.split(",")
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                    except (ValueError, IndexError):
                        pass
                ph = phones(mob, tel)     # 10-digit landlines without their 0 (Indore 7312711108) stay as published
                level = "police_station"
                otype = "police post" if re.search(r"chowki|chauki|out ?post|\bP\.?P\b", name, re.I) else "police station"
                if re.search(r"\b(S\.?P|DCP|ACP|CSP|SDOP|ASP|Commissioner|Control Room|Police Line)\b", name, re.I):
                    level, otype = "district", "office"
                recs.append(rec(M, f"{slug(district)}:{slug(name)}", level=level, office_type=otype, area=name,
                                post="SHO" if otype == "police station" else "Officer in charge" if otype == "police post" else name,
                                phone=ph, email=email(mail), zone=zone, unit=title, state="MP", district=district,
                                lat=lat, lon=lon, source=url))

    if doc is not None:
        walk(doc, None)
    return uniq(recs)


def fetch(p, get):
    url = p["url"]
    district = p.get("district") or re.sub(r"^https?://([^.]+)\..*$", r"\1", url).title()
    files = []
    mid = p.get("mid")
    if not mid:
        r = get(url)
        if r is None:
            return [], [], "no answer"
        files.append(gz(M, f"{slug(district)}-home.html", r.content))
        mid = find_mid(r.text)
        if not mid:
            return [], files, "no map on the home page"
    k = get(KML.format(mid=mid))
    if k is None:
        return [], files, "kml did not answer"
    files.append(gz(M, f"{slug(district)}-{mid}.kml", k.content))
    try:
        recs = parse_kml(k.content, district, url)
    except ET.ParseError:
        return [], files, "kml not xml"
    for _, d in recs:
        d["map"] = f"https://www.google.com/maps/d/viewer?mid={mid}"
    return recs, files, "" if recs else "empty map"
