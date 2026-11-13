"""Himachal Pradesh: Jal Shakti Vibhag officers from the state telephone directory, services.hp.gov.in/hpcivil/TelephoneDirectory
(answers only from India; jsv.hp.gov.in itself does not answer). One POST to GetDataViewPV with DepartmentId=B22 (Jal Shakti Vibhag)
and TabId=2, the same form fields the directory page sends; the answer is an HTML fragment with one table: a heading row per office
("JAL SHAKTI VIBHAG,JAL SHAKTI BHAWAN, SHIMLA-5") and one row per officer: name, post ("Executive Engineer Una", "S E Dharampur",
"Chief Engineer (D&QC)"), "(O):" office phone, "(R):" residence (often the mobile), "(@):" email. About 165 rows, no date. PA rows
(no name) are left out. One queue item.
Level from the post; area = the post without the rank ("Executive Engineer (D) Hamirpur" -> "(D) Hamirpur").
Record ids: dept:water_hp:HP-JSV-<slug of post>.
"""
import re

from dforms import _esw, _water
from dforms._power import tr_pos
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water_hp"
URL = "https://services.hp.gov.in/hpcivil/TelephoneDirectory/GetDataViewPV"
FORM = {"TabId": "2", "OfficerNm": "", "DepartmentId": "B22", "DepartmentNm": "", "Designation": "", "PhoneNo": ""}
ORG = "Jal Shakti Vibhag, Himachal Pradesh"
RANK = re.compile(r"(?i)^(engineer[\s-]*in[\s-]*chief|chief engineer|supdt\.?\s*eng(?:ineer|g)?\.?|superintending engineer|s\s?e|"
                  r"executive engineer|e\s?e|assistant engineer|a\s?e|junior engineer|j\s?e)\b\.?\s*")
SKIP = re.compile(r"(?i)^(p\s?\.?\s?a\.?|personal assistant)$")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "HP", "india_only": True, "form": FORM}}]


def label(cell, mark):
    for d in cell.find_all("div", style=re.compile("nowrap")):
        t = _esw.clean(d.get_text(" "))
        if t.startswith(mark):
            return t[len(mark):].strip()
    return ""


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen, office = [], set(), ""
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) == 1 and tds[0].get("colspan"):
            office = _esw.clean(tds[0].get_text(" "))
            continue
        if len(tds) < 2:
            provenance.skip_row(tr, 'skip: len(tds) < 2')
            continue
        nm = tds[0].select_one(".fs-5")
        badge = tds[0].select_one(".badge")
        name = _esw.clean(nm.get_text(" ")) if nm else ""
        post = _esw.clean(badge.get_text(" ")) if badge else ""
        if name == post:                         # rows without an officer repeat the post in the name line
            name = ""
        if not post or (SKIP.match(post) and not name):
            provenance.skip_row(tr, 'skip: not post or (SKIP.match(post) and not name)')
            continue
        o, res, mail = label(tds[1], "(O):"), label(tds[1], "(R):"), label(tds[1], "(@):")
        phone = _esw.phones(o, res if len(re.sub(r"\D", "", res)) >= 10 else "")
        email = _esw.emails(mail)
        if not (name or phone or email):
            provenance.skip_row(tr, 'skip: not (name or phone or email)')
            continue
        area = RANK.sub("", post).strip(" ,-") or office
        key = _water.unique(f"HP-JSV-{_esw.slug(post)}", seen)
        recs.append(_esw.record(MODULE, key, dept="water", level=_water.level_of(post, "state"), area=area, post=post, name=name,
                                phone=phone, email=email, state="HP", office_id=key, org=ORG, office=office, source=url,
                                src_pos=tr_pos(tr)))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL), method="POST", data=p.get("form", FORM))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "jsv-B22", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
