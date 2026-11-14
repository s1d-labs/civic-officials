"""Bank ATMs of India with their map point: the Department of Financial Services ATM layer on Bharatmaps (2022; 196,360 rows), as
compiled by ramSeraph/indian_facilities (release "banking", Bharatmaps_DFS_Bank_ATMs_2022.parquet). Rows with only the IFSC bank code take the bank name from BANKS
(else the code itself). Columns used: atm_cd,
bank_name, atm_ad (address), atm_city, atm_area, atm_pin_cd, atm_site (onsite / offsite), atm_type, atm_time, atm_help_c (help
line), stcode11 / state_cd / state_name, dtname11 / district_n, bbox. Record id dept:points_atm_dfs:<bank code>-<ATM id> (row
number when the ATM id is missing); dept banking, layer atm, area "<bank> ATM". Seed: seeds/dept_points_atm_all.json; shared code
dforms/_points.py.
"""
import re

from dforms import _esw, _points

MODULE = "points_atm_dfs"
METHOD = _points.METHOD
COLUMNS = ["atm_cd", "bank_name", "bank_cd", "atm_ad", "atm_city", "atm_area", "atm_pin_cd", "atm_site", "atm_type", "atm_time",
           "atm_help_c", "stcode11", "state_cd", "state_name", "dtname11", "district_n"]


# IFSC bank codes of rows that give the code without the bank name (the 2022 mobile edits, editstatus "Mob_AL")
BANKS = {"SBIN": "State Bank of India", "CNRB": "Canara Bank", "CORP": "Corporation Bank", "VIJB": "Vijaya Bank",
         "FDRL": "Federal Bank", "BKID": "Bank of India", "BARB": "Bank of Baroda", "PUNB": "Punjab National Bank",
         "UBIN": "Union Bank of India", "SYNB": "Syndicate Bank", "KARB": "Karnataka Bank", "IOBA": "Indian Overseas Bank",
         "IDIB": "Indian Bank", "CBIN": "Central Bank of India", "MAHB": "Bank of Maharashtra", "UCBA": "UCO Bank",
         "PSIB": "Punjab and Sind Bank", "HDFC": "HDFC Bank", "ICIC": "ICICI Bank", "UTIB": "Axis Bank", "KKBK": "Kotak Mahindra Bank",
         "ANDB": "Andhra Bank", "ALLA": "Allahabad Bank", "ORBC": "Oriental Bank of Commerce", "UTBI": "United Bank of India",
         "KVBL": "Karur Vysya Bank", "CIUB": "City Union Bank", "SIBL": "South Indian Bank", "LAVB": "Lakshmi Vilas Bank",
         "TMBL": "Tamilnad Mercantile Bank", "IBKL": "IDBI Bank", "YESB": "Yes Bank", "INDB": "IndusInd Bank"}


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
                     phone=_esw.phones(v(row.get("atm_help_c")) or "") or None,
                     state=_points.state_of(row.get("stcode11"), row.get("state_cd"), row.get("state_name")),
                     district=v(row.get("dtname11")) or v(row.get("district_n")))


def fetch(p, get):
    return _points.fetch(p, get, MODULE, make, COLUMNS)
