"""Telangana: education officers from the contact page of the Commissioner and Director of School Education,
https://schooledu.telangana.gov.in/ISMS/contactus.do (HTML, 105 KB, no login, no captcha; fetched once from Mumbai on
2026-11-12; from abroad unchecked). Four tables, each under a title row:
  "Telangana Commissioner and Director of School Education" (state officers: S. No. | Name | Designation | Phone | Cell),
  "HODs Under Control of School Education" (same columns),
  "RJDs Under Control of School Education" (Regional Joint Directors: S. No. | District Name | Name of the RJDSE | Cell | E-Mail),
  "DEOs Under Control of School Education" (one District Educational Officer per district, 33 rows: S. No. | District Name |
  Name of the DEO | Cell No. | E-Mail Ids). "(FAC)" after a name = full additional charge; kept in the name as printed.
Records (depts.py contract): dept education; DEO rows level district (post "District Educational Officer", district = LGD
name), RJD rows level region (area = the zone city), state and HOD rows level state (post = the designation). A row whose name
is "-" is a vacant post (vacant=true, no name). Ids dept:edu_tg_dse:<deo|rjd|state|hod>:<slug>. src_pos = {table, row}.
"""
import re

from dforms import _esw
import provenance

METHOD = "html table"

MODULE = "edu_tg_dse"
URL = "https://schooledu.telangana.gov.in/ISMS/contactus.do"
LGD = ["Adilabad", "Bhadradri Kothagudem", "Hanumakonda", "Hyderabad", "Jagitial", "Jangoan", "Jayashankar Bhupalapally",
       "Jogulamba Gadwal", "Kamareddy", "Karimnagar", "Khammam", "Kumuram Bheem Asifabad", "Mahabubabad", "Mahabubnagar",
       "Mancherial", "Medak", "Medchal Malkajgiri", "Mulugu", "Nagarkurnool", "Nalgonda", "Narayanpet", "Nirmal", "Nizamabad",
       "Peddapalli", "Rajanna Sircilla", "Ranga Reddy", "Sangareddy", "Siddipet", "Suryapet", "Vikarabad", "Wanaparthy",
       "Warangal", "Yadadri Bhuvanagiri"]
ALIAS = {"medchal": "Medchal Malkajgiri", "jagityal": "Jagitial", "jangaon": "Jangoan", "komarambheemasifabad": "Kumuram Bheem Asifabad",
         "jayashankarbhoopalpally": "Jayashankar Bhupalapally", "yadadribhongiri": "Yadadri Bhuvanagiri"}


def lgd(name):
    k = re.sub(r"[^a-z]", "", (name or "").lower())
    for d in LGD:
        if re.sub(r"[^a-z]", "", d.lower()) == k:
            return d
    return ALIAS.get(k)


def parse(html, url=URL):
    sp = _esw.soup(html)
    recs, seen = [], set()
    for ti, t in enumerate(sp.find_all("table")):
        trs = t.find_all("tr")
        if not trs:
            continue
        title = _esw.clean(trs[0].get_text(" "))
        kind = ("deo" if title.startswith("DEOs") else "rjd" if title.startswith("RJDs") else "hod" if title.startswith("HODs")
                else "state" if "Commissioner and Director" in title else None)
        if not kind:
            continue
        for ri, tr in enumerate(trs):
            tds = [_esw.cell_text(td) for td in tr.find_all("td")]
            if len(tds) < 4 or not re.match(r"^\d+$", tds[0] or ""):
                provenance.skip_row(tr, 'skip: len(tds) < 4 or not re.match(r"^\\d+$", tds[0] or "")')
                continue
            if kind in ("deo", "rjd"):
                area, name, cell, mail = (tds + [""] * 5)[1:5]
                post = "District Educational Officer" if kind == "deo" else "Regional Joint Director of School Education"
                phone, other = _esw.phones(cell), ""
            else:
                name, post, tel, cell = (tds + [""] * 5)[1:5]
                area, mail, phone = "Telangana", "", _esw.phones(cell, tel)
            vacant = not re.search(r"[A-Za-z]{2}", name or "") or bool(re.fullmatch(r"(?i)vacant", name or ""))
            if vacant and not phone and not _esw.emails(mail):
                provenance.skip_row(tr, 'skip: vacant and not phone and not _esw.emails(mail)')
                continue
            key = f"{kind}:{_esw.slug(area if kind in ('deo', 'rjd') else post)}"
            if key in seen:
                key += f":{ri}"
            seen.add(key)
            district = lgd(area) if kind == "deo" else None
            recs.append(_esw.record(
                MODULE, key, dept="education", level={"deo": "district", "rjd": "region"}.get(kind, "state"),
                area=(district or area.title()) if kind in ("deo", "rjd") else "Telangana", area_regional=None, post=post,
                name=None if vacant else name, vacant=True if vacant else None, phone=phone or None, email=_esw.emails(mail) or None,
                state="TG", district=district, district_as_printed=area if kind == "deo" else None, table_title=title,
                source=url, src_url=url, src_pos={"table": ti, "row": ri, "title": title}))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}:contact", "payload": {"reader": MODULE, "url": URL, "state": "TG", "route": "abroad", "expected": 64}}]


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [_esw.keep(MODULE, "contactus", r.content)], "" if recs else "no rows"
