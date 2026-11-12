"""Punjab: councillors of the urban bodies on the Local Government Department's e-Nigam "Digital MC-House" sites
(mc<town>.punjab.gov.in, National Informatics Centre Punjab). They hold the bodies elected on 21.12.2024 (Ludhiana, Patiala,
Phagwara and the councils and nagar panchayats of that poll) that cforms/pb.py (LBPAMS, 2026 poll) and cforms/cn_pb.py
(Amritsar, Jalandhar) do not read.

One platform serves all 114 bodies by id ("mcid"; the list is in the state switcher of every site's home page,
ChangeMC(<mcid>, '<name>', ...)). Any platform host answers for any mcid: /Home/Index?mcid=1094 on mcpatiala.punjab.gov.in is
Municipal Council Talwara (tested 2026-11-11, 13 cards). Pages read:
- /Home/Index?mcid=<id>&lng=: "House Authorities and Members", one card per member (.gallery_card2): link
  /Councilors/CouncillorsDetail?mcid=<id>&MemberCode=<n>, name (h6), "<post>  Ward 02" or "<post>  ward no-5" (p).
- /Councilors/CouncillorsDetail?mcid=<id>&MemberCode=<n>: name, "Ward 02", and PERSONAL INFORMATION rows Name, Email, Mobile,
  Permanent Address.
The home page of a large body shows only part of its members (Patiala: 30 cards for 60 wards, MemberCode 687-742). When the
cards are fewer than the body's LGD wards (payload "wards"), the member codes between the lowest and the highest card are read
too (at most 80 more pages); a code that is not a member answers with no name and is skipped.
/Councilors/Index?mcid= answers HTTP 500 (2026-11-11): not used. Each site also links a PDF list (Patiala: "LIST OF MUNICIPAL
COUNCILLORS PATIALA (2025 to till date) Partywise.pdf", party + phone); the reader does not need it.
The sites answer from outside India. One queue item = one body (payload mcid, body, district, lgd_code, wards, host).
Record id councillor:PB:<body slug>:<ward> (the scheme of cforms/pb.py and cforms/cn_pb.py).
"""
import gzip
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from cforms.cr_common import clean

METHOD = "html page (member detail pages, home page cards)"     # source trail (provenance.py): how this reader reads its sources

HOST = "https://mcpatiala.punjab.gov.in"
ELECTION = "Punjab municipal general election 21.12.2024 (e-Nigam Digital MC-House member list)"
POSTS = {"councillor": None, "president": "President", "vice president": "Vice President", "senior vice president":
         "Senior Vice President", "mayor": "Mayor", "deputy mayor": "Deputy Mayor", "senior deputy mayor": "Senior Deputy Mayor"}


def post_ward(s):
    """("Vice President", "7") from "Vice President  ward no-7"; (None, "2") from "Councillor  Ward 02"; ("President", "5") from
    "President Ward Number-5" (Alawalpur, 2026-11-12)."""
    m = re.match(r"\s*(.*?)\s*ward\s*(?:no\.?|number)?\s*[-:]?\s*0*(\d+)\s*$", s or "", re.I)
    if not m:
        return None, None
    post = clean(m.group(1)).lower()
    return POSTS.get(post, clean(m.group(1)) or None), m.group(2)


def code_of(href):
    m = re.search(r"MemberCode=(\d+)", href or "")
    return int(m.group(1)) if m else None


def cards(html, base=HOST):
    out = []
    for k, c in enumerate(BeautifulSoup(html, "lxml").select(".gallery_card2"), 1):
        a = c.find("a", href=re.compile("CouncillorsDetail"))
        h6, p = c.find("h6"), c.find("p")
        if not a or not h6:
            continue
        post, ward = post_ward(p.get_text(" ", strip=True) if p else "")
        out.append({"code": code_of(a["href"]), "url": urljoin(base, a["href"]), "name": clean(h6.get_text(" ", strip=True)),
                    "position": post, "ward_no": ward, "card": clean(p.get_text(" ", strip=True)) if p else None, "card_no": k})
    return out


def detail(html):
    soup = BeautifulSoup(html, "lxml")
    d = {}
    for row in soup.select(".card-body .row"):
        cols = row.find_all("div", recursive=False)
        if len(cols) >= 2:
            k, v = clean(cols[0].get_text(" ", strip=True)), clean(cols[1].get_text(" ", strip=True))
            if v:
                d[{"Name": "name", "Email": "email", "Mobile": "phone", "Permanent Address": "address"}.get(k, k.lower())] = v
    top = soup.select_one(".card-body.text-center")
    if top:
        p = top.find("p")
        if p:
            post, ward = post_ward(p.get_text(" ", strip=True))
            d["ward_no"], d["position"] = ward, post
    return d


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def fetch(p, get):
    host = p.get("host") or HOST
    home = f"{host}/Home/Index?mcid={p['mcid']}&lng="
    r = get(home)
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/PB/enigam-{p['mcid']}-home.html.gz", gzip.compress(r.content), "application/gzip")]
    cs = cards(r.text, host)
    if not cs:
        return [], files, "no member cards"
    todo = {c["code"]: c for c in cs if c["code"]}
    if p.get("wards") and len(cs) < int(p["wards"]) and todo:
        lo, hi = min(todo), max(todo)
        for code in [c for c in range(lo, hi + 1) if c not in todo][:80]:
            todo[code] = {"code": code, "url": f"{host}/Councilors/CouncillorsDetail?mcid={p['mcid']}&MemberCode={code}",
                          "from_range": True}
    saved, recs = [], {}
    for code, c in sorted(todo.items()):
        m = get(c["url"])
        d = detail(m.text) if m is not None else {}
        if m is not None:
            saved.append(f"<!-- MemberCode {code} -->" + m.text[m.text.find("Councillor Detail"):][:12000])
        name = d.get("name") or c.get("name")
        ward = d.get("ward_no") or c.get("ward_no")
        if not name or not ward:
            continue
        rec = {"type": "councillor", "state": "PB", "body": p["body"], "body_type": p.get("body_type"), "district": p.get("district"),
               "lgd_code": p.get("lgd_code"), "ward_no": ward, "name": name, "position": d.get("position") or c.get("position"),
               "phone": d.get("phone"), "email": d.get("email"), "address": d.get("address"), "member_code": code,
               "on_home_page": not c.get("from_range"), "election": ELECTION, "url": c["url"], "list_url": home,
               # source trail: the member's detail page when it answered (fields from its .card-body rows), else the home page card
               "src_url": c["url"] if d else home,
               "src_pos": {"selector": ".card-body .row"} if d else {"selector": ".gallery_card2", "card": c.get("card_no")},
               "method": "html page (member detail)" if d else "html cards (home page)"}
        rid = f"councillor:PB:{p.get('slug') or slug(p['body'])}:{ward}"
        if rid in recs and recs[rid].get("on_home_page") and c.get("from_range"):
            continue    # a home page card wins over another code of the same ward; between two range codes the higher wins
        recs[rid] = {k: v for k, v in rec.items() if v not in (None, "")}
    if saved:
        doc = "<html><head><meta charset=\"utf-8\"></head><body>" + "\n".join(saved) + "</body></html>"
        files.append((f"councillors/PB/enigam-{p['mcid']}-members.html.gz", gzip.compress(doc.encode()), "application/gzip"))
    return list(recs.items()), files, "" if recs else "member pages did not answer"


# the 114 bodies of the platform's state switcher (mcid, name as the platform gives it), read 2026-11-11 from the archive copy
# of mcpatiala.punjab.gov.in/Home/Index?mcid=1002 (saved 2026-11-05)
PLATFORM = {1001: "Mohali", 1002: "Patiala", 1003: "Jalandhar", 1004: "Zirakpur", 1005: "Kharar", 1006: "Amritsar",
            1007: "Bathinda", 1008: "Hoshiarpur", 1009: "Phagwara", 1010: "Ludhiana", 1011: "Moga", 1012: "Pathankot",
            1013: "Abohar", 1014: "Batala", 1015: "Kapurthala", 1016: "Gurdaspur", 1017: "Jandiala Guru", 1018: "Dinanagar",
            1019: "Dhariwal", 1020: "Sujanpur", 1021: "Tarn Taran", 1022: "Patti", 1023: "Majitha", 1024: "Ramdass",
            1025: "Qadian", 1026: "Sri Hargovindpur", 1027: "Dera Baba Nanak", 1028: "Fatehgarh Churian", 1029: "Nakodar",
            1030: "Noormahal", 1031: "Phillaur", 1032: "Kartarpur", 1033: "Bhogpur", 1034: "Adampur", 1035: "Goraya",
            1036: "Sultanpur Lodhi", 1037: "Dasuya", 1038: "Mukerian", 1039: "Urmur Tanda", 1040: "Garh Shankar", 1041: "Alawalpur",
            1042: "Garhdiwala", 1043: "Hariana", 1044: "Sham Churasi", 1045: "Nawan Shehar", 1046: "Khanna", 1047: "Jagraon",
            1048: "Nangal", 1049: "Anandpur Sahib", 1050: "Gobindgarh", 1051: "Rajpura", 1052: "Nabha", 1053: "Samana",
            1054: "Sangrur", 1055: "Malerkotla", 1056: "Sunam Udham Singh Wala", 1057: "Barnala", 1058: "Dera Bassi", 1059: "Mansa",
            1060: "Sri Muktsar Sahib", 1061: "Malout", 1062: "Ferozepur", 1063: "Fazilka", 1064: "Faridkot", 1065: "Kotkapura",
            1066: "Lalru", 1068: "Morinda", 1069: "Sirhind Fatehgarh Sahib", 1070: "Patran", 1071: "Ahmedgarh", 1072: "Dhuri",
            1073: "Lehragaga", 1074: "Kurali", 1075: "Rampuraphul", 1076: "Bhucho Mandi", 1077: "Goniana", 1078: "Maur",
            1079: "Raman", 1080: "Budhladha", 1081: "Gidderbaha", 1082: "Guru Har Sahai", 1083: "Zira", 1084: "Talwandi Bhai",
            1085: "Jalalabad", 1086: "Jaito", 1087: "Bagha Purana", 1088: "Dharamkot", 1089: "Banur", 1090: "Bhawanigarh",
            1091: "Nayagaon", 1092: "Chamkaur Sahib", 1093: "Bassi Pathana", 1094: "Talwara", 1095: "Talwandi Sabo", 1096: "Rahon",
            1097: "Balachaur", 1098: "Payal", 1099: "Machhiwara", 1101: "Amloh", 1102: "Sanaur", 1103: "Longowal", 1104: "Tapa",
            1105: "Bhadaur", 1106: "Dhanaula", 1108: "Kotfatta", 1109: "Sangat", 1110: "Bareta", 2001: "Banga", 2002: "Samrala",
            2003: "Raikot", 2004: "Sahnewal", 2005: "Doraha", 2006: "Mullanpur Dakha", 2007: "Roopnagar"}
