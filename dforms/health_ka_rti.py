"""Karnataka: health officers of the whole state from the RTI list of the Health & Family Welfare Department (Commissionerate,
hfwcom.karnataka.gov.in): "Public Information Officers, Nodal Officers and First Appellate Authorities Information Under RTI ACT
2005 of Health and Family Welfare Department, Karnataka". The home page links it as "PIOs, FAAs & RTI Nodal Officers Details"
(uploads/<Kannada file name>__1794050934.pdf, 13.6 MB, 217 pages, text layer, Pdftools SDK; measured 2026-11-12 from Mumbai).

Pages 1-15: Commissionerate, directorates, NHM, engineering unit, district hospitals and training centres. Page 16 onwards:
"DISTRICTWISE PIO, Nodal Officer and FAA INFORMATION", one block per district under a centred heading ("BANGALORE URBAN
DISTRICT", "KARWAR, UTTARA KANNADA DISTRICT"; Mandya and Belagavi have no heading of their own). Each row: Sl. No. | PIO name,
designation and office (PHC / CHC / taluk hospital medical officers, THO, DHO office staff) | phone | e-mail | Nodal Officer
(mostly the District Family Welfare Officer) | phone | e-mail | First Appellate Authority (THO, DHO, district surgeon) | phone |
e-mail. Cells wrap over several lines and rows are centred vertically, so lines above the serial number belong to its row.

Reading (pdftotext -layout, else pypdf layout): the page header gives the x of "Nodal" and of "First Appellate"; a text piece left
of the Nodal column belongs to the PIO, then the Nodal Officer, then the FAA. A line belongs to the row of the nearest serial
number (a tie goes to the next row; a blank line ends a row). E-mails cut by the column ("phcguillalu@gmail.co" + "m") are
joined. The person name is the leading part of a cell when it starts with a title (Dr / Mr / Mrs / Smt / Sri) or when the first
comma piece names no post.

Records (depts.py contract, dept health): one per row for the PIO (id dept:health_ka_rti:p<page>-<serial>), one per distinct
Nodal Officer and FAA (id dept:health_ka_rti:<nodal|faa>:<district>:<slug of name and post>). level: district (DHO, DFWO,
RCHO, DSO, DTO, DVBDCO, district surgeon, district hospital), subdistrict (Taluk Health Officer, taluk hospital), facility
(PHC / CHC / UPHC medical officer), state (pages before the district part). post keeps the whole cell text without the name
(it carries the office and place); rti_role says which column the person stands in. src_pos = page + line of the serial number
(+ the row's first and last line).
"""
import re

import provenance
from dforms import _esw, _field

METHOD = "pdf text (pdftotext -layout, else pypdf layout): rows by serial number, columns by the x of the header words"

MODULE = "health_ka_rti"
HOME = "https://hfwcom.karnataka.gov.in/en"
URL = ("https://hfwcom.karnataka.gov.in/uploads/%E0%B2%86%E0%B2%B0%E0%B3%8D_%E0%B2%9F%E0%B2%BF%E0%B2%90%20%E0%B2%95%E0%B2%BE%E0%B2%AF"
       "%E0%B3%8D%E0%B2%A6%E0%B3%86%202005%E0%B2%B0%E0%B2%A1%E0%B2%BF%20%E0%B2%A8%E0%B3%87%E0%B2%AE%E0%B2%BF%E0%B2%B8%E0%B2%BF%E0%B2"
       "%B0%E0%B3%81%E0%B2%B5%20PIO,%20FAA%20&%20RTI%20%E0%B2%A8%E0%B3%8B%E0%B2%A1%E0%B2%B2%E0%B3%8D_%20%E0%B2%85%E0%B2%A7%E0%B2%BF"
       "%E0%B2%95%E0%B2%BE%E0%B2%B0%E0%B2%BF%E0%B2%97%E0%B2%B3%20%E0%B2%B5%E0%B2%BF%E0%B2%B5%E0%B2%B0%E0%B2%97%E0%B2%B3__1794050934.pdf")
LINK = re.compile(r"(?i)PIOs?,\s*FAAs?\s*&(?:amp;)?\s*RTI")

# LGD district names of Karnataka (2024) and the spellings the list uses
DISTRICTS = {
    "bagalkot": "Bagalkote", "bagalkote": "Bagalkote", "ballari": "Ballari", "bellary": "Ballari", "belagavi": "Belagavi",
    "belgaum": "Belagavi", "bengaluru rural": "Bengaluru Rural", "bangalore rural": "Bengaluru Rural",
    "bengaluru urban": "Bengaluru Urban", "bangalore urban": "Bengaluru Urban", "bidar": "Bidar",
    "chamarajanagara": "Chamarajanagar", "chamarajanagar": "Chamarajanagar", "chamarajnagara": "Chamarajanagar",
    "chikkaballapur": "Chikkaballapura", "chikkaballapura": "Chikkaballapura", "chikmagaluru": "Chikkamagaluru",
    "chikkamagaluru": "Chikkamagaluru", "chikkmagalur": "Chikkamagaluru", "chitradurga": "Chitradurga",
    "dakshina kannada": "Dakshina Kannada", "davanagere": "Davanagere", "davangere": "Davanagere", "dharwad": "Dharwad",
    "gadag": "Gadag", "hassan": "Hassan", "haveri": "Haveri", "kalaburagi": "Kalaburagi", "kalburgi": "Kalaburagi",
    "gulbarga": "Kalaburagi", "kodagu": "Kodagu", "kolar": "Kolar", "koppal": "Koppal", "mandya": "Mandya", "mysuru": "Mysuru",
    "mysore": "Mysuru", "raichur": "Raichur", "ramanagara": "Bengaluru South", "ramanagaram": "Bengaluru South",
    "bangalore sourth": "Bengaluru South", "shivamogga": "Shivamogga", "shimoga": "Shivamogga", "tumakuru": "Tumakuru",
    "tumkuru": "Tumakuru", "tumkur": "Tumakuru", "udupi": "Udupi", "uttara kannada": "Uttara Kannada", "karwar": "Uttara Kannada",
    "vijayapura": "Vijayapura", "vijayapur": "Vijayapura", "bijapur": "Vijayapura", "vijayanagara": "Vijayanagara",
    "yadgir": "Yadgir", "yadagiri": "Yadgir",
}
_DRX = re.compile(r"(?i)\b(" + "|".join(sorted((re.escape(k) for k in DISTRICTS), key=len, reverse=True)) + r")\b")
SERIAL = re.compile(r"^(\s{0,6})(\d{1,3})(?=\s+\S|\s*$)")
HEAD = re.compile(r"(?i)telephone|e-?mail address|phone number|designation (and|&) office|public information officer|"
                  r"^\s*(sl\.?|no\.?|s\.?\s*no)\b|appellate authority|nodal officer\s*$")
FRAG = re.compile(r"(?i)\.?(m|om|com|in|co|il\.com|ail\.com|mail\.com|\.co\.in|gov\.in|nic\.in)")    # e-mail tails left over
EMAIL_END = re.compile(r"(?i)\.(com|in|org|net|edu)$")
TITLE = re.compile(r"(?i)^(dr|mr|mrs|ms|smt|sri|shri|kum|miss)\b\.?\s*")
POSTWORD = re.compile(r"(?i)officer|director|health|medical|superintendent|surgeon|\bc?a\.?a?\.?o\b|\bdd\b|\bjd\b|manager|engineer|"
                      r"assistant|clerk|\b(tho|dho|rcho|dso|dto|amo|mo|pho|rmo|smo|dfwo|dvbdco)\b|centre|center|hospital|\b[cpu]?phc\b|"
                      r"\bchc\b|office|floor|soudha|district|taluk|in-?charge|i/c|superintendent|section|branch|accounts|programme")
DISTRICT_POST = re.compile(r"(?i)district|\b(dho|dfwo|rcho|dso|dto|dvbdco|dlo|dmo)\b|zilla")
TALUK_POST = re.compile(r"(?i)taluk|thaluk|\btho\b|\bthq\b|general hospital")
FACILITY_POST = re.compile(r"(?i)\b[cu]?phc\b|\bchc\b|primary health|community health|health cent|dispensar|\bnamma clinic")


def chunks(line):
    """[(x, text)] pieces of a layout line split at 2+ spaces."""
    return [(m.start(), m.group()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def district_of(text):
    """LGD district named in a text (longest spelling first), or None."""
    m = _DRX.search(text or "")
    return DISTRICTS[m.group(1).lower()] if m else None


def heading(line):
    """A centred district heading ("BANGALORE URBAN DISTRICT", "MYSURU DIVISION-CHAMARAJNAGARA DISTRICT") -> LGD name."""
    s = line.strip()
    if len(line) - len(line.lstrip()) < 20 or len(chunks(line)) != 1 or not re.search(r"DISTRICT\b", s) or s != s.upper():
        return None
    return district_of(s.replace("CHAMARAJNAGARA", "CHAMARAJANAGARA")) or None


def split_name(text):
    """(name, post) of one cell: the name is the leading part when it starts with a title or names no post."""
    t = _esw.clean(text).strip(" ,")
    if not t:
        return "", ""
    parts = [p.strip() for p in re.split(r"\s*,\s*", t)]
    if TITLE.match(t):
        first = parts[0]
        m = POSTWORD.search(first[3:])           # "Dr.Shivaswamy.M.R General Duty medical Officer": cut where the post starts
        if m and len(parts) == 1:
            k = 3 + m.start()
            gm = re.search(r"(?i)\b(general|administrative|senior|junior|chief|assistant|deputy|joint|taluk[a]?|district)\s*$", first[:k])
            k = gm.start() if gm else k
            return first[:k].strip(" ,-"), first[k:].strip(" ,-")
        if m and len(parts) > 1 and not POSTWORD.search(" ".join(first.split()[:3])):
            k = 3 + m.start()
            gm = re.search(r"(?i)\b(general|administrative|senior|junior|chief|assistant|deputy|joint|taluk[a]?|district)\s*$", first[:k])
            k = gm.start() if gm else k
            if k > 4 and first[k:].strip():
                return first[:k].strip(" ,-"), (first[k:] + ", " + ", ".join(parts[1:])).strip(" ,-")
        return first.strip(" -"), ", ".join(parts[1:]).strip(" ,-")
    if len(parts) > 1 and not POSTWORD.search(parts[0]) and len(parts[0].split()) <= 4 and POSTWORD.search(", ".join(parts[1:])):
        return parts[0], ", ".join(parts[1:])
    return "", t


def words(line):
    """[(x, word)] of a layout line."""
    return [(m.start(), m.group()) for m in re.finditer(r"\S+", line)]


def join_mails(rows):
    """rows: {line no: [(x, word)]}. E-mail addresses cut by the column width continue on the next line, under the first part
    (left-aligned or centred: "phcguillalu@gmail.co" + "m"): join them and drop the fragment. Returns {line no: [(x, word)]}."""
    rows = {k: list(v) for k, v in rows.items()}
    for ln in sorted(rows):
        for idx, (x, w) in enumerate(rows[ln]):
            if "@" not in w:
                continue
            mail, cur = w, ln
            while not EMAIL_END.search(mail):
                hit = None
                for step in (1, 2):                  # the next line, or the one after when a row's serial line is between
                    nl = rows.get(cur + step) or []
                    k = next((k for k, (x2, w2) in enumerate(nl) if x - 3 <= x2 and x2 + len(w2) <= x + len(w) + 3
                              and "@" not in w2 and re.fullmatch(r"[\w.\-]{1,30}", w2) and not re.fullmatch(r"\d{5,}", w2)), None)
                    if k is not None:
                        hit = (cur + step, k)
                        break
                if hit is None:
                    break
                mail += rows[hit[0]][hit[1]][1]
                rows[hit[0]][hit[1]] = (rows[hit[0]][hit[1]][0], "")
                cur = hit[0]
            rows[ln][idx] = (x, mail)
    return {k: [(x, w) for x, w in v if w] for k, v in rows.items()}


def zone_of(x, w, tels):
    """Column group of one word: tels = x of the three phone columns (PIO, Nodal, FAA)."""
    t1, t2, t3 = tels
    if "@" in w:                                     # e-mail columns sit right of their phone column
        return "pio" if x < t2 - 3 else "nodal" if x < t3 - 3 else "faa"
    if re.fullmatch(r"[\d()+/,\-]+", w) and sum(ch.isdigit() for ch in w) >= 2:
        return min(zip((abs(x - t) for t in tels), ("pio", "nodal", "faa")))[1]
    return "pio" if x < t1 - 3 else "nodal" if x < t2 - 3 else "faa"


def fix_mail(m):
    """A web-mail address whose last letters the print cut off ("dhochitradurga@gmail.co", "thomaddur@gmail.") -> the full
    address; other addresses as printed."""
    m = m.rstrip(".")
    mm = re.fullmatch(r"(.+@)(gmail|yahoo|rediffmail|hotmail)(\.c|\.co|\.)?", m, re.I)
    return f"{mm.group(1)}{mm.group(2)}.com" if mm else m


def _fields(ws):
    """[(line, x, word)] of one column group -> (text, phones, emails, phone text as printed)."""
    ws = sorted(ws)
    mails = [w for _, _, w in ws if "@" in w]
    nums = [w for _, _, w in ws if "@" not in w and re.fullmatch(r"[\d()+/,\-]+", w) and sum(ch.isdigit() for ch in w) >= 2]
    text = " ".join(w for _, _, w in ws if "@" not in w and w not in nums)
    raw = " ".join(nums)
    return (text, _esw.phones(" , ".join(re.sub(r"/0$", "", n) for n in nums)), _esw.emails(" ".join(fix_mail(m) for m in mails)),
            raw, " ".join(mails))


def parse(text, url=URL):
    """Layout text (pages split by form feeds) -> records."""
    recs, seen = [], set()
    tels, district = (37, 105, 176), None
    for pno, page in enumerate(text.split("\f"), 1):
        lines = [re.sub(r"\s{3,}Page \d+\s*$", "", ln) if re.search(r"\s{3,}Page \d+\s*$", ln) else ln for ln in page.split("\n")]
        kinds = []                                  # per line: "head", "blank", "district", "serial", "text"
        serials = []
        for i, ln in enumerate(lines):
            if not ln.strip():
                kinds.append("blank")
                continue
            ph = [m.start() for m in re.finditer(r"(?i)telephone|phone", ln)]
            if len(ph) == 3 and not re.search(r"\d{5,}|@", ln):
                tels = tuple(ph)
            if HEAD.search(ln) and not re.search(r"\d{6,}|@", ln):
                kinds.append("head")
                continue
            h = heading(ln)
            if h:
                kinds.append(("district", h))
                continue
            if re.search(r"(?i)^\s*(information of|districtwise|public information officers, nodal)", ln) and not re.search(r"\d{6,}", ln):
                kinds.append("head")
                continue
            m = SERIAL.match(ln)
            if m and len(m.group(1)) + len(m.group(2)) < tels[0] - 10:
                kinds.append("serial")
                serials.append(i)
            else:
                kinds.append("text")
        # each text line goes to the nearest serial line in its blank / heading separated stretch
        owner = {}
        for i, k in enumerate(kinds):
            if k != "text":
                continue
            prev = next((j for j in range(i - 1, -1, -1) if kinds[j] != "text"), None)
            nxt = next((j for j in range(i + 1, len(kinds)) if kinds[j] != "text"), None)
            a = prev if prev is not None and kinds[prev] == "serial" else None
            b = nxt if nxt is not None and kinds[nxt] == "serial" else None
            if a is None and b is None:
                continue
            if a is None or b is None:
                owner[i] = a if b is None else b
            elif (b - i) != (i - a):
                owner[i] = b if (b - i) < (i - a) else a
            else:                                     # half way: a cell starts with the person's name, so a name line opens the next row
                owner[i] = b if TITLE.match(lines[i].strip()) else a
        pw = join_mails({i: words(ln) for i, ln in enumerate(lines) if kinds[i] in ("text", "serial")})
        dist_at = {}
        cur = district
        for i, k in enumerate(kinds):
            if isinstance(k, tuple):
                cur = k[1]
            dist_at[i] = cur
        district = cur
        for s in serials:
            rows = sorted([s] + [i for i, o in owner.items() if o == s])
            zones = {"pio": [], "nodal": [], "faa": []}
            serial = SERIAL.match(lines[s]).group(2)
            for i in rows:
                for x, w in pw.get(i, []):
                    if i == s and x < len(SERIAL.match(lines[s]).group(0)) and w == serial:
                        continue
                    if FRAG.fullmatch(w):
                        continue
                    zones[zone_of(x, w, tels)].append((i, x, w))
            fields = {z: _fields(p) for z, p in zones.items()}
            alltext = " ".join(f[0] for f in fields.values())
            row_d = dist_at.get(s)
            named = district_of(fields["pio"][0]) or district_of(fields["faa"][0]) or district_of(fields["nodal"][0])
            if row_d is None or (named and named != row_d and not any(re.search(r"\b" + re.escape(k) + r"\b", alltext, re.I)
                                                                       for k, v in DISTRICTS.items() if v == row_d)):
                row_d = named if pno >= 16 else (named or None)
            pos = provenance.line_pos(pno, s + 1, lines[s], first_line=rows[0] + 1, last_line=rows[-1] + 1, serial=serial)
            for role, (txt, phone, email, raw_ph, raw_mail) in fields.items():
                name, post = split_name(txt)
                if not (name or post) and not (phone or email):
                    continue
                if role == "pio":
                    key = f"p{pno}-{serial}"
                else:
                    key = f"{role}:{_esw.slug(row_d or 'state')}:{_esw.slug(name + ' ' + post)[:80] or _esw.slug(phone)}"
                    if key in seen:
                        continue
                if key in seen:
                    key += f"-{s + 1}"
                seen.add(key)
                if pno < 16 and not DISTRICT_POST.search(post or ""):
                    level = "state"
                elif FACILITY_POST.search(post or ""):
                    level = "facility"
                elif TALUK_POST.search(post or ""):
                    level = "subdistrict"
                elif DISTRICT_POST.search(post or "") or pno >= 16:
                    level = "district"
                else:
                    level = "state"
                if level == "state" and row_d and pno >= 16:
                    level = "district"
                recs.append(_esw.record(
                    MODULE, key, dept="health", level=level, area=(post or name)[:200], post=post or None, name=name or None,
                    phone=phone or None, email=email or None, state="KA", district=row_d if (row_d and level != "state") else None,
                    rti_role={"pio": "Public Information Officer", "nodal": "Nodal Officer", "faa": "First Appellate Authority"}[role],
                    cell_text=txt or None, phone_text=raw_ph or None,
                    email_text=raw_mail if raw_mail and raw_mail.lower() != (email or "") else None, source=url, src_url=url, src_pos=pos,
                    list_title="PIOs, Nodal Officers and First Appellate Authorities under the RTI Act 2005, Health and Family "
                               "Welfare Department, Karnataka"))
    return recs


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "home": HOME, "discover": True, "state": "KA", "india_only": True,
                                        "route": "proxy", "expected": 3700}}]


def current_url(get):
    """The newest list linked from the home page (the file name changes with each upload), or None."""
    r = get(HOME)
    if r is None:
        return None
    m = re.search(r"""href=["']([^"']+\.pdf)["'][^>]*>\s*(?:<[^>]+>\s*)*[^<]*?PIOs?,\s*FAAs?""", r.text or "", re.I)
    if not m:
        return None
    u = m.group(1)
    return u if u.startswith("http") else "https://hfwcom.karnataka.gov.in/" + u.lstrip("/")


def stored(p, get):
    """(bytes, key) of the PDF from the bucket when the payload names a saved copy ("stored": "<project>/<path>.pdf")."""
    hub, k = getattr(get, "hub", None), p.get("stored")
    if not hub or not k:
        return None
    try:
        import requests
        u = hub.read_urls(k.split("/", 1)[0], [k])[k]
        r = requests.get(u, timeout=(20, 300))
        if r.status_code == 200 and r.content[:5] == b"%PDF-":
            return r.content, k
    except Exception:  # noqa: BLE001 - fall back to the site
        pass
    return None


def fetch(p, get):
    url = p.get("url") or URL
    got = stored(p, get)
    content, key, files = (got[0], got[1], []) if got else (None, None, [])
    if content is None:
        if p.get("discover"):
            url = current_url(get) or url
        r = get(url)
        if r is None:
            return [], [], "no answer"
        content = r.content
        if content[:5] != b"%PDF-":
            return [], [], "not a pdf"
        files = [(f"depts/{MODULE}/rti-pio-faa-list.pdf", content, "application/pdf")]
    text, engine = _field.pdf_text_engine(content)
    recs = parse(text, url)
    src = {"src": provenance.file_src(content, url, key)} if key else {}
    for _, d in recs:
        d["method"] = f"pdf text ({engine}): rows by serial number, columns by the x of the header words"
        d.update(src)
    return recs, files, "" if recs else "no rows"
