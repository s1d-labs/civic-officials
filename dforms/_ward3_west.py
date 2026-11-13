"""Shared helpers of the ward3 readers of West India corporations (dforms/ward3_<city>.py, branch ward-staff-west).
officer_rows(html): the rows of every officer table of a page (a table whose header row names a name column and a post / phone /
email column, in English, Marathi, Hindi or Gujarati), as dicts {name, post, email, phone, cells, pos}; pos = {"table", "row"}
(source trail, the same numbering as _esw.grid)."""
import re

from dforms import _esw

COLS = (
    ("name", r"(name|नाव|नाम|નામ)"),
    ("post", r"(designation|post|पदनाम|पद|हुद्दा|હોદ્દો|જગ્યા)"),
    ("email", r"(e-?\s?mail|ई-?\s?मेल|ઈ-?\s?મેલ|ઇમેલ)"),
    ("phone", r"(phone|mobile|contact|tel|दुरध्वनी|दूरध्वनी|भ्रमणध्वनी|मोबा|फोन|संपर्क|મોબાઈલ|ફોન|સંપર્ક)"),
    ("area", r"(ward|zone|office|area|प्रभाग|विभाग|क्षेत्र|झोन|कार्यालय|વોર્ડ|ઝોન|કચેરી)"),
)


def header_map(cells):
    """{field: column index} of a header row; a cell takes the first field that matches and is not taken yet."""
    out = {}
    for i, c in enumerate(cells):
        t = _esw.clean(c).lower()
        if not t or len(t) > 60:
            continue
        for field, rx in COLS:
            if field not in out and re.search(rx, t):
                out[field] = i
                break
    return out


def officer_rows(html):
    s = _esw.soup(html)
    out = []
    for table in s.find_all("table"):
        pos = []
        g = _esw.grid(table, pos=pos)
        hm, start = {}, 0
        for k, row in enumerate(g[:3]):
            hm = header_map(row)
            if "name" in hm and len(hm) >= 2:
                start = k + 1
                break
        else:
            continue
        for row, p in zip(g[start:], pos[start:]):
            if header_map(row).get("name") is not None and len(header_map(row)) >= 3:
                continue        # a repeated header row
            d = {f: (row[i] if i < len(row) else "") for f, i in hm.items()}
            d["cells"], d["pos"] = row, p
            out.append(d)
    return out


# ---------------------------------------------------------------- Devanagari PDFs whose font has no text map for conjuncts
# Word PDFs set in a Devanagari font without ToUnicode entries for its conjunct glyphs: pypdf prints chr(glyph id) for them, in
# visual order (the i-sign before its consonant, the reph after its syllable). GLYPHS maps the glyph ids seen in these PDFs
# (read by eye from the words they stand in: "आयु᭍ त" = आयुक्त, "᮰ी" = श्री, 2026-11-13, mclatur.org HOD list); "\x02" = pre-base
# i-sign, "\x01" = reph. The font draws त्र as the glyph of ञ (क्षेञ = क्षेत्र): glyph_fix writes त्र for ञ.
# Known gap: an e-sign is sometimes printed after the next letter (दवे for देव); not repaired.
GLYPHS = {
    "\u1bb0": "श्र", "\u1ba7": "प्र", "\u1b43": "क्ष", "\u1b66": "य्", "\u1b93": "क्र", "\u1b4d": "क्", "\u1b6d": "स्",
    "\u1b45": "\x01", "\u1ba4": "द्र", "\u1b5c": "त्", "\u1cd2": "द्य", "\u1cf0": "\x02", "\u1c76": "ें", "\u1cef": "\x02",
    "\u1b4e": "ख्", "\u1b60": "न्", "\u1b6a": "व्", "\u1b52": "च्", "\u1cf1": "ी", "\u1b6b": "श्", "\u1b68": "ल्", "\u1cf2": "\x02",
    "\u1ba2": "त्र", "\u1c5f": "हु", "\u1c6e": "\x01ी", "\u1ce1": "श्व", "\u1b6c": "ष्", "\u1b95": "ग्र", "\u1b4f": "ग्",
    "\u1ca8": "ग्न", "\u1c6b": "त्त", "\u1b6f": "क्ष्", "\u1c70": "ँ", "\u1b61": "प्", "\u1c82": "ों", "\u1b44": "",
    "\u093f": "\x02",
}
_C = "[\u0915-\u0939\u0958-\u095f]\u093c?"
CLUSTER = f"(?:{_C}\u094d)*{_C}"
MATRAS = "[\u093e-\u094c\u0962\u0963\u0901-\u0903]*"


def glyph_fix(s):
    """Text of one line of such a PDF in logical Unicode order (glyph ids mapped, i-sign and reph put back)."""
    s = "".join(GLYPHS.get(ch, ch) for ch in s)
    s = re.sub("\u094d (?=[\u0915-\u0939])", "\u094d", s)          # pypdf leaves a space after a half form
    s = re.sub(f"\x02\\s?({CLUSTER})", "\\1\u093f", s)
    s = re.sub(f"\x03\\s?({CLUSTER})", "\\1\u093f\u0902", s)
    s = re.sub(f"({CLUSTER})({MATRAS})\x01", "र्\\1\\2", s)
    s = s.replace("\u091e", "त्र")
    return s.replace("\x01", "").replace("\x02", "\u093f").replace("\x03", "\u093f\u0902")
