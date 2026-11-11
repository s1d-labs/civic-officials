"""Kruti Dev 010 (legacy Hindi font encoding) -> Unicode Devanagari: a copy of civic-india/krutidev.py (investigations repo), for
dforms/ulb_uk.py. Text from PDFs set in Kruti Dev comes out as Latin letters ("vkse izdk'k" = "ओम प्रकाश").
"""
import re

# longest sequences first (order matters)
SEQ = [
    ("ñ", "॰"), ("Q+Z", "QZ+"), ("sas", "sa"), ("aa", "a"), (")Z", "र्द्ध"), ("ZZ", "Z"), ("‘", "\""), ("’", "\""),
    ("“", "'"), ("”", "'"),
    ("å", "०"), ("ƒ", "१"), ("„", "२"), ("…", "३"), ("†", "४"), ("‡", "५"), ("ˆ", "६"), ("‰", "७"), ("Š", "८"), ("‹", "९"),
    ("¶+", "फ़्"), ("d+", "क़"), ("[+k", "ख़"), ("[+", "ख़्"), ("x+", "ग़"), ("T+", "ज़्"), ("t+", "ज़"), ("M+", "ड़"), ("<+", "ढ़"),
    ("Q+", "फ़"), (";+", "य़"), ("j+", "ऱ"), ("u+", "ऩ"),
    ("Ùk", "त्त"), ("Ù", "त्त्"), ("ä", "क्त"), ("–", "दृ"), ("—", "कृ"), ("é", "न्न"), ("™", "न्न्"), ("=kk", "=k"),
    ("f=k", "f="), ("à", "ह्न"), ("á", "ह्य"), ("â", "हृ"), ("ã", "ह्म"), ("ºz", "ह्र"), ("º", "ह्"), ("í", "द्द"),
    ("{k", "क्ष"), ("{", "क्ष्"), ("=", "त्र"), ("«", "त्र्"), ("Nî", "छ्य"), ("Vî", "ट्य"), ("Bî", "ठ्य"), ("Mî", "ड्य"),
    ("<î", "ढ्य"), ("|", "द्य"), ("K", "ज्ञ"), ("}", "द्व"), ("J", "श्र"), ("Vª", "ट्र"), ("Mª", "ड्र"), ("<ªª", "ढ्र"),
    ("Nª", "छ्र"), ("Ø", "क्र"), ("Ý", "फ्र"), ("nzZ", "र्द्र"), ("æ", "द्र"), ("ç", "प्र"), ("Á", "प्र"), ("xz", "ग्र"),
    ("#", "रु"), (":", "रू"),
    ("v‚", "ऑ"), ("vks", "ओ"), ("vkS", "औ"), ("vk", "आ"), ("v", "अ"), ("b±", "ईं"), ("Ã", "ई"), ("bZ", "ई"), ("b", "इ"),
    ("m", "उ"), ("Å", "ऊ"), (",s", "ऐ"), (",", "ए"), ("_", "ऋ"),
    ("ô", "क्क"), ("d", "क"), ("Dk", "क"), ("D", "क्"), ("[k", "ख"), ("[", "ख्"), ("x", "ग"), ("Xk", "ग"), ("X", "ग्"),
    ("Ä", "घ"), ("?k", "घ"), ("?", "घ्"), ("³", "ङ"), ("pkS", "चै"), ("p", "च"), ("Pk", "च"), ("P", "च्"), ("N", "छ"),
    ("t", "ज"), ("Tk", "ज"), ("T", "ज्"), (">", "झ"), ("÷", "झ्"), ("¥", "ञ"), ("ê", "ट्ट"), ("ë", "ट्ठ"), ("V", "ट"),
    ("B", "ठ"), ("ì", "ड्ड"), ("ï", "ड्ढ"), ("M", "ड"), ("<", "ढ"), (".k", "ण"), (".", "ण्"), ("rk", "ता"), ("r", "त"),
    ("Rk", "त"), ("R", "त्"), ("Fk", "थ"), ("F", "थ्"), (")", "द्ध"), ("n", "द"), ("/k", "ध"), ("èk", "ध"), ("/", "ध्"),
    ("è", "ध्"), ("Ë", "ध्"), ("u", "न"), ("Uk", "न"), ("U", "न्"), ("i", "प"), ("Ik", "प"), ("I", "प्"), ("Q", "फ"),
    ("¶", "फ्"), ("c", "ब"), ("Ck", "ब"), ("C", "ब्"), ("Hk", "भ"), ("H", "भ्"), ("e", "म"), ("Ek", "म"), ("E", "म्"),
    (";", "य"), ("¸", "य्"), ("j", "र"), ("y", "ल"), ("Yk", "ल"), ("Y", "ल्"), ("G", "ळ"), ("o", "व"), ("Ok", "व"),
    ("O", "व्"), ("'k", "श"), ("'", "श्"), ("\"k", "ष"), ("\"", "ष्"), ("l", "स"), ("Lk", "स"), ("L", "स्"), ("g", "ह"),
    ("È", "ीं"), ("z", "्र"), ("Ì", "द्द"), ("Í", "ट्ट"), ("Î", "ट्ठ"), ("Ï", "ड्ड"), ("Ñ", "कृ"), ("Ò", "भ"), ("Ó", "्य"),
    ("Ô", "ड्ढ"), ("Ö", "झ्"), ("Ø", "क्र"), ("Ù", "त्त्"), ("Ú", "फ्र"), ("Ü", "ह्न"), ("‚", "ॉ"), ("ks", "ो"),
    ("kS", "ौ"), ("k", "ा"), ("h", "ी"), ("q", "ु"), ("w", "ू"), ("`", "ृ"), ("s", "े"), ("S", "ै"), ("a", "ं"),
    ("¡", "ँ"), ("%", "ः"), ("W", "ॅ"), ("•", "ऽ"), ("·", "ऽ"), ("∙", "ऽ"), ("~", "्"), ("+", "़"), ("A", "।"), ("-", "."),
    ("&", "-"), ("@", "/"), ("^", "‘"), ("*", "’"), ("Þ", "“"), ("ß", "”"),
]
VOWEL_SIGNS = "ािीुूृेैोौंःँॅ"
CONSONANT = re.compile("[\u0915-\u0939\u0958-\u095F]")


def convert(text):
    s = text
    for a, b in SEQ:
        s = s.replace(a, b)
    # short i: "ि" was typed before its consonant (cluster): move it after the consonant cluster
    out, i = [], 0
    chars = list(s)
    while i < len(chars):
        if chars[i] == "f" and i + 1 < len(chars):
            j = i + 1
            cluster = [chars[j]]
            j += 1
            while j + 1 < len(chars) and chars[j] == "्" and CONSONANT.match(chars[j + 1]):
                cluster += chars[j:j + 2]
                j += 2
            if j < len(chars) and chars[j] == "़":
                cluster.append(chars[j])
                j += 1
            out += cluster + ["ि"]
            i = j
            continue
        out.append(chars[i])
        i += 1
    s = "".join(out)
    # reph: "Z" follows the syllable (consonant + vowel signs) it sits on: put "र्" before that syllable
    while "Z" in s:
        k = s.index("Z")
        p = k - 1
        while p >= 0 and s[p] in VOWEL_SIGNS:
            p -= 1
        while p - 2 >= 0 and s[p - 1] == "्" and CONSONANT.match(s[p - 2]):
            p -= 2
        s = s[:max(p, 0)] + "र्" + s[max(p, 0):k] + s[k + 1:]
    return s


def is_krutidev(text):
    """Heuristic: Latin text with the letter patterns Kruti Dev produces (k after consonant letters, 'f' before letters, ';' etc.)."""
    t = text or ""
    latin = sum(ch.isascii() and ch.isalpha() for ch in t)
    if latin < 20:
        return False
    hits = len(re.findall(r"[dxtrnuieyolgjc]k|f[dxtrnuiepyolgjc]|vk|;k|'k|ks\b", t))
    return hits / max(1, latin) > 0.08
