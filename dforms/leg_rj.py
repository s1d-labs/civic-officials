"""Rajasthan: MLAs of the 16th Rajasthan Vidhan Sabha (2023-) from the assembly's member contacts page
(assembly.rajasthan.gov.in/Containers/Members/Contacts.aspx). Answers from Germany too.

One ASP.NET grid, one row per member (about 200): name with the list's serial number "(187)" (not the AC number), party,
"Constituency (District)", mobile, email (written name[at]gmail[dot]com), permanent address + phone, local (Jaipur) address +
phone, Vidhan Sabha terms. Here: permanent_address + phone_constituency (the permanent column's phone), residence_address +
phone_residence (the Jaipur column). The page gives no AC number: the constituency name decides it (_leg.ac_seat). No constituency
office. One queue item = the whole page (a plain GET; the grid needs no postback).
"""
import re

from dforms._trail import tr_pos
from dforms import _leg

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_rj"
URL = "https://assembly.rajasthan.gov.in/Containers/Members/Contacts.aspx"
# the page's spellings -> the names of dforms/ac_no.json (all 53 checked by hand against the AC list, 2026-11-11)
ALIAS = {"aaspur": "aspur", "alwarcity": "alwarurban", "amer": "amber", "anupgrah": "anupgarh", "baali": "bali",
         "basedi": "baseri", "baytu": "baytoo", "bhadara": "bhadra", "bheem": "bhim", "bheenmaal": "bhinmal",
         "chabra": "chhabra", "chauhtan": "chohtan", "chaurasee": "chorasi", "dantharamgrah": "dantaramgarh",
         "degaana": "degana", "devliuniara": "deoliuniara", "dhariyavd": "dhariawad", "didwana": "deedwana",
         "falaudi": "phalodi", "hanumangrah": "hanumangarh", "jamvaramgarh": "jamwaramgarh", "khandaar": "khandar",
         "kherwada": "kherwara", "khinvsar": "khinwsar", "kishanpol": "kishanpole", "kumbhlgarh": "kumbhalgarh",
         "laadpura": "ladpura", "ladanu": "ladnun", "laxmangarh": "lachhmangarh", "mahwa": "mahuwa", "makarana": "makrana",
         "masooda": "masuda", "mawali": "mavli", "nathwara": "nathdwara", "neemkathana": "neemakathana",
         "nimbaheda": "nimbahera", "osians": "osian", "pokran": "pokaran", "pratapgrah": "pratapgarh",
         "rajakheda": "rajakhera", "raniwada": "raniwara", "raysinghnagar": "raisinghnagar", "revdar": "reodar",
         "sadulshar": "sadulshahar", "sahada": "sahara", "salumbar": "salumber", "sanchor": "sanchore",
         "sangriya": "sangaria", "shiv": "sheo", "sikray": "sikrai", "thanagaji": "thanagazi",
         "vidhadharnagar": "vidhyadharnagar", "wair": "weir"}


def items(get=None):
    return [{"key": "leg_rj-list", "payload": {"reader": MODULE, "url": URL, "state": "RJ", "india_only": False}}]


def _span(tr, part):
    s = tr.find("span", id=re.compile(r"_" + part + r"_\d+$"))
    return _leg.clean(s.get_text(" ")) if s else ""


def _addr(*parts):
    return ", ".join(p.strip(" ,•") for p in parts if p.strip(" ,•"))


def parse(html, url=URL):
    from bs4 import BeautifulSoup
    html = html.replace("\u200d", "").replace("\u200c", "")   # _esw.clean turns ZWJ/ZWNJ into spaces inside Devanagari words
    soup = BeautifulSoup(html, "lxml")
    grid = soup.find("table", id=re.compile(r"GrdMemberContact$"))
    recs = []
    for tr in grid.find_all("tr") if grid else []:
        a = tr.find("a", id=re.compile(r"_btnmember\w*_\d+$"))
        if a is None:
            continue
        name = re.sub(r"\s*\(\d+\)\s*$", "", _leg.clean(a.get_text(" ")))
        area = _span(tr, "LblMemElectedArea")
        m = re.match(r"(.+?)\s*\(([^()]+)\)\s*$", area)
        cons, district = (m.group(1), m.group(2)) if m else (area, "")
        key = _leg.norm(cons)
        seat, note = _leg.ac_seat("RJ", None, ALIAS.get(key, key), district)
        perm = _addr(_span(tr, "lbl_PemAdd1"), _span(tr, "lbl_PemAdd2"), _span(tr, "lbl_PemAdd3"))
        local = _addr(_span(tr, "lbl_LocAdd1"), _span(tr, "lbl_LocAdd2"), _span(tr, "lbl_LocAdd3"))
        recs.append(_leg.member(MODULE, "RJ", "AC", seat, name, constituency=cons, party=_span(tr, "lblparty"), source=url,
                                mobile=_span(tr, "lblmobile"), email=_span(tr, "lblemail"), permanent_address=perm,
                                phone_constituency=_span(tr, "lblLocTel"), residence_address=local,
                                phone_residence=_span(tr, "lblPreTel"), district=district, terms=_span(tr, "LblHouseNo"),
                                note=note or ("" if seat else "constituency name not in the AC list"), src_pos=tr_pos(tr)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "contacts", r.content, "html")]
    recs = parse(r.content.decode("utf-8", "replace"), p["url"])
    return recs, files, "" if recs else "no members"
