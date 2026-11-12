"""RTO offices (regional / sub-regional transport offices) and their officers from state transport sites. Payload "site" picks the
page layout:
- "uk": transport.uk.gov.in/organization/office-<x>/ (S3WaaS, 16 offices): a table "Name of Officer | Designation | Email" (one
  record per officer) and the office card (Telephone, Email, Address; one record for the office). The page also gives the
  registration code ("Registration Code – UK07").
- "mh": transport.maharashtra.gov.in/1184/Regional-Offices: one table of every RTO / sub-RTO (about 53 rows): office name (Marathi),
  office code MH-NN, address (Marathi), phones, emails. No officer names. The site glues emails together
  ("mh01@mahatranscom.inrto.01-mh@gov.in"); split() takes them apart.
dept "transport"; level "district" for an RTO, "subdivision" for a sub-regional / assistant RTO. Payload: url, state, site,
district (uk). Record ids dept:central_transport:<state>:<office slug>[:<officer slug>]. Seed: seeds/dept_central_transport.json.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from dforms import _esw
from dforms.police_s3waas import last_updated

METHOD = "html table (+ office card on Uttarakhand pages)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "central_transport"
TITLE = re.compile(r"^(?:(?:shri|smt|sri|mr|mrs|ms|dr|km|kumari)(?:\.\s*|\s+))+", re.I)


def items(get=None):
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def split(s):
    """Glued emails 'mh01@mahatranscom.inrto.01-mh@gov.in' -> 'mh01@mahatranscom.in rto.01-mh@gov.in'."""
    return re.sub(r"(\.(?:in|com))(?=[a-z][\w.-]*@)", r"\1 ", s or "")


def uk(html, url, p):
    soup = _esw.soup(html)
    node = soup.select_one("#row-content") or soup.body
    lu = last_updated(html)
    h = node.find(["h1", "h2"])
    office = _esw.clean(h.get_text(" ")) if h else ""
    office = office or _esw.clean(urlparse(url).path.strip("/").split("/")[-1].replace("office-", "").title())
    lvl = "subdivision" if re.search(r"(?i)sub|assistant|\bARTO\b|\bARTO\b", office) else "district"
    code = re.search(r"Registration Code\s*[–-]\s*([A-Z]{2}\s?\d{2})", node.get_text(" "))
    slug = _esw.slug(office)
    card = {}
    for li in node.select(".meta-info li"):
        st = li.find("strong")
        if st:
            lab = _esw.clean(st.get_text(" ")).rstrip(" :").lower()
            card[lab] = _esw.clean(li.get_text(" "))[len(_esw.clean(st.get_text(" "))):].strip(" :")
    recs = [_esw.record(MODULE, f"{p['state']}:{slug}", dept="transport", level=lvl, area=office, post="Office",
                        phone=_esw.phones(card.get("telephone", "")), email=_esw.emails(card.get("email", "")),
                        address=card.get("address"), registration_code=code.group(1) if code else None,
                        state=p["state"], district=p.get("district"), office_id=slug, source=url, last_updated=lu,
                        src_pos={"selector": "#row-content .meta-info"}, method="html page (office card)")]
    seen = set()
    for t in node.find_all("table"):
        gpos = []
        g = _esw.grid(t, pos=gpos)
        if not g:
            continue
        head = [x.lower() for x in g[0]]
        ni = next((i for i, x in enumerate(head) if "name" in x), None)
        di = next((i for i, x in enumerate(head) if "designation" in x or "post" in x), None)
        ei = next((i for i, x in enumerate(head) if "mail" in x), None)
        pi = next((i for i, x in enumerate(head) if re.search(r"phone|mobile|contact", x)), None)
        if ni is None:
            continue
        for row, rp in zip(g[1:], gpos[1:]):
            name = TITLE.sub("", row[ni]).strip() if ni < len(row) else ""
            if not name:
                continue
            k = f"{p['state']}:{slug}:{_esw.slug(name)}"
            k = k if k not in seen else f"{k}-{len(seen)}"
            seen.add(k)
            post = row[di] if di is not None and di < len(row) else None
            recs.append(_esw.record(
                MODULE, k, dept="transport", level=lvl, area=office, post=post, name=name,
                email=_esw.emails(row[ei]) if ei is not None and ei < len(row) else None,
                phone=_esw.phones(row[pi]) if pi is not None and pi < len(row) else None,
                address=card.get("address"), state=p["state"], district=p.get("district"), office_id=slug, source=url,
                last_updated=lu, kind="officer", src_pos=rp, method="html table"))
    return recs


def mh(html, url, p):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        gpos = []
        g = _esw.grid(t, pos=gpos)
        if not g or not any("code" in x.lower() for x in g[0]):
            continue
        head = [x.lower() for x in g[0]]
        col = {k: next((i for i, x in enumerate(head) if re.search(pat, x)), None) for k, pat in
               (("name", r"name"), ("code", r"code"), ("address", r"address"), ("map", r"map"), ("phone", r"^office$|phone|tele"),
                ("email", r"mail"))}
        last_code = None
        for row, rp in zip(g[1:], gpos[1:]):
            val = {k: (row[i] if i is not None and i < len(row) else "") for k, i in col.items()}
            code = re.sub(r"\s+", "", val["code"]).upper() or last_code
            if not (val["name"] or code):
                continue
            last_code = code
            name = val["name"]
            k = f"{p['state']}:{_esw.slug(code or name)}"
            n = 1
            while k in seen:
                n += 1
                k = f"{p['state']}:{_esw.slug(code or name)}-{n}"
            seen.add(k)
            lvl = "subdivision" if re.search(r"उप|sub", val["address"] + name, re.I) else "district"
            recs.append(_esw.record(
                MODULE, k, dept="transport", level=lvl, area=code, area_regional=name, post="RTO",
                phone=_esw.phones(val["phone"]), email=_esw.emails(split(val["email"])), address=val["address"],
                map=val["map"] or None, registration_code=code, state=p["state"], office_id=code, source=url,
                last_updated=last_updated(html), src_pos=rp, method="html table"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    tag = _esw.slug(urlparse(p["url"]).path)[-60:] or "home"
    files = [_esw.keep(MODULE, f"{p['state']}-{tag}", r.content)]
    recs = {"uk": uk, "mh": mh}[p["site"]](r.text, p["url"], p)
    return recs, files, "" if recs else "no rows"
