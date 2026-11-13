"""Madhya Pradesh: the Electoral Registration Officer (ERO) of each of the 230 assembly constituencies, with mobile, from the Chief
Electoral Officer's directory (ceoelection.mp.gov.in/CEO_District.aspx, tab "Electoral Registration Officer"). In Madhya Pradesh the
ERO of an assembly constituency is the Sub-Divisional Officer (Revenue) / SDM of the sub-division that holds it, so this list gives the
SDMs of the state with their mobiles. Answers only from India; the server needs TLS legacy renegotiation (the runner's get() retries
with it).

The page is an ASP.NET form: GET (sets the __AntiXsrfToken cookie), then one postback with __EVENTTARGET =
ctl00$ContentPlaceHolder1$lnk_CEO_ERO and the page's hidden fields; the answer holds one table ContentPlaceHolder1_Grid_ERO
(AC.No., District, Assembly/Constituency, ERO Name, Mobile), 230 rows. The page shows no date and no designation.

One queue item: 1 GET + 1 POST. Area = the assembly constituency name as the site writes it, in title case ("Sabalagadh"); the AC
name is the sub-division's head town for most rural ACs. District = the LGD district name (the site uses the 52 districts before
Mauganj, Maihar and Pandhurna). Record ids: dept:sub2_mp_ero:MP-AC-<AC no>.
"""
import re

import provenance
from dforms import _esw

METHOD = "html table (ASP.NET postback answer, table#*Grid_ERO)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub2_mp_ero"
URL = "https://ceoelection.mp.gov.in/CEO_District.aspx"
TARGET = "ctl00$ContentPlaceHolder1$lnk_CEO_ERO"
# LGD districts of Madhya Pradesh (lgd.districts, state 23): name -> code
LGD = {"Anuppur": "390", "Ashoknagar": "391", "Balaghat": "392", "Barwani": "393", "Betul": "394", "Bhind": "395", "Bhopal": "396",
       "Burhanpur": "397", "Chhatarpur": "398", "Chhindwara": "399", "Damoh": "400", "Datia": "401", "Dewas": "402", "Dhar": "403",
       "Dindori": "404", "Khandwa (East Nimar)": "405", "Guna": "406", "Gwalior": "407", "Harda": "408", "Narmadapuram": "409",
       "Indore": "410", "Jabalpur": "411", "Jhabua": "412", "Katni": "413", "Khargone (West Nimar)": "414", "Mandla": "415",
       "Mandsaur": "416", "Morena": "417", "Narsimhapur": "418", "Neemuch": "419", "Panna": "420", "Raisen": "421", "Rajgarh": "422",
       "Ratlam": "423", "Rewa": "424", "Sagar": "425", "Satna": "426", "Sehore": "427", "Seoni": "428", "Shahdol": "429",
       "Shajapur": "430", "Sheopur": "431", "Shivpuri": "432", "Sidhi": "433", "Tikamgarh": "434", "Ujjain": "435", "Umaria": "436",
       "Vidisha": "437", "Singrauli": "638", "Alirajpur": "639", "Agar-Malwa": "667", "Niwari": "722", "Mauganj": "766",
       "Maihar": "784", "Pandhurna": "785"}
ALIAS = {"KHANDWA": "Khandwa (East Nimar)", "KHARGONE": "Khargone (West Nimar)", "MANDSOUR": "Mandsaur", "NARSINGPUR": "Narsimhapur",
         "ASHOK NAGAR": "Ashoknagar", "AGAR MALWA": "Agar-Malwa", "HOSHANGABAD": "Narmadapuram"}


def items(get=None):
    return [{"key": "sub2_mp_ero", "payload": {"reader": MODULE, "url": URL, "state": "MP", "india_only": True, "expected": 230}}]


def district_of(s):
    """(LGD name, LGD code) for the site's district spelling ("MANDSOUR" -> ("Mandsaur", "416"))."""
    s = _esw.clean(s).upper()
    name = ALIAS.get(s) or next((n for n in LGD if n.upper() == s), None)
    return (name, LGD[name]) if name else (s.title(), "")


def hidden(html):
    return {i["name"]: i.get("value", "") for i in _esw.soup(html).find_all("input", type="hidden") if i.get("name")}


def rows(html, where=None):
    """[(ac no, district, ac name, name, mobile)] of the ERO table. where: a list; when given, it gets each row's src_pos."""
    t = _esw.soup(html).find("table", id=re.compile("Grid_ERO$"))
    if t is None:
        return []
    out, tp = [], []
    for r, pos in zip(_esw.grid(t, pos=tp)[1:], tp[1:]):
        if len(r) >= 5 and r[0].strip().isdigit():
            out.append((int(r[0]), r[1], r[2], r[3], r[4]))
            if where is not None:
                where.append(pos)
    return out


def area_of(ac):
    """'SABALAGADH' -> 'Sabalagadh'; 'GWALIOR RURAL' -> 'Gwalior Rural'; reserved marks dropped."""
    ac = re.sub(r"\(\s*(sc|st)\s*\)", "", _esw.clean(ac), flags=re.I)
    return _esw.clean(ac).title()


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "home", r.content)]
    a = get(url, method="POST", data={**hidden(r.text), "__EVENTTARGET": TARGET, "__EVENTARGUMENT": ""})
    if a is None:
        return [], files, "no answer to the ERO postback"
    files.append(_esw.keep(MODULE, "ero", a.content))
    recs, where = [], []
    src = provenance.at(a, url)          # the url is asked twice (GET, then the POST that gives the list)
    for (no, dist, ac, name, mobile), pos in zip(rows(a.text, where), where):
        name = _esw.clean(name)
        if not name:
            provenance.skipped('skip: not name')
            continue
        district, dc = district_of(dist)
        recs.append(_esw.record(MODULE, f"MP-AC-{no}", dept="administration", level="subdivision", area=area_of(ac),
                                post="Electoral Registration Officer", name=name, phone=_esw.phones(mobile), district=district,
                                district_code=dc, state="MP", office_id=f"MP-ERO-AC-{no}", ac_no=no, ac_name=_esw.clean(ac),
                                source=url, src_pos=pos, **src))
    return recs, files, "" if recs else "no rows"
