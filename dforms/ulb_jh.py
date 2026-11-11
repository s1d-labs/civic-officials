"""Jharkhand: the Urban Development & Housing Department's page for each urban body, udhd.jharkhand.gov.in/ULB/<Name>/<Name>.aspx
(ASP.NET, one template; 48 pages that answer 200 in archive.s1d.me, saved 2026-11-05). Answers only from India (no answer from
Germany on 2026-11-11; the India server got the page).

Each page may show one or two officer cards (AdminLTE "widget-user": h3.widget-user-username = name, h5.widget-user-desc = post,
h5.description-header lines = phone and email): the head of the body (Executive Officer, Municipal Commissioner, Additional or
Deputy Municipal Commissioner) and on some pages the district's Deputy Commissioner. The Deputy Commissioner card is left out: it
is the district head, not an officer of the body. 14 of the 48 archive copies show a head card (2026-11-05); the others show none
or only a prose "Desk of Executive Officer" text (Garhwa), which is not read.
The footer gives the body office (address, phone, fax, email) and "Last Updated: dd/mm/yyyy": address, office_phone,
office_email and last_updated go on the first card's record, or on an "Office" record when the page has no card. The card
of Chas and Mango names an Additional / Deputy Municipal Commissioner: the officer in charge, but role_of() gives "deputy".
Body names and districts come from the department's own list, udhd.jharkhand.gov.in/Other/ULBInformation.aspx
(seeds/raw/jharkhand-ULBInformation.html, its district column as written; Hariharganj and Mahagama are only in ContactUs4.aspx, their
districts Palamu and Godda are from LGD). Area = that name with the type word
split off into body_type ("Chas Municipal Corporation" -> area "Chas", body_type "Municipal Corporation").
Ranchi Municipal Corporation has no page in this template (its own site, ranchimunicipal.com).
"""
import re

from dforms import _esw, _ulb

MODULE = "ulb_jh"
STATE = "JH"
BASE = "https://udhd.jharkhand.gov.in/"
# path | district | name as the department's list writes it
PAGES = """ulb/Adityapur/Adityapur.aspx|East Singhbhum|Adityapur Municipal Corporation
ULB/Bachra/Bachra.aspx|Chatra|Bachra Nagar Panchayat
ULB/Badakisarai/Badakisarai.aspx|Giridih|Badaki Saraiya Nagar Panchayat
ULB/Barharwa/Barharwa.aspx|Sahibganj|Barharwa Nagar Panchayat
ULB/Basukinath/Basukinath.aspx|Dumka|Basukinath Nagar Panchayat
ULB/Bishrampur/Bishrampur.aspx|Palamu|Bishrampur Nagar Parishad
ulb/bundu/bundu.aspx|Ranchi|Bundu Nagar Panchayat
ULB/Chaibasa/Chaibasa.aspx|West Singhbhum|Chaibasa Nagar Parishad
ULB/Chakradharpur/Chakradharpur.aspx|West Singhbhum|Chakradharpur Nagar Parishad
ulb/Chakuliya/Chakuliya.aspx|East Singhbhum|Chakulia Nagar panchayat
ulb/chas/chas.aspx|Bokaro|Chas Municipal Corporation
ulb/chatra/chatra.aspx|Chatra|Chatra Nagar Parishad
ulb/Chhattarpur/Chhattarpur.aspx|Palamu|Chhatarpur Nagar Panchayat
ULB/Chir/Chirkunda.aspx|Dhanbad|Chirkunda Nagar Parishad
ulb/deoghar/deoghar.aspx|Deoghar|Deoghar Municipal Corporation
ulb/Dhanbad/Dhanbad.aspx|Dhanbad|Dhanbad Municipal Corporation
ULB/Domchach/Domchach.aspx|Koderma|Domchanch Nagar Panchayat
ULB/Dumka/Dumk.aspx|Dumka|Dumka Nagar Parishad
ulb/Garhwa/Garhwa.aspx|Garhwa|Garhwa Nagar Parishad
ulb/Giridih/Giridih.aspx|Giridih|Giridih Municipal Corporation
ULB/Godda/Godda.aspx|Godda|Godda Nagar Parishad
ULB/Gumla/Gumla.aspx|Gumla|Gumla Nagar Parishad
ULB/Hariharganj/Hariharganj.aspx|Palamu|Hariharganj Nagar Panchayat
ULB/Hazaribag/Hazaribag.aspx|Hazaribag|Hazaribagh Municipal Corporation
ULB/Hussainabad/Hussainabad.aspx|Palamu|Hussainabad Nagar Panchayat
ULB/Jamshedpur/Jamshedpur.aspx|East Singhbhum|Jamshedpur NAC
ULB/Jamtara/Jamtara.aspx|Jamtara|Jamtara Nagar Panchayat
ULB/Jhumritilaiya/Jhumritilaiya.aspx|Koderma|Jhumritilaiya Nagar Parishad
ULB/Jugsalai/Jugsalai.aspx|East Singhbhum|Jugsalai Nagar Parishad
ULB/kapali/kapali.aspx|Saraikela|Kapali Nagar Parishad
ulb/Khunti/khunti.aspx|Khunti|Khunti Nagar Panchayat
ULB/Koderma/Koderma.aspx|Koderma|Koderma Nagar Panchayat
ULB/Latehar/Latehar.aspx|Latehar|Latehar Nagar Panchayat
ULB/Lohardaga/Lohardaga.aspx|Lohardaga|Lohardaga Nagar Parishad
ULB/Madhupur/Madhupur.aspx|Deoghar|Madhupur Nagar Parishad
ULB/Mahagama/Mahagama.aspx|Godda|Mahagama Nagar Panchayat
ULB/mango/mango.aspx|East Singhbhum|Mango Municipal Corporation
ULB/Manjhiaon/Manjhiaon.aspx|Garhwa|Manjhiaon Nagar Panchayat
ULB/Medininagar/Medininagar.aspx|Palamu|Medininagar Municipal Corporation
ULB/Mihijham/Mihijham.aspx|Jamtara|Mihijham Nagar Parishad
ULB/NagarUttari/NagarUttari.aspx|Garhwa|Nagar Uttari Nagar Panchayat
ULB/Pakur/Pakur.aspx|Pakur|Pakur Nagar Parishad
ulb/phusro/phusro.aspx|Bokaro|Phusro Nagar Parishad
ULB/Rajmahal/Rajmahal.aspx|Sahibganj|Rajmahal Nagar Panchayat
ULB/Ramgarh/Ramgarh.aspx|Ramgarh|Ramgarh Nagar Parishad
ULB/Sahibganj/Sahibganj.aspx|Sahibganj|Sahibganj Nagar Parishad
ULB/Saraikela/Saraikela.aspx|Saraikela|Saraikela Nagar Panchayat
ULB/Simdega/Simdega.aspx|Simdega|Simdega Nagar Parishad"""
TYPE = re.compile(r"(?i)\s+(municipal\s+corporation|nagar\s+parishad|nagar\s+panchayat|nac)$")
SKIP = re.compile(r"(?i)^deputy\s+commissioner\b|^d\.?\s?c\.?$")


def items(get=None):
    out = []
    for line in PAGES.splitlines():
        path, district, name = line.split("|")
        out.append({"key": f"{MODULE}-{_esw.slug(path.split('/')[1])}",
                    "payload": {"reader": MODULE, "url": BASE + path, "body": name, "district": district, "state": STATE,
                                "india_only": True}})
    return out


def split_type(name):
    """'Chas Municipal Corporation' -> ('Chas', 'Municipal Corporation'); 'Jamshedpur NAC' -> ('Jamshedpur', 'NAC')."""
    name = _esw.clean(name)
    m = TYPE.search(name)
    return (name[:m.start()].strip(), m.group(1)) if m else (name, None)


def footer(soup):
    """(address, phone, email, last updated as yyyy-mm-dd) of the body office."""
    lab = soup.find(id="Label7")
    addr = phone = email = ""
    if lab:
        box = lab.parent
        lines = [_esw.clean(x) for x in box.get_text("\n").split("\n") if _esw.clean(x)]
        rest = [x for x in lines[1:] if not re.match(r"(?i)(phone|fax|e-?mail)", x)]
        addr = re.sub(r"\s*,(\s*,)+", ",", ", ".join(rest))
        phone = _esw.phones(" ".join(x for x in lines if re.match(r"(?i)phone", x)))
        email = _esw.emails(" ".join(x for x in lines if re.match(r"(?i)e-?mail", x)))
    lu = soup.find(id="lblLastupdated")
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", _esw.clean(lu.get_text()) if lu else "")
    return addr, phone, email, (f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None)


def parse(html, body="", district=None, url=""):
    soup = _esw.soup(html)
    area, btype = split_type(body)
    common = {"district": district, "body_type": btype, "list_name": body}
    recs, seen = [], set()
    for w in soup.find_all("div", class_="widget-user"):
        n, d = w.find(class_="widget-user-username"), w.find(class_="widget-user-desc")
        name, post = _esw.clean(n.get_text(" ") if n else ""), _esw.clean(d.get_text(" ") if d else "")
        if not post or SKIP.match(post):
            continue
        lines = " ".join(h.get_text(" ") for h in w.find_all(class_="description-header"))
        phone, email = _esw.phones(re.sub(r"\+91\s*$", "", lines)), _esw.emails(lines)
        if not (name or phone or email):
            continue
        recs.append(_ulb.record(MODULE, STATE, area, post, seen, name=name, phone=phone, email=email, source=url, **common))
    addr, ophone, oemail, last = footer(soup)
    office = {k: v for k, v in (("address", addr), ("office_phone", ophone), ("office_email", oemail), ("last_updated", last)) if v}
    if recs:                    # the first card is the officer in charge (an Additional / Deputy Commissioner reads as "deputy")
        recs[0][1].update(office)
    elif ophone or oemail:
        recs.append(_ulb.record(MODULE, STATE, area, "Office", seen, phone=ophone, email=oemail, source=url, address=addr or None,
                                last_updated=last, **common))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, _esw.slug(p["body"]), r.content)]
    recs = parse(r.text, p["body"], p.get("district"), p["url"])
    return recs, files, "" if recs else "no rows"
