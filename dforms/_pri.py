"""Shared helpers for the Panchayati Raj (PRI) elected-member readers (dforms/pri_<state>.py), run by the depts task.

One record = one elected person of one panchayat body (or one result row: a seat with its winner):
  id   "pri:<module>:<key>"
  data {"type": "pri_member",
        "state": "BR",                       two-letter code (as the councillor readers use)
        "level": "zp" | "ps" | "gp",         zilla/district panchayat, block/intermediate (panchayat samiti, kshetra, janpad,
                                             anchalik, BDC), gram/gaon/halqa panchayat
        "role": "head" | "deputy" | "member",
        "post": "Mukhiya",                   English post as the source (or the state's law) names it
        "post_regional": "मुखिया",
        "name", "name_regional", "father_name", "gender", "category" (reservation of the seat or of the person, as given),
        "party", "votes", "age", "phone", "email", "address",
        "body_name": "Rampur",               the panchayat as written by the source (English or regional)
        "body_name_regional",
        "district", "block",                 as written by the source (district/block of the body)
        "ward" / "ward_no" / "constituency", the member's ward or territorial constituency (ZP/PS/GP members)
        "lgd_code": "123456",                LGD local_body_code of the body when the source or a safe match gives it
        "lgd_match": "source" | "name",      how lgd_code was set (source = the page gives the LGD code)
        "election": "Bihar Panchayat General Election 2021",  the round
        "election_year": 2021,
        "result_date", "status" ("won", "elected unopposed", ...),
        "source": url, "src_url": url, "src_pos": {...}, "cells": {header: text} (every raw cell kept)}
Fields the source does not give are left out. The loader (civic-india sql/75_pri_member.sql) maps lgd_code where empty.
"""
import re

from dforms._esw import clean, grid, keep, phones, slug, soup  # noqa: F401  (re-exported for the readers)

LEVELS = ("zp", "ps", "gp")
ROLES = ("head", "deputy", "member")
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
OR_DIGITS = str.maketrans("୦୧୨୩୪୫୬୭୮୯", "0123456789")
GU_DIGITS = str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789")
PA_DIGITS = str.maketrans("੦੧੨੩੪੫੬੭੮੯", "0123456789")


def digits(s):
    """Indian-script digits -> ASCII digits (other text unchanged)."""
    return (s or "").translate(DEV_DIGITS).translate(BN_DIGITS).translate(OR_DIGITS).translate(GU_DIGITS).translate(PA_DIGITS)


def int_or_none(s):
    """An int only when the text is digits (commas allowed); else None. Never cast scraped text without this check."""
    t = re.sub(r"[,\s]", "", digits(clean(s)))
    return int(t) if t.isdigit() else None


def mobile(s):
    """The first 10-digit Indian mobile number in a text (with or without +91 / 0), else ''."""
    t = re.sub(r"[\s-]", "", digits(clean(s)))
    m = re.search(r"(?<!\d)(?:\+?91|0)?([6-9]\d{9})(?!\d)", t)
    return m.group(1) if m else ""


def record(module, key, **f):
    """(record id, data) for one PRI member; empty values dropped; strings cleaned; level / role checked."""
    d = {"type": "pri_member"}
    for k, v in f.items():
        if isinstance(v, str):
            v = clean(v)
        if v not in (None, "", [], {}):
            d[k] = v
    assert d.get("level") in LEVELS, d
    assert d.get("role") in ROLES, d
    assert d.get("state") and d.get("post") and d.get("source"), d
    return f"pri:{module}:{key}", d
