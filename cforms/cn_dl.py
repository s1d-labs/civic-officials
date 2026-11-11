"""Delhi: members of the New Delhi Municipal Council (ndmc.gov.in/council_members.aspx). India only (the site timed out from
Germany on 2026-11-11).

NDMC has no wards and no election: under the NDMC Act 1994 (section 4) the Central Government appoints the Chairperson and the
members (officers and persons nominated after consultation with the Delhi Government); the area's MLAs and the New Delhi MP
are ex-officio members. The page has two tables, "Members" and "Ex-Officio Members"; each row holds the name in <strong>, then
the designation ("Chairperson & Member, NDMC", "Member & Vice Chairperson, NDMC", "MLA & Member, NDMC" ...), an address, and a
contact cell (phone, email). Empty rows ("- Member, NDMC") are skipped.
Records are type "councillor" with ward_no "member-<n>" (row order) and position "Member (nominated)", "Chairperson
(appointed)", "Vice Chairperson" or "Member (ex officio, MLA/MP)". The Delhi Cantonment Board lists no elected members (its
board page shows only the President and the CEO), so it has no reader.
Record id councillor:DL:new-delhi-municipal-council:member-<n>.
"""
import gzip
import re

from bs4 import BeautifulSoup

URL = "https://ndmc.gov.in/council_members.aspx"
BODY = "New Delhi Municipal Council"


def norm(s):
    return " ".join((s or "").replace("\xa0", " ").split()).strip(" ,;:-")


def position(desig, ex):
    d = desig.lower()
    if "vice chairperson" in d:
        return "Vice Chairperson"
    if "chairperson" in d:
        return "Chairperson (appointed)"
    if ex or re.search(r"\b(mla|mp)\b", d):
        m = re.search(r"\b(MLA|MP)\b\s*(\(\s*[LR]S\s*\))?", desig)
        return f"Member (ex officio, {m.group(1) + (' ' + m.group(2).replace(' ', '') if m.group(2) else '') if m else 'legislator'})"
    return "Member (nominated)"


def members(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs, n = [], 0
    for table in soup.find_all("table"):
        title = norm(table.find("th").get_text(" ")) if table.find("th") else ""
        if not re.search(r"Members", title):
            continue
        ex = "Ex-Officio" in title or "Ex Officio" in title
        for tr in table.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            for i, info in enumerate(tds):          # one or two members per row: each has its name in <strong>
                if info.find("strong") is None or "Name & Designation" in info.get_text():
                    continue
                name = norm(info.find("strong").get_text(" "))
                if not re.search(r"[A-Za-z]{3}", name) or re.fullmatch(r"Contact Details|Name & Designation.*", name):
                    continue
                nxt = tds[i + 1] if i + 1 < len(tds) and tds[i + 1].find("strong") is None and tds[i + 1].find("img") is None \
                    else None
                lines = [norm(x) for x in info.get_text("\n").split("\n") if norm(x) and norm(x) != name]
                desig = lines[0] if lines else ""
                addr = [x for x in lines[1:] if not re.match(r"(Phone|Email)", x)]
                contact = " ".join(lines) + " " + (norm(nxt.get_text(" ")) if nxt is not None else "")
                phone = re.search(r"Phone\s*:?\s*(.*?)\s*(Email|$)", contact)
                mails = [norm(a.get_text()) for c in (info, nxt) if c is not None for a in c.find_all("a", href=re.compile("^mailto:"))]
                mail = next((m for m in mails if "@" in m), None)
                n += 1
                d = {"type": "councillor", "state": "DL", "body": BODY, "body_en": BODY, "body_type": "NCT Municipal Council",
                     "district": "New Delhi", "ward_no": f"member-{n}", "name": name, "designation": desig,
                     "position": position(desig, ex), "address": "; ".join(addr) or None,
                     "phone": norm(phone.group(1)) if phone and re.search(r"\d", phone.group(1)) else None, "email": mail,
                     "election": "not elected: appointed under the NDMC Act 1994 (ex-officio: MLAs and MP)", "url": url}
                recs.append((f"councillor:DL:new-delhi-municipal-council:member-{n}",
                             {k: v for k, v in d.items() if v not in (None, "")}))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = members(r.text, url)
    return recs, [("councillors/DL/ndmc-council-members.html.gz", gzip.compress(r.content), "application/gzip")], \
        "" if recs else "no members read"
