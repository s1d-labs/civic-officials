"""Maharashtra: town body chairpersons and offices that dforms/ulb_mh.py does not give (it reads 4 district pages only). One queue
item per source; payload "kind" gives the source format. The parsers for Goa (dforms/ulb2_ga.py, kind "charge_order") and
Dadra-Nagar Haveli-Daman-Diu (dforms/ulb2_dd.py, kind "office_page") live here too, so the three modules share fetch().

kind "sec_president" (MH): State Election Commission of Maharashtra, mahasec.maharashtra.gov.in/Upload/PDF/President.pdf (26 pages,
made from an Excel sheet on 2026-04-16; archive.s1d.me copy of 2026-11-07). The result of the direct election of the president
(Nagaradhyaksha) of 288 nagar parishads and nagar panchayats in the 2025-26 general election: Sr. No., division, district, body,
reservation (GEN, GEN W, BCC, BCC W, SC, SC W, ST, ST W), name of the winning candidate, gender, valid votes, party, runner-up,
votes, party. The text (pypdf, plain mode) gives each row in order, with wrapped cells; the reader finds the rows by their running
Sr. No. and the division word. One record per row: post "President", role chair; name as the list writes it (surname first in
most rows); district as written; reservation, gender, votes; lgd_code from dforms/ulb2_mh_lgd.json (the tie made once to civic.ulb
by name in the district, 2026-11-11). Party is left out: the plain text runs the party and the runner-up together. Answers from
Germany (206 on 2026-11-11).

kind "office_list" (MH): district pages that list each body with its office phone and email, not a card list (Nashik
"Municipal Council" and "Nagar Panchayat" pages, nashik.gov.in, archive copies of 2026-11-06). "<Body> Municipal Council Phone No.
<phone> Email <email>". One record per body: post "Office" (role staff). Many mailboxes are the chief officer's ("co.manmad",
"coyeola"): extra key mailbox "chief officer" says so; the post stays "Office". Answers from Germany.

kind "charge_order" (GA, used by ulb2_ga): orders of the Department of Personnel, Government of Goa (www.goa.gov.in/wp-content/uploads/...) of the
form "<Shri|Smt> <name>, <own post> shall (also) hold the charge of (the post of) Chief Officer, <town> Municipal Council". One
record per order: post "Chief Officer" (role head), name, own_post, order date as last_updated. The posting orders that list many
officers in a table are not read (the table text comes out in mixed order). 403 from Germany: india_only.

kind "office_page" (DD, used by ulb2_dd): the Diu district page of Diu Municipal Council (diu.gov.in/diu-municipal-council/: name, phone, address,
email, "Last Updated: 18.10.2022"). One "Office" record.
"""
import io
import json
import re
from pathlib import Path

from dforms import _esw, _ulb

METHOD = "pdf text (pypdf plain mode)"     # sec_president, charge_order; office_list / office_page records say "html page text"
METHOD_HTML = "html page text (pattern match)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_mh"
SEC_URL = "https://mahasec.maharashtra.gov.in/Upload/PDF/President.pdf"
SOURCES = (  # key, kind, state, url, india_only, extra payload
    ("sec-president", "sec_president", "MH", SEC_URL, False, {}),
    ("nashik-mc", "office_list", "MH", "https://nashik.gov.in/en/municipal-council/", False,
     {"district": "Nashik", "body_type": "Municipal Council"}),
    ("nashik-np", "office_list", "MH", "https://nashik.gov.in/en/nagar-panchayat/", False,
     {"district": "Nashik", "body_type": "Nagar Panchayat"}),
)
LGD = json.loads((Path(__file__).with_name("ulb2_mh_lgd.json")).read_text())
DIVISIONS = r"(AMRAVATI|KOKAN|KONKAN|NAGPUR|NASHIK|PUNE|CHHATRAPATI\s+SAMBHAJI\s*NAGAR|CHH\.?\s*SAMBHAJI\s*NAGAR|AURANGABAD)"
DISTRICTS = ("AHILYANAGAR AHMEDNAGAR AKOLA AMRAVATI BEED BHANDARA BULDHANA CHANDRAPUR DHARASHIV OSMANABAD DHULE GADCHIROLI GONDIA "
             "HINGOLI JALGAON JALNA KOLHAPUR LATUR NAGPUR NANDED NANDURBAR NASHIK PALGHAR PARBHANI PUNE RAIGAD RATNAGIRI SANGLI SATARA "
             "SINDHUDURG SOLAPUR THANE WARDHA WASHIM YAVATMAL AURANGABAD").split() + ["CHHATRAPATI SAMBHAJI NAGAR",
                                                                                "CHHATRAPATI SAMBHAJINAGAR", "CHH. SAMBHAJINAGAR",
                                                                                "CHH. SAMBHAJI NAGAR"]
RES = re.compile(r"^(GEN|GENERAL|BCC|OBC|NAMAPRA|SC|ST)$")
GENDER = re.compile(r"^(F|M|MALE|FEMALE)$")


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "kind": kind, "url": url, "state": st, "india_only": ind, **x}}
            for k, kind, st, url, ind, x in SOURCES]


def lgd_key(district, body):
    """Key of dforms/ulb2_mh_lgd.json: district and body, letters only, upper case ("NAGPUR|KAMPTEE")."""
    return re.sub(r"[^A-Z]", "", (district or "").upper()) + "|" + re.sub(r"[^A-Z]", "", (body or "").upper())


def plain_text(content):
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(content))
    made = None
    try:
        m = re.match(r"D:(\d{4})(\d{2})(\d{2})", str(r.metadata.get("/CreationDate") or ""))
        made = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
    except Exception:
        pass
    return " ".join(_esw.clean(p.extract_text() or "") for p in r.pages), made


def page_starts(content):
    """Offsets in plain_text's joined text where each page starts (source trail: an offset -> its page)."""
    from pypdf import PdfReader
    out, n = [], 0
    for p in PdfReader(io.BytesIO(content)).pages:
        out.append(n)
        n += len(_esw.clean(p.extract_text() or "")) + 1
    return out


def sec_rows(text, first=1, where=None):
    """[{sr, division, district, body, reservation, name, gender, votes}] from the plain text of President.pdf (rows from Sr. No.
    `first` on; a test sample may start in the middle). where: a list; when given, it gets (character offset, row text) per row."""
    out, pos, n = [], 0, first
    starts = []
    while True:
        m = re.compile(rf"(?:^|\s){n}\s+{DIVISIONS}\s").search(text, pos)
        if not m:
            break
        starts.append((n, m.start() + (m.group(0)[0].isspace()), m.end(), m.group(1)))
        pos, n = m.end(), n + 1
    for i, (sr, _s, e, div) in enumerate(starts):
        raw = text[_s:starts[i + 1][1] if i + 1 < len(starts) else len(text)]
        chunk = text[e:starts[i + 1][1] if i + 1 < len(starts) else len(text)].split()
        dist = None
        for d in sorted(DISTRICTS, key=len, reverse=True):
            w = d.split()
            if [t.upper() for t in chunk[:len(w)]] == w:
                dist, chunk = d, chunk[len(w):]
                break
        if not dist:
            continue
        ri = next((j for j in range(1, len(chunk)) if RES.match(chunk[j])), None)
        if ri is None:
            continue
        body, rest = " ".join(chunk[:ri]), chunk[ri:]
        res = rest[0] + (" W" if len(rest) > 1 and rest[1] in ("W", "WOMEN") else "")
        rest = rest[2:] if res.endswith(" W") else rest[1:]
        gi = next((j for j in range(1, len(rest) - 1) if GENDER.match(rest[j]) and re.match(r"^(\d+|UNOPP)", rest[j + 1])), None)
        if gi is None:
            continue
        votes = rest[gi + 1]
        votes = "unopposed" if votes.startswith("UNOPP") else votes
        out.append({"sr": sr, "division": " ".join(div.split()), "district": dist, "body": body, "reservation": res,
                    "name": " ".join(rest[:gi]), "gender": "F" if rest[gi].startswith("F") else "M", "votes": votes})
        if where is not None:
            where.append((_s, raw.strip()))
    return out


def parse_sec(content, url=SEC_URL):
    return parse_sec_text(*plain_text(content), url=url, starts=page_starts(content))


def parse_sec_text(text, made=None, url=SEC_URL, starts=None):
    """Records from the plain text of President.pdf; made = the PDF's creation date (yyyy-mm-dd), written as last_updated."""
    recs, seen = [], set()
    import bisect
    where = []
    for r, (off, row_text) in zip(sec_rows(text, where=where), where):
        lgd = LGD.get(lgd_key(r["district"], r["body"]))
        pg = bisect.bisect_right(starts, off) if starts else None
        pos = {"page": pg, "offset": off - starts[pg - 1] if pg else off, "line_text": row_text}
        pos = {k: v for k, v in pos.items() if v is not None}     # offset = character offset of the row in its page's plain text
        recs.append(_ulb.record(MODULE, "MH", r["body"], "President", seen, name=r["name"], district=r["district"].title(),
                                source=url, lgd_code=lgd, reservation=r["reservation"], gender=r["gender"], votes=r["votes"],
                                election="Municipal council and nagar panchayat general election 2025-26 (direct election of the president)",
                                sec_sr=r["sr"], last_updated=made, src_pos=pos))
    return recs


# Nashik list spellings -> LGD local body code (the list writes "Trambak", "Devla", "Kalvan", "Yeola"; LGD "Trimbak", "Deola" ...)
OFFICE_LGD = {"manmad": "251440", "yeola": "251450", "nandgaon": "251439", "satana": "251435", "igatpuri": "251445",
              "bhagur": "251444", "trambak": "251441", "trimbak": "251441", "chandwad": "276281", "sinnar": "251447",
              "dindori": "276276", "kalvan": "276278", "niphad": "276279", "devla": "276277", "peth": "276280", "surgana": "251434"}
ENTRY = re.compile(r"([A-Z][A-Za-z.\- ]+?)\s+(Municipal\s+Council|Nagar\s+Panchayat)\s+(?:Phone\s*No\.?|Telephone\s*number)\s*:?\s*"
                   r"([\d\-/ ]+?)\s+E-?\s*mail\s*:?\s*(\S+)")


def parse_office_list(html, district, body_type, url, state="MH", module=MODULE):
    soup = _esw.soup(html)
    main = soup.find(id="wpb-content-root") or soup.find("main") or soup      # the S3WaaS page body (WPBakery root)
    text = _esw.clean(main.get_text(" "))
    recs, seen = [], set()
    for k, m in enumerate(ENTRY.finditer(text), 1):
        body = re.sub(r"^(Municipal\s+Council|Nagar\s+Panchayat)\s+", "", m.group(1).strip())
        email = _esw.emails(m.group(4))
        extra = {"mailbox": "chief officer"} if re.match(r"(?i)co[._]?[a-z]", email or "") else {}
        recs.append(_ulb.record(module, state, body, "Office", seen, phone=m.group(3), email=email, district=district,
                                body_type=_esw.clean(m.group(2)), source=url, lgd_code=OFFICE_LGD.get(body.lower()),
                                src_pos={"selector": "page text", "match": k, "line_text": m.group(0)}, method=METHOD_HTML, **extra))
    return recs


CHARGE = re.compile(r"(?:(Shri|Smt|Ms|Kum|Dr)\.?\s+)([A-Z][^,]{2,60}?),\s*(.{2,120}?)\s+shall\s+(?:also\s+)?hold\s+the\s+charge\s+of\s+"
                    r"(?:the\s+post\s+of\s+)?Chief\s+Officer,?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+Municipal\s+Council")


def parse_order(text, district, url, state="GA", module="ulb2_ga"):
    t = _esw.clean(text)
    d = re.search(r"Dated\s*:?\s*(\d{1,2})\s*[/.\- ]\s*(\d{1,2})\s*[/.\- ]\s*(\d{4})", t)
    date = f"{d.group(3)}-{int(d.group(2)):02d}-{int(d.group(1)):02d}" if d else None
    recs, seen = [], set()
    for k, m in enumerate(CHARGE.finditer(t), 1):
        title = m.group(1) + "." if m.group(1) in ("Smt", "Dr", "Ms") else m.group(1)
        recs.append(_ulb.record(module, state, m.group(4), "Chief Officer", seen, name=f"{title} {m.group(2)}", district=district,
                                body_type="Municipal Council", source=url, own_post=_esw.clean(m.group(3)), charge="additional charge",
                                last_updated=date, src_pos={"selector": "pdf plain text", "match": k, "line_text": m.group(0)},
                                method=METHOD))
    return recs


def parse_office_page(html, district, url, state="DD", module="ulb2_dd"):
    text = _esw.clean(_esw.soup(html).get_text(" "))
    m = re.search(r"Name\s*:\s*(.+?)\s+Phone\s*:\s*([\d\- ,/]+?)\s+Address\s*:\s*(.+?)\s+Email\s*:\s*(\S+)", text)
    if not m:
        return []
    up = re.search(r"Last\s*Updated\s*:?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    body = re.sub(r"\s+Municipal\s+Council$", "", m.group(1).strip())
    return [_ulb.record(module, state, body, "Office", set(), phone=m.group(2), email=m.group(4), district=district,
                        body_type="Municipal Council", source=url, address=m.group(3),
                        src_pos={"selector": "page text", "match": 1, "line_text": m.group(0)}, method=METHOD_HTML,
                        last_updated=f"{up.group(3)}-{int(up.group(2)):02d}-{int(up.group(1)):02d}" if up else None)]


def fetch(p, get, module=MODULE):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    kind = p["kind"]
    name = _esw.slug(re.sub(r"(?i)\.pdf$", "", p["url"].rstrip("/").split("/")[-1].replace("%20", " ")))[:60] or kind
    if kind in ("sec_president", "charge_order"):
        files = [_esw.keep(module, name, r.content, "pdf")]
        if r.content[:5] != b"%PDF-":
            return [], files, "not a PDF"
        if kind == "sec_president":
            recs = parse_sec(r.content, p["url"])
        else:
            recs = parse_order(plain_text(r.content)[0], p.get("district"), p["url"], p["state"], module)
    else:
        files = [_esw.keep(module, name, r.content)]
        if kind == "office_list":
            recs = parse_office_list(r.text, p.get("district"), p.get("body_type"), p["url"], p["state"], module)
        else:
            recs = parse_office_page(r.text, p.get("district"), p["url"], p["state"], module)
    return recs, files, "" if recs else "no rows"
