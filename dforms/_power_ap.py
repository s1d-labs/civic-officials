"""Shared reading of Andhra Pradesh discom designations (APSPDCL, APEPDCL, APCPDCL): the post code and the office are written
together, e.g. "AE/O/Kallur", "Dy.EE/ O/Seethammadhara", "EE TOWN-1 GUNTUR", "DE / O / Adoni", "A.D.E/Opn./Rayachoti".
Operation posts: SE = circle, EE / DE = division, DEE / Dy.EE / ADE = sub-division, AEE / AE / AAE / JE = section (the AP
discoms put an AE or AEE at the head of each operation section). A post with a wing word (technical, commercial, M&P, DPE,
construction, meters, ERO ...) or a non-engineer post (AAO, JAO, CI ...) is a staff post of the office it sits in: it gets the
level of that office (circle or division) and the office's own area.
"""
import re

from dforms._power import clean

LONG = ((r"deputy executive engineer", "DYEE"), (r"assistant executive engineer", "AEE"), (r"assistant divisional engineer", "ADE"),
        (r"executive engineer", "EE"), (r"superintending engineer", "SE"), (r"divisional engineer", "DE"),
        (r"assistant engineer", "AE"), (r"junior engineer", "JE"))
LEVEL = {"SE": "circle", "EE": "division", "DE": "division", "DEE": "subdivision", "DYEE": "subdivision", "ADE": "subdivision",
         "AEE": "section", "AE": "section", "AAE": "section", "JE": "section"}
FUNC = re.compile(r"\b(TECH\w*|COMM?L|COMMERCIAL|M\s*&\s*P(-\d)?|MRT|CONST\w*|TRANSFORMERS?|TRE|SPM|PROTECTION|\w*METERS?|HTM|LTM|"
                  r"STORES?|CIVIL|INHOUSE|ASSESSMENT|DPE(-\d)?|ERO|PH|IT|ACCOUNTS?|REV|REVENUE|PLANNING|PROJECTS?|LMC|CSC|QC|"
                  r"APTS|OCC|C\.?\s?C\.?\s?O|PMU|RDSS|DDUGJY|IPDS|SOLAR|ENERGY|AUDIT|LEGAL|HRD?|ADMIN\w*|SCADA|ESTIMATION|CGRF|"
                  r"VIGILANCE|TRAINING|INSPECTOR|EXPENDITURE|IRDA|NABL|PROCUREMENT|TPSS|SAFETY|DRAWING|DESIGN\w*|MMS|"
                  r"C\.?O|DIST\.?\s*STORES|INTERNAL|LEC|DATA)\b", re.I)
DROP = {"O", "OPN", "OPERATION", "OPERATIONS", "OP", "D.O", "DO", "OPN.", "(O)", "SECTION"}


def split(desig):
    """(post code, office words) of one designation; code None when it is not an engineer post."""
    d = clean(desig) or ""
    low = d.lower()
    for rx, code in LONG:
        if low.startswith(rx):
            return code, d[len(rx):]
    m = re.match(r"\s*([A-Za-z.\s]{1,9}?)\s*(?:[/:-]|\s(?=\S)|$)(.*)", d)
    if not m:
        return None, d
    code = re.sub(r"[^A-Z]", "", m.group(1).upper())
    code = {"DYEE": "DYEE", "DYE": "DYEE", "DYEXE": "DYEE"}.get(code, code)
    if code not in LEVEL:
        return None, d
    return code, m.group(2)


def place(rest):
    parts = [p.strip(" .,-") for p in re.split(r"\s*/\s*", rest or "") if p.strip(" .,-")]
    if len(parts) == 1:                                  # "TOWN-1 GUNTUR", "O TENALI": words split by spaces
        parts = [w for w in parts[0].split()]
        return clean(" ".join(w for w in parts if w.upper() not in DROP))
    return clean(" ".join(p for p in parts if p.upper() not in DROP))


def classify(desig, office_level="circle", office_area=None):
    """(level, area, staff) for one designation. staff = True for a wing or non-engineer post of the office."""
    code, rest = split(desig)
    if code is None or FUNC.search(rest or "") or (code in ("EE", "DE", "SE") and FUNC.search(desig or "")):
        return office_level, office_area, True
    if code == "SE":
        return "circle", office_area or place(rest), False
    return LEVEL[code], place(rest) or office_area, False
