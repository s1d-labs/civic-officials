"""Himachal Pradesh: District Development Officers (DDO, head of the DRDA) of the 12 districts and Block Development Officers of
every block, from the Rural Development Department's "Directory" page (rural.hp.gov.in/directory; React site). The page asks
the site's CMS API for the page "Directory" (GET https://rural.hp.gov.in/cms/api/pages/v1/view/slug/Directory with the headers
the site's bundle sends: X-Channel-Id WEB, Project HPRURAL; without them the API answers 401 / "ESS-699"). The answer lists one
section per file: "Contact details of District Development Officers & Block Development Officers" (date 2026-02-13), file
"DDOsBDO contacts.pdf", mediaId -> GET /cms/api/media/v1/view/<mediaId> (PDF, 2 pages, 0.5 MB, text layer; measured
2026-11-13 from Mumbai). Open: no login, no captcha.

PDF columns (x in points): District (53) | District / Block (103) | Name of DDO / BDO (157) | Mobile (232) | Office phone (282) |
Office email (354). The text layer merges neighbouring cells into one piece ("2.Ghumarwin Abhishek Sharma 98827-59245 ...").
Page 1 starts with the 12 DDO rows (district twice: "Bilaspur Bilaspur Yashpal Singh ..."); then block rows "<n>.<Block> <name>
<mobile> <office> <email>", numbered from 1 again in each district, districts in the order of the DDO rows (the district labels
"5.Kinnaur" in the first column are not needed). A piece in the block column without a number continues the block name
("11.Nagrota" / "Bagwan"); pieces in the name column continue the name ("Vivek Kumar" / "Chauhan"); other pieces belong to the
row nearest in height. Wrapped emails ("drdakin-" / "hp@nic.in", "narkanda" / "@ yahoo.com") are joined.

Records: DDO: dept rural_development, level district, post "District Development Officer"; BDO: level block, area = block as
the list spells it, post "Block Development Officer", lgd_block_code when the name matches LGD (lgd.blocks state 2; aliases for
HQ names: Kaza = Spiti, Keylong = Lahaul, Chirgaon = Chhohara, Swarghat = Shree Naina Devi). "Vacant" -> vacant=true, no name.
phone = mobile(s) and office phone. One queue item: 1 GET (page JSON) + 1 GET (PDF; kept in the bucket).
Record ids: dept:sub4_hp_bdo:<district slug>:ddo and dept:sub4_hp_bdo:<district slug>:<block slug>.
"""
import io
import json
import re

from dforms import _esw

METHOD = "cms json (page Directory) -> pdf text pieces by position (pypdf), rows by serial number and height"

MODULE = "sub4_hp_bdo"
PAGE = "https://rural.hp.gov.in/cms/api/pages/v1/view/slug/Directory"
MEDIA = "https://rural.hp.gov.in/cms/api/media/v1/view/{}"
HEADERS = {"X-Channel-Id": "WEB", "Project": "HPRURAL", "Accept": "*/*", "Content-Type": "application/json"}
SECTION = re.compile(r"(?i)block\s+development\s+officers?|bdo")
# DDO rows in list order: (district as printed, LGD code, LGD name)
DISTRICTS = [("Bilaspur", "15", "Bilaspur"), ("Chamba", "16", "Chamba"), ("Hamirpur", "17", "Hamirpur"), ("Kangra", "18", "Kangra"),
             ("Kinnaur", "19", "Kinnaur"), ("Kullu", "20", "Kullu"), ("Lahual & Spiti", "21", "Lahaul And Spiti"),
             ("Mandi", "22", "Mandi"), ("Shimla", "23", "Shimla"), ("Sirmour", "24", "Sirmaur"), ("Solan", "25", "Solan"),
             ("Una", "26", "Una")]
# LGD blocks (lgd.blocks, state 2, 2026-11-13): district code -> {letters key: (block name, block code)}
_LGD = {"15": "Bilaspur Sadar=135; Ghumarwin=137; Jhandutta=136; Shree Naina Devi=7089",
        "16": "Bharmour=139; Bhatiyat=138; Chamba=140; Mehla=141; Pangi=142; Salooni=143; Tissa=144",
        "17": "Bamsan=145; Bhoranj=146; Bijhari=147; Hamirpur=148; Nadaun=149; Sujanpur Tira=150",
        "18": "Badoh=7496; Baijnath=151; Bhawarna=152; Dehra=153; Dharamshala=6504; Fatehpur=154; Indora=155; Kangra=156; "
              "Lambagaon=157; Nagrota Bagwan=158; Nagrota Surian=159; Nurpur=160; Palampur=7559; Panchrukhi=161; Pragpur=162; "
              "Rait=163; Sulah=164; Surani=7561",
        "19": "Kalpa=165; Nichar=166; Pooh=167", "20": "Anni=168; Banjar=169; Bhunter=7507; Kullu=170; Naggar=171; Nirmand=172",
        "21": "Lahaul=173; Spiti=174",
        "22": "Balh=175; Balichowki=7349; Chauntra=177; Churag=7494; Dhanotu=7490; Dharmpur=178; Drang=179; Gohar=176; Gopalpur=180; "
              "Karsog=181; Mandi Sadar=182; Nihri=7491; Seraj=183; Sundarnagar=184",
        "23": "Basantpur=185; Chhohara=186; Chopal=187; Jubbal=188; Kotkhai=7492; Kupvi=7348; Mashobra=189; Nankhari=6538; "
              "Narkanda=190; Rampur=191; Rohru=192; Theog=193; Totu=7481",
        "24": "Dadahu=7623; Nahan=194; Pachhad=195; Paonta Sahib=196; Rajgarh=197; Sangrah=198; Shillai=199; Tilordhar=7493",
        "25": "Dharampur=200; Kandaghat=201; Kunihar=202; Nalagarh=203; Patta=7560; Solan=204",
        "26": "Amb=205; Bangana=206; Gagret=207; Haroli=208; Una=209"}


def key(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


LGD_BLOCKS = {dc: {key(n): (n, c) for n, c in (x.split("=") for x in v.split("; "))} for dc, v in _LGD.items()}
ALIAS = {"kaza": "spiti", "keylong": "lahaul", "chirgaon": "chhohara", "swarghat": "shreenainadevi", "bamson": "bamsan",
         "bhattiyat": "bhatiyat", "sullah": "sulah", "baroh": "badoh", "bhuntar": "bhunter", "sujanpur": "sujanpurtira",
         "sujanpurtihra": "sujanpurtira", "sundernagar": "sundarnagar", "dharampur": "dharmpur", "bilaspur": "bilaspursadar"}
ROW = re.compile(r"^\s*(\d{1,2})\s*\.?\s*([A-Za-z].*)$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*")
NUM = re.compile(r"(?<![\d@])\d[\d-]{8,13}\d(?![\d])")


def block_code(dc, block):
    t = LGD_BLOCKS.get(dc, {})
    k = key(block)
    hit = t.get(k) or t.get(ALIAS.get(k, "")) or (t.get(ALIAS[k]) if k in ALIAS else None)
    if hit is None and dc == "22" and k == "dharampur":
        hit = t.get("dharmpur")
    return hit or ("", "")


def pieces(content):
    """[(page, x, y, text)] of every text piece of the PDF."""
    from pypdf import PdfReader

    from dforms._util2_pdfgrid import page_parts
    reader = PdfReader(io.BytesIO(content))
    out = []
    for n, page in enumerate(reader.pages, 1):
        texts, _, _ = page_parts(reader, page)
        out += [(n, x, y, t) for x, y, t in texts if t and t.strip()]
    return out


def rows(content):
    """[{"kind": "ddo"|"bdo", "page", "y", "start", "block_more": [...], "name_more": [...], "other": [...]}] in list order."""
    ps = pieces(content)
    starts = []
    for n, x, y, t in ps:
        s = t.strip()
        if 95 <= x < 150 and ROW.match(s):
            starts.append({"kind": "bdo", "page": n, "y": y, "x": x, "start": s, "block_more": [], "name_more": [], "other": []})
        elif x < 95 and n == 1 and any(s.lower().startswith(d.lower()) for d, _, _ in DISTRICTS) and not ROW.match(s):
            starts.append({"kind": "ddo", "page": n, "y": y, "x": x, "start": s, "block_more": [], "name_more": [], "other": []})
    for n, x, y, t in ps:
        s = t.strip()
        if any(r["page"] == n and r["y"] == y and r["x"] == x and r["start"] == s for r in starts):
            continue
        if x < 95 or y > 700 or "Details of" in s:
            continue                    # district labels, headers, title
        same = [r for r in starts if r["page"] == n]
        if not same:
            continue
        if 95 <= x < 150:               # block name continues below its row start
            above = [r for r in same if r["y"] >= y and r["y"] - y <= 15]
            if above:
                min(above, key=lambda r: r["y"] - y)["block_more"].append(s)
            continue
        # a cell that wraps runs downwards: the piece belongs to the nearest row start at or above it
        up = [r for r in same if r["y"] >= y - 3]
        r = min(up, key=lambda r: r["y"] - y) if up else max(same, key=lambda r: r["y"])
        if 150 <= x < 230 and not re.search(r"\d|@", s):
            r["name_more"].append(s)
        else:
            r["other"].append((x, y, s))
    starts.sort(key=lambda r: (r["page"], -r["y"]))
    return starts


def split_block(dc, words):
    """(block, rest) from the words after the serial number: two words when they make an LGD block name or end with Sadar /
    Sahib / Bagwan / Surian."""
    if len(words) >= 2 and (key(words[0] + words[1]) in LGD_BLOCKS.get(dc, {})
                            or words[1].lower() in ("sadar", "sahib", "bagwan", "surian", "tihra", "tira")):
        return " ".join(words[:2]), words[2:]
    return (words[0] if words else ""), words[1:]


def parse_contacts(texts):
    t = " ".join(texts)
    t = re.sub(r"\s*@\s*", "@", t)
    t = re.sub(r"(?<=[A-Za-z0-9])-\s+(?=[A-Za-z0-9.]+@|[A-Za-z0-9-]*@?[A-Za-z0-9-]*\.(in|com))", "-", t)
    emails = list(dict.fromkeys(e.strip(".") for e in EMAIL.findall(t)))
    rest = EMAIL.sub(" ", t)
    mob, off = [], []
    for m in NUM.findall(rest):
        d = m.replace("-", "")
        if not d.isdigit():
            continue
        (mob if len(d) == 10 and d[0] in "6789" else off).append(m if "-" in m else d)
    return mob, off, emails


def name_words(words):
    out = []
    for w in words:
        if re.search(r"\d|@", w) or w == "-":
            break
        out.append(w)
    return out


def build(rs, source=PAGE):
    recs, di = [], -1
    prev_n = None
    for r in rs:
        others = [s for _, _, s in sorted(r["other"], key=lambda o: (-o[1], o[0]))]
        if r["kind"] == "ddo":
            s = r["start"]
            d = next(d for d in DISTRICTS if s.lower().startswith(d[0].lower()))
            rest = s[len(d[0]):].strip()
            second = "L & Spiti" if d[0].startswith("Lahual") else d[0]
            if rest.lower().startswith(second.lower()):
                rest = rest[len(second):].strip()
            words = rest.split()
            nm = " ".join(name_words(words) + r["name_more"]).strip()
            mob, off, em = parse_contacts([" ".join(words[len(name_words(words)):])] + others)
            vacant = bool(re.fullmatch(r"(?i)vacant", nm))
            recs.append(_esw.record(MODULE, f"{_esw.slug(d[2])}:ddo", dept="rural_development", level="district", area=d[2],
                                    district=d[2], district_code=d[1], state="HP", name="" if vacant else nm,
                                    post="District Development Officer", phone=", ".join(mob + off), email=", ".join(em),
                                    vacant=True if vacant else None, source=source,
                                    src_pos={"page": r["page"], "y": round(r["y"], 1), "row": "ddo"}))
            continue
        m = ROW.match(r["start"])
        n = int(m.group(1))
        if prev_n is None or n <= prev_n:
            di += 1
        prev_n = n
        if di >= len(DISTRICTS):
            break
        dname, dc, lgd_name = DISTRICTS[di]
        words = (m.group(2) + " " + " ".join(r["block_more"])).split() if r["block_more"] and not re.search(r"\s", m.group(2).strip()) \
            else m.group(2).split()
        block, rest = split_block(dc, words)
        nw = name_words(rest)
        if not nw and not r["name_more"]:
            # the name cell came as its own piece with the numbers ("Latika Sejhpal 98056-23081 ...")
            for i, (x, y, t) in enumerate(sorted(r["other"], key=lambda o: (-o[1], o[0]))):
                if 150 <= x < 232 and name_words(t.split()):
                    w = t.split()
                    nw = name_words(w)
                    others = [o for o in others if o != t] + [" ".join(w[len(nw):])]
                    break
            rest = [] if nw else rest
        nm = " ".join(nw + r["name_more"]).strip()
        if r["block_more"] and re.search(r"\s", m.group(2).strip()):
            nm = (nm + " " + " ".join(r["block_more"])).strip()
        mob, off, em = parse_contacts([" ".join(rest[len(nw):])] + others)
        vacant = bool(re.fullmatch(r"(?i)vacant", nm))
        lgd_block, code = block_code(dc, block)
        recs.append(_esw.record(MODULE, f"{_esw.slug(lgd_name)}:{_esw.slug(block)}", dept="rural_development", level="block",
                                area=block, district=lgd_name, district_code=dc, state="HP", name="" if vacant else nm,
                                post="Block Development Officer", phone=", ".join(mob + off), email=", ".join(em),
                                vacant=True if vacant else None, lgd_block_code=code or None, lgd_block_name=lgd_block or None,
                                list_no=str(n), source=source, src_pos={"page": r["page"], "y": round(r["y"], 1), "sn": str(n)}))
    seen, out = set(), []
    for rid, d in recs:
        if not (d.get("name") or d.get("phone") or d.get("email")):
            continue        # a vacant post with no office contact ("8.Dadahu Vacant") says nothing to reach
        x, i = rid, 2
        while x in seen:
            x, i = f"{rid}:{i}", i + 1
        seen.add(x)
        out.append((x, d))
    return out


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": PAGE, "state": "HP", "india_only": False, "route": "abroad"}}]


def media_url(page_json):
    """(media url, date) of the BDO contacts file in the page JSON, newest first; (None, None) when missing."""
    try:
        secs = (page_json.get("response") or {}).get("sections") or []
    except AttributeError:
        return None, None
    best = None
    for s in secs:
        d = s.get("data") or {}
        doc = d.get("documentId") or {}
        if doc.get("mediaId") and SECTION.search((s.get("name") or "") + " " + (d.get("subject") or "")):
            if best is None or (d.get("date") or "") > (best[1] or ""):
                best = (MEDIA.format(doc["mediaId"]), d.get("date"))
    return best or (None, None)


def fetch(p, get):
    r = get(p.get("url") or PAGE, headers=HEADERS)
    if r is None:
        return [], [], "no answer"
    try:
        js = json.loads(r.content)
    except ValueError:
        return [], [], "page answer not json"
    url, date = media_url(js)
    if not url:
        return [], [], "no BDO file in the page"
    f = get(url, headers=HEADERS)
    if f is None or f.content[:5] != b"%PDF-":
        return [], [], "file not a pdf"
    recs = build(rows(f.content), url)
    for _, d in recs:
        d["src_url"] = url
        if date:
            d["last_updated"] = date
    return recs, [(f"depts/{MODULE}/ddo-bdo-contacts.pdf", f.content, "application/pdf")], "" if recs else "no rows"
