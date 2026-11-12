"""Punjab: PWSSB (Punjab Water Supply & Sewerage Board) officers, pwssb.punjab.gov.in. India only (times out from Germany) and the
server needs TLS legacy renegotiation (OpenSSL 3 refuses it by default: see the report; whoswho.py has the LegacyTLS retry, the
depts get() in councillors.py does not yet).

Pages (one queue item each): "Officers of the Board (Head Office)" /officers-of-the-board-head-office/ and the five field circles
/amritsar-circle/, /bhatinda-circle/, /jalandhar-circle/, /ludhiana-circle/, /patiala-circle/. Each page holds an empty Ninja
Tables table (plugin 2.4.1, render_type ajax_table); the page script names its table ("table_id":"466"). The rows come from a
plain public GET: /wp-admin/admin-ajax.php?action=wp_ajax_ninja_tables_public_action&table_id=<id>&target_action=get-all-data
&default_sorting=old_first -> JSON list of {s_no, name ("Er. Satnam Singh, Chief Engineer, Amritsar"), office (landline),
mobile, email}; the head office table names its columns sr_no, name_and_designation, office, mobile_no, email.
Table ids on 2026-11-05: 463 head office, 466 Amritsar, 469 Bathinda, 472 Jalandhar, 474 Ludhiana, 478 Patiala (the reader
reads the id from the page first and falls back to the payload's table_id). About 4-8 officers per circle: CE (zone), SE
(circle), EE divisions (division); no sub-divisions are published. Names, phones and e-mails: yes. No date on the pages.
Record id dept:water2_pwssb:<page>:<post>-<area>.
"""
import json
import re

from dforms import _esw
from dforms._water import level_of, unique

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water2_pwssb"
BASE = "https://pwssb.punjab.gov.in/"
AJAX = BASE + "wp-admin/admin-ajax.php?action=wp_ajax_ninja_tables_public_action&table_id={}&target_action=get-all-data" \
              "&default_sorting=old_first"
ORG = "Punjab Water Supply & Sewerage Board"
PAGES = {"head-office": ("officers-of-the-board-head-office/", "463", None),
         "amritsar": ("amritsar-circle/", "466", "Amritsar"), "bathinda": ("bhatinda-circle/", "469", "Bathinda"),
         "jalandhar": ("jalandhar-circle/", "472", "Jalandhar"), "ludhiana": ("ludhiana-circle/", "474", "Ludhiana"),
         "patiala": ("patiala-circle/", "478", "Patiala")}
POST = re.compile(r"(?i)engineer|director|secretary|officer|manager|chairman|controller|accounts|adviser|advisor|head|chief|"
                  r"draftsman|superintendent|\bS\.?D\.?E\b|\bX\.?EN\b")


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "page": k, "url": BASE + path, "table_id": tid,
                                                 "circle": circle, "state": "PB", "india_only": True}}
            for k, (path, tid, circle) in PAGES.items()]


def split_name(s):
    """'Er. Satnam Singh, Chief Engineer, Amritsar' -> (name, post, area)."""
    parts = [_esw.clean(x) for x in re.split(r"\s*,\s*", s or "") if _esw.clean(x)]
    i = next((k for k, x in enumerate(parts) if POST.search(x)), None)
    if i is None:
        return (parts[0] if parts else ""), "", ", ".join(parts[1:])
    return ", ".join(parts[:i]), parts[i], ", ".join(parts[i + 1:])


def level(post, circle):
    lvl = level_of(post, default="state")
    if lvl == "state" and re.search(r"(?i)chief\s+engineer", post) and circle:
        return "zone"                                  # a field CE ("Chief Engineer, Amritsar") heads a region
    return lvl


def parse(rows, page, url, circle=None):
    recs, seen = [], set()
    for x in rows if isinstance(rows, list) else []:
        if not isinstance(x, dict):
            continue
        text = x.get("name") or x.get("name_and_designation") or ""
        name, post, area = split_name(text)
        if not (name or post):
            continue
        lvl = level(post, circle)
        area = area or (f"{circle} Circle" if circle and lvl == "circle" else circle) or "Head Office"
        if lvl == "circle" and circle and not re.search(r"(?i)circle", area):
            area = f"{area} Circle"
        key = unique(f"{page}:{_esw.slug(post)}-{_esw.slug(area)}", seen)
        par = {"circle": f"{circle} Circle"} if circle and lvl in ("division", "subdivision") else None
        recs.append(_esw.record(MODULE, key, dept="water", level=lvl, area=area, post=post or None,
                                name=re.sub(r"^(Er|Sh|Smt|Mr|Ms)\.?\s+", "", name), phone=_esw.phones(x.get("office"),
                                x.get("mobile") or x.get("mobile_no")), email=_esw.emails(x.get("email")) or None,
                                state="PB", district=circle, source=url, org=ORG, parents=par))
    return recs


def fetch(p, get):
    page = p.get("page", "amritsar")
    path, tid, circle = PAGES.get(page, (None, p.get("table_id"), p.get("circle")))
    url = p.get("url") or BASE + path
    files, r = [], get(url)
    if r is not None:
        files.append(_esw.keep(MODULE, page, r.content))
        m = re.search(r'"table_id":"(\d+)"', r.text)
        tid = m.group(1) if m else (p.get("table_id") or tid)
    else:
        tid = p.get("table_id") or tid
    if not tid:
        return [], files, "no answer"
    a = get(AJAX.format(tid))
    if a is None:
        return [], files, "no answer (table data)"
    files.append(_esw.keep(MODULE, f"{page}-table-{tid}", a.content, "json"))
    try:
        rows = json.loads(a.content)
    except ValueError:
        return [], files, "not json"
    recs = parse(rows, page, url, p.get("circle", circle))
    return recs, files, "" if recs else "no rows"
