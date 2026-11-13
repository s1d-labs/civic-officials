"""Gujarat Police: IPS cadre register, https://www.police.gujarat.gov.in/upload/ips_gujarat_cadre_register.html (one static page,
276 KB, 2026-11-13). The table is drawn by JavaScript from a literal in the page: `const officers = [ {sr:2, name:"..", edu:"..",
educationCategory, domicile, gender, status, post:"S.P., Morbi", recruitment, year, level, dob, appt, present, pay, medals,
contact:"99784 05837 (M); (079) 23254402 (O); (079) 29700997 (R); (079) 23257545 (F)", email, remarks, photo}, ... ]` (146
officers; entries inside <!-- --> are left out by the page itself and here too). Works from Mumbai; abroad unchecked.

Every officer is kept (all fields). The present post gives the level:
- "S.P., <district> (<HQ town>)", "S.P., Surat Rural", "S.P., East-Kutch (Gandhidham)": level district, the district in LGD spelling;
- "Commissioner of Police, <X> City", "Joint / Addl. C.P. ..., <X> City": level district (commissionerate X);
- "D.C.P., Zone-N, <X> City": level zone (area "Zone-N"); D.C.P. (Traffic / Cyber / Crime / S.O.G. / HQ): level district, office_type
  traffic / cyber / unit;
- "I.G.P. / D.I.G.P., <X> Range": level range; everything else (CID, ACB, intelligence, prisons, HQ, deputation): level state.
"Waiting For Posting; Additional Charge- Commissioner of Police, Surat City": the additional charge is used (additional_charge true).
Phones: (M) and (O) numbers in phone; the whole contact text in contact. dob is kept as published (public register).
One queue item = the page. Record id dept:police3_gj:<slug of the post used>."""
import re

from dforms._police import clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "javascript data literal in html page"     # source trail (provenance.py): how this reader reads its sources

M = "police3_gj"
URL = "https://www.police.gujarat.gov.in/upload/ips_gujarat_cadre_register.html"

LGD = {"aravalli": "Arvalli", "banaskantha": "Banas Kantha", "sabarkantha": "Sabar Kantha", "mehsana": "Mahesana",
       "panchmahal": "Panch Mahals", "dang": "Dangs", "gir-somnath": "Gir Somnath", "east-kutch": "Kachchh",
       "west-kutch": "Kachchh", "kutch": "Kachchh", "chhota udepur": "Chhotaudepur"}
DISTRICTS = {"Ahmedabad", "Amreli", "Anand", "Arvalli", "Banas Kantha", "Bharuch", "Bhavnagar", "Botad", "Chhotaudepur", "Dahod",
             "Dangs", "Devbhumi Dwarka", "Gandhinagar", "Gir Somnath", "Jamnagar", "Junagadh", "Kachchh", "Kheda", "Mahesana",
             "Mahisagar", "Morbi", "Narmada", "Navsari", "Panch Mahals", "Patan", "Porbandar", "Rajkot", "Sabar Kantha", "Surat",
             "Surendranagar", "Tapi", "Vadodara", "Valsad", "Vav-Tharad"}
PAIR = re.compile(r'(\w+):("(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?)')


def officers(html):
    """[(index, dict)] from the `const officers = [...]` literal; commented entries are dropped."""
    a = html.find("const officers = [")
    if a < 0:
        return []
    b = html.find("];", a)
    body = re.sub(r"<!--.*?-->", "", html[a:b], flags=re.S)
    out = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("{sr:"):
            provenance.skip_line(line, 'skip: not line.startswith("{sr:")')
            continue
        d = {}
        for k, v in PAIR.findall(line):
            d[k] = v[1:-1].replace('\\"', '"') if v.startswith('"') else v
        out.append((len(out), d))
    return out


def district_of(place):
    """'Morbi' -> Morbi; 'Aravalli (Modasa)' -> Arvalli; 'Surat Rural' -> Surat; 'East-Kutch (Gandhidham)' -> Kachchh; else None."""
    p = re.sub(r"\(.*?\)", "", place or "").strip(" .,")
    p = re.sub(r"\s+(Rural|City)$", "", p, flags=re.I).strip()
    p = LGD.get(p.lower(), p)
    return p if p in DISTRICTS else None


def classify(post):
    """-> (level, office_type, district, area, post used, additional charge) for one present-post text."""
    segs = [clean(re.sub(r"^\s*(?:Additional\s+)?Charge\s*[-:]*\s*(?:\(\d\)\s*)?", "", s, flags=re.I))
            for s in re.split(r";", post or "")]
    segs = [s for s in segs if s]
    for i, s in enumerate(segs):
        m = re.match(r"^S\.\s?P\.,\s*([^,]+)$", s)
        if m and district_of(m.group(1)):
            d = district_of(m.group(1))
            return "district", "office", d, d, s, i > 0
        m = re.search(r",\s*(\w[\w ]*?)\s+City\.?$", s)
        if m and district_of(m.group(1)) and re.search(r"Commissioner|C\.P\.|\bCP\b|D\.C\.P|DCP", s):
            d = district_of(m.group(1))
            z = re.search(r"Zone[- ]?(\d+)", s)
            if z and re.search(r"D\.?C\.?P", s):
                return "zone", "zone", d, f"Zone-{z.group(1)}", s, i > 0
            if re.search(r"traffic", s, re.I) and re.search(r"D\.?C\.?P", s):
                return "district", "traffic", d, f"{d} City", s, i > 0
            if re.search(r"cyber", s, re.I):
                return "district", "cyber", d, f"{d} City", s, i > 0
            if re.search(r"D\.?C\.?P", s):
                return "district", "unit", d, f"{d} City", s, i > 0
            return "district", "office", d, f"{d} City", s, i > 0
        m = re.search(r",\s*([\w-]+(?:\s[\w-]+)?)\s+Range", s)
        if m and re.search(r"I\.?G\.?P|D\.I\.G", s):
            return "range", "office", None, f"{m.group(1)} Range", s, i > 0
    return "state", "unit", None, "Gujarat", segs[0] if segs else post, False


def parse(html, url=URL):
    recs = []
    for i, o in officers(html):
        name = clean(o.get("name"))
        if not name:
            provenance.skipped('skip: not name')
            continue
        level, otype, district, area, used, extra = classify(o.get("post", ""))
        contact = clean(o.get("contact"))
        parts = [re.sub(r"\((?:M|O)\)", "", x) for x in re.split(r";", contact or "") if re.search(r"\((?:M|O)\)", x)]
        f = {("pay_level" if k == "level" else k): clean(str(v)) for k, v in o.items()
             if k not in ("name", "post", "contact", "email", "photo")}
        recs.append(rec(M, slug(used), level=level, office_type=otype, area=area, post=used, post_full=clean(o.get("post")),
                        additional_charge=True if extra else None, name=name, phone=phones(*parts), contact=contact,
                        email=email(o.get("email")), photo=clean(o.get("photo")), state="GJ", district=district, source=url,
                        src_url=url, src_pos={"index": i, "id": o.get("sr")}, **f))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [gz(M, "ips_cadre_register", r.content)], "" if recs else "no rows"
