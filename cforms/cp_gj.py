"""Gujarat councillor contacts from the corporations' own sites (records "councillor_contact", see cforms/cp_common.py).
One queue item = one corporation; payload "layout" picks the page type:
- "bmc": Bhavnagar, bmcgujarat.com Umbraco cards, 12 members per page (?page=1, 2 ...). Each card calls
  openModel(photo, -, name, ward, address, -, mobile, -, -). English names.
- "smc": Surat, suratmunicipal.gov.in/Corporation/Corp_list: one form per member (anti-forgery token + "data" from the
  same page, as a browser posts it) -> /Corporation/Navigate answers a second form (no script: a "Continue" button) ->
  /Corporation/CorpDetail: name, ward ("Elected From"), residential address, mobile. English names, two posts per member.
- "rmc": Rajkot, www.rmc.gov.in/ElectedBody: one page, cards "ક્રમ/વોર્ડ :- serial/ward", "નામ :-", "સરનામું :-" (address with
  "મોબા." and the mobile in Gujarati digits). Gujarati names, the same script as the SEC records. This page still lists the
  2021-26 council: only members who won again in 2026 match (about 33 of 72).
- "vmcpdf": Vadodara, vmc.gov.in/pdf/2026/Muni_sab_2026website.pdf ("List of Municipal councilors", 2026 council, 6 pages;
  India only: vmc.gov.in does not answer from abroad). One entry = "serial ward name mobile" and address lines under it.
  The PDF's font maps some Gujarati letters to wrong code points, so the text of names and addresses comes out with letters
  missing. The mobiles are plain digits and correct. The name goes to "name" for the match only (sql/72 pairs the members of
  one ward by best name likeness), the address goes to "address_pdf" (not "address": it is not readable as it is).
The SEC records (cw_gj, OCR of the results) hold the names in Gujarati and number members inside a ward by position
(councillor:GJ:<body>:<ward>-<n>), so record_for stays empty: sql/72 ties a member by body (lgd_code) + ward + name. For the
English layouts the name is matched across scripts (first and last word, see the parent report).
Record id cp:GJ:<body slug>:<ward>-<n> (n = the order on the page)."""
import gzip
import html as htmlmod
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from cforms.cp_common import clean, phones, record, slug, useful, ward_no

METHOD = "html page + pdf text (pypdf) + Gujarati font fix"     # source trail (provenance.py): how this reader reads its sources

TITLE = re.compile(r"^(shri|shree|smt|mr|mrs|ms|dr|shrimati)\.?\s+", re.I)
GU_TITLE = re.compile(r"^(શ્રીમતી|શ્રી|ર્ડો\.|ડો\.|ડૉ\.)\s*")


def name_of(s, gu=False):
    s = clean(s) or ""
    for _ in range(3):
        s = (GU_TITLE if gu else TITLE).sub("", s).strip()
    return s or None


def bmc_cards(html):
    """(name, ward label, address, phone) per card of a Bhavnagar list page."""
    out = []
    for m in re.finditer(r"openModel\(((?:\s*'(?:[^'\\]|\\.)*'\s*,?)+)\)", html):
        a = [htmlmod.unescape(x) for x in re.findall(r"'((?:[^'\\]|\\.)*)'", m.group(1))]
        if len(a) >= 7:
            out.append((a[2], a[3], a[4], a[6]))
    return out


def smc_list(html):
    """(name, ward label, form fields) per member of Surat's list."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for item in soup.select("div.list-group-item"):
        h = item.find("h3")
        label = clean(h.get_text(" ")) if h else None
        for f in item.find_all("form"):
            fields = {i["name"]: i.get("value", "") for i in f.find_all("input") if i.get("name")}
            b = f.find("button")
            out.append((clean(b.get_text(" ")) if b else None, label, f.get("action"), fields))
    return out


def smc_form(html):
    """The follow-on form of /Corporation/Navigate: (action, fields), or None."""
    f = BeautifulSoup(html, "lxml").find("form", id="secure-navigation-form")
    if not f:
        return None
    return f.get("action"), {i["name"]: i.get("value", "") for i in f.find_all("input") if i.get("name")}


def smc_detail(html):
    t = " ".join(BeautifulSoup(html, "lxml").get_text(" ").split())
    m = re.search(r"Corporator's information Name (.*?) Elected From (.*?) Residential Address (.*?) Mobile:?\s*([\d\s,/+-]*)", t)
    if not m:
        return None
    return {"name": m.group(1), "ward_label": m.group(2), "address": m.group(3).strip(" ."), "phone": phones(m.group(4))}


def rmc_cards(html):
    """(serial, ward, name, address, phone) per card of Rajkot's page."""
    t = " ".join(BeautifulSoup(html, "lxml").get_text(" ").split())       # \d also matches Gujarati digits
    out = []
    for m in re.finditer(r"ક્રમ/વોર્ડ\s*:-\s*(\d+)\s*/\s*(\d+)\s*નામ\s*:-\s*(.*?)\s*સરનામું\s*:-\s*(.*?)(?=ક્રમ/વોર્ડ|Ward-\d|$)", t):
        addr = m.group(4)
        mob = re.search(r"મોબા\.?\s*:?\s*([\d\s,/-]+)", addr)
        out.append((m.group(1), m.group(2), m.group(3), re.sub(r"[,\s]*મોબા\.?.*$", "", addr).strip(" ,."),
                    phones(mob.group(1)) if mob else None))
    return out


def vmc_entries(text):
    """(serial, ward, name, phones, address lines) per entry of the Vadodara PDF text (pypdf layout mode)."""
    out, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^\s*(\d{1,3})\s+(\d{1,2})\s+(\S.*)$", line)
        if m:
            cur = [m.group(1), m.group(2), m.group(3), []]
            out.append(cur)
        elif cur is not None and line.strip():
            cur[3].append(line.strip())
    res = []
    for serial, ward, first, rest in out:
        block = " ".join([first] + rest)
        ph = phones(" , ".join(re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", block)))
        name = " ".join(re.split(r"(?<!\d)[6-9]\d{9}", first)[0].split())
        name = re.sub(r"^\W*(\S{1,2}ી|શ્રી)\s+", "", name).strip()           # "શ્રી" comes out as "̒ી" / "ી"
        addr = " ".join(re.sub(r"(?<!\d)[6-9]\d{9}(?!\d)", "", x).strip() for x in rest).strip() or None
        res.append((serial, ward, name, ph, addr))
    return res


def numbered(state, body, recs):
    seen, out = {}, []
    for d in recs:
        w = d.get("ward_no") or "0"
        seen[w] = seen.get(w, 0) + 1
        out.append((f"cp:{state}:{slug(body)}:{w}-{seen[w]}", d))
    return out


def fetch(p, get):
    body, lgd, layout = p["body"], p.get("lgd_code"), p["layout"]
    files, recs = [], []
    if layout == "bmc":
        seen = set()
        for page in range(1, 21):
            url = f"{p['url']}?page={page}"
            r = get(url)
            if r is None:
                break
            cards = [c for c in bmc_cards(r.text) if c[0] not in seen]
            if not cards:
                break
            files.append((f"councillors/GJ/cp-{slug(body)}-p{page}.html.gz", gzip.compress(r.content), "application/gzip"))
            for name, label, addr, ph in cards:
                seen.add(name)
                recs.append(record("GJ", body, ward_no(label), name_of(name), url, phone=phones(ph), address=addr,
                                   ward_label=label, lgd_code=lgd))
    elif layout == "smc":
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        files.append((f"councillors/GJ/cp-{slug(body)}-list.html.gz", gzip.compress(r.content), "application/gzip"))
        for name, label, action, fields in smc_list(r.text):
            a = get(urljoin(p["url"], action or "/Corporation/Navigate"), method="POST", data=fields)
            nav = a is not None and smc_form(a.text)
            b = nav and get(urljoin(p["url"], nav[0]), method="POST", data=nav[1])
            d = b and smc_detail(b.text)
            if not d:
                continue
            files.append((f"councillors/GJ/cp-{slug(body)}-{slug(name)}.html.gz", gzip.compress(b.content), "application/gzip"))
            recs.append(record("GJ", body, ward_no(label), name_of(d["name"]) or name_of(name), p["url"], phone=d["phone"],
                               address=d["address"], ward_label=label, lgd_code=lgd, extra={"ward_name": d["ward_label"]}))
    elif layout == "rmc":
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        files.append((f"councillors/GJ/cp-{slug(body)}.html.gz", gzip.compress(r.content), "application/gzip"))
        for serial, ward, name, addr, ph in rmc_cards(r.text):
            recs.append(record("GJ", body, str(int(ward)), name_of(name, gu=True), p["url"], phone=ph, address=addr,
                               lgd_code=lgd, extra={"serial": serial}))
    elif layout == "vmcpdf":
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        files.append((f"councillors/GJ/cp-{slug(body)}.pdf", r.content, "application/pdf"))
        import io
        from pypdf import PdfReader
        try:
            text = "\n".join(pg.extract_text(extraction_mode="layout") or "" for pg in PdfReader(io.BytesIO(r.content)).pages)
        except Exception as e:
            return [], files, f"pdf: {type(e).__name__}"
        for serial, ward, name, ph, addr in vmc_entries(text):
            recs.append(record("GJ", body, str(int(ward)), name, p["url"], phone=ph, lgd_code=lgd,
                               extra={"serial": serial, "address_pdf": addr, "name_quality": "pdf font: letters missing"}))
    else:
        return [], [], f"unknown layout {layout}"
    recs = useful(recs)
    return numbered("GJ", body, recs), files, "" if recs else "no members with contacts"
