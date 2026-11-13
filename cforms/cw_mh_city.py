"""Maharashtra municipal corporations, general election 2026 (polls 15 Jan 2026): corporators listed on the corporations' own sites.

- "pcmc": Pimpri Chinchwad, www.pcmcindia.gov.in/corporator. One table row per ward (prabhag 1-32), four seats (अ ब क ड),
  each cell the corporator's name (link to /corporator-details?Id=<n>) and mobile number. The detail page adds the address,
  the party and the e-mail (one request per member).
- "amravati": Amravati, amravaticorporation.in/en/elected-members/. One table: party heading rows ("भारतीय जनता पक्ष" ...),
  then one row per corporator (serial, name, prabhag, mobile numbers), all in Devanagari digits.
Both checked 2026-11-11: the 2026 term (PCMC: 128 members, mayor Ravi Landge; Amravati: 87 members, Yuva Swabhiman Party 15).
Titles (श्री., सौ., डॉ. ...) stay in the name as the site gives it; posts written after the name ("(महापौर)") go to "post".
One queue item = one corporation (payload site). Both sites also answer from outside India.
Record id councillor:MH:<slug>:<ward>-<seat or serial>.
"""
import gzip
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from cforms import gj
from cforms.cp_common import tr_pos
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
ELECTION = "Maharashtra Municipal Corporation General Election 2026"
SITES = {
    "pcmc": {"url": "https://www.pcmcindia.gov.in/corporator", "body": "Pimpri Chinchwad", "body_local": "पिंपरी चिंचवड महानगरपालिका",
             "district": "Pune", "slug": "pimpri-chinchwad-mc"},
    "amravati": {"url": "https://amravaticorporation.in/en/elected-members/", "body": "Amravati",
                 "body_local": "अमरावती महानगरपालिका", "district": "Amravati", "slug": "amravati-mc"},
}
PARTY = ((r"उबाठा|उद्ध?व|ठाकरे", "SS(UBT)"), (r"शरद", "NCP(SP)"), (r"राष्ट्रवादी", "NCP"), (r"भारतीय\s*जनता", "BJP"),
         (r"शिवसेना", "SHS"), (r"राष्ट्रीय\s*कॉ|काँग्रेस|कॉंग्रेस|कॉग्रेस", "INC"), (r"मजलिस|इत्तेह", "AIMIM"),
         (r"वंचित", "VBA"), (r"बहुजन\s*समाज", "BSP"), (r"नवनिर्माण", "MNS"), (r"समाजवादी", "SP"),
         (r"युवा\s*स्वाभिमान", "Yuva Swabhiman Party"), (r"अपक्ष", "Independent"))
POST = re.compile(r"\s*\(([^()]*(?:महापौर|उपमहापौर|नेता|सभापती|अध्यक्ष)[^()]*)\)\s*")
PHONE = re.compile(r"[6-9]\d{9}")


def norm(t):
    return gj.norm(t).replace("‍", "").replace("‌", "")


def party_of(t):
    t = norm(t)
    for k, v in PARTY:
        if re.search(k, t):
            return v
    return t


def name_post(t):
    t = norm(t)
    posts = [m.group(1).strip() for m in POST.finditer(t)]
    return POST.sub(" ", t).strip(" ,"), "; ".join(posts)


def rec(site, **kw):
    s = SITES[site]
    d = {"type": "councillor", "state": "MH", "body": s["body"], "body_en": s["body"], "body_local": s["body_local"],
         "body_type": "Municipal Corporation", "district": s["district"], "position": "Member", "election": ELECTION,
         "list_url": s["url"]}
    d.update(kw)
    return d


def pcmc_list(html, pos=None):
    """[(ward, seat, name, phone, detail url)] from the corporator table. pos: a list that gets each entry's src_pos
    ({"table", "row", "col"}: the cell of the seat)."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2 or not norm(tds[0].get_text()).translate(DIGITS).isdigit():
            provenance.skip_row(tr, 'skip: len(tds) < 2 or not norm(tds[0].get_text()).translate(DIGITS).isdig...')
            continue
        ward = str(int(norm(tds[0].get_text()).translate(DIGITS)))
        for col, (seat, td) in enumerate(zip("अबकड", tds[1:5]), 2):
            a = td.find("a")
            name = norm(a.get_text(" ")) if a else ""
            if not name:
                continue
            phone = PHONE.search(norm(td.get_text(" ")).translate(DIGITS))
            out.append((ward, seat, name, phone.group(0) if phone else "", urljoin(SITES["pcmc"]["url"], a.get("href", ""))))
            if pos is not None:
                pos.append({**tr_pos(tr), "col": col})
    return out


def pcmc_detail(html):
    """{"address", "party", "phone", "email"} from a corporator's detail page (label, then value)."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "head", "nav", "header", "footer"]):
        t.decompose()
    tok = [norm(s) for s in soup.stripped_strings]
    out = {}
    for label, key in (("पत्ता", "address"), ("राजकीय पक्ष", "party"), ("मोबाईल क्रमांक", "phone"), ("ई-मेल", "email")):
        for i, t in enumerate(tok[:-1]):
            if t == label:
                out[key] = tok[i + 1]
                break
    return out


def pcmc(p, get):
    r = get(SITES["pcmc"]["url"])
    if r is None:
        return [], [], "no answer"
    files = [("councillors/MH/pcmc-corporators.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = []
    pos = []
    for (ward, seat, name, phone, url), sp in zip(pcmc_list(r.text, pos), pos):
        name, post = name_post(name)
        # source trail: name, ward, seat and phone from the list page cell; address, party and email from the detail page
        d = rec("pcmc", name=name, ward_no=ward, seat=seat, phone=phone, url=url, src_url=SITES["pcmc"]["url"], src_pos=sp)
        if post:
            d["post"] = post
        if p.get("details", True) and "corporator-details" in url:
            m = get(url)
            if m is not None:
                d["src_pos"] = {**sp, "detail_page": url, "detail_fields": "address, party, email (labels on the page)"}
                d["method"] = "html table (list) + html page (member detail)"
                det = pcmc_detail(m.text)
                d["address"] = det.get("address", "")
                d["party_local"] = det.get("party", "")
                d["party"] = party_of(det.get("party", ""))
                if det.get("email") and "@" in det["email"]:
                    d["email"] = det["email"]
                d["phone"] = d["phone"] or det.get("phone", "")
        recs.append((f"councillor:MH:{SITES['pcmc']['slug']}:{ward}-{seat}", d))
    return recs, files, "" if recs else "no members in the table"


def amravati_list(html, pos=None):
    """[(serial, name, ward, phones, party)]: party heading rows set the party of the rows below them. pos: a list that gets
    each row's src_pos {"table", "row"}."""
    soup = BeautifulSoup(html, "lxml")
    out, party = [], ""
    for tr in soup.find_all("tr"):
        tds = [norm(td.get_text(" ")) for td in tr.find_all("td")]
        if len(tds) != 4 or not any(tds):
            provenance.skip_row(tr, 'skip: len(tds) != 4 or not any(tds)')
            continue
        if tds[0] and not any(tds[1:]):
            party = tds[0]
            continue
        if not tds[1]:
            provenance.skip_row(tr, 'skip: not tds[1]')
            continue
        phones = PHONE.findall(tds[3].translate(DIGITS))
        out.append((tds[0].translate(DIGITS), tds[1], str(int(tds[2].translate(DIGITS))) if tds[2].translate(DIGITS).isdigit()
                    else tds[2].translate(DIGITS), phones, party))
        if pos is not None:
            pos.append(tr_pos(tr))
    return out


def amravati(p, get):
    r = get(SITES["amravati"]["url"])
    if r is None:
        return [], [], "no answer"
    files = [("councillors/MH/amravati-elected-members.html.gz", gzip.compress(r.content), "application/gzip")]
    recs, seen = [], {}
    pos = []
    for (serial, name, ward, phones, party), sp in zip(amravati_list(r.text, pos), pos):
        name, post = name_post(name)
        seen[ward] = seen.get(ward, 0) + 1
        d = rec("amravati", name=name, ward_no=ward, phone=", ".join(phones), party=party_of(party), party_local=party,
                url=SITES["amravati"]["url"], src_pos=sp)
        if post:
            d["post"] = post
        recs.append((f"councillor:MH:{SITES['amravati']['slug']}:{ward}-{seen[ward]}", d))
    return recs, files, "" if recs else "no members in the table"


READERS = {"pcmc": pcmc, "amravati": amravati}


def items(get=None):
    return [{"key": f"cw-mh-city-{s}", "payload": {"kind": "form-cw_mh_city", "state": "MH", "site": s, "url": SITES[s]["url"]}}
            for s in SITES]


def fetch(p, get):
    return READERS[p["site"]](p, get)
