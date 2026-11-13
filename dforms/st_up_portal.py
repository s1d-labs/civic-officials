"""Uttar Pradesh: "Contact Details of District Level Officials" of the state portal (up.gov.in/en/page/contact-details-of-
district-level-officials, checked 2026-11-13 from dev-vps-3, Mumbai; 61 KB HTML), three tables:
1. Divisional Commissioners (18): Sr. No. | Division Name | Name | Mobile No | Email ID -> level division, districts from
   dforms/st_div_up.json (the same 18 groups as table 2; checked by the test).
2. District Magistrates (75), under one heading row per division ("A | Agra Division"): Sr. No. | District Name | Name |
   Mobile No | Email ID -> level district, with the division.
3. Police heads of districts (75): Sr. No. | Name of District | Designation (SSP / SP / CP) | Name of Officer | Phone ->
   level district (CP = police commissionerate).
E-mails are written "commagr[at]nic[dot]in" (read with _esw.emails). Record id dept:st_up_portal:<divcom|dm|police>:<slug of the
division or district>. src_pos {"table", "row"}. One item = the page (one GET). Route: direct (answers from Mumbai); abroad unchecked.
"""
import re

from dforms import _esw, _state, st_lgd_upbrjh as lgd

METHOD = "html table"
MODULE = "st_up_portal"
URL = "https://up.gov.in/en/page/contact-details-of-district-level-officials"
DIV_NAMES = {"chitrakootdham": "Chitrakoot", "vindhyachal": "Mirzapur", "faizabad": "Ayodhya", "allahabad": "Prayagraj",
             "devipatangonda": "Devipatan"}


def div_name(s):
    s = re.sub(r"(?i)\s*division\s*$", "", _esw.clean(s))
    return DIV_NAMES.get(re.sub(r"[^a-z]", "", s.lower()), s)


def parse(html, url=URL):
    s = _esw.soup(html)
    out = []
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        head = next((r for r in rows if any("Sr" in c for c in r)), None)
        if not head:
            continue
        h = " ".join(head).lower()
        kind = "divcom" if "divisional commissioner" in h else "dm" if "district magistrate" in h else "police" if "designation" in h else ""
        if not kind:
            continue
        division = ""
        for cells, sp in zip(rows, pos):
            if cells is head:
                continue
            if len(set(cells)) <= 2 and len(cells) >= 2 and re.search(r"(?i)division\s*$", cells[-1]):
                division = div_name(cells[-1])
                continue
            if not re.fullmatch(r"\d{1,3}\.?", cells[0] or ""):
                continue
            c = (cells + [""] * 5)[:5]
            if kind == "divcom":
                div = div_name(c[1])
                out.append(_state.rec(MODULE, f"divcom:{_esw.slug(div)}", state="UP", level="division",
                                      post="Divisional Commissioner", name=c[2], dept="revenue",
                                      body=f"Office of the Divisional Commissioner, {div}", body_kind="division",
                                      department="Revenue Department", division=div, phone=c[3], email=_esw.emails(c[4]),
                                      cells=cells, source=url, src_url=url, src_pos=sp))
            elif kind == "dm":
                code, name = lgd.district("UP", c[1])
                out.append(_state.rec(MODULE, f"dm:{_esw.slug(name or c[1])}", state="UP", level="district",
                                      post="District Magistrate", name=c[2], dept="administration",
                                      body=f"Collectorate, {name or c[1]}", body_kind="other", department="Revenue Department",
                                      district=name or c[1], district_code=code, division_of_district=division or None,
                                      phone=c[3], email=_esw.emails(c[4]), cells=cells, source=url, src_url=url, src_pos=sp))
            else:
                code, name = lgd.district("UP", c[1])
                post = c[2]
                full = {"CP": "Commissioner of Police", "SSP": "Senior Superintendent of Police",
                        "SP": "Superintendent of Police"}.get(post.upper().replace(".", ""), post)
                out.append(_state.rec(MODULE, f"police:{_esw.slug(name or c[1])}", state="UP", level="district", post=full,
                                      name=c[3], dept="police", body=f"UP Police: {name or c[1]}", body_kind="police",
                                      department="Home Department", district=name or c[1], district_code=code,
                                      post_short=post, phone=c[4], cells=cells, source=url, src_url=url, src_pos=sp))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:district-officials", "payload": {"reader": MODULE, "url": URL, "state": "UP", "india_only": True,
                                                                "route": "direct"}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.content.decode("utf-8", "replace"), p["url"])
    return recs, [_esw.keep(MODULE, "district-officials", r.content)], "" if recs else "no rows"
