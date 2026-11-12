"""Rajasthan: heads of the urban bodies elected after the ULB general election of SEP 2026 (indirect elections by the ward members,
Feb 2026 orders 154/155): mayor / chairperson (सभापति, अध्यक्ष) and deputy mayor / vice chairperson.
Source: SEC Rajasthan "Chairperson Detail" (ChairpersonNomination.aspx?code=CEM) and "Dy. Chairperson Detail"
(DyChairpersonNomination.aspx?code=CEM), linked from ULB_Election_Reports.aspx. India only (answers from Mumbai).
ASP.NET postbacks: Election Type 2 (Urban Local Body) + Election 1 (General) + Period 61 ("SEP 2026"), then Submit with District
"--All--". The answer holds six tabs (received, rejected, accepted, withdrawn nominations, Winner, Runner-Up) for all 309 bodies;
the "Winner" tab (div#tabs-5) has one row per body: district, ULB, seat category, name, gender, age, candidate category, party
(chairperson only), electorate (the ward members), votes polled, rejected, valid, candidate votes, NOTA, unopposed.
One queue item = one post ("chair" or "vice"), four requests. Record id councillor:RJ:<body slug>:chair / :vice, with the body slug
of cforms/rj.py (body name; a name that two districts share gets the district), so the head sits with the ward members.
"""
import gzip
import re

from bs4 import BeautifulSoup

import provenance
from forms.aspnet import hidden

METHOD = "html table (ASP.NET result page after dropdown postbacks, Winner tab)"

BASE_URL = "https://sec.rajasthan.gov.in/"
PAGES = {"chair": "ChairpersonNomination.aspx?code=CEM", "vice": "DyChairpersonNomination.aspx?code=CEM"}
P = "ctl00$ContentPlaceHolder1$"
# body type in the ULB name -> (head, vice, head in Hindi, vice in Hindi)
POSTS = (("NAGAR NIGAM", "Mayor", "Deputy Mayor", "महापौर", "उपमहापौर"),
         ("NAGAR PARISHAD", "Chairperson", "Vice Chairperson", "सभापति", "उपसभापति"),
         ("NAGAR PALIKA", "Chairperson", "Vice Chairperson", "अध्यक्ष", "उपाध्यक्ष"))


def norm(s):
    return " ".join((s or "").split())


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def post_names(body, which):
    b = norm(body).upper()
    for key, head, vice, head_hi, vice_hi in POSTS:
        if b.endswith(key):
            return (head, head_hi) if which == "chair" else (vice, vice_hi)
    return ("Chairperson", None) if which == "chair" else ("Vice Chairperson", None)


def body_type(body):
    b = norm(body).upper()
    return {"NAGAR NIGAM": "Municipal Corporation", "NAGAR PARISHAD": "Municipal Council",
            "NAGAR PALIKA": "Municipal Board"}.get(next((k for k, *_ in POSTS if b.endswith(k)), ""), None)


def parse(html, which, url, period_label="SEP 2026", src=None):
    soup = BeautifulSoup(html, "lxml")
    panel = soup.select_one("#tabs-5")
    t = panel.find("table") if panel else None
    if t is None:
        return []
    trs = t.find_all("tr")
    head = [norm(c.get_text(" ", strip=True)) for c in trs[0].find_all(["th", "td"])] if trs else []
    if "Name" not in head or "ULB Name" not in head:
        return []
    rows = []
    for ri, tr in enumerate(trs[1:], 2):
        cells = [norm(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        if len(cells) != len(head):
            continue
        rows.append((ri, dict(zip(head, cells))))
    names = [norm(c["ULB Name"]) for _, c in rows]
    recs = []
    for ri, c in rows:
        body = norm(c["ULB Name"])
        sl = slug(body + (" " + c.get("District Name", "") if names.count(body) > 1 else ""))
        position, position_local = post_names(body, which)
        votes = c.get("Candidate Vote")
        d = {"type": "councillor", "state": "RJ", "body": body, "body_type": body_type(body), "district": c.get("District Name"),
             "ward_no": which, "name": c.get("Name"), "position": position, "position_local": position_local,
             "party": c.get("Party Name"), "reservation": c.get("Category"), "gender": c.get("Gender"), "age": c.get("Age"),
             "category": c.get("Candidate Category"),
             "votes": votes if votes and votes.isdigit() else None,
             "electorate": c.get("Total Electorate"), "votes_polled": c.get("Votes Polled"), "valid_votes": c.get("Valid Votes"),
             "rejected_votes": c.get("Rejected"), "nota": c.get("NOTA"),
             "unopposed": {"Yes": True, "No": False}.get(c.get("Is Unopposed")),
             "elected_by": "ward members (indirect election)",
             "election": f"Rajasthan ULB General Election {period_label}: {position} election by the ward members",
             "url": url, "src_url": url, **(src or {}), "src_pos": {"table": "#tabs-5 (Winner)", "row": ri}}
        recs.append((f"councillor:RJ:{sl}:{which}", {k: v for k, v in d.items() if v not in (None, "")}))
    return recs


def fetch(p, get):
    which = p.get("post", "chair")
    url = BASE_URL + PAGES[which]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    f = {"ElecType": "2", "Election": p.get("election_value", "1")}
    h = r.text
    for target in ("Election", "Period"):
        if target == "Period":
            f["Period"] = p.get("period", "61")
        d = hidden(h)
        d.update({"__EVENTTARGET": P + target, "__EVENTARGUMENT": "", **{P + k: v for k, v in f.items()}})
        r = get(url, method="POST", data=d)
        if r is None:
            return [], [], f"{target} postback did not answer"
        h = r.text
    d = hidden(h)
    d.update({"__EVENTTARGET": "", "__EVENTARGUMENT": "", **{P + k: v for k, v in f.items()},
              P + "DistrictDropDownList": "0", P + "btnSubmit": "Submit"})
    r = get(url, method="POST", data=d)
    if r is None:
        return [], [], "submit did not answer"
    files = [(f"councillors/RJ/heads-{p.get('period', '61')}-{which}.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = parse(r.text, which, url, p.get("period_label", "SEP 2026"), provenance.at(r, url))
    return recs, files, "" if recs else "no winner rows"
