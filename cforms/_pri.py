"""Panchayati Raj elected representatives: shared record shape and LGD matching for the pri_<xx> readers (cforms/pri_<xx>.py).

Record type "pri_member" (one record per elected person; the civic-india loader for civic.pri_member reads these; contract agreed
with the pri-north work, 2026-11-13):
  state      two-letter code (KL, TN, KA, AP, TG, MH, GJ, GA, PY ...)
  level      "zp" (district panchayat / zilla parishad), "ps" (block / mandal / taluka panchayat, panchayat samiti, Puducherry
             commune panchayat), "gp" (gram / village panchayat)
  lgd_code   LGD local_body_code of the PRI body (from the source, the seed, or match() below); "" when not matched
  body       the body's name as the source writes it
  district, block   names as the source writes them (block = the intermediate panchayat / mandal / taluk of a gp or ps)
  post       "President", "Vice President", "Sarpanch", "Member" ... as the source names it (post_regional when not English)
  name, party, ward_no, phone, email   as the source gives them ("" or absent when it does not)
  election   the election round ("Kerala 2025", "Tamil Nadu 2019 rural local bodies" ...)
  url        the page or file the row comes from
  head       True for the body's president / chairperson / sarpanch (and vice heads: head_rank 2)
plus the source trail: METHOD (module constant), src_pos, src_url (or provenance.at(r, url)).
Record id: pri:<state>:<level>:<lgd_code or body key>:<post key> where post key = "head", "vice", or "w<ward_no>" (members).
"""
import gzip
import json
import re
import unicodedata
from pathlib import Path

LEVELS = ("zp", "ps", "gp")
FIELDS = ("state", "level", "lgd_code", "body", "district", "block", "post", "name", "party", "ward_no", "phone", "email",
          "election", "url")
HERE = Path(__file__).resolve().parent / "pri_lgd"
# LGD local_body_type_name -> level
TYPE_LEVEL = {
    "district panchayat": "zp", "zilla parishad": "zp", "zila panchayat": "zp", "zilla panchayat": "zp",
    "block panchayat": "ps", "mandal panchayat": "ps", "taluka panchayat": "ps", "taluk panchayat": "ps",
    "panchayat samiti": "ps", "intermediate panchayat": "ps", "commune panchayat": "ps",
    "gram panchayat": "gp", "grama panchayat": "gp", "village panchayat": "gp",
}
_STOP = re.compile(r"\b(grama?|gram|village|panchayath?|panchayat|block|mandal|taluka?|district|zilla|zila|parishad|parishath|"
                   r"samiti|commune|gp|vp|bp|dp|zp|ps|tp)\b")


def level_of(type_name):
    return TYPE_LEVEL.get(" ".join((type_name or "").lower().split()), "")


_KEEP = r"a-z0-9\u0900-\u0dff"     # Latin letters, digits and the Indic scripts (Devanagari ... Sinhala blocks)


def norm(s):
    """Name key for matching: lower case, Latin letters (accents dropped), digits and Indic letters, body-type words removed.
    Indic text is kept (2026-11-13: an ASCII-only key made every Marathi/Tamil/Gujarati name empty, so LGD local names never
    matched and different bodies got one record id)."""
    s = unicodedata.normalize("NFC", s or "").lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not (unicodedata.combining(c) and ord(c) < 0x0900))
    s = unicodedata.normalize("NFC", s)
    s = _STOP.sub(" ", re.sub(rf"[^{_KEEP}]+", " ", s))
    return re.sub(rf"[^{_KEEP}]", "", s)


def digits(s):
    """Text kept as is; a value is treated as a number only when it is all digits (owner rule: no int() without a check)."""
    s = (s or "").strip()
    return s if s.isdigit() else ""


def phone(s):
    """Indian phone numbers in a cell, joined with ", "; the cell text when none is found (kept as written)."""
    t = s or ""
    found = re.findall(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5}|0\d{2,4}[\s-]?\d{6,8})(?!\d)", t)
    out = [re.sub(r"[\s-]", "", f) for f in found]
    return ", ".join(dict.fromkeys(out)) if out else " ".join(t.split())


def post_key(head=False, vice=False, ward_no=None, extra=""):
    if head:
        return "head" + (f"-{extra}" if extra else "")
    if vice:
        return "vice" + (f"-{extra}" if extra else "")
    w = " ".join(str(ward_no or "").split())
    return "w" + re.sub(r"[^A-Za-z0-9]+", "-", w).strip("-") + (f"-{extra}" if extra else "")


def rid(state, level, body_key, pkey):
    return f"pri:{state}:{level}:{body_key}:{pkey}"


def record(state, level, *, body_key=None, pkey=None, **f):
    """(record id, data). body_key defaults to lgd_code, else district/block/body names; pkey defaults to post_key(...)."""
    assert level in LEVELS, level
    d = {"type": "pri_member", "state": state, "level": level}
    for k, v in f.items():
        if v is None or v == "":
            continue
        d[k] = " ".join(v.split()) if isinstance(v, str) and k not in ("src_url",) else v
    d.setdefault("lgd_code", "")
    if body_key is None:
        body_key = d["lgd_code"] or "~".join(norm(d.get(k, "")) for k in ("district", "block", "body"))
    if pkey is None:
        pkey = post_key(d.get("head") is True and d.get("head_rank", 1) == 1, d.get("head") is True and d.get("head_rank") == 2,
                        d.get("ward_no"))
    return rid(state, level, body_key, pkey), d


class Lgd:
    """LGD PRI bodies of one state (cforms/pri_lgd/<st>.json.gz, made by seeds/build_pri_lgd.py from DB civic lgd tables):
    rows [code, level, name, local name, parent code]. match() by level and names; the parent chain gives district and block."""

    def __init__(self, state):
        p = HERE / f"{state.lower()}.json.gz"
        self.rows = json.loads(gzip.decompress(p.read_bytes())) if p.exists() else []
        self.by_code = {r[0]: r for r in self.rows}
        self.idx = {}
        for r in self.rows:
            code, lev, name, local, parent = r
            chain = self.chain(code)
            zp = next((self.by_code[c] for c in chain if self.by_code[c][1] == "zp"), None)
            ps = next((self.by_code[c] for c in chain if self.by_code[c][1] == "ps"), None)
            dists = {x for x in (zp[2], zp[3]) if x} if zp else {""}       # district and block in English and the local script
            blks = {x for x in (ps[2], ps[3]) if x} if ps else {""}
            for nm in {name, local}:
                if not nm:
                    continue
                n = norm(nm)
                self.idx.setdefault((lev, n), set()).add(code)
                for dist in dists:
                    self.idx.setdefault((lev, norm(dist), n), set()).add(code)
                    for blk in blks:
                        self.idx.setdefault((lev, norm(dist), norm(blk), n), set()).add(code)

    def chain(self, code):
        out, seen = [], set()
        while code and code in self.by_code and code not in seen:
            seen.add(code)
            out.append(code)
            code = self.by_code[code][4]
        return out

    def match(self, level, body, district="", block=""):
        """The one LGD code for this body, or "" (none or more than one candidate)."""
        n = norm(body)
        if not n:
            return ""
        for key in ((level, norm(district), norm(block), n), (level, norm(district), n), (level, n)):
            if "" in key[1:-1]:
                continue
            c = self.idx.get(key)
            if c and len(c) == 1:
                return next(iter(c))
        return ""
