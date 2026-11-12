"""Uttar Pradesh: ward councillors (parshads) of municipal corporations elected in May 2023, from the corporations' own sites.

The State Election Commission's winner list (sec.up.nic.in/site/NewWinnerList2023.aspx, every body and post) did not answer on
2026-11-11 from Germany, from the India servers or from a US vantage (connection timed out / refused); it is the source for
the 199 nagar palika parishads and 544 nagar panchayats once it answers again. Readers here (payload "source"):
- "lucknow": Nagar Nigam Lucknow, "नव निर्वाचित मा0 पार्षदों की सूची (निर्वाचन आयोग की सूची के अनुसार)", oath date 26.05.2023
  (lmc.up.nic.in/pdf/Corporator_2023_2027_sapath_date_26_05_2023_Main_List.pdf, 4 pages, Word file in the Kruti Dev font:
  the text layer is converted to Unicode with cforms/cn_krutidev.py). Columns: ward no | ward name | councillor | father or
  husband | party | address | phone; the Mayor stands in a line above the table.
- "kanpur": Nagar Nigam Kanpur, "कानपुर के महापौर एवं नगरसेवक" (kmc.up.nic.in/mayor-corporators.html): ward no | name | address |
  phone, and the Mayor's table above it. The site sends an incomplete TLS chain; the family's trust store (certs_trust) has it.
- "gorakhpur": Nagar Nigam Gorakhpur, "नवनिर्वाचित मा. पार्षदगणो की सुची" (gorakhpurnagarnigam.up.gov.in/parsadlist.aspx):
  serial | ward no | ward name | name | mobile.
All three answer outside India. One queue item = one corporation. Record id councillor:UP:<body slug>:<ward no or "chair">.
"""
import gzip
import hashlib
import io
import re
import subprocess
import tempfile

from bs4 import BeautifulSoup

import provenance
from cforms.cn_krutidev import convert
from cforms.cp_common import tr_pos

METHOD = "pdf text (pdftotext -layout) + Kruti Dev map (Lucknow), html table (Kanpur, Gorakhpur)"     # source trail (provenance.py): how this reader reads its sources

ELECTION = "Uttar Pradesh urban local bodies general election 2023 (poll 4 and 11 May 2023)"
SOURCES = {
    "lucknow": {"url": "https://lmc.up.nic.in/pdf/Corporator_2023_2027_sapath_date_26_05_2023_Main_List.pdf", "body_en": "Lucknow",
                "body": "नगर निगम लखनऊ", "district": "Lucknow"},
    "kanpur": {"url": "https://kmc.up.nic.in/mayor-corporators.html", "body_en": "Kanpur", "body": "नगर निगम कानपुर",
               "district": "Kanpur Nagar"},
    "gorakhpur": {"url": "https://gorakhpurnagarnigam.up.gov.in/parsadlist.aspx", "body_en": "Gorakhpur", "body": "नगर निगम गोरखपुर",
                  "district": "Gorakhpur"}}
PARTIES = [(r"भ0?\s*जा0?\s*पा0?|भा0?\s*ज0?\s*पा0?|भाजपा", "Bharatiya Janata Party"), (r"^स0?\s*पा0?$|समाजवादी", "Samajwadi Party"),
           (r"ब0?\s*स0?\s*पा0?|बसपा", "Bahujan Samaj Party"), (r"कांग्रेस|कॉंग्रेस", "Indian National Congress"),
           (r"निर्दलीय", "Independent"), (r"आप$|आम आदमी", "Aam Aadmi Party"), (r"ए0?\s*आई0?\s*एम", "AIMIM")]
# Kruti Dev text: father/husband words and party words that anchor the Lucknow columns
KD_FATHER = re.compile(r"(?<!\S)(Jh|Lo0|Lo-|Jherh|eks0|Mk0|lS0)\s")
KD_PARTY = re.compile(r"(?<!\S)(l0ik0|Hk0tk0ik0|Hkk0t0ik0|c0l0ik0|dkaxzsl|funZyh;|vki|,0vkbZ0,e0vkbZ0,e0)(?!\S)")


def norm(s):
    return " ".join((s or "").replace("\xa0", " ").split()).strip(" ,;:-")


def party(s):
    s = norm(s)
    for rx, en in PARTIES:
        if re.search(rx, s):
            return en
    return s or None


def phones(s):
    out = [d for d in (re.sub(r"\D", "", m) for m in re.findall(r"\d[\d\s-]{8,}\d", s or "")) if len(d) == 10]
    return ", ".join(dict.fromkeys(out)) or None


def base(src):
    s = SOURCES[src]
    return {"type": "councillor", "state": "UP", "body": s["body"], "body_en": s["body_en"], "body_type": "Municipal Corporation",
            "district": s["district"], "election": ELECTION}


def rec(src, ward, d):
    d = {**base(src), **d}
    return f"councillor:UP:{src}:{ward}", {k: v for k, v in d.items() if v not in (None, "")}


def kd(s):
    return norm(convert(s).replace("]", ",").replace("^^", "\"").replace("@", "/").replace("&", "-"))


def lucknow(text, url):
    """pdftotext -layout text of the Lucknow list -> records."""
    recs = []
    m = re.search(r"(Jherh|Jh)\s+(.+?)\]\s*ek0\s*egkikSj.*?la0\s*&?\s*([\d]{10})", text)
    if m:
        before = text[:m.start()]
        pg, ln = before.count("\f") + 1, before.split("\f")[-1].count("\n") + 1
        recs.append(rec("lucknow", "chair", {"ward_no": "chair", "name": kd(m.group(2)), "position": "Mayor", "phone": m.group(3),
                                             "url": url, "src_pos": provenance.line_pos(pg, ln, text.split("\f")[pg - 1].split("\n")[ln - 1]),
                                             "method": "pdf text (pdftotext -layout) + Kruti Dev map"}))
    for pg, page in enumerate(text.split("\f"), 1):
        lines = page.splitlines()
        rows, name_x = [], []
        for ln in lines:
            mm = re.match(r"\s*(\d{1,3})\s{2,}(.*)$", ln)
            f = KD_FATHER.search(ln)
            if mm and f:
                rows.append(ln)
                w = re.search(r"okMZ\s{2,}", ln)
                if w and w.end() < f.start():
                    name_x.append(w.end())
        nx = sorted(name_x)[len(name_x) // 2] if name_x else None
        cur = None
        for li, ln in enumerate(lines, 1):
            mm = re.match(r"\s*(\d{1,3})\s{2,}(.*)$", ln)
            f = KD_FATHER.search(ln)
            p = KD_PARTY.search(ln)
            if mm and f and p and f.start() < p.start():
                ward_end = mm.start(2)
                w = re.search(r"okMZ\s{2,}", ln)
                cut = w.end() if w and w.end() <= p.start() else (ln.rfind(" ", 0, nx + 1) + 1 if nx and nx < p.start() else f.start())
                # the father column starts with Jh / Lo0 / eks0 ...; a name may start with one too (eks0 = मो0): take the first
                # such word after the name's own start
                f = next((x for x in KD_FATHER.finditer(ln, cut + 1) if x.start() < p.start()), f)
                ph = re.search(r"(\d{10}(\s+\d{10})*)\s*$", ln)
                cur = {"ward": str(int(mm.group(1))), "ward_name": ln[ward_end:cut], "name": ln[cut:f.start()],
                       "father": ln[f.start():p.start()], "party": p.group(1),
                       "address": ln[p.end():ph.start() if ph else len(ln)], "phone": ph.group(1) if ph else "",
                       "x": (cut, f.start(), p.end()), "pos": provenance.line_pos(pg, li, ln)}
                recs.append(cur)
            elif cur is not None and ln.strip() and not re.search(r"okMZ\s+okMZ dk uke|la0\s+loZ", ln):
                for c in re.finditer(r"\S+(?:\s\S+)*", ln):
                    x = c.start()
                    if x < cur["x"][0] - 1:
                        cur["ward_name"] += " " + c.group(0)
                    elif x < cur["x"][1] - 1:
                        cur["name"] += " " + c.group(0)
                    elif x >= cur["x"][2] - 1:
                        cur["address"] += " " + c.group(0)
    out = []
    for r in recs:
        if isinstance(r, tuple):
            out.append(r)
            continue
        out.append(rec("lucknow", r["ward"], {"ward_no": r["ward"], "ward_name": kd(r["ward_name"]), "name": kd(r["name"]),
                                              "father_or_husband": kd(r["father"]), "party": party(kd(r["party"])),
                                              "address": kd(r["address"]), "phone": phones(r["phone"]), "position": "Member",
                                              "url": url, "src_pos": r["pos"], "method": "pdf text (pdftotext -layout) + Kruti Dev map"}))
    return out


def cells(tr):
    return [norm(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"], recursive=False)]


def kanpur(html, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for tr in soup.find_all("tr"):
        c = cells(tr)
        if len(c) >= 3 and re.search(r"महापौर", c[0]) and re.search(r"\d{10}", " ".join(c)):
            recs.append(rec("kanpur", "chair", {"ward_no": "chair", "name": norm(re.sub(r",?\s*महापौर$", "", c[0])), "position": "Mayor",
                                                "address": c[1], "phone": phones(c[2]), "email": c[3] if len(c) > 3 else None,
                                                "url": url, "src_pos": tr_pos(tr), "method": "html table"}))
        elif len(c) >= 3 and re.fullmatch(r"\d{1,3}", c[0]) and c[1]:
            recs.append(rec("kanpur", str(int(c[0])), {"ward_no": str(int(c[0])), "name": c[1], "address": c[2] if c[2] != "कानपुर" else None,
                                                       "phone": phones(c[3]) if len(c) > 3 else None, "position": "Member", "url": url,
                                                       "src_pos": tr_pos(tr), "method": "html table"}))
    return recs


def gorakhpur(html, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for tr in soup.find_all("tr"):
        c = cells(tr)
        if len(c) >= 5 and re.fullmatch(r"\d{1,3}", c[1]) and c[3]:
            recs.append(rec("gorakhpur", str(int(c[1])), {"ward_no": str(int(c[1])), "ward_name": c[2], "name": c[3],
                                                          "phone": phones(c[4]), "position": "Member", "url": url,
                                                          "src_pos": tr_pos(tr), "method": "html table"}))
    return recs


def fetch(p, get):
    src = p["source"]
    url = p.get("url") or SOURCES[src]["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    key = hashlib.sha1(url.encode()).hexdigest()[:12]
    if src == "lucknow":
        if not r.content.startswith(b"%PDF"):
            return [], [], "not a PDF"
        files = [(f"councillors/UP/{key}.pdf", r.content, "application/pdf")]
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(r.content)
            f.flush()
            text = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
        recs = lucknow(text, url)
    else:
        files = [(f"councillors/UP/{src}-{key}.html.gz", gzip.compress(r.content), "application/gzip")]
        recs = (kanpur if src == "kanpur" else gorakhpur)(r.text, url)
    return recs, files, "" if recs else "no councillors read"
