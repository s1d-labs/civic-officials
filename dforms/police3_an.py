"""Andaman and Nicobar Islands Police: police.andamannicobar.gov.in/index.php/en/new-laws/contact-details/<district>.html
(Joomla; answers from Mumbai, abroad unchecked; the archive copies of 2026 are cut at 16 or 32 KB, so the live page is read).
One page per police district (south-district, n-m-district, nicobar-district). The page has a summary block (SP, SDPOs) and
one table "Sl. No. | Name of Officers | Designation | Phone No. | Mobile No. | E-mail Id": the SP, the SDPOs, the SHOs of every
police station ("SHO, PS Shaheed Dweep", "SHO PS Campbell Bay") and some units. The e-mail is cloaked by Joomla's script
('var addy_text<id> = ...'): the string pieces are joined and HTML entities decoded (no JavaScript is run).
Levels: SHO -> police_station (area = the station name after "PS"), SDPO / DySP -> subdivision, SP -> district, others ->
district with office_type unit (traffic, women, cyber, control room by keyword). One queue item = one district page.
Record id dept:police3_an:<district slug>:<station or post slug>."""
import html as htmllib
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table (+ Joomla e-mail cloak script text)"     # source trail (provenance.py)

M = "police3_an"
BASE = "https://police.andamannicobar.gov.in/index.php/en/new-laws/contact-details/"
PAGES = {"south-district": "South Andamans", "n-m-district": "North And Middle Andaman", "nicobar-district": "Nicobars"}
UNIT = [("traffic", r"traffic"), ("women", r"women|mahila|crime against women|\bcaw\b"), ("cyber", r"cyber"),
        ("control_room", r"control room|\bpcr\b|dial 112|\b112\b")]


def cloaked(td):
    """Joomla cloak: the 'addy_text' string pieces joined, entities decoded -> 'spsa.and@nic.in'."""
    s = td.find("script")
    if s is None:
        return None
    m = re.search(r"var addy_text\w*\s*=\s*((?:'[^']*'\s*\+?\s*)+)", s.string or s.get_text(), re.S)
    if not m:
        return None
    return email(htmllib.unescape("".join(re.findall(r"'([^']*)'", m.group(1)))))


def parse(html, url, district):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ti, t in enumerate(soup.find_all("table")):
        if t.find("table"):
            continue
        rows = t.find_all("tr")
        head = [clean(x.get_text(" ", strip=True)) or "" for x in rows[0].find_all(["td", "th"])] if rows else []
        if not any(re.search(r"designation", h, re.I) for h in head):
            continue
        col = {k: next((i for i, h in enumerate(head) if re.search(p, h, re.I)), None)
               for k, p in (("name", r"name"), ("post", r"designation"), ("phone", r"phone"), ("mobile", r"mobile"),
                            ("email", r"mail"))}
        for ri, tr in enumerate(rows[1:], 1):
            tds = tr.find_all("td")
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tds]
            if len(c) < len(head) or not c[col["post"]]:
                provenance.skip_row(tr, 'skip: len(c) < len(head) or not c[col["post"]]')
                continue
            post = c[col["post"]]
            name = c[col["name"]]
            ph = phones(re.sub(r"\((?:O|R|M)\)", " ", c[col["phone"]]), c[col["mobile"]])
            mail = cloaked(tds[col["email"]]) if col["email"] is not None else None
            if not mail and col["email"] is not None:
                mail = email(c[col["email"]])
            common = dict(name=name or None, phone=ph, email=mail, district=district, state="AN", source=url,
                          src_pos={"table": ti, "row": ri})
            m = re.match(r"^(?:SHO|S\.H\.O\.?|OIC|O/C)[\s,]*(?:PS|P\.S\.?|Police Station)\s+(.+)$", post, re.I)
            if m:
                st = m.group(1).strip(" .")
                recs.append(rec(M, f"{slug(district)}:{slug(st)}", area=st, post="SHO", **common))
                continue
            if re.search(r"\bSDPO\b|sub-?division|\bDy\.?\s?SP\b|\bDYSP\b", post, re.I):
                area = re.sub(r"^SDPO[\s,]*|\s*Sub-?Division$", "", post, flags=re.I).strip(" ,") or district
                recs.append(rec(M, f"{slug(district)}:{slug(post)}", level="subdivision", office_type="subdivision",
                                area=area, post=post, **common))
                continue
            ot = next((k for k, p in UNIT if re.search(p, post, re.I)), None)
            head_post = re.match(r"^(SP|S\.P\.?|Superintendent of Police|Addl\.? SP)\b", post, re.I) and not ot
            recs.append(rec(M, f"{slug(district)}:{slug(post)}", level="district", office_type="office" if head_post else ot or "unit",
                            area=district, post=post, **common))
    return uniq(recs)


def items(get=None):
    return [{"key": f"{M}:{k}", "payload": {"reader": M, "url": BASE + k + ".html", "state": "AN", "district": d}}
            for k, d in PAGES.items()]


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    key = url.rsplit("/", 1)[1].replace(".html", "")
    recs = parse(r.text, url, p.get("district") or PAGES.get(key, ""))
    return recs, [gz(M, key, r.content)], "" if recs else "no rows"
