"""Telangana: MLAs (Telangana Legislative Assembly, 3rd term 2023-) and MLCs (Telangana Legislative Council) with address,
phones and e-mail, from the Legislature's member profiles (legislature.telangana.gov.in).

- List: /assemblymemprofile?selectedtab=m (119 rows: "<AC no>. <CONSTITUENCY>" | name | party, grouped under district
  headings) and /councilmemprofile?selectedtab=m (40 seats under the headings Graduates, Teachers, Local Authorities, Assembly
  Constituency, Nominated; a "VACANT" row has no profile). Each row links its profile: getMLAMemberDetails?q=<base64 of
  "memid=..&constid=..&termid=16&orderby=1"> / getMLCMemberDetails?q=...
- Profile: a table of <th>label</th><td>value</td>: Permanent Address, Contact Number ("9502781218; 6302608518"), Email Id,
  and personal data (parents, birth, education, profession, positions ...), kept whole in "profile".
The site's own "Address List" view (POST mlaprofilebycateogry) answered 403 to a plain request (2026-11-12): not used.
legislature.telangana.gov.in answered dev-vps-3 (Mumbai) on 2026-11-12; GitHub runners abroad got 403 (archive.s1d.me pool
copy 2026-11-11): route = India (depts-direct or proxy). One item per house: the list + one GET per member (120 + 40).
Record ids: dept:leg_tg:TS-AC-<no> (ECI number from the list), dept:leg_tg:TS-LC-<name slug>.
"""
import base64
import json
import re

from dforms import _esw, _leg

METHOD = 'html table (member list) + html member pages'     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_tg"
HOST = "https://legislature.telangana.gov.in/"
LISTS = {"AC": "assemblymemprofile?selectedtab=m", "LC": "councilmemprofile?selectedtab=m"}
DETAIL = re.compile(r"get(?:MLA|MLC)MemberDetails\?q=[A-Za-z0-9+/=%]+")
LC_GROUPS = ("Graduates", "Teachers", "Local Authorities", "Assembly Constituency", "Nominated")


def items(get=None):
    return [{"key": f"leg_tg-{k.lower()}", "payload": {"reader": MODULE, "url": HOST + path, "state": "TS", "kind": k,
                                                       "house_name": "Telangana Legislative " + ("Assembly" if k == "AC" else "Council"),
                                                       "india_only": True, "route": "direct"}}
            for k, path in LISTS.items()]


def _cells(tr):
    return [_esw.clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]


def rows(html, kind):
    """[{no, constituency, name, party, detail, group}] from a list page (rows with a profile link, and vacant seats)."""
    out, group = [], ""
    for tr in _esw.soup(html).find_all("tr"):
        cells = _cells(tr)
        txt = " ".join(cells)
        a = tr.find("a", href=DETAIL)
        if not a and len(cells) <= 2:
            g = next((x for x in LC_GROUPS if txt.strip().lower() == x.lower()), None)
            group = g or group
            if not g and kind == "AC" and txt.strip() and not re.search(r"\d", txt) and len(txt) < 60:
                group = txt.strip()                           # district heading
            continue
        if len(cells) < 3:
            continue
        m = re.match(r"^\s*(\d{1,3})\.\s*(.*)$", cells[0])
        if not m:
            continue
        out.append({"no": int(m.group(1)), "constituency": m.group(2).strip(), "name": cells[1], "party": cells[2],
                    "detail": HOST + a["href"].lstrip("/") if a else "", "group": group})
    return out


def query(detail):
    """The decoded profile query: {"memid": "3576", "constid": "1", "termid": "16", "orderby": "1"}."""
    q = detail.split("q=", 1)[-1]
    try:
        return dict(x.split("=", 1) for x in base64.b64decode(q + "=" * (-len(q) % 4)).decode().split("&") if "=" in x)
    except Exception:  # noqa: BLE001 - a link the site changed
        return {}


def profile(html):
    """{label: value} of a member profile page (th / td pairs)."""
    out = {}
    for tr in _esw.soup(html).find_all("tr"):
        th, td = tr.find("th"), tr.find("td")
        if th and td:
            k, v = _esw.clean(th.get_text(" ")), _esw.clean(td.get_text(" "))
            if k and k not in out:
                out[k] = v
    return out


def honorific(name):
    return re.sub(r"^(?:(?:sri|smt|kum|shri)\.?\s*)+", "", _esw.clean(name), flags=re.I).strip()


def record(row, prof, kind, source):
    phone = re.sub(r"\s*;\s*", ", ", prof.get("Contact Number", ""))
    name = honorific(row["name"])
    if kind == "AC":
        cons = re.sub(r"\s*\((sc|st)\)", lambda m: f" ({m.group(1).upper()})", row["constituency"].title(), flags=re.I)
        cons = re.sub(r"\((Urban|Rural)\)", lambda m: f"({m.group(1)})", cons)
        no = row["no"] if 1 <= row["no"] <= 119 else None
    else:
        cons = ", ".join(x for x in (row["group"], row["constituency"].title()) if x)
        no = None
    return _leg.member(MODULE, "TS", kind, no, name, constituency=cons, party=row["party"], source=row["detail"] or source,
                       phone=phone, email=prof.get("Email Id", ""), address=prof.get("Permanent Address", ""),
                       permanent_address=prof.get("Permanent Address", ""), seat_no=str(row["no"]),
                       profile={k: v for k, v in prof.items() if v and k not in ("Contact Number", "Email Id")} or None,
                       member_id=query(row["detail"]).get("memid") if row["detail"] else None, term=query(row["detail"]).get("termid")
                       if row["detail"] else None)


def fetch(p, get):
    kind = p.get("kind", "AC")
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (member list)"
    files = [_leg.keep(MODULE, f"list-{kind.lower()}", r.content)]
    lst = rows(r.text, kind)
    if not lst:
        return [], files, "no members in the list"
    recs, saved, missing = [], {}, 0
    for row in lst:
        if not row["detail"] or row["name"].upper() == "VACANT":
            continue
        d = get(row["detail"])
        if d is None:
            missing += 1
            prof = {}
        else:
            saved[row["detail"]] = d.text
            prof = profile(d.text)
        recs.append(record(row, prof, kind, p["url"]))
    files.append((f"depts/{MODULE}/profiles-{kind.lower()}.json.gz", __import__("gzip").compress(json.dumps(saved).encode()),
                  "application/gzip"))
    why = "" if recs and missing <= len(recs) // 4 else f"{missing} of {len(recs)} profiles did not answer"
    return recs, files, why
