"""Telangana: secretariat and district officers from the state portal telangana.gov.in (WordPress, HTML tables, checked in the
archive copy of 2026-11-13; page sizes 170-175 KB):

1. https://telangana.gov.in/contacts/secretariat/ : table 1 "Department | Name | Designation | Office Phone | Email" (51 rows:
   Chief Secretary, Spl. Chief Secretaries, Prl. Secretaries, Secretaries, Spl. Secretaries of every department, CMO, Chief
   Electoral Officer); table 2 "Name | Designation | Email | Office | Residence" (6 rows: the Governor's secretariat, Raj Bhavan).
2. https://telangana.gov.in/contacts/district-officials/ : "District Name | Name | Designation | Office Phone | Email" (96 rows:
   Collector, Additional Collector, SP / CP of each district). E-mails written as "collector_adbd[at]telangana[dot]gov[dot]in".

Records: level state (secretariat, Raj Bhavan) or district (district list, with the LGD district code). One queue item = one page.
Ids: dept:st_tg_portal:<page>:<table>:<row>. Route: the portal answers from Mumbai (archive vantage IN); abroad unchecked.
"""
import re

from dforms import _esw, _state, _st_ape

METHOD = "html table (header names)"
MODULE = "st_tg_portal"
BASE = "https://telangana.gov.in/contacts/"
PAGES = {"secretariat": BASE + "secretariat/", "district-officials": BASE + "district-officials/"}
# LGD district names (state 36) -> code; the portal's spellings that differ are added
TG = {"adilabad": "501", "bhadradrikothagudem": "690", "hanumakonda": "686", "hanamkonda": "686", "hyderabad": "507",
      "jagitial": "681", "jagtial": "681", "jangoan": "689", "jangaon": "689", "jayashankarbhupalapally": "687",
      "jayashankarbhupalpally": "687", "jayashankarbhoopalpally": "687", "jogulambagadwal": "695", "kamareddy": "685", "karimnagar": "508", "khammam": "509",
      "kumurambheemasifabad": "699", "komarambheemasifabad": "699", "kumrambheemasifabad": "699", "mahabubabad": "688",
      "mahabubnagar": "512", "mahbubnagar": "512", "mancherial": "684", "medak": "513", "medchalmalkajgiri": "700",
      "medchal": "700", "mulugu": "720", "nagarkurnool": "694", "nalgonda": "514", "narayanpet": "721", "nirmal": "680",
      "nizamabad": "516", "peddapalli": "682", "rajannasircilla": "683", "rangareddy": "518", "sangareddy": "691",
      "siddipet": "692", "suryapet": "696", "vikarabad": "698", "wanaparthy": "693", "warangal": "522",
      "yadadribhuvanagiri": "697"}


def district_code(name):
    return TG.get(re.sub(r"[^a-z]", "", re.sub(r"\(.*?\)", "", (name or "").lower()).replace("district", "")), "")


def phone_of(s):
    return _esw.phones(re.sub(r"[?​]", " ", s or ""))


def parse(html, url, page):
    recs = []
    for ti, t in enumerate(_st_ape.tables(html), 1):
        rows = _st_ape.header_rows(t)
        for d, pos, cells in rows:
            post = d.get("post", "")
            name = d.get("name", "")
            if not (post or name):
                continue
            phone = ", ".join(x for x in (phone_of(d.get("phone")), phone_of(d.get("residence"))) if x)
            fax = re.search(r"(?i)fax\s*:?\s*([\d\s/-]{6,})", " ".join(cells))
            common = dict(state="TG", post=post, post_kind=_st_ape.post_kind(post), name=name, phone=phone, email=_esw.emails(" ".join(cells)),
                          src_url=url, src_pos=pos, cells=cells, section=page, fax=fax.group(1).strip() if fax else None,
                          residence_phone=phone_of(d.get("residence")) or None)
            k = f"{page}:{ti}:{pos['row']}"
            if page == "district-officials":
                dist = d.get("district", "")
                recs.append(_state.rec(MODULE, k, level="district", district=dist, district_code=district_code(dist),
                                       body=f"District administration, {dist}", body_kind="district",
                                       department="Police" if re.search(r"(?i)police|\bS\.?P\b|\bC\.?P\b|\bDCP\b", post)
                                       else "Revenue", **common))
            elif "department" in d:
                dep = d["department"]
                kind = "cm_office" if re.search(r"(?i)chief minister", dep) else "secretariat"
                recs.append(_state.rec(MODULE, k, level="state", body=f"Telangana Secretariat: {dep}", body_kind=kind,
                                       department=dep, **common))
            else:   # table 2: the Governor's secretariat
                recs.append(_state.rec(MODULE, k, level="state", body="Raj Bhavan, Hyderabad", body_kind="governor",
                                       department="Governor's Secretariat", **common))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}:{p}", "payload": {"reader": MODULE, "url": u, "page": p, "state": "TG", "india_only": True,
                                                 "route": "direct"}} for p, u in PAGES.items()]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    html = r.text
    recs = parse(html, p["url"], p.get("page") or "secretariat")
    return recs, [_esw.keep(MODULE, p.get("page") or "page", r.content)], "" if recs else "no rows"
