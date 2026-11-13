"""Punjab: the police district sites <district>.punjabpolice.gov.in (WordPress, the same template; Barnala answered from outside India on 2026-11-11, Patiala and Amritsar Rural refused connections from everywhere). Pages:
- /officers-list: 'Photo | Name | Designation | Phone No. | Mobile No. | Email ID': SSP, SPs, DSPs ("Deputy Superintendent of
  Police Sub Division Tapa" -> level subdivision, area Tapa).
- /shos-mhcs: the SHO of every police station with the station munshi (MHC): 'S. No | Name Of SHO's | Name Of Police Stations |
  MOBILE NO. | MHC's | Email ID' (Malerkotla) or 'S. No. | Name | Designation ("SHO PS CITY-1 BARNALA") | Mobile No. | MHC's |
  Email ID' (Barnala).
- /officers-contact/ (commissionerate Jalandhar City): officers in one cell "Sh. Karnail Singh, PPS ACP-1 (North)" (CP, DCPs,
  ADCPs, ACPs: the ACP of a zone is level circle), then 'Rank | Name | Police Station | Mobile No.' for the SHOs and
  'Rank | Name | Police Post | Mobile No.' for the police post in-charges ("I/C PP Dakoha: Ramamandi").
Names keep the officer's belt number apart ("Jaspal Singh 19/JR" -> name Jaspal Singh, belt_no 19/JR). Units without an area
(CIA, crime branch, special branch, legal, accounts) are left out. police_pb (Saanjh JSON) has SHO names for most stations of
the state; these pages add the SDPO/DSP and ACP levels, the station munshi mobile and the district sites' own SHO lists.
One queue item = one page. Record id dept:police2n_pb:<district>:<station or office>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq
from dforms.police_s3waas import grid
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police2n_pb"

SUBDIV = re.compile(r"(?:Deputy Superintendent of Police|D\.?S\.?P\.?)\s*,?\s*(?:\(?\s*)?Sub[- ]?Div(?:ision|n)?\.?\s*(?:\)\s*)?,?\s*(.+)$", re.I)
ACP = re.compile(r"\bACP\s*-?\s*(\d+)\s*\(([^)]+)\)|\bACP\s+(?!\()([A-Za-z][\w .]+?)\s*$", re.I)
HEAD = re.compile(r"^(?:Commissioner of Police|Senior Superintendent of Police|SSP|Superintendent of Police|SP\b|DCP|"
                  r"Deputy Commissioner of Police|Addl\.?\s*DCP|Additional Deputy Commissioner|Deputy Inspector General)", re.I)
UNIT = re.compile(r"\b(?:HQ|Hqrs|Investigation|INV|PBI|Detective|Traffic|Spl\.?|Special|Security|Licen|Command|CAW|Cyber|"
                  r"Crime|Narcotic|NDPS|Legal|DA\b|Accounts|ACF|Lines|Operations|OSI|CIA|Staff|Branch|Cell)", re.I)
BELT = re.compile(r"\s+(\d+\s*/\s*[A-Za-z]+)\b(?:\s*\(Temp\.?\))?\s*$")
SERVICE = re.compile(r",?\s*\b(IPS|PPS)\b(?:\s*\(DR\))?\s*,?\s*")


def ph(*cells):
    s = " , ".join(c for c in cells if c and c.strip(" -–—"))
    s = re.sub(r"(?<=\d)\s+(?=\d{5}-\d{5}|\d{10})", ", ", s)
    s = re.sub(r"\((?:O|R|M)\)", "", s)
    return phones(s)


RANKP = re.compile(r"^((?:L/|W/)?(?:INSP|Insp|Inspector|SI|S\.I\.|ASI|A\.S\.I\.|HC|H\.C\.)(?:/LR)?\.?)\s+(?=[A-Za-z])")
NONAME = re.compile(r"^(?:additional charge|addl\.? charge|vacant|-+|n/?a)$", re.I)


def name_belt(n):
    n = clean(n) or ""
    if NONAME.match(n):
        return None, None
    m = BELT.search(n)
    belt = None
    if m:
        belt, n = m.group(1).replace(" ", ""), n[:m.start()]
    n = re.sub(r"\s*\(Temp\.?\)\s*$", "", n).strip(" ,")
    return (n or None), belt


def station_name(s):
    """'PS City-1 Malerkotla' / 'SHO PS CITY-1 BARNALA' -> 'City-1 Malerkotla' / 'City-1 Barnala'."""
    s = clean(s) or ""
    s = re.sub(r"^(?:SHO\s+)?(?:P\.?S\.?|Police Station)\s+", "", s, flags=re.I)
    return s.title() if s.isupper() else s


def split_officer(cell):
    """'Sh. Karnail Singh, PPS ACP-1 (North)' -> ('Sh. Karnail Singh', 'ACP-1 (North)')."""
    c = clean(cell) or ""
    m = re.search(r",\s*(?:IPS|PPS)(?:\s*\(DR\))?\s*", c)
    if m:
        return c[:m.start()].strip(), c[m.end():].strip()
    m = re.match(r"^((?:Sh|Smt|Ms|Dr)\.?\s+(?:[A-Z][\w.]*\s+){1,4}?)(?=DA\b|Dy\.|\(|ACP|DCP|SP|Addl)", c)
    return (m.group(1).strip(), c[m.end():].strip()) if m else (None, c)


def columns(head):
    k = {}
    for i, h in enumerate(head):
        h = (h or "").lower()
        if "mhc" in h:
            k.setdefault("mhc", i)
        elif "email" in h or "e-mail" in h:
            k.setdefault("email", i)
        elif "mobile" in h:
            k.setdefault("mobile", i)
        elif "phone" in h or "office no" in h:
            k.setdefault("phone", i)
        elif "police station" in h or "police post" in h:
            k.setdefault("station", i)
        elif "designation" in h or "posting" in h:
            k.setdefault("post", i)
        elif h.strip() == "rank":
            k.setdefault("rank", i)
        elif "name" in h:
            k.setdefault("name", i)
    return k


def parse(html, url, district, state="PB"):
    soup = BeautifulSoup(html, "lxml")
    d = slug(district)
    recs = []
    for t in soup.find_all("table"):
        rows = [r for r in grid(t) if any(r)]
        if not rows:
            continue
        k = columns(rows[0])
        if "name" not in k:
            continue
        post_head = (rows[0][k["station"]] if "station" in k else "").lower()
        for r in rows[1:]:
            g = lambda f: (r[k[f]] if f in k and k[f] < len(r) else "") or ""
            name, belt = name_belt(g("name"))
            mail = email(g("email"))
            rank = clean(g("rank")) or None
            m0 = RANKP.match(name or "")
            if m0 and not rank:
                rank, name = m0.group(1), name[m0.end():]
                name = name.title() if name.isupper() else name
            designation = clean(g("post"))
            if "station" in k or re.match(r"^\s*SHO\b", designation or "", re.I):           # a station or a police post
                label = g("station") or designation
                if not label:
                    provenance.skip_row(r, 'skip: not label')
                    continue
                if "police post" in post_head or re.match(r"I/C\s+PP\b", label, re.I):
                    m = re.match(r"^(?:I/C\s+)?PP\s+(.+?)\s*:\s*(.+)$", label, re.I)
                    area, parent = (m.group(1), m.group(2)) if m else (re.sub(r"^(?:I/C\s+)?PP\s+", "", label, flags=re.I), None)
                    recs.append(rec(M, f"{d}:pp-{slug(area)}", office_type="police post", area=area, post="In-charge police post",
                                    name=name, belt_no=belt, rank=rank, phone=ph(g("mobile"), g("phone")), email=mail,
                                    parent_station=parent, state=state, district=district, source=url))
                    continue
                area = station_name(label)
                if UNIT.search(area) and not re.search(r"women|cyber crime|^ps\b|police station", label, re.I) and "station" not in k:
                    provenance.skip_row(r, 'skip: UNIT.search(area) and not re.search(r"women|cyber crime|^ps\\b|polic...')
                    continue
                recs.append(rec(M, f"{d}:{slug(area)}", office_type="police station", area=area, post="SHO", name=name,
                                belt_no=belt, rank=rank, phone=ph(g("mobile"), g("phone")), mhc_phone=ph(g("mhc")), email=mail,
                                state=state, district=district, source=url))
                continue
            post = designation
            if not post:                     # Jalandhar: name and post in one cell
                name, post = split_officer(g("name"))
            post = clean(post) or ""
            if not post:
                provenance.skip_row(r, 'skip: not post')
                continue
            name = SERVICE.sub(" ", name or "").strip(" ,") or None
            common = dict(name=name, phone=ph(g("mobile"), g("phone")), email=mail, state=state, district=district, source=url)
            m = SUBDIV.search(post)
            a = ACP.search(post)
            if m and not UNIT.search(m.group(1)):
                area = clean(m.group(1)).strip(" ,.")
                recs.append(rec(M, f"{d}:sdpo-{slug(area)}", level="subdivision", office_type="subdivision", area=area,
                                post="DSP", designation=post, **common))
            elif a and not UNIT.search(post):
                area = f"{a.group(2)} (ACP-{a.group(1)})" if a.group(1) else a.group(3)
                recs.append(rec(M, f"{d}:acp-{slug(area)}", level="circle", office_type="circle", area=area, post="ACP",
                                designation=post, **common))
            elif HEAD.match(post) and not UNIT.search(post):
                recs.append(rec(M, f"{d}:{slug(post)}", level="district", office_type="office", area=district, post=post, **common))
    return uniq(recs)


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    district = p.get("district") or url.split("//")[1].split(".")[0]
    recs = parse(r.text, url, district, p.get("state", "PB"))
    name = slug(re.sub(r"^https?://", "", url))[:80]
    return recs, [gz(M, name, r.content)], "" if recs else "no rows"
