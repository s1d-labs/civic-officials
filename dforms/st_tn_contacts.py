"""Tamil Nadu: the state Contact Directory of the Government of Tamil Nadu portal (www.tn.gov.in/contact_directory.php, NIC).

Pages (HTML, checked 2026-11-13 from dev-vps-3, Mumbai; 60-110 KB each):
- secret_to_govt.php: "Secretaries to Government", one card per Secretariat department (div.data1: department in <strong>,
  name in <h4>, then the post, "Phone : ...", a mailto link). About 42 cards.
- cont_cheif_secret_to_govt.php?id=<b64>: Chief Secretary (id Nw==), Vigilance Commissioner (MTA=), Chief Electoral Officer (MTE=).
- cont_dir_dept_view.php?dept_id=<b64>&category_value=Mw==: one Secretariat department (42 links on cont_dir_department_list.php).
- detail_contact_hod.php?org_name=<b64>&category_value=NA==: one head of department / directorate (242 links on
  cont_dir_All_hod_list.php).
- detail_contact.php?org_name=<b64>&category_value=NQ==: one undertaking / autonomous body / commission (172 links on
  cont_dir_All_und_tak.php).
The office pages have one header line (office name and address, PBX numbers; then "Email : ...") and one table:
Designation | Name | Direct | Residence. Phones are Chennai numbers as written (no STD code; 044 is Chennai).
Records: level state (Chennai offices of the state), body = the office as the list names it, body_kind secretariat /
department / directorate / commission / other; post as written; name as written (title + service kept).
One queue item = one page. items(get) reads the three list pages and gives every office page as an item.
Ids: dept:st_tn_contacts:<page kind>:<b64 id>:<row n>.
"""
import re

from dforms import _esw, _state
from provenance import at

METHOD = "html table (Designation | Name | Direct | Residence) + html cards (secretaries)"

MODULE = "st_tn_contacts"
BASE = "https://www.tn.gov.in/"
LISTS = [("dept", "cont_dir_department_list.php", r"cont_dir_dept_view\.php\?[^'\"]+", "department"),
         ("hod", "cont_dir_All_hod_list.php", r"detail_contact_hod\.php\?[^'\"]+", "directorate"),
         ("und", "cont_dir_All_und_tak.php", r"detail_contact\.php\?[^'\"]+", "other")]
TOP = [("cs", "cont_cheif_secret_to_govt.php?id=Nw==", "Chief Secretary to Government", "secretariat"),
       ("vc", "cont_cheif_secret_to_govt.php?id=MTA=", "Vigilance Commissioner", "commission"),
       ("ceo", "cont_cheif_secret_to_govt.php?id=MTE=", "Chief Electoral Officer", "department")]


def kind_of(label, default):
    if re.search(r"(?i)commission\b|tribunal|ombudsman|lokayukta", label or ""):
        return "commission"
    if re.search(r"(?i)police|fire and rescue|prisons", label or ""):
        return "police" if re.search(r"(?i)police", label) else default
    return default


def id_of(url):
    m = re.search(r"(?:dept_id|org_name|id)=([A-Za-z0-9+/=]+)", url)
    return m.group(1).rstrip("=") if m else _esw.slug(url)


def list_items(html, kind, rx, body_kind):
    """Queue items of one list page: one per office page link (label = link text)."""
    s = _esw.soup(html)
    out, seen = [], set()
    for a in s.find_all("a", href=True):
        if not re.fullmatch(rx, a["href"].strip()):
            continue
        url = BASE + a["href"].strip()
        if url in seen:
            continue
        seen.add(url)
        label = _esw.clean(a.get_text(" "))
        out.append({"key": f"{MODULE}:{kind}:{id_of(url)}",
                    "payload": {"reader": MODULE, "url": url, "page": "table", "kind": kind, "label": label,
                                "body_kind": kind_of(label, body_kind), "state": "TN", "india_only": True, "route": "direct"}})
    return out


def items(get=None):
    out = [{"key": f"{MODULE}:secretaries", "payload": {"reader": MODULE, "url": BASE + "secret_to_govt.php", "page": "cards",
                                                         "kind": "secy", "state": "TN", "india_only": True, "route": "direct"}}]
    out += [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "url": BASE + u, "page": "table", "kind": k, "label": lab,
                                                 "body_kind": bk, "state": "TN", "india_only": True, "route": "direct"}}
            for k, u, lab, bk in TOP]
    if get is None:
        return out
    for kind, page, rx, bk in LISTS:
        r = get(BASE + page)
        if r is not None and r.status_code == 200:
            out += list_items(r.text, kind, rx, bk)
    return out


def parse_cards(html, url):
    """Secretaries to Government: one record per card."""
    s = _esw.soup(html)
    recs = []
    for n, card in enumerate(s.select("div.data1"), 1):
        dept = _esw.clean(card.find("strong").get_text(" ")) if card.find("strong") else ""
        h4 = card.find("h4")
        name = _esw.clean(h4.get_text(" ")) if h4 else ""
        lines = [_esw.clean(x) for x in card.get_text("\n").split("\n")]
        lines = [x for x in lines if x and x not in (dept, name)]
        post = next((x for x in lines if not re.match(r"(?i)phone|.*\[at\]|.*@", x)), "")
        phone = " ".join(re.sub(r"(?i)^phone\s*:\s*", "", x) for x in lines if re.match(r"(?i)phone", x))
        mail = card.find("a", href=re.compile(r"^mailto:", re.I))
        recs.append(_state.rec(MODULE, f"secy:{n}", state="TN", level="state", post=post, name=name,
                               body=dept, body_kind="department", department=dept, phone=_esw.phones(phone) or phone,
                               phone_raw=phone, email=_esw.emails(mail["href"][7:] if mail else " ".join(lines)),
                               address="Secretariat, Chennai 600 009", list_no=str(n), src_url=url,
                               src_pos={"card": n, "selector": "div.data1"}))
    return recs


def parse_table(html, url, p):
    """One office page: header (office name and address, e-mail) + table rows."""
    s = _esw.soup(html)
    head = s.select_one("div.email")
    head_text = _esw.clean(head.get_text(" ")) if head else ""
    email_office = _esw.emails(head_text)
    addr = _esw.clean(re.sub(r"(?i)e-?mail\s*:.*$", "", head_text))
    label = p.get("label") or addr.split(",")[0]
    t = s.find("table")
    if t is None:
        return []
    pos = []
    rows = _esw.grid(t, pos=pos)
    recs, n = [], 0
    for row, sp in zip(rows, pos):
        if not row or re.match(r"(?i)designation", row[0] or ""):
            continue
        row = (row + ["", "", "", ""])[:4]
        post, name, direct, res = row
        if not (post or name):
            continue
        n += 1
        recs.append(_state.rec(
            MODULE, f"{p.get('kind', 'page')}:{id_of(url)}:{n}", state="TN", level="state", post=post, name=name,
            body=label, body_kind=p.get("body_kind") or "other", department=label, phone=_esw.phones(direct) or direct,
            phone_residence=_esw.phones(res) or res or None, email=email_office, address=addr, office_phone=_esw.phones(re.sub(r"(?i)(?<=[a-z])\s*-\s*\d{3}\s?\d{3}\b", " ", addr)) or None,
            section=p.get("kind"), cells=row, list_no=str(n), src_url=url, src_pos=sp))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.status_code != 200:
        return [], [], f"http {r.status_code}"
    html = r.text
    recs = parse_cards(html, p["url"]) if p.get("page") == "cards" else parse_table(html, p["url"], p)
    recs = [(k, {**d, **at(r, p["url"])}) for k, d in recs]
    return recs, [_esw.keep(MODULE, f"{p.get('kind', 'page')}-{id_of(p['url'])}", r.content)], "" if recs else "no rows"
