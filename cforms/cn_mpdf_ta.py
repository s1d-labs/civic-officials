"""Tamil text from PDFs made by mPDF 5.x with its Indic font ind_ta_1_001 (Tamil Nadu SEC result files ulbe2022/*.pdf).

mPDF shaped the Tamil itself: ligature glyphs (கு, மு, டி, the i-sign ி after most consonants, க்ஷ ...) sit at Private Use
code points U+E002-U+E04C, and the ToUnicode map of the file is the identity, so pdftotext gives those PUA characters as they
are. The pre-base vowel signs ெ ே ை come BEFORE their consonant (visual order) and ொ ோ ௌ are split (ெ C ா).
This module maps the PUA glyphs back (the reverse of mPDF's own table includes/ind_ta_1_001.volt.php, v5.7.4) and puts the
vowel signs in logical order. No OCR is needed for these files.
"""
import re

# PUA glyph -> Unicode (from mPDF 5.7.4 includes/ind_ta_1_001.volt.php; the consonant before E006-E00D stays in the text)
PUA = {
    "": "்", "ŋ": "்", "Ŋ": "்",
    "": "க்ஷ", "": "ஸ்ரீ", "": "ஓம்",
    "": "ு", "": "ூ",                                  # after ஸ
    "": "ி", "": "ி", "": "ி", "": "ி", "": "ி", "": "ீ",
    "": "கு", "": "கூ", "": "ஙு", "": "ஙூ", "": "சு", "": "சூ", "": "ஜு",
    "": "ஜூ", "": "ஞு", "": "ஞூ", "": "டி", "": "டீ", "": "டு", "": "டூ",
    "": "ணா", "": "ணு", "": "ணூ", "": "ணை", "": "து", "": "தூ", "": "நு",
    "": "நூ", "": "னா", "": "னு", "": "னூ", "": "னை", "": "பு", "": "பூ",
    "": "மு", "": "மூ", "": "யு", "": "யூ", "": "ரு", "": "ரூ", "": "றா",
    "": "று", "": "றூ", "": "லி", "": "லீ", "": "லு", "": "லூ", "": "லை",
    "": "ளு", "": "ளூ", "": "ளை", "": "ழு", "": "ழூ", "": "வு", "": "வூ",
    "": "ஷி", "": "ஷீ", "": "ஷு", "": "ஷூ", "": "ஸி", "": "ஸீ", "": "ஹு",
    "": "ஹூ", "": "க்ஷி", "": "க்ஷீ", "": "க்ஷு", "": "க்ஷூ",
}
CONS = "கஙசஜஞடணதநனபமயரறலளழவஷஸஹ"
# a pre-base sign, then one consonant (or க்ஷ / ஸ்ரீ), optionally ா / ௗ (the second half of ொ ோ ௌ)
PRE = re.compile("([ெேை])((?:க்ஷ|[" + CONS + "]))([ாௗ]?)")
JOIN = {("ெ", "ா"): "ொ", ("ே", "ா"): "ோ", ("ெ", "ௗ"): "ௌ"}


def _swap(m):
    sign, cons, tail = m.groups()
    if tail and (sign, tail) in JOIN:
        return cons + JOIN[(sign, tail)]
    return cons + sign + tail


def unpua(s):
    return "".join(PUA.get(c, c) for c in s)


def convert(s):
    """Text from pdftotext (any layout) -> logical-order Unicode Tamil. Latin text and digits pass unchanged."""
    if not s:
        return s
    s = unpua(s)
    return PRE.sub(_swap, s)


def is_mpdf_ta(s):
    """True when the text carries mPDF Tamil PUA glyphs or visual-order vowel signs (a word that starts with ெ ே ை)."""
    return bool(re.search("[-]", s or "")) or bool(re.search(r"(?:^|\s)[ெேை][" + CONS + "]", s or ""))
