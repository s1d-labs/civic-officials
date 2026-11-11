"""Shared helpers for the police readers (dforms/police_<xx>.py). Not a reader itself.

rec(module, key, **fields) -> (record id, record): type dept_office, dept police, level police_station unless given; empty
fields are left out. Record id "dept:<module>:<key>" with key = slug of the station (plus the district when names repeat).
phones(*cells) -> "a, b": the numbers as published, Indic digits made ASCII, spaces inside a number removed, duplicates out.
"""
import gzip
import hashlib
import re
import unicodedata

from officials import deobfuscate  # noqa: F401  (readers import it from here)

_DIGITS = {}
for _base in (0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66):   # Devanagari .. Malayalam
    for _i in range(10):
        _DIGITS[_base + _i] = str(_i)
ZW = re.compile("[­​-‍﻿]")


def ascii_digits(s):
    return (s or "").translate(_DIGITS)


def clean(s):
    """One line, single spaces, no zero-width characters, NFC."""
    if s is None:
        return None
    s = unicodedata.normalize("NFC", ZW.sub("", str(s)).replace("\xa0", " "))
    return " ".join(s.split())


def slug(s):
    s = unicodedata.normalize("NFKD", clean(s) or "").lower()
    s = re.sub(r"[\u0300-\u036f]", "", s)                     # Latin accents; Indic vowel signs stay
    s = re.sub(r"[^\w\u0900-\u0dff]+", "-", s).strip("-_")
    return s or hashlib.sha1((s or "").encode()).hexdigest()[:8]


_PHONE = re.compile(r"(?<!\d)(?:\(?0\d{2,4}\)?[\s-]*\d{6,8}|(?:\+?91[\s-]*)?[6-9]\d{4}[\s-]?\d{5}|\d{6,8})(?!\d)")


def one_phone(s):
    """'(0129)- 2296824' -> '0129-2296824'; '94979 87006' -> '9497987006'; '+91 98765 43210' -> '9876543210'."""
    s = (clean(ascii_digits(s)) or "").strip(" .,;:")
    s = re.sub(r"^\+?91[\s-]+|^\+91", "", s)
    d = re.sub(r"\D", "", s)
    std = re.match(r"^\(?0\d{2,4}\)?\s*[-\s]", s)      # '08372-278213', '(0129)- 2296824': STD code + local number
    if len(d) == 10 and d[0] in "6789" and not std:
        return d
    if len(d) == 11 and d[0] == "0" and d[1] in "6789" and not std:
        return d[1:]
    m = re.match(r"^\(?(0?\d{2,5})\)?\s*[-\s]\s*(\d[\d\s]{4,9})$", s)
    if m:
        return m.group(1) + "-" + re.sub(r"\D", "", m.group(2))
    return d if 6 <= len(d) <= 12 else ""


def phones(*cells):
    out = []
    for c in cells:
        if not c:
            continue
        c = ascii_digits(str(c))
        parts = [p for p in re.split(r"\s*(?:,|/|;|\bor\b|&|\n|\s{2,})\s*", c) if p.strip()]
        for p in parts:
            n = one_phone(p)
            if not n:   # several numbers in one part without a separator
                for m in _PHONE.finditer(p):
                    n2 = one_phone(m.group(0))
                    if n2 and n2 not in out:
                        out.append(n2)
                continue
            if n not in out and not re.fullmatch(r"(\d)\1{5,}|0+", n.replace("-", "")):
                out.append(n)
    return ", ".join(out) or None


def email(s):
    s = deobfuscate(clean(s) or "")
    s = re.sub(r"\s+", "", s)
    return s.lower() if re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", s, re.I) else None


def rec(module, key, **f):
    d = {"type": "dept_office", "dept": "police", "level": "police_station"}
    for k, v in f.items():
        if isinstance(v, str):
            v = clean(v)
        if v not in (None, "", [], {}):
            d[k] = v
    return f"dept:{module}:{key}", d


def gz(module, name, content):
    """A raw answer, kept so the records can be re-parsed: depts/police/<module>/<name>.gz."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return (f"depts/police/{module}/{name}.gz", gzip.compress(content), "application/gzip")


def uniq(recs):
    """Same record id twice (a station listed twice): keep the first, number the rest."""
    seen, out = {}, []
    for rid, d in recs:
        if rid in seen:
            seen[rid] += 1
            rid = f"{rid}-{seen[rid]}"
        else:
            seen[rid] = 1
        out.append((rid, d))
    return out
