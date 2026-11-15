"""Himachal Pradesh: winners of the urban local body general election of 17 May 2026 from the SEC DPMIS poll results
(sechimachal.hp.gov.in/DPMIS/, "Poll Results" of the row "General Elections : Municipal Councils/Nagar Panchayat", then
GenListNomination.aspx). India only (as cforms/hp.py).

The "Elected Representatives" list (cforms/hp.py, repList.aspx) answers 'Could Not Find Records' for the eight Shimla district
bodies of this round (Rampur, Theog, Jubbal, Chopal, Kotkhai, Sunni, Nerwa, Chirgaon; checked 2026-11-15). The poll results page
lists every candidate of a district with the votes; the winner's status cell starts with "*" ("*Votes Secured: 197" or
"*Elected Unopposed"). Checked live 2026-11-15: district Shimla (1309), 128 candidates, 58 winners (53 by poll, 5 unopposed),
9 wards in Rampur and 7 in each of the other seven bodies.

The page keeps its state in the session: home page, language, the row's result link (a postback that only opens
GenListNomination.aspx in a new window), GET GenListNomination.aspx, district, then "खोज परिणाम" (search). Names, wards and body
names stay in Devanagari. One queue item = one district: payload {"kind": "form-hp_res", "state": "HP", "url", "district_id",
"district", "row": text that names the election row}. Record id councillor:HP:res:<LGD code>:<ward>.
"""
import gzip
import re
import unicodedata

from bs4 import BeautifulSoup

import provenance
from forms.aspnet import hidden

METHOD = "html table (ASP.NET grid after postbacks; winner = status cell with '*')"

HOME = "https://sechimachal.hp.gov.in/DPMIS/"
LIST = HOME + "GenListNomination.aspx"
ELECTION = "Himachal Pradesh urban local bodies general election 2026 (poll 17.05.2026)"
# Devanagari body name on the results page -> (LGD code, English name, body type)
BODIES = {
    "रामपुर": ("248245", "Rampur", "Municipal Council"),
    "ठियोग": ("248249", "Theog", "Municipal Council"),
    "जुब्बल": ("248251", "Jubbal", "Nagar Panchayat"),
    "चोपाल": ("248250", "Chopal", "Nagar Panchayat"),
    "कोटखाई": ("248252", "Kotkhai", "Nagar Panchayat"),
    "सुन्नी": ("248247", "Suni", "Nagar Panchayat"),
    "नेरवा": ("297014", "Nerwa", "Nagar Panchayat"),
    "\u091a\u093f\u095c\u0917\u093e\u0901\u0935": ("297013", "Chirgaon", "Nagar Panchayat"),   # चिड़गाँव with the one-letter ड़ (U+095C)
}
BODIES_EN = {v[1].upper(): v for v in BODIES.values()} | {"SUNNI": BODIES["सुन्नी"]}
COLS = ("post", "name", "relative", "age", "address", "category", "elector_entry", "proposer", "proposer_entry", "status")


def form(html):
    soup = BeautifulSoup(html, "lxml")
    d = hidden(html)
    for i in soup.select("input[type=radio][checked]"):
        d[i["name"]] = i.get("value")
    for sel in soup.select("select[name]"):
        o = sel.find("option", selected=True) or sel.find("option")
        if o is not None:
            d[sel["name"]] = o.get("value")
    return d


def postback(get, r, url, target, **fields):
    if r is None:
        return None
    d = form(r.text)
    d.update(fields)
    d.update({"__EVENTTARGET": target, "__EVENTARGUMENT": ""})
    return get(url, method="POST", data=d)


def click(get, r, url, name):
    if r is None:
        return None
    b = BeautifulSoup(r.text, "lxml").find("input", attrs={"name": name})
    if b is None:
        return None
    d = form(r.text)
    d.update({"__EVENTTARGET": "", "__EVENTARGUMENT": "", name: b.get("value", "")})
    return get(url, method="POST", data=d)


def result_link(html, row):
    """The postback target of the 'Poll Results' link in the grid row whose text has `row`."""
    grid = BeautifulSoup(html, "lxml").find(id="MyGrid")
    for tr in grid.find_all("tr", recursive=False) if grid else []:
        if row in tr.get_text(" ", strip=True):
            a = tr.find("a", id=re.compile(r"lnkResultDate_\d+$"))
            m = re.search(r"__doPostBack\('([^']+)'", a.get("href", "")) if a else None
            if m:
                return m.group(1)
    return None


def parse(html):
    """[(body hi, ward no, ward name, cells dict)] of the winners."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for ri, tr in enumerate(soup.select("#gvNominationList tr"), 1):
        tds = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]
        if len(tds) != len(COLS):
            provenance.skip_row(tr, "header")
            continue
        x = dict(zip(COLS, tds))
        if not x["status"].startswith("*"):
            provenance.skipped("not elected")
            continue
        m = re.match(r"(.+?)\s*:\s*(\d+)\s*-\s*(.*?)\s*/\s*(.*)$", x["post"])   # "रामपुर: 1- पीपटी मोहल्ला / वार्ड सदस्य"
        if not m:
            provenance.skipped("post not read")
            continue
        x["name"] = re.sub(r"\s*अनुबन्ध-I देखें\s*$", "", x["name"]).strip()      # "see annexure I" link after the name
        x["_pos"] = {"table_id": "gvNominationList", "row": ri}
        out.append((m.group(1).strip(), m.group(2), m.group(3).strip(), m.group(4).strip(), x))
    return out


def fetch(p, get):
    r = postback(get, get(HOME), HOME, "ddllang", ddllang="en-GB")      # English grid: the row is found by its English text
    if r is None:
        return [], [], "no answer"
    target = result_link(r.text, p.get("row", "RAMPUR"))
    if target is None:
        return [], [], "election row not found"
    if postback(get, r, HOME, target) is None:                           # opens GenListNomination.aspx for this election
        return [], [], "no answer"
    r = get(LIST)
    r = postback(get, r, LIST, "ddlDis", ddlDis=p["district_id"])
    r = click(get, r, LIST, "btnSubmit")
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/HP/results-{p['district_id']}.html.gz", gzip.compress(r.content), "application/gzip")]
    src = provenance.at(r, LIST)
    recs = []
    for body_hi, ward, ward_name, post, x in parse(r.text):
        key = unicodedata.normalize("NFC", body_hi)
        lgd, body, btype = BODIES.get(key) or BODIES.get(key.replace("\u0921\u093c", "\u095c")) or BODIES_EN.get(body_hi.upper()) or (None, body_hi, None)
        if lgd is None:
            provenance.skipped("body not in BODIES")
            continue
        unopposed = "unopposed" in x["status"].lower()
        votes = re.search(r"(\d+)", x["status"])
        d = {"type": "councillor", "state": "HP", "body": body, "body_hi": body_hi, "body_type": btype, "lgd_code": lgd,
             "district": p.get("district"), "ward_no": ward, "ward_name": ward_name, "position": "Ward Member",
             "post_hi": post, "name": x["name"], "relative": x["relative"], "age": x["age"], "address": x["address"],
             "category": x["category"], "votes": votes.group(1) if votes and not unopposed else None,
             "elected_unopposed": True if unopposed else None, "status_cell": x["status"], "election": ELECTION,
             "url": LIST, "src_pos": x["_pos"], **src}
        recs.append((f"councillor:HP:res:{lgd}:{ward}", {k: v for k, v in d.items() if v not in (None, "")}))
    if not recs:
        return [], files, "no winners read"
    return recs, files, ""
