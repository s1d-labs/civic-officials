"""Shared helpers for the state-level readers (dforms/st_<state>_<source>.py, 2026-11-13): state secretariat telephone
directories, "Who's Who" pages of state portals, department contact pages, state police officer lists (DGP, range IGs/DIGs,
commissioners of police), divisional commissioners, state commissions (SEC, information, human rights, women, child rights)
and state public grievance officers.

Records follow the depts.py contract (type dept_office), with level "state" or "division", plus these keys:
  body        the office as the source names it ("Home Department", "Office of the Divisional Commissioner, Jalandhar",
              "Punjab State Information Commission")
  body_kind   secretariat | department | directorate | commission | police | division | governor | cm_office | other
  department  the state department the post belongs to, as the source names it (may equal body)
  post_kind   a fixed key for the rank (POST_KINDS below), so the site can sort and filter: chief_secretary, acs, ...
  division    the revenue division / police range / zone the post covers (division-level records)
  districts   LGD district codes the post covers, when the source or dforms/st_div_<st>.json says so (list of str)
  section     the heading of the list the row sits under, as the source writes it
level "state": the post covers the whole state (secretariat, HoD, commission, DGP). level "division": a revenue division,
police range or zone (area = its name). A district nodal officer that a state list names gets level "district" and district.
Readers keep every field the source gives (raw cells in "cells").
"""
import json
import re
from pathlib import Path

from dforms import _esw

HERE = Path(__file__).resolve().parent

# two-letter code (as in the depts records) -> (LGD state code, LGD state name)
STATES = {
    "AN": ("35", "Andaman And Nicobar Islands"), "AP": ("28", "Andhra Pradesh"), "AR": ("12", "Arunachal Pradesh"),
    "AS": ("18", "Assam"), "BR": ("10", "Bihar"), "CH": ("4", "Chandigarh"), "CG": ("22", "Chhattisgarh"),
    "DH": ("38", "The Dadra And Nagar Haveli And Daman And Diu"), "DL": ("7", "Delhi"), "GA": ("30", "Goa"),
    "GJ": ("24", "Gujarat"), "HR": ("6", "Haryana"), "HP": ("2", "Himachal Pradesh"), "JK": ("1", "Jammu And Kashmir"),
    "JH": ("20", "Jharkhand"), "KA": ("29", "Karnataka"), "KL": ("32", "Kerala"), "LA": ("37", "Ladakh"),
    "LD": ("31", "Lakshadweep"), "MP": ("23", "Madhya Pradesh"), "MH": ("27", "Maharashtra"), "MN": ("14", "Manipur"),
    "ML": ("17", "Meghalaya"), "MZ": ("15", "Mizoram"), "NL": ("13", "Nagaland"), "OD": ("21", "Odisha"),
    "PY": ("34", "Puducherry"), "PB": ("3", "Punjab"), "RJ": ("8", "Rajasthan"), "SK": ("11", "Sikkim"),
    "TN": ("33", "Tamil Nadu"), "TG": ("36", "Telangana"), "TR": ("16", "Tripura"), "UP": ("9", "Uttar Pradesh"),
    "UK": ("5", "Uttarakhand"), "WB": ("19", "West Bengal"),
}

# rank keys, tried in this order (the specific secretaries before the plain "secretary"); RANK below is the sort order
POST_KINDS = [
    ("personal_staff", r"\b(?:p\.?\s?p\.?\s?s|private secretary|personal secretary|personal assistant|p\.?\s?a\.?|o\.?\s?s\.?\s?d|"
                       r"a\.?\s?d\.?\s?c|aide[- ]de[- ]camp)\.?\s+to\b"),
    ("governor", r"\bgovernor\b(?!.*secretar)|\blt\.? governor\b|\badministrator\b(?=.*\bUT\b|$)"),
    ("chief_minister", r"^(hon'?ble\s+)?chief minister\b"),
    ("minister", r"\b(cabinet |deputy |state )?minister\b(?!.*secretar)"),
    ("chief_secretary", r"^(the\s+)?chief secretary\b|^cs\b"),
    ("acs", r"\badditional chief secretary\b|\badd(?:l|itional)?\.?\s*chief secretary\b|\bspecial chief secretary\b|"
            r"\bspl\.?\s*chief secretary\b|\badd(?:l|itional)?\.?\s*c\.?\s*s\.?\b|\bACS\b"),
    ("principal_secretary", r"\bprincipal secretary\b|\bpr\.?\s*secy\b|\bP\.?S\.?\b(?=\s*(?:to|,|-|\(|$))"),
    ("special_secretary", r"\bspecial secretary\b|\bspl\.?\s*secy"),
    ("additional_secretary", r"\badditional secretary\b|\baddl\.?\s*secy"),
    ("joint_secretary", r"\bjoint secretary\b|\bjt\.?\s*secy"),
    ("deputy_secretary", r"\bdeputy secretary\b|\bdy\.?\s*secy"),
    ("under_secretary", r"\bunder secretary\b|\bassistant secretary\b|\bsection officer\b"),
    ("secretary", r"^(the\s+)?(commissioner\s*(?:&|and)\s*)?secretary\b|\bsecretary\s*(?:to|,|-|\(|$)|^secy\b"),
    ("adgp", r"\badd(?:l|itional)?\.?\s*director general\b|\bADGP?\b|\bA\.D\.G\b"),
    ("dgp", r"\bdirector general of police\b|\bDGP\b|\bD\.G\.P\b|\bDG\s*(?:&|and)\s*IGP?\b"),
    ("special_cp", r"\bspecial commissioner of police\b|\bspl\.?\s*c\.?p\b"),
    ("joint_cp", r"\bjoint commissioner of police\b|\bjt\.?\s*c\.?p\b"),
    ("cp", r"(?<!additional )(?<!deputy )(?<!assistant )\bcommissioner of police\b|\bpolice commissioner\b|\bC\.?P\.?\b(?=\s*[,(-]|\s*$)"),
    ("dig", r"\bdeputy inspector general\b|\bDIGP?\b|\bD\.I\.G\b"),
    ("igp", r"\binspector general\b|\bIGP?\b|\bI\.G\.P?\b"),
    ("ssp", r"\bsenior superintendent of police\b|\bSSP\b"),
    ("dysp", r"\bdeputy superintendent of police\b|\bdy\.?\s*s\.?p\b|\bDSP\b"),
    ("sp", r"\bsuperintendent of police\b|\bS\.?P\.?\b(?=\s*[,(-]|\s*$)"),
    ("divisional_commissioner", r"(?<!additional )(?<!deputy )(?<!joint )\bdivisional commissioner\b|"
                                r"(?<!additional )(?<!deputy )(?<!joint )\bcommissioner,?\s+\w+\s+(?:revenue\s+)?division\b|"
                                r"\bregional commissioner\b|\brevenue divisional commissioner\b"),
    ("state_election_commissioner", r"\bstate election commissioner\b"),
    ("chief_information_commissioner", r"\bchief information commissioner\b|\bCIC\b"),
    ("information_commissioner", r"\binformation commissioner\b|\bSIC\b"),
    ("vice_chairperson", r"\bvice[- ]chair"),
    ("chairperson", r"\bchair(?:person|man|woman)\b"),
    ("collector", r"\bdistrict collector\b|^collector\b|\bdistrict magistrate\b|\bdeputy commissioner\b(?!.*police)"),
    ("officer", r"\b(?:joint|deputy|additional|addl\.?|assistant|asst\.?)\s+director\b"),
    ("member", r"^(hon'?ble\s+)?member\b|\bmember\s*(?:secretary)?\b"),
    ("head_of_department", r"\bdirector general\b|\bdirector\b|\bcommissioner\b|\bcontroller\b|\bregistrar\b|"
                           r"\bchief engineer\b|\bconservator\b|\bmission director\b|\bmanaging director\b|\bchief executive\b"),
    ("grievance_officer", r"\bgrievance\b|\bpublic grievance\b|\bnodal officer\b"),
    ("pio", r"\bpublic information officer\b|\bP\.?I\.?O\b|\bappellate authority\b"),
]
RANK = ["governor", "chief_minister", "minister", "chief_secretary", "acs", "principal_secretary", "special_secretary",
        "secretary", "additional_secretary", "joint_secretary", "deputy_secretary", "under_secretary", "dgp", "adgp", "special_cp",
        "joint_cp", "cp", "igp", "dig", "divisional_commissioner", "collector", "ssp", "sp", "dysp", "state_election_commissioner",
        "chief_information_commissioner", "information_commissioner", "chairperson", "vice_chairperson", "member",
        "head_of_department", "officer", "grievance_officer", "pio", "personal_staff"]
_POST_RX = [(k, re.compile(rx, re.I)) for k, rx in POST_KINDS]
_POST_D = dict(_POST_RX)
_TO_HIGH = re.compile(r"(?<=\w)[\s,.]+to\s+(?:the\s+)?(?:hon'?ble\s+)?(?:chief minister|c\.?\s?m\.?|minister\b|governor|lt\.? governor)\b.*$", re.I)

# department words -> TAGGING.md dept key (first match wins)
DEPTS = [
    ("police", r"police|home guard|\bvigilance\b|crime|prison|jail|correctional"),
    ("elections", r"election"),
    ("revenue", r"revenue|land|disaster|relief|settlement|survey|registration|stamp"),
    ("health", r"health|medical|family welfare|ayush|drug"),
    ("education", r"education|school|higher|technical|university|literacy|sarva shiksha|samagra"),
    ("food_supplies", r"food|civil supplies|consumer"),
    ("rural_development", r"rural|panchayat"),
    ("town_body", r"urban|municipal|housing|town planning|local (self )?government|local bodies"),
    ("public_works", r"public works|\bworks\b|\bpwd\b|roads|building"),
    ("water", r"water|irrigation|phed|jal|public health engineering|drinking"),
    ("electricity", r"power|energy|electric"),
    ("women_child", r"women|child|icds"),
    ("agriculture", r"agricultur|horticultur|animal|fisher|veterinar|dairy|cooperati|sericulture"),
    ("labour_industry", r"micro,? small|\bmsme\b"),
    ("social_welfare", r"social|welfare|tribal|scheduled|backward|minorit|disab|empowerment"),
    ("transport", r"transport"),
    ("forest", r"forest|environment|wildlife|climate"),
    ("treasury", r"finance|treasur|account|budget"),
    ("excise_tax", r"excise|taxation|commercial tax|\bgst\b|\btax"),
    ("labour_industry", r"labour|industr|commerce|employment|skill|msme|mines|textile"),
    ("planning", r"planning|statistic|economics"),
    ("courts", r"law|judicial|legal|justice|court"),
    ("information", r"information|public relations|\bipr\b|\bdipr\b"),
    ("sports_culture", r"sport|youth|culture|tourism|art"),
    ("fire", r"\bfire\b"),
    ("administration", r"general administration|\bgad\b|personnel|chief secretary|chief minister|governor|raj bhavan|"
                       r"cabinet|secretariat|administrative reforms|appointment|\bcm\b|vidhan|legislat|parliamentary"),
]
_DEPT_RX = [(k, re.compile(r"\b(?:" + rx + ")", re.I)) for k, rx in DEPTS]


def post_kind(post):
    """The rank key of a post text ("Principal Secretary to Govt.", "IGP, Jalandhar Range") or "" when none fits."""
    t = _esw.clean(post)
    if _POST_D["personal_staff"].search(t):      # PPS / PA / OSD / ADC to someone: their own rank, not the principal's
        return "personal_staff"
    # "Principal Secretary to the Chief Minister", "Secretary to Governor": the post's own rank, not the CM's or Governor's
    t = _TO_HIGH.sub("", t) or t
    for k, rx in _POST_RX:
        if rx.search(t):
            return k
    return ""


def dept_key(*texts):
    """TAGGING.md dept key of a department / office name ("Department of Water Resources" -> water); "administration" when the
    text names no field (the secretariat itself), "other" for empty input."""
    t = " ".join(_esw.clean(x) for x in texts if x)
    if not t:
        return "other"
    for k, rx in _DEPT_RX:
        if rx.search(t):
            return k
    return "administration"


_DIV = {}


def divisions(state):
    """{division name: [LGD district codes]} of one state, from dforms/st_div_<state lower>.json (made by hand from the state's
    own list of divisions; {} when the file is not there)."""
    st = state.upper()
    if st not in _DIV:
        f = HERE / f"st_div_{st.lower()}.json"
        _DIV[st] = json.loads(f.read_text())["divisions"] if f.exists() else {}
    return _DIV[st]


def div_key(s):
    return re.sub(r"[^a-z]", "", re.sub(r"(?i)\b(division|divisional|range|zone|commissionerate|revenue|police|region)\b", "", s or "").lower())


def districts_of(state, division):
    """(division name as the state file spells it, [LGD district codes]) for a division name in any spelling; ("", []) if unknown."""
    k = div_key(division)
    if not k:
        return "", []
    for name, codes in divisions(state).items():
        if div_key(name) == k:
            return name, list(codes)
    return "", []


HONORIFIC = re.compile(r"(?i)^(dr|sh|shri|smt|sri|mr|mrs|ms|miss|kumari|km|thiru|tmt|selvi|er|prof|capt|col|lt\.?\s*col)\b\.?\s*")
SERVICE = re.compile(r"(?i),?\s*\(?\b(I\.?A\.?S|I\.?P\.?S|I\.?F\.?S|IRS|IAAS|PCS|HCS|RAS|WBCS|KAS|OAS|BAS|MCS|PCS|HPAS|JKAS|"
                     r"TNCS|APCS|IPoS|IRTS|IDAS|IRAS|ITS|IES|IRSE)\.?\b\)?(\s*\(\s*retd\.?\s*\))?")


def name_parts(s):
    """(name as written, service) of a name cell: "Sh. Anurag Verma, IAS" -> ("Sh. Anurag Verma, IAS", "IAS"). The name is
    not changed (titles and service stay as the source writes them)."""
    s = _esw.clean(s)
    m = SERVICE.search(s)
    return s, (re.sub(r"[^A-Za-z]", "", m.group(1)).upper() if m else "")


def rec(module, key, *, state, level, post, name="", body="", body_kind="", department="", division="", district="",
        district_code="", districts=None, phone="", email="", address="", source="", src_url="", src_pos=None, **extra):
    """(record id, data) for one state-level post (depts.py contract plus the keys in this module's docstring).
    area: the state name for level state, the division for level division, the district for level district.
    division: the division's districts come from dforms/st_div_<st>.json when the reader does not give them."""
    st = state.upper()
    code, sname = STATES.get(st, ("", ""))
    div_name, codes = ("", [])
    if division:
        div_name, codes = districts_of(st, division)
    if districts is None:
        districts = codes
    area = {"state": sname, "division": division, "district": district}.get(level) or sname
    nm, service = name_parts(name)
    if re.fullmatch(r"(?i)(post\s+)?vacant|vacancy|-+|nil|n/?a", nm or ""):
        extra.setdefault("vacant", True)
        nm = ""
    return _esw.record(
        module, key, dept=extra.pop("dept", None) or dept_key(department, body, post), level=level, area=area, state=st,
        state_code=code or None, post=post, post_kind=extra.pop("post_kind", None) or post_kind(post), name=nm,
        service=extra.pop("service", None) or service or None, body=body, body_kind=body_kind, department=department or None,
        division=division or None, division_lgd_name=div_name or None, districts=districts or None, district=district or None,
        district_code=district_code or None, phone=phone, email=email, address=address, source=source or src_url,
        src_url=src_url or source, src_pos=src_pos, **extra)
