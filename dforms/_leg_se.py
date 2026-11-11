"""Small helpers for the south / east / north-east MLA readers (dforms/leg_tn, leg_ap, leg_py, leg_od, leg_as, leg_ml, leg_mz,
leg_mn, leg_tr, leg_nl, leg_sk). The shared rules (record shape, seat numbers) are in dforms/_leg.py."""
import re

from dforms import _esw, _leg

TITLES = re.compile(r"^(?:(?:hon'?ble|hon\.?|shri\.?|sri\.?|smt\.?|smti\.?|kumari|km\.?|selvi|thiru\.?|tmt\.?|mr\.?|mrs\.?|ms\.?|"
                    r"adv\.?)\s+)+", re.I)


def name(s):
    """A member's name without the leading honorifics (Shri, Smt, Thiru, Hon'ble ...); Dr., Prof., Lt. Col. stay."""
    s = _esw.clean(s)
    prev = None
    while prev != s:
        prev, s = s, TITLES.sub("", s).strip(" .,")
    return s


def seat(state, no, constituency, district=None, alias=None):
    """(site AC number, note): the source number when it is given, else the number for the constituency name."""
    c = re.sub(r"\s+", " ", constituency or "").strip()
    if alias:
        c = alias.get(_esw.norm_ac(c), c)
    n, note = _leg.ac_seat(state, no, c, district)
    if not n and c:
        n, note = _leg.ac_seat(state, None, re.sub(r"\((sc|st|bl|gen)\)", "", c, flags=re.I), district)
    return n, note


def title(s):
    """'DHOLAI (SC)' -> 'Dholai (SC)'."""
    return re.sub(r"\((sc|st|bl)\)", lambda m: m.group(0).upper(), _esw.clean(s).title(), flags=re.I)
