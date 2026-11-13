"""Andhra Pradesh: officers of the state portal www.ap.gov.in (Angular app; its own open JSON API at
https://www.ap.gov.in/api/api/<list>, the calls the page makes, found in its api_service chunk; checked 2026-11-13 from Mumbai):

group        master list (names the group)          child list (the officers)              rows (2026-11-13)
secretaries  ApSecretaries (37 departments)         ApSecretariesChilds                    72 (Spl. CS, Prl. Secretaries, Secretaries)
hods         ApHoDs (29) + ApSubHoDs (167 offices)  ApHodsChilds (subHodId = office)        219 (commissioners, directors)
district     ApDistrictOfficials (28 districts)     ApDistrictOfficialsChilds              94 (Collector, Joint Collector, SP)
cmo          -                                      ChiefMinisterOffice                    4 (Secretaries to CM, portfolios)
advisors     ApAdvisorsToGovernments                ApAdvisorsToGovernmentChilds           5
psus         ApPsus + ApSubPsus                      ApPsusChilds (psuSubId)                98 (MDs, VCs of corporations)
nominated    ApNominatedOfficers (56 corporations)  ApNominatedOfficersChilds              725 (chairpersons, directors)

Every list answers {"isSuccess", "dataList": [...]}. A child row: name, designation, contactDetails (HTML: "Address:",
"Phone:", "Email:" with "[at]" / "[dot]"), masterId (and subHodId / psuSubId). Records: level state, district for the district
group (LGD code from the master's district name). One queue item = one group (2-3 GETs). Ids: dept:st_ap_portal:<group>:<id>.
src_pos {"index", "id"} = the row's place and id in the child list. Route: answered from Mumbai (direct); abroad unchecked.
"""
import json
import re

from dforms import _esw, _state, _st_ape

METHOD = "json api (dataList rows; contactDetails html labels)"
MODULE = "st_ap_portal"
API = "https://www.ap.gov.in/api/api/"
GROUPS = {
    "secretaries": {"master": "ApSecretaries", "child": "ApSecretariesChilds", "kind": "secretariat"},
    "hods": {"master": "ApHoDs", "sub": "ApSubHoDs", "sub_key": "subHodId", "child": "ApHodsChilds", "kind": "directorate"},
    "district": {"master": "ApDistrictOfficials", "child": "ApDistrictOfficialsChilds", "kind": "district"},
    "cmo": {"child": "ChiefMinisterOffice", "kind": "cm_office"},
    "advisors": {"master": "ApAdvisorsToGovernments", "child": "ApAdvisorsToGovernmentChilds", "kind": "other"},
    "psus": {"master": "ApPsus", "sub": "ApSubPsus", "sub_key": "psuSubId", "child": "ApPsusChilds", "kind": "other"},
    "nominated": {"master": "ApNominatedOfficers", "child": "ApNominatedOfficersChilds", "kind": "other"},
}
AP = {"alluri sitharama raju": "745", "anakapalli": "744", "ananthapuramu": "502", "anantapur": "502", "annamayya": "753",
      "bapatla": "750", "chittoor": "503", "dr b r ambedkar konaseema": "747", "konaseema": "747", "east godavari": "505",
      "eluru": "748", "guntur": "506", "kakinada": "746", "krishna": "510", "kurnool": "511", "markapuram": "790",
      "nandyal": "755", "ntr": "749", "palnadu": "751", "parvathipuram manyam": "743", "polavaram": "791", "prakasam": "517",
      "srikakulam": "519", "sri potti sriramulu nellore": "515", "potti sreeramulu nellore": "515", "nellore": "515",
      "sri sathya sai": "754", "sri satyasai": "754", "tirupati": "752", "visakhapatnam": "520", "vizianagaram": "521",
      "west godavari": "523", "y s r kadapa": "504", "ysr kadapa": "504", "kadapa": "504"}
AP_NAME = {"745": "Alluri Sitharama Raju", "744": "Anakapalli", "502": "Ananthapuramu", "753": "Annamayya", "750": "Bapatla",
           "503": "Chittoor", "747": "Dr. B.R. Ambedkar Konaseema", "505": "East Godavari", "748": "Eluru", "506": "Guntur",
           "746": "Kakinada", "510": "Krishna", "511": "Kurnool", "790": "Markapuram", "755": "Nandyal", "749": "Ntr",
           "751": "Palnadu", "743": "Parvathipuram Manyam", "791": "Polavaram", "517": "Prakasam", "519": "Srikakulam",
           "515": "Sri Potti Sriramulu Nellore", "754": "Sri Sathya Sai", "752": "Tirupati", "520": "Visakhapatnam",
           "521": "Vizianagaram", "523": "West Godavari", "504": "Y.S.R. Kadapa"}


def district_code(name):
    k = re.sub(r"\s+", " ", re.sub(r"[^a-z]", " ", (name or "").lower())).strip()
    if k in AP:
        return AP[k]
    for n, c in sorted(AP.items(), key=lambda x: -len(x[0])):
        if n in k:
            return c
    return ""


def district_rank(post):
    """Rank key of a district-list post (Collector, Joint Collector, SP; police ranges as the list writes them)."""
    t = _esw.clean(post)
    for k, rx in (("district_magistrate", r"(?i)^collector"), ("adm", r"(?i)^joint collector"),
                  ("sp", r"(?i)superintendent of police"), ("dig", r"(?i)deputy inspector general|^D\.?I\.?G\b|^DIG\b")):
        if re.search(rx, t):
            return k
    return _st_ape.post_kind(t)


def rows(doc):
    if isinstance(doc, dict):
        doc = doc.get("dataList") or []
    return [x for x in doc if isinstance(x, dict)] if isinstance(doc, list) else []


def label_name(s):
    """Master name without its code: "Department : [AGC01] – Agriculture & Cooperation" -> ("Agriculture & Cooperation", "AGC01")."""
    s = _esw.clean(s)
    m = re.search(r"\[?([A-Z]{2,4}\d{2})\]\s*[–-]\s*(.*)$", s)
    if m:
        return _esw.clean(m.group(2)), m.group(1)
    return re.sub(r"(?i)^department\s*:\s*", "", s), ""


def contact(html):
    """{address, phone, email} of a contactDetails HTML cell."""
    if not html or html.strip() in ("-", ""):
        return {}
    t = _esw.clean(_esw.soup(html.replace("<br>", "\n").replace("<br/>", "\n")).get_text(" "))
    out = {}
    m = re.search(r"(?i)address\s*:?\s*(.*?)(?=\b(?:phone|mobile|tel|email|e-mail|fax)\b|$)", t)
    if m:
        out["address"] = m.group(1).strip(" :,")
    m = re.search(r"(?i)(?:phone|mobile|tel)\w*\s*:?\s*(.*?)(?=\b(?:email|e-mail|fax|address)\b|$)", t)
    out["phone"] = _esw.phones(m.group(1)) if m else _esw.phones(re.sub(r"(?i)\S+\[at\]\S+", " ", t))
    out["email"] = _esw.emails(t)
    return {k: v for k, v in out.items() if v}


def portfolio(html):
    if not html:
        return []
    soup = _esw.soup(html)
    items = [_esw.clean(d.get_text(" ")) for d in soup.find_all("div")] or [_esw.clean(soup.get_text(" "))]
    return [re.sub(r"^\d+\.\s*", "", x) for x in items if x]


def parse(group, child, master=None, sub=None, url=""):
    g = GROUPS[group]
    mnames = {x.get("id"): x.get("name") for x in rows(master)}
    snames = {x.get("id"): x.get("name") for x in rows(sub)}
    recs = []
    for i, x in enumerate(rows(child)):
        if x.get("isActive") is False or x.get("isDeleted"):
            continue
        name, post = _esw.clean(x.get("name")), _esw.clean(x.get("designation"))
        if not (name or post):
            continue
        mname, mcode = label_name(mnames.get(x.get("masterId"), ""))
        sname, scode = label_name(snames.get(x.get(g.get("sub_key", "")), "")) if g.get("sub_key") else ("", "")
        c = contact(x.get("contactDetails"))
        common = dict(state="AP", name=name, post=post or "Officer", post_kind=_st_ape.post_kind(post), phone=c.get("phone", ""),
                      email=c.get("email", ""), address=c.get("address", ""), src_url=url, src_pos={"index": i, "id": x.get("id")},
                      section=group, dept_code=mcode or None, office_code=scode or None, portfolio=portfolio(x.get("portfolio")) or None,
                      modified=x.get("modifiedDate") or x.get("createdDate"))
        if group == "nominated" and common["post_kind"] == "head_of_department":
            common["post_kind"] = "member"       # board directors of the welfare corporations, not heads of departments
        k = f"{group}:{x.get('id', i)}"
        if group == "district":
            code = district_code(mname)
            common["post_kind"] = district_rank(post)
            recs.append(_state.rec(MODULE, k, level="district", district=AP_NAME.get(code) or mname.title(), district_code=code,
                                   body=f"District administration, {mname.title()}", body_kind="district",
                                   department="Police" if re.search(r"(?i)police|\bS\.?P\b", post) else "Revenue", **common))
        elif group == "cmo":
            recs.append(_state.rec(MODULE, k, level="state", body="Chief Minister's Office, Andhra Pradesh", body_kind="cm_office",
                                   department="Chief Minister's Office", dept="administration", **common))
        else:
            body = sname or mname
            recs.append(_state.rec(MODULE, k, level="state", body=body, body_kind=g["kind"], department=mname,
                                   office=sname or None, **common))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}:{g}", "payload": {"reader": MODULE, "group": g, "url": API + v["child"], "state": "AP",
                                                 "india_only": True, "route": "direct"}} for g, v in GROUPS.items()]


def _json(get, url):
    r = get(url)
    if r is None:
        return None, None
    try:
        return json.loads(r.content.decode("utf-8-sig")), r
    except ValueError:
        return None, r


def fetch(p, get):
    g = GROUPS[p["group"]]
    child, r = _json(get, API + g["child"])
    if child is None:
        return [], [], "no json"
    files = [_esw.keep(MODULE, g["child"], r.content, "json")]
    master = sub = None
    for key in ("master", "sub"):
        if g.get(key):
            doc, rr = _json(get, API + g[key])
            if rr is not None:
                files.append(_esw.keep(MODULE, g[key], rr.content, "json"))
            if key == "master":
                master = doc
            else:
                sub = doc
    recs = parse(p["group"], child, master, sub, API + g["child"])
    return recs, files, "" if recs else "no rows"
