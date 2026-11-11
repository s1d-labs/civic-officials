"""Uttar Pradesh: every elected member of the 2023 urban local body general election, from the State Election Commission's
winner list "नगरीय निकाय सामान्य निर्वाचन 2023 के घोषित परिणाम का विवरण" (sec.up.nic.in/site/NewWinnerList2023.aspx). India only.

The page is ASP.NET WebForms with two auto-postback lists: DropDownList1 = post (7 नगर निगम महापौर, 8 नगर निगम पार्षद,
9 नगर पालिका परिषद अध्यक्ष, 10 नगर पालिका परिषद सदस्य, 11 नगर पंचायत अध्यक्ष, 12 नगर पंचायत सदस्य) and ddlDistrict (75
districts, ids in cforms/cr_up_lgd.json; 0 = all). fetch() GETs the page, posts both lists at once (else the post list, then
the district list) and reads table ctl00_ContentPlaceHolder1_winnerdetail. Its 16 columns: जनपद | निकाय का नाम | वार्ड का नाम ("7-जगदीशपुरा पूर्वी")
| पद का आरक्षण | उम्मीदवार | पिता/पति | प्रत्याशी का जाति/वर्ग | शैक्षिक योग्यता | पार्टी का नाम | लिंग | आयु | मोबाइल नं० |
प्राप्त वैध मत | प्राप्त मत % | मतदान % | परिणाम (सविरोध = won a contest, निर्विरोध = unopposed).
The form and the table are known from the Wayback Machine copy of 13 May 2023 (tests/data/cr_up_sec_winners.html, cut to
4 rows). On 2026-11-11 the site did not answer on ports 80 and 443 from vpsin2 (connection timed out; also from Germany and
the US earlier the same day), so no live postback was tested. The hub retries failed items; the items wait for the site.
Queue items (items()): posts 8, 10 and 12 for each of the 75 districts (225 items, about 13,000 members of 760 bodies),
plus posts 7, 9 and 11 for the whole state (3 items: mayors and chairpersons).
The body name is Hindi; it is tied to LGD here (cforms/cr_up_lgd.json: LGD bodies of civic.ulb, 2026-11-11) with the
Devanagari-to-Latin key of cforms/cr_common.py inside the LGD district, so records carry lgd_code (sql/70 keeps it).
Record id councillor:UP:<lgd code, or district-body slug when no LGD body is close>:<ward no | chair>.
"""
import gzip
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from cforms.cr_common import best_body, clean, digits, key, latin, sim
from forms.aspnet import hidden

URL = "https://sec.up.nic.in/site/NewWinnerList2023.aspx"
P = "ctl00$ContentPlaceHolder1$"
ELECTION = "UP urban local bodies general election 2023 (SEC Uttar Pradesh)"
POSTS = {"7": ("Municipal Corporation", "Mayor"), "8": ("Municipal Corporation", None),
         "9": ("Municipal Council", "Chairperson"), "10": ("Municipal Council", None),
         "11": ("Nagar Panchayat", "Chairperson"), "12": ("Nagar Panchayat", None)}
LGD_TYPES = {"Municipal Corporation": {"Municipal Corporation"}, "Municipal Council": {"Municipality", "Municipal Council"},
             "Nagar Panchayat": {"Town Panchayat", "Nagar Panchayat", "Notified Area Council"}}
COLS = ["district", "body", "ward", "reservation", "name", "father", "caste", "education", "party_hi", "gender", "age", "phone",
        "votes", "vote_pct", "turnout_pct", "result"]
PARTIES = {"भारतीय जनता पार्टी": "Bharatiya Janata Party", "समाजवादी पार्टी": "Samajwadi Party",
           "बहुजन समाज पार्टी": "Bahujan Samaj Party", "इंडियन नेशनल कांग्रेस": "Indian National Congress",
           "भारतीय राष्ट्रीय कांग्रेस": "Indian National Congress", "राष्ट्रीय लोक दल": "Rashtriya Lok Dal",
           "आम आदमी पार्टी": "Aam Aadmi Party", "निर्दलीय": "Independent", "ऑल इंडिया मजलिस-ए-इत्तेहादुल मुस्लिमीन":
           "All India Majlis-E-Ittehadul Muslimeen", "अपना दल (सोनेलाल)": "Apna Dal (Soneylal)"}
_LGD = None


def lgd():
    global _LGD
    if _LGD is None:
        _LGD = json.loads((Path(__file__).parent / "cr_up_lgd.json").read_text(encoding="utf-8"))
    return _LGD


def district_en(hi):
    """LGD district of an SEC district name (Hindi): the SEC list's own name first, then the closest key."""
    d = lgd()
    for _, (name_hi, en) in d["districts"].items():
        if clean(name_hi) == clean(hi):
            return en
    ds = sorted({b[2] for b in d["bodies"]})
    lk = key(latin(hi))
    best = max(ds, key=lambda x: sim(key(x), lk))
    return best if sim(key(best), lk) >= 0.7 else None


def lgd_code(body_hi, district_hi, body_type):
    dn = district_en(district_hi)
    bodies = [b for b in lgd()["bodies"] if b[2] == dn] if dn else []
    code, _ = best_body(body_hi, bodies, LGD_TYPES.get(body_type))
    return code, dn


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", latin(s).lower()).strip("-")[:50]


def winners(html):
    """Rows of the winner table as dicts (COLS)."""
    t = BeautifulSoup(html, "lxml").find("table", id="ctl00_ContentPlaceHolder1_winnerdetail")
    out = []
    for tr in (t.find_all("tr") if t else []):
        c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(c) == len(COLS):
            out.append(dict(zip(COLS, c)))
    return out


def num(s):
    s = digits(s or "").replace(",", "").strip()
    return s if re.fullmatch(r"\d+(\.\d+)?", s) else None


def records(rows, post, url=URL):
    body_type, chair = POSTS[post]
    recs, codes = [], {}
    for r in rows:
        k = (r["district"], r["body"])
        if k not in codes:
            codes[k] = lgd_code(r["body"], r["district"], body_type)
        code, dn = codes[k]
        m = re.match(r"\s*(\d+)\s*[-–.]?\s*(.*)$", digits(r["ward"]))
        ward_no, ward_name = (m.group(1), clean(m.group(2)) or None) if m and not chair else ("chair" if chair else None, None)
        if not ward_no:
            continue
        d = {"type": "councillor", "state": "UP", "body": r["body"], "body_type": body_type, "district": r["district"],
             "district_en": dn, "lgd_code": code, "ward_no": ward_no, "ward_name": ward_name if not chair else None,
             "position": chair, "name": r["name"], "father_or_husband": r["father"], "reservation": r["reservation"],
             "caste_category": r["caste"], "education": r["education"], "party": PARTIES.get(r["party_hi"], r["party_hi"]),
             "party_hi": r["party_hi"], "gender": r["gender"], "age": num(r["age"]), "phone": num(r["phone"]),
             "votes": num(r["votes"]), "vote_pct": num(r["vote_pct"]), "turnout_pct": num(r["turnout_pct"]),
             "unopposed": True if "निर्विरोध" in r["result"] else None, "result": r["result"], "election": ELECTION,
             "url": url, "sec_post": post}
        place = code or f"{slug(dn or r['district'])}-{slug(r['body'])}"
        recs.append((f"councillor:UP:{place}:{ward_no}", {k2: v for k2, v in d.items() if v not in (None, "")}))
    return recs


def _post(get, html, target, post, district):
    d = hidden(html)
    d.update({"__EVENTTARGET": P + target, "__EVENTARGUMENT": "", "__LASTFOCUS": "", P + "DropDownList1": post,
              P + "ddlDistrict": district})
    r = get(URL, method="POST", data=d)
    return r.text if r is not None else None


def fetch(p, get):
    r = get(URL)
    if r is None:
        return [], [], "no answer"
    # one postback with both lists set (both are in the first page with all options); when that gives no rows, the two
    # steps a person takes (post, then district) on the answer's own view state
    h = _post(get, r.text, "ddlDistrict" if p["district_id"] != "0" else "DropDownList1", p["post"], p["district_id"])
    if h is not None and not winners(h) and p["district_id"] != "0":
        h = _post(get, r.text, "DropDownList1", p["post"], "0")
        h = h and _post(get, h, "ddlDistrict", p["post"], p["district_id"])
    if not h:
        return [], [], "postback did not answer"
    files = [(f"councillors/UP/sec2023-post{p['post']}-d{p['district_id']}.html.gz", gzip.compress(h.encode()), "application/gzip")]
    recs = records(winners(h), p["post"])
    return recs, files, "" if recs else "no winner rows"


def items(get=None):
    """The queue items (no request needed: the district ids are in cr_up_lgd.json)."""
    out = []
    for post in ("8", "10", "12"):
        for did, (hi, en) in sorted(lgd()["districts"].items(), key=lambda x: int(x[0])):
            out.append({"key": f"cr-up-sec2023-p{post}-d{did}", "payload": {"kind": "form-cr_up", "state": "UP", "url": URL,
                        "post": post, "district_id": did, "district": hi, "district_en": en}})
    for post in ("7", "9", "11"):
        out.append({"key": f"cr-up-sec2023-p{post}-all", "payload": {"kind": "form-cr_up", "state": "UP", "url": URL,
                    "post": post, "district_id": "0"}})
    return out
