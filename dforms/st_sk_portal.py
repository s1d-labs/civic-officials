"""Sikkim: state-level officials from the state portal www.sikkim.gov.in (checked 2026-11-13 from dev-vps-3, Mumbai; HTML,
no captcha on these GET pages; the portal loads reCAPTCHA v3 only for its feedback form).

Pages (one queue item reads all of them):
1. /mygovernment/whos-who/head-of-departments: table Departments | Name | Designation (about 70 rows: Chief Administrator,
   Chief Secretary, DGP, ACS/PS/Commissioner-cum-Secretaries/Secretaries of every department, commissions' secretaries).
2. /mygovernment/information/telephone-directory: "Important dignitaries" tabs (Members of Parliament, Council of Ministers,
   MLA's, HOD's), each person a list "Name: / Official Contact No.: / Departments:". The HOD tab gives the phone of each
   row of page 1 (joined by name + department); the ministers' tab gives the ministers (post "Minister", their departments).
   MPs and MLAs are left out (the legislators readers have them).
3. /mygovernment/whos-who/district-collectors: Name | District | Position | Contact No. (6 districts; level district).
4. /mygovernment/EmpTelephoneDirectoryList?PageNo=N&sTerm=timeZone%3D0: the employee telephone directory, 10 per page;
   page 1 gives the total ("totalRec", 54 on 2026-11-13). Name, Contact No., Place of Posting, Department (no post).
Record ids: dept:st_sk_portal:<hod|minister|dc|emp>:<slug>.
"""
import re

from dforms import _esw, _state, st_ne
import provenance

METHOD = "html table + html label lists (www.sikkim.gov.in)"
MODULE = "st_sk_portal"
BASE = "https://www.sikkim.gov.in"
HOD = BASE + "/mygovernment/whos-who/head-of-departments"
TEL = BASE + "/mygovernment/information/telephone-directory"
DC = BASE + "/mygovernment/whos-who/district-collectors"
EMP = BASE + "/mygovernment/EmpTelephoneDirectoryList?PageNo={n}&sTerm=timeZone%3D0"
EMP_FIRST = BASE + "/mygovernment/information/employeetelephone-directory"
DISTRICTS = {"gangtok": "Gangtok", "mangan": "Mangan", "namchi": "Namchi", "gyalshing": "Gyalshing", "pakyong": "Pakyong",
             "soreng": "Soreng"}


def nkey(s):
    return re.sub(r"[^a-z]", "", re.sub(r"(?i)^(mr|mrs|ms|dr|shri|smt)\.?\s+|,.*$|\(.*?\)", "", _esw.clean(s)).lower())


def parse_hod(html, url=HOD, phones=None):
    phones = phones or {}
    out, seen = [], {}
    for r in st_ne.table_rows(html):
        dept, name, post = r.get("department", ""), r.get("name", ""), r.get("post", "")
        if not (name or post):
            provenance.skip_row(r, 'skip: not (name or post)')
            continue
        k = f"hod:{_esw.slug(dept)}:{_esw.slug(post)}:{nkey(name)}"
        seen[k] = seen.get(k, 0) + 1
        if seen[k] > 1:
            k += f":{seen[k]}"
        ph = phones.get((nkey(name), _esw.slug(dept)), {})
        bk = "police" if re.search(r"(?i)police", dept) else "commission" if re.search(r"(?i)commission", dept) else \
            "secretariat" if re.search(r"(?i)government of sikkim", dept) else "department"
        out.append(_state.rec(MODULE, k, state="SK", level="state", post=post, post_kind=st_ne.post_kind(post), name=name, body=dept, body_kind=bk, department=dept, dept=st_ne.dept(dept, post),
                              phone=ph.get("phone", ""), phone_source=ph.get("src_url"), phone_src_pos=ph.get("src_pos"),
                              section="Head of Departments", cells=r["cells"], src_url=url, src_pos=r["src_pos"]))
    return out


def parse_tel(html, url=TEL):
    """(HOD phones by (name key, department slug), minister records)."""
    phones, recs, n = {}, [], 0
    for r in st_ne.label_lists(html):
        lab, sec = r["labels"], r["section"].lower()
        name, ph, depts = lab.get("name", ""), lab.get("official contact no.", lab.get("official contact no", "")), lab.get("departments", "")
        ph = "" if re.fullmatch(r"\(?0?3592\)?", ph.strip()) else ph       # the bare STD code, no number
        if "hod" in sec:
            for d in [x.strip() for x in depts.split(",")] or [""]:
                phones.setdefault((nkey(name), _esw.slug(d)), {"phone": ph, "src_url": url, "src_pos": r["src_pos"]})
        elif "minister" in sec:
            n += 1
            recs.append(_state.rec(MODULE, f"minister:{nkey(name) or n}", state="SK", level="state", post="Minister", name=name,
                                   body="Council of Ministers", body_kind="other", department=depts, phone=ph, dept="administration",
                                   post_kind="minister", section=r["section"], src_url=url, src_pos=r["src_pos"]))
    return phones, recs


def parse_dc(html, url=DC):
    out = []
    for r in st_ne.table_rows(html):
        dist = re.sub(r"(?i)\s*district\s*$", "", r.get("district", "")).strip()
        out.append(_state.rec(MODULE, f"dc:{_esw.slug(dist) or nkey(r.get('name', ''))}", state="SK", level="district",
                              district=DISTRICTS.get(dist.lower(), dist), post=r.get("post", "") or "District Collector",
                              name=r.get("name", ""), body=f"Office of the District Collector, {dist}", body_kind="other",
                              dept="administration", phone=_esw.phones(r.get("phone", "") or r.get("contact", "")),
                              cells=r["cells"], src_url=url, src_pos=r["src_pos"]))
    return out


def parse_emp(html, url):
    out = []
    for r in st_ne.label_lists(html):
        lab = r["labels"]
        name = lab.get("name", "")
        if not name:
            continue
        ph = lab.get("contact no.", lab.get("contact no", ""))
        ph = "" if re.fullmatch(r"\(?0?3592\)?", ph.strip()) else ph
        dept, place = lab.get("department", ""), lab.get("place of posting", "")
        out.append(_state.rec(MODULE, f"emp:{_esw.slug(dept)}:{nkey(name)}", state="SK", level="state", post="", name=name,
                              body=dept, body_kind="department", department=dept, dept=st_ne.dept(dept), phone=ph, place_of_posting=place,
                              section="Employee Telephone Directory", src_url=url, src_pos=r["src_pos"]))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:all", "payload": {"reader": MODULE, "url": HOD, "state": "SK", "india_only": False,
                                                 "route": "direct"}}]


def fetch(p, get):
    files, recs = [], []
    t = get(TEL)
    phones = {}
    if t is not None and t.status_code == 200:
        files.append(_esw.keep(MODULE, "telephone-directory", t.content))
        phones, recs = parse_tel(t.text, TEL)
    h = get(p.get("url") or HOD)
    if h is None or h.status_code != 200:
        return recs, files, "head-of-departments page: no answer"
    files.append(_esw.keep(MODULE, "head-of-departments", h.content))
    recs = parse_hod(h.text, p.get("url") or HOD, phones) + recs
    d = get(DC)
    if d is not None and d.status_code == 200:
        files.append(_esw.keep(MODULE, "district-collectors", d.content))
        recs += parse_dc(d.text, DC)
    e = get(EMP_FIRST)
    if e is not None and e.status_code == 200:
        files.append(_esw.keep(MODULE, "employees-1", e.content))
        recs += parse_emp(e.text, EMP_FIRST)
        m = re.search(r'id="totalRec"[^>]*value="(\d{1,5})"', e.text)
        pages = -(-int(m.group(1)) // 10) if m else 1
        for n in range(2, min(pages, 200) + 1):
            u = EMP.format(n=n)
            r = get(u)
            if r is None or r.status_code != 200:
                continue
            files.append(_esw.keep(MODULE, f"employees-{n}", r.content))
            recs += parse_emp(r.text, u)
    return recs, files, "" if recs else "no rows"
