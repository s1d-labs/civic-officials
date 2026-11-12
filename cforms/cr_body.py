"""Ward members from a body's own website: one page with a plain member table (gap round 2026-11-11, seeds keys "cr-body-").

Payload: {"kind": "form-cr_body", "state", "body", "body_type", "district", "lgd_code", "url", "election", "slug"}.
The page's member table is read through its header words (cforms/cr_common.py member_tables: Hindi, English, Gujarati, Bengali,
Punjabi headers; ward number, ward name, name, party, phone, address, email, post). Pages found in archive.s1d.me copies:
- Uttar Pradesh: Nagar Palika Parishad Banda (nppbanda.in/members.php: ward no | ward name | सभासद नाम), Fatehpur
  (nppfatehpur.com: ward | name | ward name | mobile), Khairabad (khairabadnpp.in/page/member-list: name | ward name | mobile),
  Nagar Nigam Firozabad (Parshads.aspx: ward | ward name | name | address | mobile).
- Gujarat: Chanasma Nagarpalika (Members_List.html: ward | name | address | post | party | mobile, Gujarati digits).
- West Bengal: Budge Budge Municipality ("board of councillors.php": serial | name with post | ward | address | phone; 20 of
  21 wards), Konnagar Municipality (councillors.php: name | ward; 8 of 20 wards carry a name, the rest are dashes).
- Punjab: Municipal Corporation Bathinda (mcbathinda.com/Councillors.aspx: ward | name | post | address | mobile; Bathinda is
  already covered, so it is not queued).
A row without a ward number keeps its ward name; its record id then uses the row's position ("s<n>").
Record id councillor:<XX>:<slug>:<ward no or s<n>>. The page goes to the bucket under councillors/<XX>/.
"""
import gzip
import re

from cforms.cr_common import table_members

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

POSTS = {"प्रमुख": "President", "ઉપપ્રમુખ": "Vice President", "પ્રમુખ": "President", "उपाध्यक्ष": "Vice Chairperson",
         "अध्यक्ष": "Chairperson", "Mayor": "Mayor", "Deputy Mayor": "Deputy Mayor", "Sr. Deputy Mayor": "Senior Deputy Mayor"}


def post(s):
    """English post of a member row; plain councillors get none (as the other readers)."""
    s = (s or "").strip()
    if not s or re.fullmatch(r"(?i)councill?or|corporator|member|सदस्य|सभ्य|સભ્ય", s):
        return None
    if s in POSTS:
        return POSTS[s]
    return re.sub(r"[-\s]+", " ", s).title() if re.fullmatch(r"[A-Za-z .-]+", s) else s


def records(html, p):
    out, seen = [], set()
    for i, m in enumerate(table_members(html), 1):
        w = m.get("ward_no") or f"s{i}"
        if w in seen:                            # a second seat of the same ward (two tables, or a multi-member ward)
            w = f"{w}-{i}"
        seen.add(w)
        d = {"type": "councillor", "state": p["state"], "body": p["body"], "body_type": p.get("body_type"),
             "district": p.get("district"), "lgd_code": p.get("lgd_code"), "ward_no": m.get("ward_no"),
             "ward_name": m.get("ward_name"), "name": m["name"], "party": m.get("party"), "phone": m.get("phone"),
             "email": m.get("email"), "address": m.get("address"), "father": m.get("father"),
             "reservation": m.get("reservation"), "post": m.get("position"),
             "position": post(m.get("position")),
             "election": p.get("election"), "note": p.get("note"), "url": p["url"]}
        out.append((f"councillor:{p['state']}:{p['slug']}:{w}", {k: v for k, v in d.items() if v not in (None, "")}))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/{p['state']}/body-{p['slug']}.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = records(r.text, p)
    return recs, files, "" if recs else "no member table"
