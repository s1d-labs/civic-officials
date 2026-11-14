"""Bank ATMs of India with their map point: the Department of Financial Services ATM layer on Bharatmaps (2022; 196,360 rows), as
compiled by ramSeraph/indian_facilities (release "banking", Bharatmaps_DFS_Bank_ATMs_2022.parquet). Rows with only the IFSC bank code take the bank name from BANKS
(else the code itself). Columns used: atm_cd,
bank_name, atm_ad (address), atm_city, atm_area, atm_pin_cd, atm_site (onsite / offsite), atm_type, atm_time, atm_help_c (help
line), atm_own (owner type: bank, brown label, Bhagidari ...), atm_oper (the operator: FIS, AGS ...), stcode11 / state_cd /
state_name, dtname11 / district_n, bbox. Record id dept:points_atm_dfs:<bank code>-<ATM id> (row number when the ATM id is
missing); dept banking, layer atm, area "<bank> ATM". Seed: seeds/dept_points_atm_all.json; shared code dforms/_points.py.

Owning branch (branch_ifsc, 2026-11-14): three banks write the branch that owns the ATM into the ATM id. The rules below were checked
on the first 400 rows of the file against the RBI IFSC list (dforms/central_banking.py records in civic.dept_office): every
derived IFSC that the RBI list has is a branch of the ATM's own district (SBI 53 of 53, Canara 38 of 38, Syndicate 23 of 23);
14 SBI and 1 Syndicate IFSCs are not in the 2026 list (closed or merged branches). Other banks' ids gave branches in other districts
(Karnataka Bank, Bank of India, Corporation Bank) or no branch at all (IOB, Vijaya): no branch_ifsc for them.
  - SBI (and the old associate banks SBMY, SBTR, SBHY, SBBJ, SBPS, merged into SBI in 2017): S1 + 2 letters (or S10 + 1 letter)
    + the 6-digit branch code + 3-digit serial: "S1BB005080002" -> SBIN0005080. For SBI this is the base branch that runs the
    ATM (often the main branch of the town), not always the nearest branch.
  - Canara Bank: 8 characters, the first 4 digits the branch: "13336148" -> CNRB0001333.
  - Syndicate Bank (merged into Canara Bank in 2020; its branches took CNRB001 + the old 4-digit code): "A0199001" -> CNRB0010199.
civic-india checks each derived IFSC against the RBI list before it uses it.
"""
import re

from dforms import _esw, _points

MODULE = "points_atm_dfs"
METHOD = _points.METHOD
COLUMNS = ["atm_cd", "bank_name", "bank_cd", "atm_ad", "atm_city", "atm_area", "atm_pin_cd", "atm_site", "atm_type", "atm_time",
           "atm_help_c", "atm_own", "atm_oper", "stcode11", "state_cd", "state_name", "dtname11", "district_n"]
SBI = {"SBIN", "SBMY", "SBTR", "SBHY", "SBBJ", "SBPS"}
OWN_NONE = {"na", "n", "nil", "-", "none", "no", "not applicable", "&nbsp;", "no white label atm"}


# IFSC bank codes of rows that give the code without the bank name (the 2022 mobile edits, editstatus "Mob_AL")
BANKS = {"SBIN": "State Bank of India", "CNRB": "Canara Bank", "CORP": "Corporation Bank", "VIJB": "Vijaya Bank",
         "FDRL": "Federal Bank", "BKID": "Bank of India", "BARB": "Bank of Baroda", "PUNB": "Punjab National Bank",
         "UBIN": "Union Bank of India", "SYNB": "Syndicate Bank", "KARB": "Karnataka Bank", "IOBA": "Indian Overseas Bank",
         "IDIB": "Indian Bank", "CBIN": "Central Bank of India", "MAHB": "Bank of Maharashtra", "UCBA": "UCO Bank",
         "PSIB": "Punjab and Sind Bank", "HDFC": "HDFC Bank", "ICIC": "ICICI Bank", "UTIB": "Axis Bank", "KKBK": "Kotak Mahindra Bank",
         "ANDB": "Andhra Bank", "ALLA": "Allahabad Bank", "ORBC": "Oriental Bank of Commerce", "UTBI": "United Bank of India",
         "KVBL": "Karur Vysya Bank", "CIUB": "City Union Bank", "SIBL": "South Indian Bank", "LAVB": "Lakshmi Vilas Bank",
         "TMBL": "Tamilnad Mercantile Bank", "IBKL": "IDBI Bank", "YESB": "Yes Bank", "INDB": "IndusInd Bank"}


def branch_ifsc(code, atm):
    """The IFSC of the branch that owns the ATM, from the ATM id (rules in the docstring), else None."""
    atm = (atm or "").strip().upper()
    if code in SBI:
        m = re.fullmatch(r"S1[A-Z0-9]{2}(\d{6})\d{3}", atm) or re.fullmatch(r"S10[A-Z](\d{6})\d{3}", atm)
        return "SBIN0" + m.group(1) if m else None
    if code == "CNRB":
        m = re.fullmatch(r"(\d{4})\d{4}", atm)
        return "CNRB000" + m.group(1) if m else None
    if code == "SYNB":
        m = re.fullmatch(r"A(\d{4})\d{3}", atm)
        return "CNRB001" + m.group(1) if m else None
    return None


def label(v):
    """An owner / operator cell as text, None for NA / NIL / -."""
    return None if not v or v.strip().lower() in OWN_NONE else v.strip()


def make(row, n, p):
    v = _points.val
    code, atm = (v(row.get("bank_cd")) or "").upper(), v(row.get("atm_cd"))
    bank = v(row.get("bank_name")) or BANKS.get(code) or (code if re.fullmatch(r"[A-Z]{4}", code) else None)
    if not bank:
        return None, "no bank name or code"
    key = f"{v(row.get('bank_cd')) or 'x'}-{atm}" if atm else f"r{n}"
    return key, dict(layer="atm", dept="banking", area=f"{bank} ATM", bank=bank, office_id=atm, address=v(row.get("atm_ad")),
                     city=v(row.get("atm_city")), place=v(row.get("atm_area")), pin=v(row.get("atm_pin_cd")),
                     atm_site=v(row.get("atm_site")), atm_type=v(row.get("atm_type")), hours=v(row.get("atm_time")),
                     phone=_esw.phones(v(row.get("atm_help_c")) or "") or None, branch_ifsc=branch_ifsc(code, atm),
                     atm_owner=label(v(row.get("atm_own"))), atm_operator=label(v(row.get("atm_oper"))),
                     state=_points.state_of(row.get("stcode11"), row.get("state_cd"), row.get("state_name")),
                     district=v(row.get("dtname11")) or v(row.get("district_n")))


def fetch(p, get):
    return _points.fetch(p, get, MODULE, make, COLUMNS)
