"""West Bengal: Bidhannagar Police Commissionerate (North 24 Parganas), bidhannagarcitypolice.gov.in/police_station.php (PHP page
by SeMT WB). Station cards under zone headings (<h4>Bidhannagar Zone</h4>, Airport Zone, New Town Zone, Detective Department):
<div class="card-header">Bidhannagar East PS</div> <h5>Contact No.: 9147889496 / 9147889451</h5> <p>Email: ...</p>; then
traffic blocks (<h5><b> Traffic Control Room</b></h5> <p>📞 9051213100 ...</p>: traffic guards, helpline) and the Special Branch
and control room numbers. No officer names on the page. Kept: one record per station (level police_station; Cyber-Crime PS
office_type cyber police station, Women PS women police station), one per traffic guard / control room / helpline block
(level district, office_type traffic / control room). The state site (wbpolice.gov.in, policewb.gov.in), Kolkata Police and the
other commissionerates (Howrah, Barrackpore, Asansol-Durgapur, Siliguri, Chandannagar) did not answer from Mumbai on
2026-11-13 (archive: no 200 copy from any vantage). Answers from Mumbai; from abroad unchecked. One queue item = the page.
Record id dept:police3_wb:bidhannagar:<station or block>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq

METHOD = "html cards"

M = "police3_wb"
URL = "https://bidhannagarcitypolice.gov.in/police_station.php"
UNIT = "Bidhannagar Police Commissionerate"
DISTRICT = "North 24 Parganas"


def otype_of(name):
    if re.search(r"cyber", name, re.I):
        return "cyber police station"
    if re.search(r"women|mahila", name, re.I):
        return "women police station"
    return "police station"


def parse_bidhannagar(html, url=URL, state="WB"):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for i, card in enumerate(soup.select("div.card-header")):
        name = clean(card.get_text(" ", strip=True))
        body = card.find_next_sibling("div")
        if not name or body is None:
            continue
        h5 = body.find("h5")
        p = body.find("p")
        zone_h = card.find_previous("h4")
        zone = clean(zone_h.get_text(" ", strip=True)) if zone_h else None
        contact = clean(h5.get_text(" ", strip=True)) if h5 else ""
        if not re.match(r"Contact", contact, re.I):      # "Bidhannagar Traffic" / "Special Branch": a heading card, blocks below
            continue
        mail = re.sub(r"^\s*E-?mail\s*:?\s*", "", clean(p.get_text(" ", strip=True)) if p else "", flags=re.I)
        recs.append(rec(M, f"bidhannagar:{slug(name)}", level="police_station", office_type=otype_of(name), area=name,
                        post="Officer in charge", phone=phones(re.sub(r"^Contact No\.?\s*:?\s*-?", "", contact)), email=email(mail),
                        zone=zone, circle=zone, state=state, district=DISTRICT, unit=UNIT, source=url,
                        src_pos={"card": i, "zone": zone}))
    for i, b in enumerate(soup.select("h5 > b")):
        title = clean(b.get_text(" ", strip=True))
        p = b.parent.find_next_sibling("p")
        if not title or p is None:
            continue
        txt = p.get_text(" ", strip=True)
        nums = re.findall(r"(?:0\d{2,4}[\s-]*)?\d[\d\s-]{6,12}\d", txt.split("💬")[0] if "💬" in txt else txt)
        whatsapp = re.findall(r"💬\s*(\d{10})", txt)
        level, otype = "district", ("control room" if re.search(r"control room|emergency", title, re.I) else
                                    "traffic" if re.search(r"traffic", title, re.I) else "unit")
        recs.append(rec(M, f"bidhannagar:{slug(title)}", level=level, office_type=otype, area=title, post=title,
                        phone=phones(*nums), whatsapp=", ".join(whatsapp) or None, state=state, district=DISTRICT, unit=UNIT,
                        source=url, src_pos={"block": i, "title": title}))
    foot = soup.get_text(" | ", strip=True)
    m = re.search(r"Control Room \(24x7\):\s*\|\s*([\d\s|/-]+?)\s*\|\s*Special", foot)
    if m:
        recs.append(rec(M, "bidhannagar:control-room-24x7", level="district", office_type="control room", area="Control Room (24x7)",
                        post="Control Room (24x7)", phone=phones(*re.split(r"\s*[|/]\s*", m.group(1))), state=state,
                        district=DISTRICT, unit=UNIT, source=url, src_pos={"footer": "Control Room (24x7)"}))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse_bidhannagar(r.text, url, p.get("state", "WB"))
    return recs, [gz(M, "bidhannagar", r.content)], "" if recs else "no rows"
