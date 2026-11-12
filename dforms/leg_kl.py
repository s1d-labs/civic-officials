"""Kerala Legislative Assembly: every sitting MLA with phone, mobile, email, home address and MLA Hostel room, from
https://niyamasabha.nic.in/index.php/content/member_contacts (one HTML table, 140 rows, ~270 KB).

Columns: Sl. No | Name of member (Constituency) | Permanent Address | Telephone / Mobile | E-mail. The phone cell often starts
with the member's office in Thiruvananthapuram ("MLA Hostel, Neyyar Block 6C, 0471-2512226 | 9447978800"): that text goes to
office_address. The page gives no party and no AC number: the constituency name goes to the ECI number (ac_no.json, with the
spellings of ero_kl.ALIAS and ALIAS here).
The server omits its Let's Encrypt intermediate (YR2): certs/letsencrypt_gen_y_yr1_yr2_root_yr_by_x1.pem completes the chain to ISRG
Root X1 (verification stays on). The archive copy (2026-11-05) is cut off at 32 KB, so the reader needs the live page.
Record ids: dept:leg_kl:KL-AC-<no>.
"""
import re

from dforms import _esw, _leg
from dforms.ero_kl import ALIAS as ERO_ALIAS

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_kl"
URL = "https://niyamasabha.nic.in/index.php/content/member_contacts"
ALIAS = {"karunagapally": "karunagappally", "kuttiady": "kuttiadi", "kunnathunadu": "kunnathunad", "thrikkaripur": "trikaripur",
         "thirurangadi": "tirurangadi"}
FIRST_PHONE = re.compile(r"\(?0\d{2,4}\)?[\s-]*\d{5,8}|(?:\+?91[\s-]*)?\b[6-9]\d{9}\b")   # STD number or mobile


def items(get=None):
    return [{"key": f"{MODULE}-contacts", "payload": {"reader": MODULE, "url": URL, "state": "KL", "india_only": False}}]


def ac(name):
    k = _leg.norm(name)
    for cand in (k, ERO_ALIAS.get(k), ALIAS.get(k)):
        if cand and _esw.ac_no("KL", cand):
            return _esw.ac_no("KL", cand)
    return None


def parse(html, url):
    recs = []
    for table in _esw.soup(html).find_all("table"):
        rows = _esw.grid(table)
        if not rows or "constituency" not in " ".join(rows[0]).lower():
            continue
        for row in rows[1:]:
            row = row + [""] * (5 - len(row))
            m = re.match(r"\s*(.+?)\s*\|?\s*\(\s*(.+)\)\s*$", row[1])
            if not m:
                continue
            name, const = m.group(1).strip(" |"), m.group(2).strip()
            const = re.sub(r"\s*\(\s*(SC|ST)\s*\)\s*", r" (\1)", const).strip()
            cut = FIRST_PHONE.search(row[3])          # "Nila Block 53 0471-2512317 | 99952..." -> office "Nila Block 53"
            office = _leg.clean((row[3][:cut.start()] if cut else row[3]).replace("|", " ")).strip(" ,;-")
            phone = row[3][cut.start():] if cut else (row[3] if not re.search(r"[A-Za-z]{3,}", row[3]) else "")  # as written
            no = ac(const)
            recs.append(_leg.member(MODULE, "KL", "AC", no, name, constituency=const, source=url, phone=phone,
                                    email=row[4], residence_address=row[2].replace(" | ", ", "),
                                    office_address=office if re.search(r"[A-Za-z]{3,}", office) else "",
                                    house="Kerala Legislative Assembly", term="16th KLA"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "member_contacts", r.content, "html")]
    recs = parse(r.content, p["url"])
    return recs, files, "" if recs else "no member table"
