"""Assam, second pass: the 41 bodies of the state's urban body platform (<sub>.assamurban.in, read by dforms/ulb_as.py) that have
no tied official in DB civic (2026-11-11). Same pages and the same parser as ulb_as (ulb_as.parse); this module adds the LGD local
body code to every record (key lgd_code), so civic-india sql/87 ties the record to the body by code and not by name.

Why a second pass:
- 30 bodies (Bongaigaon, Jorhat, Nagaon, Hojai, Lumding, Digboi ...) gave no record in the hub run of 2026-11-11 05:28-05:37: the
  hub's failures table says "gave up after 3 attempts" (no answer) for every one, while the other 73 bodies answered in the same
  minutes. A live check from Germany on 2026-11-11 got Bongaigaon /office-staff (HTTP 200, 8 cards, Executive Officer
  "Prashanti Bhattacharyya"), so the pages are up: the run met a short outage or a rate limit.
- 11 bodies have records that sql/87 does not tie: the platform writes the name or the district in another way than LGD
  ("B. Chariali" = Biswanath Chariali, "N.Guwahati" = North Guwahati, "N.Lakhimpur" = North Lakhimpur, "Kampur" = Kampur Town,
  "Titabar" = Titabor Town, "Teok" = Teoktc; Patacharkuchi and Pathsala are in Bajali district for LGD, Barpeta for the platform;
  Sootea is in Sonitpur for LGD, Biswanath for the platform).
Ramkrishnanagar is left out: LGD has two codes for it (277150 Town Committee, 289553 Municipal Board, "Converted into New Ulb"
2019-04-20) and 289553 already has officials. Fakiragram has no LGD code (no lgd_code on its records). Guwahati Municipal
Corporation is not on the platform; gmc.assam.gov.in did not answer from Germany or from India (2026-11-11).
Not India-only.
"""
import re

from dforms import _esw, ulb_as

MODULE = "ulb2_as"
STATE = "AS"
# subdomain | name as the platform's list writes it (ulb_as.BODIES) | district as the platform writes it | LGD local body code
BODIES = """basugaon|Basugaon MB|Chirang|249823
bihpuria|Bihpuria MB|Lakhimpur|249881
bilasipara|Bilasipara MB|Dhubri|300488
bongaigaon|Bongaigaon MB|Bongaigaon|249836
chapakhowa|Chapakhowa MB|Tinsukia|259861
dhekiajuli|Dhekiajuli MB|Sonitpur|249875
digboi|Digboi MB|Tinsukia|249890
doomdooma|Doom Dooma MB|Tinsukia|249886
fakiragram|Fakiragram MB|Kokrajhar|
gauripur|Gauripur MB|Dhubri|249826
golukganj|Golukganj MB|Dhubri|300491
gossaigaon|Gossaigaon MB|Kokrajhar|249821
hojai|Hojai MB|Hojai|249870
howly|Howly MB|Barpeta|249844
jorhat|Jorhat MB|Jorhat|249912
kajalgaon|Kajalgaon MB|Chirang|296999
lakhipurcachar|Lakhipur MB(Cachar)|Cachar|249939
lala|Lala MB|Hailakandi|249945
langhin|Langhin MB|Karbi-Anglong|277148
lanka|Lanka MB|Hojai|300495
lumding|Lumding MB|Hojai|249872
moran|Moran MB|Charaideo|249902
nagaon|Nagaon MB|Nagaon|249866
naharkatia|Naharkatia MB|Dibrugarh|249903
namrup|Namrup MB|Dibrugarh|249904
narayanpur|Narayanpur MB|Lakhimpur|253212
raha|Raha MB|Nagaon|271990
sarupathar|Sarupathar MB|Golaghat|249921
sipajhar|Sipajhar MB|Darrang|296992
sorbhog|Sorbhog MB|Barpeta|249842
biswanathchariali|B. Chariali MB|Biswanath|249879
kampur|Kampur MB|Nagaon|249869
northguwahati|N.Guwahati MB|Kamrup|249855
nlakhimpur|N.Lakhimpur MB|Lakhimpur|249882
patacharkuchi|Patacharkuchi MB|Barpeta|262892
pathsala|Pathsala MB|Barpeta|249847
sootea|Sootea MB|Biswanath|277151
teok|Teok MB|Jorhat|263017
titabar|Titabar MB|Jorhat|249916
badarpur|Badarpur MB|Karimganj|249941
karimganj|Karimganj MB|Karimganj|249940"""


def items(get=None):
    out = []
    for line in BODIES.splitlines():
        sub, name, district, lgd = line.split("|")
        p = {"reader": MODULE, "url": f"https://{sub}.assamurban.in/office-staff", "members": f"https://{sub}.assamurban.in/members",
             "body": name, "district": district, "state": STATE, "india_only": False}
        if lgd:
            p["lgd_code"] = lgd
        out.append({"key": f"{MODULE}-{sub}", "payload": p})
    return out


def parse(staff_html, members_html=None, body="", district=None, url="", members_url="", lgd_code=None):
    """ulb_as.parse with this module's record ids and the LGD code on every record."""
    out = []
    for rid, d in ulb_as.parse(staff_html, members_html, body, district, url, members_url):
        if lgd_code:
            d["lgd_code"] = lgd_code
        if d.get("office_phone"):         # ulb_as.footer() keeps the PIN of "Bongaigaon : 783380" as a phone
            ph = ", ".join(x for x in d["office_phone"].split(", ") if not re.fullmatch(r"\d{6}", x))
            if ph:
                d["office_phone"] = ph
            else:
                del d["office_phone"]
        out.append((rid.replace(f"dept:{ulb_as.MODULE}:", f"dept:{MODULE}:", 1), d))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"{_esw.slug(p['body'])}-office-staff", r.content)]
    m = get(p["members"]) if p.get("members") else None
    if m is not None:
        files.append(_esw.keep(MODULE, f"{_esw.slug(p['body'])}-members", m.content))
    recs = parse(r.text, m.text if m is not None else None, p["body"], p.get("district"), p["url"], p.get("members", ""),
                 p.get("lgd_code"))
    return recs, files, "" if recs else "no rows"
