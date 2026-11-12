"""Helpers of the cr_* councillor readers (gap round, 2026-11-11): Devanagari to Latin, name keys for tying a body to LGD,
regional digits, and a header-mapped reader for the plain member tables that body sites publish.

- latin(s): a plain Latin spelling of a Devanagari name (consonants with the inherent "a", matras, nukta letters).
- key(s): consonant key of a Latin name (vowels, aspiration and doubled letters dropped; the first letter kept), so that
  "Kasganj" and latin("कासगंज") = "kasaganja" give the same key. sim(a, b) compares two keys (0..1).
- digits(s): Devanagari, Gujarati, Bengali, Gurmukhi and Odia digits to ASCII.
- member_tables(html): every table with a member-name column, read through its header. The header words (Hindi, English,
  Gujarati, Bengali, Marathi, Punjabi) give each column a role: serial, ward_no, ward_name, name, father, party, phone,
  address, email, position, reservation. A header cell "क्रमांक/वार्ड नं0" (serial and ward in one) is read as the ward.
"""
import re
import unicodedata
from difflib import SequenceMatcher

from bs4 import BeautifulSoup

from cforms.cp_common import Cells

CONS = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n", "ट": "t",
        "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph",
        "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h", "ळ": "l"}
NUKTA = {"ड": "r", "ढ": "rh", "क": "q", "ख": "kh", "ग": "g", "ज": "z", "फ": "f"}
PRECOMPOSED = {"ड़": "r", "ढ़": "rh", "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "फ़": "f"}
VOWELS = {"अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au"}
MATRA = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e"}
DIGITS = str.maketrans("०१२३४५६७८९૦૧૨૩૪૫૬૭૮૯০১২৩৪৫৬৭৮৯੦੧੨੩੪੫੬੭੮੯୦୧୨୩୪୫୬୭୮୯", "0123456789" * 5)


def digits(s):
    return (s or "").translate(DIGITS)


def latin(s):
    s = unicodedata.normalize("NFC", s or "")
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c in CONS or c in PRECOMPOSED:
            if c in PRECOMPOSED:
                out.append(PRECOMPOSED[c])
                i += 1
            elif i + 1 < len(s) and s[i + 1] == "़":
                out.append(NUKTA.get(c, CONS[c]))
                i += 2
            else:
                out.append(CONS[c])
                i += 1
            n = s[i] if i < len(s) else ""
            if n in MATRA:
                out.append(MATRA[n])
                i += 1
            elif n == "्":
                i += 1
            else:
                out.append("a")
            continue
        if c in VOWELS:
            out.append(VOWELS[c])
        elif c in "ंँ":
            out.append("n")
        elif c in MATRA:
            out.append(MATRA[c])
        elif c.isascii():
            out.append(c.lower())
        else:
            out.append(" ")
        i += 1
    return " ".join("".join(out).split())


def key(s):
    s = re.sub(r"[^a-z]", "", (s or "").lower())
    if not s:
        return ""
    s = s.replace("ph", "f").replace("chh", "c").replace("ch", "c").replace("sh", "s")
    s = re.sub(r"([kgcjtdpbr])h", r"\1", s)
    s = s.translate(str.maketrans("wzqfx", "vjkpk"))
    head = "a" if s[0] in "aeiou" else ""          # a first vowel separates Amanpur from Mohanpur
    s = re.sub(r"[aeiouyh]", "", s)
    return head + re.sub(r"(.)\1+", r"\1", s)


def sim(a, b):
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def body_keys(name):
    """Keys of an LGD body name: the whole name without brackets, the part before "-", the first word."""
    n = re.sub(r"\([^)]*\)", " ", name or "")
    ks = {key(n), key(n.split("-")[0])}
    if n.split():
        ks.add(key(n.split()[0]))
    return {k for k in ks if k}


def best_body(src_name, bodies, prefer_type=None, latinize=True):
    """(lgd_code, score) of the body in `bodies` [(code, name, district, type)] whose name is closest to src_name, or (None, s)
    when the best is weak (< 0.8) or a second body is as close (margin < 0.08)."""
    l = latin(src_name) if latinize else (src_name or "")
    l = re.sub(r"\([^)]*\)", " ", l)
    hks = {key(l)} | ({key(l.split()[0])} if l.split() else set())
    hks = {k for k in hks if k}
    if not hks or not bodies:
        return None, 0.0
    sc = sorted(((max(sim(h, k) for h in hks for k in body_keys(b[1])) + (0.05 if prefer_type and b[3] in prefer_type else 0), b[0])
                 for b in bodies), reverse=True)
    if sc[0][0] >= 0.8 and (len(sc) == 1 or sc[0][0] - sc[1][0] >= 0.08):
        return sc[0][1], round(sc[0][0], 3)
    return None, round(sc[0][0], 3)


def clean(s):
    return " ".join((s or "").replace("\xa0", " ").split())


ROLES = [  # (role, header pattern); the first role whose pattern matches a header cell wins
    ("name", r"name of the (councill?or|member|corporator)s?"),     # "Name of the Councillors with Designation"
    ("father", r"पिता|पति|father|husband|पिता/पति|वडील"),
    ("ward_name", r"वार्ड\s*का\s*नाम|ward\s*name|मोहल्ला|वार्ड\s*का\s*क्षेत्र|area|locality|প্রভাগ নাম|વોર્ડનું નામ"),
    ("ward_no", r"वार्ड|ward|वॉर्ड|प्रभाग|ওয়ার্ড|વોર્ડ|ਵਾਰਡ"),
    ("serial", r"^(क्र|क्रमांक|क्र0|sl|s\.?\s*no|sr|serial|क्रम|अनु|ક્રમ|અનુ|ক্রমিক|ਲੜੀ)"),
    ("party", r"पार्टी|दल|party|पक्ष|পক্ষ|দল|પક્ષ|ਪਾਰਟੀ"),
    ("phone", r"मोबा|mobile|phone|contact|दूरभाष|संपर्क|फोन|মোবাইল|ফোন|যোগাযোগ|મોબાઈલ|ફોન|ਮੋਬਾਈਲ"),
    ("email", r"e-?mail|ई-?मेल"),
    ("address", r"पता|address|ঠিকানা|સરનામું|पत्ता|ਪਤਾ"),
    ("position", r"designation|पद\b|post|हुद्दा|હોદ્દો|পদ"),
    ("reservation", r"आरक्षण|reserv|category|श्रेणी|સંવર્ગ"),
    ("name", r"name|नाम|सभासद|पार्षद|सदस्य|councill?or|concill?or|corporator|member|नगरसेवक|নাম|কাউন্সিলর|નામ|ઉમેદવાર|ਨਾਮ|ਕੌਂਸਲਰ"),
]


def roles(head):
    return [next((role for role, pat in ROLES if re.search(pat, clean(h).lower(), re.I)), None) for h in head]


def member_tables(html):
    """[(roles, [cells, ...]), ...] for the innermost tables that have a name column."""
    soup = BeautifulSoup(html, "lxml")
    found = []
    for ti, t in enumerate(soup.find_all("table"), 1):
        if t.find("table"):                      # a layout table: its inner tables are read
            continue
        trs = t.find_all("tr")
        for hi, tr in enumerate(trs[:4]):
            head = [clean(c.get_text(" ", strip=True)) for c in tr.find_all(["th", "td"])]
            rs = roles(head)
            if "name" in rs and ("ward_no" in rs or "ward_name" in rs):
                rows = []
                for ri, r in enumerate(trs[hi + 1:], hi + 2):     # rows carry .pos = {"table", "row"} for the source trail
                    row = Cells(clean(c.get_text(" ", strip=True)) for c in r.find_all(["td", "th"]))
                    row.pos = {"table": ti, "row": ri}
                    rows.append(row)
                found.append((rs, [r for r in rows if any(r)]))
                break
    return found


TITLE = re.compile(r"^(श्री(मती)?|सुश्री|कु0|कु\.|डॉ0?|मो0|Sh\.|Shri|Smt\.?|Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s*", re.I)


def ward_of(s):
    m = re.match(r"\s*(?:ward\s*(?:no\.?)?\s*)?(\d+)\s*\.?\s*(?:[-–(]\s*([A-Za-z])\)?)?", digits(s or ""), re.I)
    return (m.group(1) + (m.group(2) or "").upper()) if m else None


POST_TAIL = re.compile(r"\s+(Chairman|Chairperson|Vice[- ]Chairman|Vice[- ]Chairperson|Councillor|Mayor|Deputy Mayor|"
                       r"President|Vice[- ]President|Chairman[- ]in[- ]Council|MIC)\s*$", re.I)


def table_members(html, pos=None):
    """Dicts {ward_no, ward_name, name, party, phone, address, email, position, reservation, father} of every member row.
    pos: a list that gets each member's src_pos {"table", "row"} (source trail)."""
    out = []
    for rs, rows in member_tables(html):
        for cells in rows:
            if len(cells) < len(rs) - 1:
                continue
            d = {}
            for r, v in zip(rs, cells):
                if r and v and r not in d:
                    d[r] = v
            name = clean(d.get("name"))
            if not name or re.fullmatch(r"[-–.\s]*", name):
                continue
            m = POST_TAIL.search(name)              # "Sri Gautam Dasgupta Chairman": the post written after the name
            if m and m.start() > 0:
                d.setdefault("position", m.group(1))
                name = clean(name[:m.start()])
            d["name"] = name
            if d.get("ward_no"):
                w = ward_of(d["ward_no"])
                if w:
                    d["ward_no"] = w
                else:                            # "वार्ड" column with ward names (Khairabad): the name, no number
                    d.setdefault("ward_name", d["ward_no"])
                    d.pop("ward_no")
            if d.get("phone"):
                d["phone"] = ", ".join(re.findall(r"(?<!\d)(?:\+?91[-\s]?)?([6-9]\d{4}[-\s]?\d{5}|0\d{2,4}[-\s]?\d{6,8})(?!\d)",
                                                  digits(d["phone"]))) or digits(d["phone"])
            out.append(d)
            if pos is not None:
                pos.append(getattr(cells, "pos", None))
    return out
