"""Maharashtra: district collectorate pages on the municipal councils and nagar panchayats of one district (S3WAAS / NIC sites).

The Directorate of Municipal Administration (mahadma.maharashtra.gov.in) publishes no list of chief officers: its "list-of-councils"
(8 pages of 50) gives division, district, name, class, year, population and area only, and "details-of-urban-local-bodies-in-maharashtra"
is a population / area dashboard (checked live 2026-11-11). So this module reads the district pages that name the officers. One queue
item per page; the payload gives the district ("district") and the page format ("kind"):
- kind "table": a table with a column for the body and a column for the chief officer's name (Marathi or English headings).
  Chandrapur (chanda.nic.in "Nagar Palika Department", Marathi, 18 bodies: chief officer name, fire officer name + post + mobile, office
  email; page date not shown) and Pune (pune.gov.in "Nagarpalika Branch", English, 18 councils: chief officer name, mobile, email; the
  page has four other tables without officers). The office email goes on the chief officer's record.
- kind "cards": a public-utility card list ("Municipal Council, Dahiwadi" / "Chief Officer, Dahiwadi" / "Phone : 02165-220945").
  Satara (www.satara.gov.in, 2 pages, 16 councils, "Last Updated: 06.11.2026"): the card names the post, not the person, so the
  record has the post and the office phone and no name. A card whose lines do not name a chief officer gives no record.
Records: "Chief Officer" (role head) per body; "Fire Department Head" (role staff; the page's "अग्निशमन विभाग प्रमुख", often an
engineer or office superintendent who holds the charge: own designation in "designation") where the table gives one. area = the body name as the
page writes it (Chandrapur writes it in Devanagari only: "बल्लारपुर"; such records also carry area_latin = "ballarpur", a plain
transliteration, and take their ids from it). The pages answer from outside India (archive.s1d.me copies of
2026-11-05/06/10 used for the samples).
"""
import re

from dforms import _esw, _ulb
import provenance

METHOD = "html table"     # kind "cards" (Satara): "html cards (S3WaaS public utility)" on each record
METHOD_CARDS = "html cards (S3WaaS public utility)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_mh"
PAGES = (
    ("chandrapur", "table", "Chandrapur", "https://chanda.nic.in/en/nagar-palika-department/"),
    ("pune", "table", "Pune", "https://pune.gov.in/en/nagarpalika-branch/"),
    ("satara-1", "cards", "Satara", "https://www.satara.gov.in/en/public-utility-category/muincipal-councils/"),
    ("satara-2", "cards", "Satara", "https://www.satara.gov.in/en/public-utility-category/muincipal-councils/page/2/"),
)
FIRE = r"(अग्निशमन|fire)"
COLS = (  # (key, heading regex, heading must not match); first key that fits a heading wins
    ("fire_phone", FIRE + r".*(भ्रमणध्वनी|mobile|phone|contact)", None),
    ("fire_name", FIRE, None),
    ("co_name", r"(मुख्याधिकारी|chief\s*officer)", r"(फोटो|photo)"),
    ("phone", r"(भ्रमणध्वनी|mobile|phone|contact)", None),
    ("email", r"(e-?\s*mail|ई\s*-?\s*मेल)", None),
    ("body_type", r"(प्रकार|\btype\b)", None),
    ("body_class", r"(वर्ग|\bclass\b)", None),
    ("body", r"(नगर\s*परिषद|नगरपरिषद|नगर\s*पंचायत|नगरपंचायत|municipal\s*council|nagar\s*panchayat|\bname\b)", r"(website|link|नियंत्रण)"),
)


# Devanagari -> Latin, plain (no diacritics), for record ids and area_latin: "बल्लारपुर" -> "ballarpur", "घुग्घुस" -> "ghugghus"
_C = dict(zip("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ", "k kh g gh n ch chh j jh n t th d dh n t th d dh n p ph b bh m y r l v sh sh s h l".split()))
_V = dict(zip("अआइईउऊऋएऐओऔऍऑ", "a aa i i u u ri e ai o au e o".split()))
_M = dict(zip("ािीुूृेैोौॅॉ", "aa i i u u ri e ai o au e o".split()))


def latin(s):
    out, i, s = [], 0, s or ""
    while i < len(s):
        ch = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if ch in _C:
            out.append(_C[ch])
            if nxt == "्":
                i += 1
            elif nxt in _M:
                out.append(_M[nxt])
                i += 1
            elif nxt and (nxt in _C or nxt in "ंँ"):
                out.append("a")
            elif nxt and not nxt.isspace() and nxt not in "ःऽ़" and not re.match(r"[\W\d]", nxt):
                out.append("a")
        elif ch in _V:
            out.append(_V[ch])
        elif ch in "ंँ":
            out.append("n")
        elif ch in "ः़ऽ":
            pass
        else:
            out.append(ch)
        i += 1
    return re.sub(r"\s+", " ", "".join(out)).strip()


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "kind": kind, "district": dist, "url": url, "state": "MH",
                                                  "india_only": False}} for k, kind, dist, url in PAGES]


DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def blank(s):
    s = _esw.clean(s).strip(" |")
    return "" if re.fullmatch(r"[-–.\s|]*", s) else s


def columns(head):
    out = {}
    for i, h in enumerate(head):
        h = _esw.clean(h).lower()
        for k, rx, no in COLS:
            if k not in out and re.search(rx, h) and not (no and re.search(no, h)):
                out[k] = i
                break
    return out


def updated(html):
    m = re.search(r"Last\s*Updated\s*:?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", _esw.clean(_esw.soup(html).get_text(" ")))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


HON = r"(?:श्रीमती|श्री|कु|सौ|shri|smt|mr|mrs|ms)\.?\s*"


def person(cell):
    """Name and own designation from one cell: 'श्री. शुभम रत्नपारखी | अग्निशमन अधिकारी', 'श्री. मनोज आंबोरकर, बांधकाम अभियंता',
    'श्री. निखिल कारेकार स्थापत्य अभियंता' (no mark: honorific + two words are the name, the rest the designation)."""
    s = blank(cell)
    if not s:
        return "", ""
    parts = [blank(x) for x in re.split(r"\s*[|,]\s*", s) if blank(x)]
    if len(parts) > 1:
        return parts[0], " ".join(parts[1:])
    m = re.match(rf"((?:{HON})?\S+(?:\s+\S+)?)\s+(.+)$", s, re.I)
    return (blank(m.group(1)), blank(m.group(2))) if m else (s, "")


def parse_table(html, url, district):
    recs, seen = [], set()
    up = updated(html)
    for t in _esw.soup(html).find_all("table"):
        tp = []
        rows = _esw.grid(t, pos=tp)
        if not rows:
            continue
        col = columns(rows[0])
        if "co_name" not in col or "body" not in col:
            continue
        for row, pos in zip(rows[1:], tp[1:]):
            c = {k: (row[i] if i < len(row) else "") for k, i in col.items()}
            body = blank(c["body"]).replace(" | ", " ").replace("|", " ")
            if not body or re.fullmatch(r"[\d\s.]+", body):
                provenance.skip_row(row, 'skip: not body or re.fullmatch(r"[\\d\\s.]+", body)')
                continue
            extra = {k: blank(c[k]) for k in ("body_class",) if blank(c.get(k, ""))}
            btype = blank(c.get("body_type", "")) or None
            name, phone, email = blank(c["co_name"]), blank(c.get("phone", "")).translate(DIGITS), blank(c.get("email", ""))
            if name or phone or email:
                recs.append(_ulb.record(MODULE, "MH", body, "Chief Officer", seen, name=name, phone=phone, email=email, district=district,
                                        body_type=btype, source=url, last_updated=up, src_pos=pos, **extra))
            fname, fdesig = person(c.get("fire_name", ""))
            fphone = blank(c.get("fire_phone", "")).translate(DIGITS)
            if fname or fphone:                       # the head of the fire wing; often another officer holds it (designation)
                recs.append(_ulb.record(MODULE, "MH", body, "Fire Department Head", seen, name=fname, phone=fphone, district=district,
                                        body_type=btype, source=url, last_updated=up, designation=fdesig or None, src_pos=pos))
    return recs


CO = re.compile(r"(?i)^(?:chief\s*officer|c\.?\s?o\.?)\b[\s,.:-]*")


def parse_cards(html, url, district):
    recs, seen = [], set()
    up = updated(html)
    for k, card in enumerate(_esw.soup(html).select("li.public-utlty-catg"), 1):
        body = blank(card.h2.get_text(" ")) if card.h2 else ""
        lines = [blank(li.get_text(" ")) for li in card.select("ul.pubutility-list > li")]
        post = next((ln for ln in lines if CO.match(ln)), "")
        if not body or not post:
            continue
        phone = " ".join(re.sub(r"(?i)^phone\s*:?", "", ln) for ln in lines if re.match(r"(?i)phone", ln))
        email = " ".join(re.sub(r"(?i)^e-?mail\s*:?", "", ln) for ln in lines if re.match(r"(?i)e-?mail", ln))
        if not (phone or email):
            continue
        recs.append(_ulb.record(MODULE, "MH", body, "Chief Officer", seen, phone=phone, email=email, district=district, source=url,
                                last_updated=up, post_as_written=post, src_pos={"selector": "li.public-utlty-catg", "card": k},
                                method=METHOD_CARDS))
    return recs


def latin_ids(recs, district):
    """Record ids and office ids from the Latin form when the body or post is in Devanagari (_esw.slug keeps a-z0-9 only), and
    area_latin for the tie to civic.ulb (sql/86 compares Latin names)."""
    out, seen = [], set()
    from dforms._water import unique
    for rid, d in recs:
        if re.search(r"[\u0900-\u097f]", d.get("area", "") + d.get("post", "")):
            body, post = latin(d["area"]), latin(d["post"])
            d = dict(d, office_id=f"MH-ULB-{_esw.slug(district or '')}-{_esw.slug(body)}")
            if body != d["area"]:
                d["area_latin"] = body
            rid = f"dept:{MODULE}:" + unique(f"MH-{_esw.slug(district or '')}-{_esw.slug(body)}-{_esw.slug(post) or 'office'}", seen)
        else:
            seen.add(rid.split(":", 2)[2])
        out.append((rid, d))
    return out


def parse(html, kind, url, district):
    return latin_ids((parse_cards if kind == "cards" else parse_table)(html, url, district), district)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    name = re.sub(r"[^a-z0-9]+", "-", re.sub(r"^https?://", "", p["url"]).lower()).strip("-")[:80]
    files = [_esw.keep(MODULE, name, r.content)]
    recs = parse(r.text, p.get("kind", "table"), p["url"], p.get("district"))
    return recs, files, "" if recs else "no rows"
