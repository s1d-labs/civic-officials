"""Karnataka panchayat elected representatives (zilla / taluk / gram panchayat), from the Ministry of Panchayati Raj
eGramSwaraj report "Elected Representatives" (egramswaraj.gov.in/ElectedRepresentativeReportVp.do; JSON calls of its own page).

Why this source (measured 2026-11-13 from dev-vps-3):
- Karnataka SEC (karsec.karnataka.gov.in): the "Elected" grids (/GV/GetResult cat GramPanchayat) give only scanned summary PDFs
  (Results_GP.pdf 2020: 2 pages, GP Result 2024.pdf: 3 pages, party totals, no names). The asset portal /sec_al_elected_2020/
  needs a member login.
- Zilla / taluk panchayats: no elections since the 2016-21 term ended; zp<district>.karnataka.gov.in member, president and
  "taluk panchayat administrators" pages are empty (Mandya /105, /104, /98, /111 checked live).
- Panchatantra 2.0 "Panchamitra" (panchatantra.karnataka.gov.in) shows gram panchayat members, but its district / taluk / GP
  lists answer "not validated" without a login session, and its GP ids are not LGD codes: not used.
- eGramSwaraj: public GET calls, no captcha, LGD codes. On 2026-11-13 its state report lists 0 elected representatives for
  Karnataka (other states: Goa 1,760, Gujarat 109,835, Kerala 21,019 ...). So each item first reads the state report and stops
  when the state has none; when Karnataka's members are entered, the same items read them.

The reader is not tied to Karnataka: payload state / state_code (LGD state code) choose the state, and the LGD tree comes from
cforms/pri_lgd/<state>.json.gz.
Calls (all GET, JSON lists):
  ElectedStateReport.do?year=<YYYY-YYYY>                          -> [{code, name, level "S", maleCount, femaleCount}]
  ElectedMemberRepresent.do?code=<LGD body>&stateCode=<s>&level=D|I|V  (zp | ps | gp)
                                     -> [{electedname, designationname, wardName, gender, mobno, emailid}]
The site masks mobile numbers and e-mail addresses itself ("93****4721"): they are kept as given, with phone_masked true.
One queue item = one district panchayat with its taluk and gram panchayats: payload {"kind": "form-pri_ka", "state": "KA",
"state_code": "29", "url" (the ZP member call), "level": "zp", "district", "lgd_code" (ZP), "year", "election", "route"}.
About 1 + 1 + taluks + GPs requests per item (Karnataka: 31 ZPs, 237 TPs, 5,946 GPs in LGD), or 1 request while the state is empty.
Record id pri:<state>:<level>:<LGD code>:<head | vice | w<ward> | m<n>>.
"""
import json
import re

from cforms import _pri

METHOD = "json api (eGramSwaraj ElectedMemberRepresent.do, one list per LGD body; state gate from ElectedStateReport.do)"

BASE = "https://egramswaraj.gov.in/"
YEAR = "2026-2027"
API_LEVEL = {"zp": "D", "ps": "I", "gp": "V"}
HEAD = re.compile(r"(?i)^\s*(sarpanch|chair\s*person|chairman|president|adhyaksha|pradhan|mukhiya)\b")
VICE = re.compile(r"(?i)^\s*(up[\s-]*sarpanch|vice[\s-]*(chair\s*person|chairman|president)|upadhyaksha|up[\s-]*pradhan|deputy)")
ELECTION = "as listed on eGramSwaraj (Ministry of Panchayati Raj), elected representatives (active)"


def member_url(code, state_code, level):
    return f"{BASE}ElectedMemberRepresent.do?code={code}&stateCode={state_code}&level={API_LEVEL[level]}"


def state_count(rows, state_code):
    """Elected representatives the state report lists for the state (male + female), or None when the state is missing."""
    for r in rows or []:
        if str(r.get("code")) == str(state_code):
            n = 0
            for k in ("maleCount", "femaleCount"):
                v = str(r.get(k) if r.get(k) is not None else "")
                n += int(v) if v.isdigit() else 0
            return n
    return None


def ward_no(text):
    """'Ward No 03' / 'Ward No. 1' -> '03' / '1'; other text as written; '' when empty."""
    t = " ".join(str(text or "").split())
    m = re.match(r"(?i)^ward\s*no\.?\s*[:\-]?\s*(\w+)$", t)
    return m.group(1) if m else t


def records(rows, url, p, level, code, body, district="", block=""):
    out, seen = [], set()
    for i, r in enumerate(rows or []):
        name = " ".join(str(r.get("electedname") or "").split())
        post = " ".join(str(r.get("designationname") or "").split())
        if not name:
            continue
        wn = ward_no(r.get("wardName"))
        head, vice = bool(HEAD.match(post)), bool(VICE.match(post))
        pkey = "head" if head else "vice" if vice else (_pri.post_key(ward_no=wn) if wn else f"m{i + 1}")
        while pkey in seen:
            pkey += "+"
        seen.add(pkey)
        mob, mail = str(r.get("mobno") or ""), str(r.get("emailid") or "")
        rid, d = _pri.record(p["state"], level, body_key=code, pkey=pkey, lgd_code=code, body=body, district=district,
                             block=block, post=post, name=name, ward_no=wn if not (head or vice) else "", ward_name=r.get("wardName"),
                             gender=r.get("gender"), phone=mob, email=mail, election=p.get("election") or ELECTION, url=url,
                             src_url=url, src_pos={"index": i}, method=METHOD)
        if head or vice:
            d["head"], d["head_rank"] = True, 1 if head else 2
        if "*" in mob or "*" in mail:
            d["phone_masked"] = True       # masked by the source itself; kept as given
        out.append((rid, d))
    return out


def read_body(get, p, level, code, body, district="", block=""):
    url = member_url(code, p["state_code"], level)
    r = get(url)
    if r is None:
        return None
    try:
        rows = json.loads(r.text or "[]")
    except ValueError:
        return None
    return records(rows if isinstance(rows, list) else [], url, p, level, code, body, district, block)


def fetch(p, get):
    year = p.get("year") or YEAR
    r = get(f"{BASE}ElectedStateReport.do?year={year}")
    if r is None:
        return [], [], "state report did not answer"
    try:
        n = state_count(json.loads(r.text or "[]"), p["state_code"])
    except ValueError:
        return [], [], "state report is not JSON"
    if not n:
        return [], [], f"eGramSwaraj lists no elected representatives for {p['state']} (state report {year}: {n})"
    lgd = _pri.Lgd(p["state"])
    kids = {}
    for code, lev, name, _local, parent in lgd.rows:
        kids.setdefault(parent, []).append((code, lev, name))
    zp = p["lgd_code"]
    district = p.get("district") or (lgd.by_code.get(zp) or [None, None, ""])[2]
    recs, failed, bodies = [], 0, 0
    todo = [("zp", zp, district, district, "")]
    for tcode, tlev, tname in kids.get(zp, []):
        if tlev == "ps":
            todo.append(("ps", tcode, tname, district, tname))
            todo += [("gp", g, gname, district, tname) for g, glev, gname in kids.get(tcode, []) if glev == "gp"]
        elif tlev == "gp":
            todo.append(("gp", tcode, tname, district, ""))
    for level, code, body, dist, blk in todo:
        got = read_body(get, p, level, code, body, dist, blk if level == "gp" else "")
        bodies += 1
        if got is None:
            failed += 1
            continue
        recs += got
    why = "" if recs else f"no members listed for {bodies} bodies ({failed} calls failed)"
    return recs, [], why
