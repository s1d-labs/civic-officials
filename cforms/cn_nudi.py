"""Kannada text in the legacy Nudi / KGP font encoding (Karnataka government PDFs, e.g. the State Election Commission's ULB
result abstracts on karsec.karnataka.gov.in) -> Unicode Kannada.

pdftotext gives such text as Latin-1 letters: "£ÀUÀgÀ ¸ÀÜ½ÃAiÀÄ ¸ÀA¸ÉÜUÀ¼À" = "ನಗರ ಸ್ಥಳೀಯ ಸಂಸ್ಥೆಗಳ". How the encoding works:
- a consonant glyph is the bare consonant; "À" after it is the inherent "a" (no Unicode character), "ï" the virama; vowel
  signs follow it (Á ಾ, Â ಿ, Ä ು, Å ು after ಪ ವ ಫ, Æ ೂ, Ç ೂ after ಪ ವ ಫ, È ೃ, É ೆ, Ë ೌ). "Ã" lengthens the vowel before it
  (ಿ -> ೀ, ೆ -> ೇ, ೊ -> ೋ), "Ê" after "É" gives ೈ, "Æ" after "É" gives ೊ.
- some syllables have their own glyph: the i-forms (Q ಕಿ, V ಗಿ, ¢ ದಿ, ¤ ನಿ, ¹ ಸಿ ...), d ಜ, l ಟ, t ಣ, § ಬ, ® ಲ, R ಖ; ಮ and ಯ
  are drawn from parts ("ªÀÄ" ಮ, "AiÀÄ" ಯ, "ªÀiÁ" ಮಾ, "«Ä" ಮಿ); "s" / "ü" add aspiration (z ದ, zs ಧ; ¢ ದಿ, ¢ü ಧಿ).
- subscript consonants (ottu: Ì ್ಕ ... æ ್ರ, è ್ಲ, å ್ಯ) come after the vowel sign of their syllable; Unicode wants them
  before it ("UÉæ" = ಗ + ೆ + ್ರ -> ಗ್ರೆ). The reph "ð" (ರ್ over the syllable) comes after the syllable's consonant; Unicode
  puts ರ್ before it ("ªÀðwæ" -> ರ್ವತ್ರಿ).
convert() applies the longest sequences first, then the two reorderings. is_nudi() tells whether a text looks like Nudi.
The table is checked on the SEC result abstract of 3 September 2018 (tests/data/cn_nudi/); rare letters (ಝ, ಞ, ಙ) are unchecked.
"""
import re
import unicodedata

VIRAMA = "್"
REPH = "\ue000"              # placeholder for ð (reph) until it is moved
LONG = "\u0cd5"              # Ã: the Kannada length mark; NFC makes ಿ+ೕ ೀ, ೆ+ೕ ೇ, ೊ+ೕ ೋ

# consonant glyph -> consonant (the glyph used before À, ï and the vowel signs)
BASE = {"P": "ಕ", "S": "ಖ", "U": "ಗ", "W": "ಘ", "Z": "ಚ", "b": "ಛ", "e": "ಜ", "m": "ಟ", "o": "ಠ", "q": "ಡ", "qs": "ಢ", "u": "ಣ",
        "v": "ತ", "x": "ಥ", "z": "ದ", "zs": "ಧ", "£": "ನ", "¥": "ಪ", "¥s": "ಫ", "¨": "ಬ", "¨s": "ಭ", "ª": "ವ", "g": "ರ",
        "¯": "ಲ", "±": "ಶ", "μ": "ಷ", "µ": "ಷ", "¸": "ಸ", "º": "ಹ", "¼": "ಳ", "Sï": "ಖ್"}
# whole syllables with their own glyph
SYL = {"R": "ಖ", "d": "ಜ", "l": "ಟ", "t": "ಣ", "§": "ಬ", "®": "ಲ",
       "Q": "ಕಿ", "T": "ಖಿ", "V": "ಗಿ", "X": "ಘಿ", "a": "ಚಿ", "c": "ಛಿ", "f": "ಜಿ", "n": "ಟಿ", "p": "ಠಿ", "r": "ಡಿ", "rü": "ಢಿ",
       "tÂ": "ಣಿ", "w": "ತಿ", "y": "ಥಿ", "¢": "ದಿ", "¢ü": "ಧಿ", "¤": "ನಿ", "¦": "ಪಿ", "¦ü": "ಫಿ", "©": "ಬಿ", "©ü": "ಭಿ", "j": "ರಿ",
       "°": "ಲಿ", "«": "ವಿ", "²": "ಶಿ", "¶": "ಷಿ", "¹": "ಸಿ", "»": "ಹಿ", "½": "ಳಿ",
       # ಮ and ಯ (built from parts), longest first in the table below
       "ªÀÄ": "ಮ", "ªÀiÁ": "ಮಾ", "ªÀiï": "ಮ್", "ªÀiË": "ಮೌ", "ªÉÄ": "ಮೆ", "«Ä": "ಮಿ", "ªÉÆ": "ಮೊ", "ªÉÇ": "ವೊ",
       "AiÀÄ": "ಯ", "AiÀiÁ": "ಯಾ", "AiÀiï": "ಯ್", "AiÀiË": "ಯೌ", "AiÉÄ": "ಯೆ", "AiÉÆ": "ಯೊ", "¬Ä": "ಯಿ", "0iÀÄ": "ಯ", "0iÀiÁ": "ಯಾ",
       "gÀhÄ": "ಝ", "gÀhiÁ": "ಝಾ", "gÀhiï": "ಝ್", "jhÄ": "ಝಿ", "gÉhÄ": "ಝೆ",
       "k": "ಞ", "Y": "ಙ"}
VOWEL = {"C": "ಅ", "D": "ಆ", "E": "ಇ", "F": "ಈ", "G": "ಉ", "H": "ಊ", "IÄ": "ಋ", "J": "ಎ", "K": "ಏ", "L": "ಐ", "M": "ಒ", "N": "ಓ",
         "O": "ಔ", "A": "ಂ", "B": "ಃ"}
SIGN = {"À": "", "Á": "ಾ", "Â": "ಿ", "Ä": "ು", "Å": "ು", "Æ": "ೂ", "Ç": "ೂ", "È": "ೃ", "É": "ೆ", "Ë": "ೌ", "ï": VIRAMA,
        "Ã": LONG, "Ê": "ೖ", "ð": REPH, "ö": "", "ü": "", "s": ""}
OTTU = {"Ì": "ಕ", "Í": "ಖ", "Î": "ಗ", "Ï": "ಘ", "Ð": "ಞ", "Ñ": "ಚ", "Ò": "ಛ", "Ó": "ಜ", "Ô": "ಝ", "Õ": "ಞ", "Ö": "ಟ", "×": "ಠ",
        "Ø": "ಡ", "Ù": "ಢ", "Ú": "ಣ", "Û": "ತ", "Ü": "ಥ", "Ý": "ದ", "Þ": "ಧ", "ß": "ನ", "à": "ಪ", "á": "ಫ", "â": "ಬ", "ã": "ಭ",
        "ä": "ಮ", "å": "ಯ", "æ": "ರ", "ç": "ರ", "è": "ಲ", "é": "ವ", "ê": "ಶ", "ë": "ಷ", "ì": "ಸ", "í": "ಹ", "î": "ಳ"}

TABLE = {}
TABLE.update(BASE)
TABLE.update({k: v for k, v in SIGN.items()})
TABLE.update(VOWEL)
TABLE.update({k: VIRAMA + v for k, v in OTTU.items()})
TABLE.update(SYL)
KEYS = sorted(TABLE, key=len, reverse=True)
TOKEN = re.compile("|".join(re.escape(k) for k in KEYS))

KN = "ಀ-೿"
SIGNS = "\u0cbe-\u0cc4\u0cc6-\u0cc8\u0cca-\u0ccc\u0cd5\u0cd6"
CONS = "ಕ-ಹ"


def _reorder(s):
    # ottus typed after the vowel sign: C + sign + (virama C)+ -> C + (virama C)+ + sign
    s = re.sub(f"([{SIGNS}]+)((?:{VIRAMA}[{CONS}])+)", r"\2\1", s)
    # reph after its syllable: (C (virama C)* signs*) REPH -> ರ್ + that
    s = re.sub(f"([{CONS}](?:{VIRAMA}[{CONS}])*[{SIGNS}]*){REPH}", "ರ" + VIRAMA + r"\1", s)
    s = s.replace(REPH, "ರ" + VIRAMA)
    # vowel length and two-part signs: NFC composes ಿ+ೕ ೀ, ೆ+ೕ ೇ, ೆ+ೂ ೊ, ೊ+ೕ ೋ, ೆ+ೖ ೈ
    return unicodedata.normalize("NFC", s)


def convert(text):
    """Nudi text -> Unicode Kannada. Digits, spaces and ASCII punctuation stay as they are."""
    if not text:
        return text
    # glyph order slips in PDF text: a stray "À" before "É", "ÄÀ" for "ÀÄ", "ÃÉ" for "ÉÃ"
    text = text.replace("ÄÀ", "ÀÄ").replace("ÃÉ", "ÉÃ")
    text = re.sub("À(?=É)", "", text)
    out = TOKEN.sub(lambda m: TABLE[m.group(0)], text)
    return _reorder(out)


NUDI_MARK = re.compile(r"[ÀÁÂÄÉ£¥¸ªº¼]")


def is_nudi(text):
    """True when at least a fifth of the letters are the Latin-1 glyph codes Nudi uses for Kannada (À, Á, Ä, É, £, ¸ ...)."""
    letters = [c for c in text or "" if c.isalpha()]
    if len(letters) < 4:
        return False
    return sum(1 for c in letters if NUDI_MARK.match(c)) / len(letters) >= 0.2
