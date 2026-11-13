"""Bihar: district and block health officers from the State Health Society's phone directory (shs.bihar.gov.in/phone-directory.php).

The page loads its tabs with jQuery POSTs (the page's own script; no key, no token):
- ajax/get_contact_district_data  {page, query: "", district: <site id>}: Sl No | District | Name | Designation | Contact No |
  Alternet No | Fax | Email. Per district: the District Magistrate, the Civil Surgeon (the district's chief medical officer),
  DPM, ACMO, DIO, DMO, DAM, ... (Patna 16 rows, 2026-11-12).
- ajax/get_contact_block_data  {page, query: "", district: <site id>, blockid: ""}: Sl No | District | Block | Name |
  Designation | Contact No | Alternate No | Fax | Email: MOIC and BHM of every block PHC (Patna 46 rows).
Both answer an HTML table plus a pager (a.page-link data-page_number); every page is read.
The site's certificate chain is self-signed (the task's insecure retry; records get tls_unverified). The archive saved the
page from the GitHub runners (vantage pool, 2026-11-11): the site answers abroad.

Records (depts.py contract): dept health (the District Magistrate row: administration); level district or block (area = block);
post = the designation as written ("CIVIL SURGEON", "MOIC", "BHM"), name, phone (contact, alternate, fax), email,
district (LGD name). One queue item = one district (2 POSTs, more if a list has pages).
Ids: dept:health_br_shs:<district|block>:<site district id>[:<block>]:<post>:<name> (slugs).
"""
import re

import provenance
from dforms import _esw

METHOD = "html table (ajax POST pages)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "health_br_shs"
BASE = "https://shs.bihar.gov.in/"
PAGE = BASE + "phone-directory.php"
# site district id -> LGD district name
DISTRICTS = {
    "7": "Araria", "41": "Arwal", "34": "Aurangabad", "23": "Banka", "20": "Begusarai", "22": "Bhagalpur", "29": "Bhojpur",
    "30": "Buxar", "13": "Darbhanga", "2": "Purbi Champaran", "35": "Gaya", "15": "Gopalganj", "37": "Jamui", "33": "Jehanabad",
    "31": "Kaimur (Bhabua)", "10": "Katihar", "21": "Khagaria", "8": "Kishanganj", "25": "Lakhisarai", "11": "Madhepura",
    "5": "Madhubani", "24": "Munger", "14": "Muzaffarpur", "27": "Nalanda", "36": "Nawada", "28": "Patna", "9": "Purnia",
    "32": "Rohtas", "12": "Saharsa", "19": "Samastipur", "17": "Saran", "26": "Sheikhpura", "3": "Sheohar", "4": "Sitamarhi",
    "16": "Siwan", "6": "Supaul", "18": "Vaishali", "1": "Pashchim Champaran",
}
KINDS = {"district": "ajax/get_contact_district_data", "block": "ajax/get_contact_block_data"}


def pages(html):
    """Highest page number the pager offers (1 when there is no pager)."""
    nums = [int(x) for x in re.findall(r'data-page_number\s*=\s*["\']?(\d{1,3})', html or "")]
    return max(nums + [1])


def parse(html, kind, did, district):
    s = _esw.soup(html)
    recs = []
    head = None
    for n, tr in enumerate(s.find_all("tr"), 1):
        cells = [_esw.cell_text(c) for c in tr.find_all(["td", "th"])]
        if tr.find("th") or (cells and cells[0].lower().startswith("sl")):
            head = [c.lower() for c in cells]
            continue
        if not head or len(cells) < len(head) - 1 or not re.match(r"^\d+$", cells[0] or ""):
            provenance.skip_row(tr, 'skip: not head or len(cells) < len(head) - 1 or not re.match(r"^\\d+$", ce...')
            continue
        row = dict(zip(head, cells))
        name = row.get("name", "")
        post = row.get("designation", "")
        phone = _esw.phones(row.get("cotnact no") or row.get("contact no", ""), row.get("alternet no") or row.get("alternate no", ""))
        fax = _esw.phones(row.get("fax", ""))
        email = _esw.emails(row.get("email", ""))
        if not (name or phone or email):
            provenance.skip_row(tr, 'skip: not (name or phone or email)')
            continue
        dept = "administration" if re.search(r"(?i)district magistrate|collector", post) else "health"
        block = row.get("block", "") if kind == "block" else ""
        key = ":".join(x for x in (kind, did, _esw.slug(block), _esw.slug(post), _esw.slug(name)) if x)
        recs.append(_esw.record(MODULE, key, dept=dept, level="block" if kind == "block" else "district",
                                area=block or district, block=block or None, post=post, name=name, phone=phone, fax=fax or None,
                                email=email, district=district, district_site=row.get("district") or None, state="BR",
                                source=PAGE, page=PAGE, serial=cells[0], src_pos={"row": n}))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}:{did}", "payload": {"reader": MODULE, "url": PAGE, "district_id": did, "district": name,
                                                   "state": "BR"}}
            for did, name in sorted(DISTRICTS.items(), key=lambda x: x[1])]


def fetch(p, get):
    did, district = str(p["district_id"]), p.get("district") or DISTRICTS.get(str(p["district_id"]), "")
    recs, files, why = [], [], []
    hdr = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest",
           "Referer": PAGE}
    for kind, path in KINDS.items():
        page, last = 1, 1
        while page <= min(last, 50):
            data = {"page": str(page), "query": "", "district": did}
            if kind == "block":
                data["blockid"] = ""
            r = get(BASE + path, method="POST", data=data, headers=hdr)
            if r is None:
                why.append(f"{kind} page {page}: no answer")
                break
            files.append(_esw.keep(MODULE, f"{did}/{kind}-{page}", r.content))
            got = parse(r.text, kind, did, district)
            src = provenance.at(r, BASE + path)        # one url, one answer per page: the hash names the answer
            for _, d in got:
                d.update(src)
                d["src_pos"] = {"ajax_page": page, **d.get("src_pos", {})}   # row: <tr> number in the answer's html
            recs += got
            last = pages(r.text)
            page += 1
    seen, out = set(), []
    for rid, d in recs:          # the same person twice in one list: keep the first row
        if rid not in seen:
            seen.add(rid)
            out.append((rid, d))
    return out, files, "; ".join(why) if not out else ""
