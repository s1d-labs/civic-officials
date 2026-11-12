"""Gujarat: the Talati-cum-Mantri (TCM, તલાટી કમ મંત્રી: the secretary of a gram panchayat, often for a "sejo" = a cluster of
gram panchayats) of each gram panchayat, with mobile numbers, from the open pages of the 33 district panchayat portals
<district>dp.gujarat.gov.in (one ASP.NET MVC template, Gujarati). Many talukas also list the Sarpanch with the TCM.

Structure (measured 2026-11-12 from Mumbai): the district home (/ -> /gu/home) has a taluka select (#ddtaluka, options
"<id>||<Taluka>"); each taluka panchayat has its own pages under /gu/taluka/<Taluka>/ (home = /gu/taluka/<Taluka>/home). The
taluka menu links the TCM list under different names: "Talati-cum-Ministers-Info" (Ahmedabad), "tcm-list" (Tapi), "TCM-Details"
(Mahisagar), "<Taluka>-Elected-Sarpanch-TCM-Details" (Botad: Sarpanch + TCM in one table), "Talati-cum-Minister-List" (Narmada,
empty on 2026-11-12). Some districts link a PDF (scans; "tcm-database.pdf", "Talati-yadi.pdf") or a Google sheet instead.
A link is followed when its address or its text names the TCM (tcm / talati / તલાટી / ત.ક. મંત્રી / મંત્રીશ્રી) or the Sarpanch.

Tables: one HTML table per page; the header row is the first row with a mobile column (મોબાઇલ / મોબાઈલ / mobile). Column roles
come from the header words: TCM name (તલાટી / ત.ક / મંત્રી / tcm + નામ; or the employee name "કર્મચારીનું નામ" with a designation
column "હોદ્દો"), Sarpanch name (સરપંચ), gram panchayat / village (ગ્રામ પંચાયત / ગામ), sejo (સેજા), villages of the sejo
(સમાવિષ્ટ ગામ), extra charge (વધારાનો ચાર્જ), taluka (તાલુકો), district (જિલ્લો). Each mobile column belongs to the nearest name
column on its left. A cell " (ditto) repeats the cell above. Gujarati digits are read as digits.

Records (dept rural_development, level gram_panchayat): one per TCM row: post "Talati-cum-Mantri (Panchayat Secretary)",
post_regional "તલાટી કમ મંત્રી", name (Gujarati, as written), phone, area = the gram panchayat / sejo as written (Gujarati),
villages, extra_charge, taluka (English, from the taluka select), district (LGD name), and the Sarpanch of the same row
(sarpanch_name, sarpanch_phone). A table with a Sarpanch column and no TCM column gives one record per Sarpanch (post
"Sarpanch", kind sarpanch). Every row also keeps its raw cells (header -> text). PDFs that the menu links are saved to the bucket
and noted as source_file records (scans: OCR later, on the runners).
One queue item per district: 1 GET of the home + 1 GET per taluka home + up to 3 list pages per taluka (about 15-40 requests).
Record ids: dept:gp_gj_tcm:<district slug>:<taluka slug>:<table>-<row>[:s] (s = Sarpanch-only record); files:
dept:gp_gj_tcm:<district slug>:file:<sha1 of url, 12>.
"""
import hashlib
import re
from urllib.parse import urljoin, urlparse

from dforms import _esw

METHOD = "html table (district panchayat taluka pages, header words -> columns)"     # source trail (provenance.py)

MODULE = "gp_gj_tcm"
# portal host -> LGD district (sub2_gj.LGD names); Kheda's portal is nadiyaddp (district seat Nadiad)
HOSTS = {
    "ahmedabaddp": "Ahmedabad", "amrelidp": "Amreli", "ananddp": "Anand", "arvallidp": "Arvalli", "banaskanthadp": "Banas Kantha",
    "bharuchdp": "Bharuch", "bhavnagardp": "Bhavnagar", "botaddp": "Botad", "chhotaudepurdp": "Chhotaudepur", "dahoddp": "Dahod",
    "dangdp": "Dangs", "devbhumidwarkadp": "Devbhumi Dwarka", "gandhinagardp": "Gandhinagar", "girsomnathdp": "Gir Somnath",
    "jamnagardp": "Jamnagar", "junagadhdp": "Junagadh", "kutchdp": "Kachchh", "nadiyaddp": "Kheda", "mahisagardp": "Mahisagar",
    "mehsanadp": "Mahesana", "morbidp": "Morbi", "narmadadp": "Narmada", "navsaridp": "Navsari", "panchmahaldp": "Panch Mahals",
    "patandp": "Patan", "porbandardp": "Porbandar", "rajkotdp": "Rajkot", "sabarkanthadp": "Sabar Kantha", "suratdp": "Surat",
    "surendranagardp": "Surendranagar", "tapidp": "Tapi", "vadodaradp": "Vadodara", "valsaddp": "Valsad",
}
TCM_LINK = re.compile(r"(?i)tcm|talati|tlati|minister|mantri|તલાટી|ત\.\s*ક\.?\s*મંત્રી|મંત્રીશ્રી|sarpanch|સરપંચ")
NOT_LINK = re.compile(r"(?i)deputy-minister|ઉપ\s*મંત્રી|yojana|yojna|gramsabha|ગ્રામસભા|women-sarpanch|award|પુરસ્")
GU_DIGITS = str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789")
DITTO = re.compile(r"^[\"”“''’]+$|^〃$|^-do-$", re.I)

MOBILE_H = re.compile(r"(?i)મોબા|mobile|સંપર્ક|contact|ફોન|phone")
TCM_H = re.compile(r"(?i)તલાટી|ત\.\s*ક|tcm|talati|મંત્રી")
SARPANCH_H = re.compile(r"(?i)સરપંચ|sarpanch")
NAME_H = re.compile(r"(?i)નામ|name")
EMP_H = re.compile(r"(?i)કર્મચારી|employee|અધિકારી")
DESIG_H = re.compile(r"(?i)હોદ્દો|designation")
SEJO_H = re.compile(r"(?i)સેજા|sejo|seja")
VILLAGES_H = re.compile(r"(?i)સમાવિષ્ટ|included")
GP_H = re.compile(r"(?i)ગ્રામ\s*પંચાયત|ગામ|village|gram|panchayat")
EXTRA_H = re.compile(r"(?i)વધારાન|additional|extra|charge")
TALUKA_H = re.compile(r"(?i)તાલુક|taluka")
DIST_H = re.compile(r"(?i)જિલ્લ|જીલ્લ|district")
SNO_H = re.compile(r"(?i)^(ક્રમ|અ\.?\s*નં\.?|ક્રમ\s*નં\.?|sr\.?\s*no\.?|s\.?\s*no\.?|no\.?)$")


def text(s):
    return _esw.clean((s or "").translate(GU_DIGITS))


def roles(header):
    """header cells -> {column index: role}."""
    out = {}
    for i, h in enumerate(header):
        h = text(h)
        if not h:
            continue
        if MOBILE_H.search(h) and not NAME_H.search(h):
            out[i] = "mobile"
        elif SNO_H.match(h):
            out[i] = "sno"
        elif SARPANCH_H.search(h):
            out[i] = "sarpanch"
        elif TCM_H.search(h) and NAME_H.search(h):
            out[i] = "tcm"
        elif EMP_H.search(h) and NAME_H.search(h):
            out[i] = "employee"
        elif DESIG_H.search(h):
            out[i] = "designation"
        elif EXTRA_H.search(h):
            out[i] = "extra"
        elif VILLAGES_H.search(h):
            out[i] = "villages"
        elif SEJO_H.search(h):
            out[i] = "sejo"
        elif TALUKA_H.search(h):
            out[i] = "taluka"
        elif DIST_H.search(h):
            out[i] = "district"
        elif GP_H.search(h):
            out[i] = "gp"
        elif TCM_H.search(h):
            out[i] = "tcm"
        elif re.search(r"(?i)remark|રિમાર્ક|નોંધ", h):
            out[i] = "remarks"
    return out


def table_rows(grid, pos, strict=False):
    """[(row dict with role lists + cells, src_pos)] for one table grid, or [] when it is not a TCM / Sarpanch table."""
    hi = next((i for i, r in enumerate(grid[:4]) if any(MOBILE_H.search(text(c)) for c in r)), None)
    if hi is None:
        return []
    header = [text(c) for c in grid[hi]]
    rl = roles(header)
    if not any(v in ("tcm", "sarpanch", "employee") for v in rl.values()):
        return []
    if strict and not any(v in ("tcm", "sarpanch") for v in rl.values()):
        return []       # district-level pages: an employee list without TCM words is another list (TDOs, branch staff)
    # each mobile column -> the nearest name column on its left
    owner, last = {}, None
    for i in range(len(header)):
        if rl.get(i) in ("tcm", "sarpanch", "employee"):
            last = rl[i]
        elif rl.get(i) == "mobile":
            owner[i] = last or "tcm"
    out, prev = [], {}
    for r, sp in zip(grid[hi + 1:], pos[hi + 1:]):
        cells = [text(c) for c in r]
        if not any(cells) or any(c and c == header[i] and rl.get(i) in ("tcm", "sarpanch", "employee", "mobile")
                                 for i, c in enumerate(cells[:len(header)])):
            continue        # a second header row (rowspan repeats the first header's name cell)
        row = {"cells": {header[i] or f"col{i + 1}": c for i, c in enumerate(cells) if c and i < len(header)}}
        for i, c in enumerate(cells):
            role = rl.get(i)
            if not role:
                continue
            if DITTO.match(c) and role in ("taluka", "district", "gp", "sejo"):
                c = prev.get(role, "")
            if role == "mobile":
                row.setdefault(owner[i] + "_phone", []).append(c)
            else:
                row.setdefault(role, []).append(c)
        for role in ("taluka", "district", "gp", "sejo"):
            if row.get(role):
                prev[role] = row[role][0]
        out.append((row, sp))
    return out


def j(row, role):
    vals = []
    for x in row.get(role) or []:
        if x and x not in vals and x.strip(" -") != "":          # colspan / rowspan cells repeat the same text
            vals.append(x)
    return " | ".join(vals) or None


def records(html, url, p, taluka):
    soup = _esw.soup(html)
    dslug, tslug = _esw.slug(p["district"]), _esw.slug(taluka or "district")
    recs = []
    for t in soup.find_all("table"):
        pos = []
        g = _esw.grid(t, pos=pos)
        rows = table_rows(g, pos, strict=not taluka)
        for row, sp in rows:
            tcm_name = j(row, "tcm")
            if not tcm_name and j(row, "employee"):
                desig = j(row, "designation") or ""
                if not desig or TCM_H.search(desig):
                    tcm_name = j(row, "employee")
            tcm_name = None if tcm_name and DITTO.match(tcm_name) else tcm_name
            phone = _esw.phones(*(row.get("tcm_phone") or []), *(row.get("employee_phone") or []))
            sar, sar_phone = j(row, "sarpanch"), _esw.phones(*(row.get("sarpanch_phone") or []))
            area = j(row, "gp") or j(row, "sejo")
            common = dict(state="GJ", district=p["district"], taluka=taluka or None, taluka_regional=j(row, "taluka"),
                          district_regional=j(row, "district"), sejo=j(row, "sejo"), villages=j(row, "villages"),
                          extra_charge=j(row, "extra"), remarks=j(row, "remarks"), list_no=j(row, "sno"),
                          designation=j(row, "designation"), cells=row["cells"], source=url, page=url, src_url=url,
                          portal=p["host"], src_pos=sp, area=area or taluka or p["district"])
            key = f"{dslug}:{tslug}:{sp['table']}-{sp['row']}"
            if tcm_name or (phone and not sar):
                recs.append(_esw.record(MODULE, key, dept="rural_development", level="gram_panchayat",
                                        post="Talati-cum-Mantri (Panchayat Secretary)", post_regional="તલાટી કમ મંત્રી",
                                        name=tcm_name, phone=phone, sarpanch_name=sar, sarpanch_phone=sar_phone,
                                        kind="panchayat_secretary", **common))
            elif sar and not DITTO.match(sar):
                recs.append(_esw.record(MODULE, key + ":s", dept="rural_development", level="gram_panchayat", post="Sarpanch",
                                        post_regional="સરપંચ", name=sar, phone=sar_phone, kind="sarpanch", **common))
    return recs


def links(html, base, host):
    """[(url, link text)] of TCM / Sarpanch lists on one page (same host, or a PDF); pdf and page links apart."""
    out = []
    for a in _esw.soup(html).find_all("a", href=True):
        href, label = a["href"].strip(), text(a.get_text(" "))
        if href.startswith(("javascript", "#", "mailto")):
            continue
        u = urljoin(base, href)
        if not TCM_LINK.search(f"{href} {label}") or NOT_LINK.search(f"{href} {label}"):
            continue
        if urlparse(u).hostname != host:
            continue
        if u not in [x for x, _ in out]:
            out.append((u, label))
    return out


def talukas(html):
    """[(id, English name)] from the taluka select of a district page."""
    out = []
    for v in re.findall(r'<option value="(\d+\|\|[^"]+)"', html):
        tid, name = v.split("||", 1)
        if (tid, name.strip()) not in out:
            out.append((tid, name.strip()))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:{label}", "payload": {"reader": MODULE, "url": f"https://{label}.gujarat.gov.in/",
                                                    "host": f"{label}.gujarat.gov.in", "district": district, "state": "GJ",
                                                    "india_only": True, "route": "direct"}}
            for label, district in sorted(HOSTS.items())]


def fetch(p, get):
    host = p["host"]
    r = get(p["url"])
    if r is None:
        return [], [], "district home did not answer"
    home = r.content.decode("utf-8", "replace")
    files, recs, seen, notes = [], [], set(), []
    pages = []          # (url, taluka English name or "")
    for u, _ in links(home, p["url"], host):
        pages.append((u, ""))
    for tid, name in talukas(home):
        th_url = f"https://{host}/gu/taluka/{name.replace(' ', '')}/home"
        th = get(th_url)
        if th is None:
            notes.append(f"taluka home {name}: no answer")
            continue
        n = 0
        for u, label in links(th.content.decode("utf-8", "replace"), th_url, host):
            if f"/taluka/{name.replace(' ', '').lower()}/" not in u.lower() and not u.lower().endswith(".pdf"):
                continue        # menu links of the district or of other talukas
            if n < 4:
                pages.append((u, name))
                n += 1
    dslug = _esw.slug(p["district"])
    for u, taluka in pages:
        if u in seen:
            continue
        seen.add(u)
        if u.lower().split("?")[0].endswith(".pdf"):
            f = get(u)
            ok = f is not None and f.content[:5] == b"%PDF-"
            h = hashlib.sha1(u.encode()).hexdigest()[:12]
            path = f"depts/{MODULE}/{dslug}/{h}.pdf" if ok else None
            if ok:
                files.append((path, f.content, "application/pdf"))
            recs.append((f"dept:{MODULE}:{dslug}:file:{h}",
                         {"type": "source_file", "url": u, "stored": path, "bytes": len(f.content) if ok else None, "fetched": ok,
                          "taluka": taluka or None, "state": "GJ", "district": p["district"], "portal": host, "source": p["url"],
                          **({"src_url": u, "method": "file saved to the bucket (pdf)"} if ok else {})}))
            continue
        g = get(u)
        if g is None:
            continue
        html = g.content.decode("utf-8", "replace")
        got = records(html, u, p, taluka)
        recs.extend(got)
        if got:
            files.append(_esw.keep(MODULE, f"{dslug}/{_esw.slug(urlparse(u).path)}", g.content, "html"))
    if not any(d.get("type") == "dept_office" for _, d in recs):
        return recs, files, "no TCM table" + (f" ({'; '.join(notes[:3])})" if notes else "")
    return recs, files, ""
