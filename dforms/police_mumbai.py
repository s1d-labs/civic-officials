"""Mumbai Police (Greater Mumbai commissionerate): station in-charge cards, mumbaipolice.gov.in/Police_incharge?page=N
(N = 1..5, 24 cards a page, ~113 stations). Each card: name (<h4 title>), rank (<p title>, Marathi), station ("<b> ( ... )</b>"),
then one row per icon: landline (lanlandSvg), fax (faxSvg), mobile (mobSvg), email (emailSvg, [dot]/[at] masked).
The default language is Marathi with Devanagari digits; digits become ASCII here, the text stays Marathi.
Works from outside India. One queue item = one page. Record id dept:police_mumbai:<station>."""
import re

from bs4 import BeautifulSoup

from dforms._police import ascii_digits, clean, email, gz, phones, rec, slug, uniq

METHOD = "html cards"     # source trail (provenance.py): how this reader reads its sources

M = "police_mumbai"
URL = "https://mumbaipolice.gov.in/Police_incharge?page={}"
ICON = {"lanland": "landline", "fax": "fax", "mob": "mobile", "email": "email"}


def key(s):
    """slug() that keeps Indic vowel signs (slug() drops them: ताडदेव -> त-डद-व)."""
    return re.sub(r"[^\w\u0900-\u0dff]+", "-", (clean(s) or "").lower()).strip("-") or slug(s)


def std(nums, code="022"):
    """Mumbai landlines are printed without the STD code: 23512109 -> 022-23512109."""
    if not nums:
        return nums
    return ", ".join(f"{code}-{n}" if re.fullmatch(r"\d{8}", n) else n for n in nums.split(", "))


def parse(html, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ci, card in enumerate(soup.select("div.senior-officer-item"), 1):
        up = card.select_one(".card-up")
        if not up:
            continue
        h4, p = up.find("h4"), up.find("p")
        name = clean(h4.get("title") or h4.get_text(" ", strip=True)) if h4 else None
        rank = clean(p.get("title")) if p and p.get("title") else None
        b = [clean(x.get_text(" ", strip=True)) for x in up.find_all("b")]
        station = next((m.group(1).strip() for x in b for m in [re.match(r"^\(\s*(.+?)\s*\)$", x or "")] if m), None)
        if not station:
            continue
        f = {}
        for row in card.select(".card-down > div"):
            img = row.find("img")
            kind = next((v for k, v in ICON.items() if img and k in (img.get("src") or "")), None)
            if not kind:
                continue
            if kind == "email":
                a = row.find("a", href=re.compile("^mailto:", re.I))
                f["email"] = email(a["href"][7:]) if a else None
            else:
                vals = [ascii_digits(a.get_text(" ", strip=True)) for a in row.find_all("a")]
                f[kind] = phones(*[v.strip(" ,") for v in vals])
        landline = std(f.get("landline"))
        recs.append(rec(M, key(station), area=station, post="Police station in-charge", name=name, rank=rank,
                        phone=phones(f.get("mobile"), landline), mobile=f.get("mobile"), landline=landline,
                        fax=std(f.get("fax")), email=f.get("email"), state="MH", district="Mumbai", source=url,
                        src_pos={"selector": "div.senior-officer-item", "card": ci}))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url") or URL.format(p.get("page", 1))
    r = get(url)
    if r is None:
        return [], [], "no answer"
    n = re.search(r"page=(\d+)", url)
    files = [gz(M, f"police_incharge-p{n.group(1) if n else 1}.html", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no cards"
