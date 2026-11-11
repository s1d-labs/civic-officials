"""Shared parts of the councillor contact readers (cforms/cp_<xx>.py): phones, emails and addresses of ward members from
the councils' own sites ("Councillors", "Corporators", "Elected members", "Council" pages).

These readers do not add members. Each record names one member that civic.councillor already holds (from the State
Election Commission readers) and adds the contact fields; civic-india/sql/72_councillor_contacts.sql copies them onto that
member by body + ward (+ name similarity).

Record: type "councillor_contact" (not "councillor": sql/70 would read a "councillor" record as one more member, and its
"one source host per body" rule would then drop the SEC rows of that body). Fields:
  state, body (the body name exactly as the SEC record gives it, so sql/72 can join on it), lgd_code (when known),
  ward_no (digits only, or None), ward_label (the cell as the page gives it), name, phone, email, address, position,
  record_for (the record id of the same member in the SEC reader, when the ward number gives it), url, source (host).
Record id: cp:<state>:<body slug>:<ward no> (sl-<n> when the page has no ward number; -2, -3 for a second row of a ward).
Phones are published as the page gives them (no masking); only empty placeholders ("00 00", ".", "N/A") are dropped.
"""
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

DIGITS = str.maketrans("०१२३४५६७८९০১২৩৪৫৬৭৮৯੦੧੨੩੪੫੬੭੮੯૦૧૨૩૪૫૬૭૮૯୦୧୨୩୪୫୬୭୮୯௦௧௨௩௪௫௬௭௮௯౦౧౨౩౪౫౬౭౮౯೦೧೨೩೪೫೬೭೮೯൦൧൨൩൪൫൬൭൮൯",
                       "0123456789" * 9)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# a run of digits with the separators a phone number uses; checked one by one in phones()
PHONE_RUN = re.compile(r"(?:\+?91[\s-]*)?(?:\(?0\d{2,4}\)?[\s-]*)?\d[\d\s-]{5,}\d")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def clean(s):
    return " ".join(str(s or "").split()) or None


def phones(s):
    """Phone numbers in a cell, as 10-digit mobiles or 0-prefixed landlines with the STD code, joined with ", ".
    Placeholders and numbers that are too short (no STD code) give None."""
    out = []
    for run in PHONE_RUN.findall((s or "").translate(DIGITS)):
        parts = []
        for part in re.split(r"\s*[,/;]\s*|\s{2,}", run):
            d = re.sub(r"\D", "", part)
            # two or more mobiles with one space between them ("9988755533 7889267809", a <br> on the page)
            chunks = [d[i:i + 10] for i in range(0, len(d), 10)]
            if len(d) > 12 and len(d) % 10 == 0 and all(c[0] in "6789" for c in chunks):
                parts += chunks
            else:
                parts.append(d)
        for d in parts:
            if d.startswith("91") and len(d) == 12:
                d = d[2:]
            if d.startswith("0") and len(d) == 11 and d[1] in "6789" and not out:
                d = d[1:]                                        # 09xxxxxxxxx: a mobile with a trunk 0
            if (len(d) == 10 and d[0] in "6789") or (len(d) in (10, 11) and d[0] == "0" and d[1] != "0"):
                if len(set(d.lstrip("0"))) > 2 and d not in out:  # 0000000000, 9999999999: placeholders
                    out.append(d)
    return ", ".join(out) or None


def emails(s):
    out = []
    for e in EMAIL.findall(s or ""):
        e = e.strip(".").lower()
        if e not in out:
            out.append(e)
    return ", ".join(out) or None


def ward_no(s):
    """The ward number in a cell such as "01", "Ward No. 1", "1ST WARD / Mallaipally", "Div.NO.4", "वार्ड 12": digits
    without leading zeros, or None."""
    t = (s or "").translate(DIGITS)
    m = re.search(r"(\d+)", t)
    return str(int(m.group(1))) if m else None


HEAD_WORDS = re.compile(r"name|ward|mobile|contact|phone|s\.?\s*no|sl\.?|नाम|वार्ड|मोबाइल|પ્રભાગ|નામ|ವಾರ್ಡ್|पद", re.I)


def table_rows(html):
    """Every <table> row as a list of cell texts, with the header row of its table (list of lower-case texts). The header is
    the first row with <th> cells, or the first row of header words with no plain number in it."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for t in soup.find_all("table"):
        head = None
        for tr in t.find_all("tr"):
            cells = [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["td", "th"])]
            if not any(cells):
                continue
            if head is None and len(cells) > 1 and not any(c.isdigit() for c in cells) and (
                    tr.find("th") or HEAD_WORDS.search(" ".join(cells))):
                head = [c.lower() for c in cells]
                continue
            out.append((head, cells))
    return out


def column(head, *patterns):
    """Index of the first header cell that matches one of the patterns (in the order given), or None."""
    if not head:
        return None
    for p in patterns:
        for i, h in enumerate(head):
            if re.search(p, h, re.I):
                return i
    return None


def record(state, body, ward, name, url, *, prefix=None, phone=None, email=None, address=None, position=None, ward_label=None,
           lgd_code=None, record_for=None, extra=None):
    d = {"type": "councillor_contact", "state": state, "body": body, "lgd_code": lgd_code, "ward_no": ward,
         "ward_label": clean(ward_label), "name": clean(name), "phone": phone, "email": email, "address": clean(address),
         "position": clean(position), "record_for": record_for, "url": url, "source": urlsplit(url).hostname}
    d.update(extra or {})
    return {k: v for k, v in d.items() if v not in (None, "")}


def keyed(state, body_slug, recs):
    """(record id, record) pairs: cp:<state>:<body slug>:<ward>, sl-<n> without a ward, -2/-3 for repeats of a ward."""
    seen, out = {}, []
    for n, d in enumerate(recs, 1):
        k = d.get("ward_no") or f"sl-{n}"
        seen[k] = seen.get(k, 0) + 1
        out.append((f"cp:{state}:{body_slug}:{k}" + (f"-{seen[k]}" if seen[k] > 1 else ""), d))
    return out


def useful(recs):
    """Only records that carry a contact field."""
    return [d for d in recs if d.get("phone") or d.get("email") or d.get("address")]


NAME_COL = (r"name of (the )?(mc|member|councillor|corporator|elected|parshad|nagarsevak)", r"member name|councillor name|corporator",
            r"^(?!.*(ward|वार्ड|प्रभाग|વોર્ડ|ವಾರ್ಡ್|వార్డు)).*(\bname\b|नाम|નામ|ಹೆಸರು|పేరు|പേര്)")
WARD_COL = (r"^w\.?\s*no|ward\s*(no|number|name)?|prabhag|प्रभाग|वार्ड|વોર્ડ|ವಾರ್ಡ್|వార్డు|div(ision)?\b|^ward",)
PHONE_COL = (r"mobile|contact|phone|cell|मोबाइल|मोबाईल|दूरभाष|फोन|સંપર્ક|ಮೊಬೈಲ್|ದೂರವಾಣಿ|ఫోన్|మొబైల్",)
EMAIL_COL = (r"e-?\s*mail|ईमेल",)
ADDR_COL = (r"address|पता|पत्ता|સરનામું|ವಿಳಾಸ|చిరునామా",)
POST_COL = (r"designation|post\b|position|पद",)


def table_members(html, state, body, url, *, lgd_code=None, record_prefix=None, keep_posts=None):
    """Members from the first kind of table most council pages use: one row per member with a name column and a phone,
    email or address column (header row in English or the state's language). record_prefix ("councillor:PB:bathinda") gives
    record_for = <prefix>:<ward>. Rows whose post is MP/MLA/MLC (ex officio) are left out."""
    recs = []
    for head, cells in table_rows(html):
        if not head:
            continue
        ni = column(head, *NAME_COL)
        pi, ei, ai = column(head, *PHONE_COL), column(head, *EMAIL_COL), column(head, *ADDR_COL)
        if ni is None or (pi is None and ei is None and ai is None) or ni >= len(cells):
            continue
        wi, di = column(head, *WARD_COL), column(head, *POST_COL)
        if wi == ni:
            wi = None
        cell = lambda i: cells[i] if i is not None and i < len(cells) else None
        name, post = cell(ni), cell(di)
        if not name or re.fullmatch(r"[\d\s.\-]*", name) or re.search(r"\b(vacant|रिक्त)\b", name, re.I):
            continue
        if post and re.search(r"\b(m\.?p|m\.?l\.?a|m\.?l\.?c|ex.?officio)\b", post, re.I):
            continue
        label = cell(wi)
        ward = ward_no(label)
        phone = phones(cell(pi)) if pi is not None else None
        email = emails(cell(ei)) if ei is not None else emails(" ".join(cells))
        addr = cell(ai)
        if addr and pi is not None and ai == pi:
            addr = None
        recs.append(record(state, body, ward, name, url, phone=phone, email=email, address=addr, position=post, ward_label=label,
                           lgd_code=lgd_code, record_for=f"{record_prefix}:{ward}" if record_prefix and ward else None))
    return recs
