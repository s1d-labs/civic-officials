"""Tamil Nadu: TNPDCL (ex-TANGEDCO) contact information, www.tnpdcl.org/en/tnpdcl/reach-us/contact-information/ (one page,
about 6 MB; answers from Germany too). One queue item = the page.

The page nests collapsible panels: "Distribution Regions" > "Director Distribution" > "Chief Engineer/Distribution/<region>" >
"Superintending Engineer/<circle>", and each circle panel holds one table (S.No, "Designation / Office Address", "Landline / Mobile",
Email) in hierarchy order: SE (circle), EE (division), AEE (sub-division), AE / JE (section). The division and sub-division of a row
are the last EE / AEE rows above it. The CE/Distribution rows under "Head Quarters" give the 12 regions (level zone).
About 3,950 offices: 45 circles, ~190 divisions, ~770 sub-divisions, ~2,900 sections. Names only for the top posts.
Not read: fuse call centres, enforcement, headquarters staff.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, cells, clean, email, phone, raw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

URL = "https://www.tnpdcl.org/en/tnpdcl/reach-us/contact-information/"
HONORIFIC = re.compile(r"^(Thiru|Tmt|Selvi|Dr|Er|Mr|Mrs|Ms|Shri|Smt)\b\.?", re.I)
QUAL = re.compile(r"^(north|south|east|west|central|rural|urban|town|city|i{1,3}|iv|v|\d)\b", re.I)
OM = re.compile(r"^(O\s*(&|and)\s*M|C\s*&\s*I|CON|Distribution)\s*[/,]?\s*(TNPDCL\s*/?)?\s*", re.I)
ADDR = re.compile(r"(\s|-|^)(?=(No\b|No\.|Door|Plot|D\.?\s?No|S\.?F\.?\s?No|\d|Near|Opp|Behind|Inside|Old\b|O,\s*o\.|O/o|Office|Asst|"
                  r"EB\b|TNEB|TANGEDCO|TNPDCL|Tamil Nadu|Electricity|BDO|SE office|Main Road|Road\b|Street|Salai|Campus|\d*\s*KV|"
                  r"kkv|SS\b|S\.S\b|Sub[- ]?Station|P\.?O\b|Post\b))", re.I)


def level(post):
    p = re.sub(r"[^a-z]", "", (post or "").lower())
    if p.startswith("superintending"):
        return "circle"
    if p.startswith("executiveengineer"):
        return "division"
    if re.match(r"as+[is]*[st]*a?n?texecutive", p) or p.startswith("assistantexecutive") or "executiveengineer" in p:
        return "subdivision"
    if p.startswith(("assistantengineer", "assitant", "assisant", "assiatant", "ssistant", "juniorengineer", "assistant")):
        return "section"
    return None


def split_office(text):
    """'Assistant Engineer / Perambur, East 33/11K.V.S.S,paper mills road ...' -> (name, post, area, address)."""
    parts = [p.strip() for p in text.split(" / ")]
    name = None
    if len(parts) >= 3 and HONORIFIC.match(parts[0]):
        name = parts.pop(0)
    post = parts[0] if parts else None
    rest = " / ".join(parts[1:]) if len(parts) > 1 else ""
    area = office_area(rest)
    return name, post, area, clean(rest)


def office_area(rest):
    """The office (area) name at the start of the free text, without the address after it."""
    t = OM.sub("", rest.strip()).strip(" /")
    parts = [x.strip() for x in t.split(",")]
    area = parts[0]
    if len(parts) > 1 and (QUAL.match(parts[1]) and len(parts[1]) < 30 or QUAL.match(area) and len(area) < 12):
        area = area + ", " + parts[1]
    m = ADDR.search(area, 3)
    if m:
        area = area[:m.start()]
    area = re.sub(r"\s+O$", "", area.strip(" ,.-/"))
    return clean(area) or clean(parts[0][:40])


def heads(tb):
    out, el = [], tb
    while True:
        el = el.find_parent("div", class_="panel")
        if el is None:
            return out[::-1]
        p = el.find("p", class_="panel-title", recursive=False)
        out.append(" ".join(p.get_text(" ", strip=True).split()) if p else "")


def parse(html, url=URL):
    html = re.sub(r"(?s)<!--.*?-->", "", html)
    soup = BeautifulSoup(html, "lxml")
    out = Out("power_tnpdcl", "TN", url, discom="TNPDCL")
    for tb in soup.find_all("table"):
        h = heads(tb)
        if len(h) >= 4 and h[0] == "Head Quarters" and h[3] is not None and "Chief Engineer/Distribution/" in h[3]:
            region = h[3].split("/")[-1]
            for tr in tb.find_all("tr")[1:]:
                c = cells(tr)
                if len(c) == 4:
                    name, post, _, addr = split_office(c[1])
                    out.add(f"zone:{region}", "zone", region, post=post, name=name, phone_=phone(*c[2].split(" / ")),
                            email_=email(c[3]), address=addr)
            continue
        if len(h) < 4 or h[0] != "Distribution Regions" or not h[3].startswith("Superintending Engineer/"):
            continue
        region = h[2].split("/")[-1]
        circle = h[3].split("/", 1)[1]
        div = sub = None
        for tr in tb.find_all("tr")[1:]:
            c = cells(tr)
            if len(c) != 4:
                continue
            name, post, area, addr = split_office(c[1])
            lvl = level(post)
            if lvl is None:
                continue
            if lvl == "circle":
                area, div, sub = circle, None, None
            elif lvl == "division":
                div, sub = area, None
            elif lvl == "subdivision":
                sub = area
            par = {"zone": region, "circle": circle if lvl != "circle" else None,
                   "division": div if lvl in ("subdivision", "section") else None, "subdivision": sub if lvl == "section" else None}
            mail = email(c[3])
            key = f"{lvl}:{mail.split(',')[0].split('@')[0] if mail else circle}:{area}:{post}"
            out.add(key, lvl, area, post=post, name=name, phone_=phone(*c[2].split(" / ")), email_=mail, address=addr, parents=par)
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_tnpdcl", "contact-information", r.content, "html")]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
