"""Rajasthan: elected Sarpanch (head of the gram panchayat, with mobile) and Ward Panch (members) of the PRI general election
OCT-NOV 2026, from the State Election Commission page "Grampanchayat Election Statistical Reports"
https://sec.rajasthan.gov.in/GramPanchayatDetails.aspx (linked from GP_Election_Reports.aspx). India only (answers from Mumbai,
measured 2026-11-13); no captcha, no login.

ASP.NET postbacks: Election 1 (General) + Period (64 = "OCT-NOV 2026") -> District -> Panchayat Samiti, then Submit with Gram
Panchayat "--All--". The answer (about 0.7 MB for a samiti of 49 GPs) holds four tabs for every GP of the samiti:
  #tabs-1 Contesting Sarpanch: GP, GP category, candidate no, name, father/husband, gender, marital status, category, education,
          occupation, age, assets, children (before/after 28.11.1995), Mobile No., E-mail;
  #tabs-3 nomination statistics (not read);
  #tabs-4 Winner Sarpanch: GP, GP category (seat reservation), contestants, unopposed YES/NO, electorate, polled, rejected, valid,
          poll %, winner name, pledge link, winner votes, runner-up name and votes, NOTA, tendered;
  #tabs-7 Ward Winning Panch: GP, ward no, villages of the ward, ward category, name, total votes (electorate), votes polled,
          poll %, unopposed, category of the winner, remark, winner votes, loser votes.
The Sarpanch record takes the winner row of #tabs-4 and, from #tabs-1, the contesting row of the same GP with the same name
(father/husband, gender, age, education, occupation, mobile, email). The election runs in phases (phase 1: 3,314 GPs in 16
districts, results 2026-10-24/25): a samiti whose poll has not taken place gives no winner rows (item ends "no winner rows";
queue it again after its phase).

One queue item = one panchayat samiti, 5 requests. items(get) lists every samiti of the period (1 GET + 1 + 41 district postbacks).
Records (dforms/_pri.py, type pri_member, level gp): pri:pri_rj:<period>-<samiti value>:<GP slug>:sarpanch and
...:<GP slug>:w<ward no>; body_name = GP as written, block = samiti name without "PANCHAYAT SAMITI", district as the page names it.
No LGD code on the page: the loader matches GP name within district + block (LGD spells many names differently).
"""
import gzip
import re

from bs4 import BeautifulSoup

import provenance
from dforms import _pri
from forms.aspnet import hidden, options

METHOD = "html table (ASP.NET result page after dropdown postbacks; tabs Winner Sarpanch, Contesting Sarpanch, Ward Winning Panch)"

MODULE = "pri_rj"
URL = "https://sec.rajasthan.gov.in/GramPanchayatDetails.aspx"
P = "ctl00$ContentPlaceHolder1$"
PERIOD = "64"
ELECTION = "Rajasthan PRI General Election"


def _post(get, html, target, fields, submit=False):
    d = hidden(html)
    d.update({"__EVENTTARGET": "" if submit else P + target, "__EVENTARGUMENT": "", **{P + k: v for k, v in fields.items()}})
    if submit:
        d[P + "btnSubmit"] = "Submit"
    return get(URL, method="POST", data=d)


def block_name(s):
    return _pri.clean(re.sub(r"(?i)\s*panchayat\s+samiti\s*$", "", s or ""))


def items(get, period=PERIOD):
    r = get(URL)
    if r is None:
        return []
    f = {"DropDownListElection": "1", "DropDownListPeriod": period}
    r = _post(get, r.text, "DropDownListPeriod", f)
    if r is None:
        return []
    h = r.text
    out = []
    for dv, dname in options(h, "DistrictDropDownList"):
        r2 = _post(get, h, "DistrictDropDownList", {**f, "DistrictDropDownList": dv})
        if r2 is None:
            raise RuntimeError(f"district {dname} did not answer")
        for sv, sname in options(r2.text, "PanchayatSamitiDropDownList"):
            out.append({"key": f"pri_rj:{period}-{sv}", "payload": {
                "reader": MODULE, "url": URL, "state": "RJ", "period": period, "district_value": dv, "district": dname,
                "samiti_value": sv, "samiti": sname, "india_only": True, "route": "direct"}})
    return out


def _tab(soup, tab_id):
    """[(row number, {header: text})] of the first table in a tab; the header is the first row."""
    div = soup.find(id=tab_id)
    t = div.find("table") if div else None
    if t is None:
        return []
    trs = t.find_all("tr")
    if not trs:
        return []
    head, spans = [], []
    for c in trs[0].find_all(["th", "td"]):
        n = int(c.get("colspan")) if (c.get("colspan") or "").isdigit() else 1
        head.append(_pri.clean(c.get_text(" ", strip=True)))
        spans.append(n)
    if any(n > 1 for n in spans) and len(trs) > 1:      # "Children" spans "Before 27.11.1995 | On Or After 28.11.1995"
        sub = [_pri.clean(c.get_text(" ", strip=True)) for c in trs[1].find_all(["th", "td"])]
        out = []
        for h, n in zip(head, spans):
            out += [f"{h} {sub.pop(0) if sub else i + 1}" for i in range(n)] if n > 1 else [h]
        head = out
    rows = []
    for ri, tr in enumerate(trs[1:], 2):
        cells = [_pri.clean(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
        if len(cells) != len(head):        # sub-header rows ("Before 27.11.1995 | On Or After 28.11.1995")
            provenance.skip_row(tr, 'skip: len(cells) != len(head)')
            continue
        rows.append((ri, dict(zip(head, cells))))
    return rows


def _key(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _selected(soup, name_end):
    sel = next((s for s in soup.find_all("select") if (s.get("name") or "").endswith(name_end)), None)
    o = sel.find("option", selected=True) if sel else None
    return _pri.clean(o.get_text(" ", strip=True)) if o else ""


def _yes(v):
    return {"YES": True, "NO": False}.get((v or "").strip().upper())


def parse(html, p, src=None):
    """Records of one samiti answer (the page after Submit)."""
    soup = BeautifulSoup(html, "lxml")
    period_label = _selected(soup, "DropDownListPeriod") or "OCT-NOV 2026"
    district = _selected(soup, "DistrictDropDownList") or p.get("district")
    samiti = _selected(soup, "PanchayatSamitiDropDownList") or p.get("samiti")
    if p.get("samiti") and samiti and _key(samiti) != _key(p["samiti"]):
        raise ValueError(f"page shows {samiti}, not {p['samiti']}")
    election = f"{ELECTION} {period_label}"
    year = int(m.group(0)) if (m := re.search(r"\b20\d\d\b", period_label)) else None
    base = {"state": "RJ", "level": "gp", "district": district, "block": block_name(samiti), "samiti": samiti,
            "election": election, "election_year": year, "source": URL, "src_url": URL, **(src or {})}
    pre = f"{p.get('period', PERIOD)}-{p.get('samiti_value', _pri.slug(samiti))}"
    # contesting Sarpanch rows by GP + name
    cand = {}
    for ri, c in _tab(soup, "tabs-1"):
        cand.setdefault((_key(c.get("Name Of GramPanchayat")), _key(c.get("Name Of Contesting Candidate"))), (ri, c))
    recs = []
    for ri, c in _tab(soup, "tabs-4"):
        gp, name = c.get("Name Of GramPanchyat"), c.get("Winner Candidate Name")
        if not gp or not name:
            continue
        ci, cc = cand.get((_key(gp), _key(name)), (None, {}))
        recs.append(_pri.record(
            MODULE, f"{pre}:{_pri.slug(gp)}:sarpanch", **base, role="head", post="Sarpanch", post_regional="सरपंच",
            name=name, body_name=gp, seat_category=c.get("Category Of GramPanchyat"),
            father_name=cc.get("Father/Husband Of Contesting Candidate"), gender=cc.get("Gender"), age=_pri.int_or_none(cc.get("Age")),
            category=cc.get("Category of Candidate"), education=cc.get("Education Status"),
            occupation=cc.get("Contesting Candidate Occupation"), phone=_pri.mobile(cc.get("Mobile No.")),
            email=cc.get("E-mail Address"), votes=_pri.int_or_none(c.get("Vote Secure By Winner")),
            unopposed=_yes(c.get("Elected Unoppose (Yes/No)")), status="won",
            contestants=_pri.int_or_none(c.get("Total No. Of Contesting Candidate")),
            electorate=_pri.int_or_none(c.get("Total Electorate Votes")), votes_polled=_pri.int_or_none(c.get("Total Polled Votes")),
            valid_votes=_pri.int_or_none(c.get("Total Valid Votes")), nota=_pri.int_or_none(c.get("Total No. Of NOTA Count")),
            runner_up=c.get("Runnerup Candidate Name"), runner_up_votes=_pri.int_or_none(c.get("Vote Secure By Runnerup")),
            cells=c, candidate_cells=cc or None,
            src_pos={"table": "#tabs-4 (Winner Sarpanch)", "row": ri, **({"candidate_row": ci} if ci else {})}))
    seen = {}
    for ri, c in _tab(soup, "tabs-7"):
        gp, name, ward = c.get("Grampanchayat"), c.get("Name of Candidate"), c.get("Ward.No")
        if not gp or not name:
            continue
        k = f"{pre}:{_pri.slug(gp)}:w{_pri.slug(ward) or ri}"
        seen[k] = seen.get(k, 0) + 1
        recs.append(_pri.record(
            MODULE, k + (f"-{seen[k]}" if seen[k] > 1 else ""), **base, role="member", post="Ward Panch", post_regional="वार्ड पंच",
            name=name, body_name=gp, ward_no=ward, ward=c.get("Name Of Village"), seat_category=c.get("Category of ward"),
            category=c.get("Category Of Winning Candidate"), unopposed=_yes(c.get("Whether Elected Unoppose(YES/NO)")),
            votes=_pri.int_or_none(c.get("Winner Votes")), loser_votes=_pri.int_or_none(c.get("Looser Votes")),
            electorate=_pri.int_or_none(c.get("Total No of Votes")), votes_polled=_pri.int_or_none(c.get("Votes Polled")),
            remark=c.get("Remark if any"), status="won", cells=c,
            src_pos={"table": "#tabs-7 (Ward Winning Panch)", "row": ri}))
    return recs


def fetch(p, get):
    r = get(URL)
    if r is None:
        return [], [], "no answer"
    f = {"DropDownListElection": "1", "DropDownListPeriod": p.get("period", PERIOD)}
    h = r.text
    for target, value in (("DropDownListPeriod", None), ("DistrictDropDownList", p["district_value"]),
                          ("PanchayatSamitiDropDownList", p["samiti_value"])):
        if value is not None:
            f[target] = value
        r = _post(get, h, target, f)
        if r is None:
            return [], [], f"{target} postback did not answer"
        h = r.text
    f["GramPanchayatdrpdwn"] = "0"
    r = _post(get, h, "", f, submit=True)
    if r is None:
        return [], [], "submit did not answer"
    files = [(f"pri/RJ/{p.get('period', PERIOD)}-{p['samiti_value']}-{_pri.slug(p.get('samiti', ''))}.html.gz",
              gzip.compress(r.content), "application/gzip")]
    try:
        recs = parse(r.text, p, provenance.at(r, URL))     # every step is a POST to one url: the answer is named by its bytes
    except ValueError as e:
        return [], files, str(e)
    return recs, files, "" if recs else "no winner rows (poll not held yet?)"
