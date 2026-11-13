"""State-level office pages with a plain HTML officers table: state commissions and offices that list their members and officers
on one page (Rajasthan: State Election Commission "Office Contacts", Human Rights Commission "Contact Directory" and
"Information of Officers"; Chhattisgarh: Public Service Commission "Directory"). Checked live from dev-vps-3 on 2026-11-13
(all answer from Mumbai; abroad unchecked; no captcha, no login).

The reader takes the innermost tables of the page (tables with no table inside: old sites lay the page out with tables), finds
the header row by its words (Name / Designation / Telephone / Mobile / Fax / E-mail / Room, and the Hindi नाम / पद / दूरभाष /
मोबाइल / ई-मेल) and reads each row under it. A "Name and Designation" column ("Shri Rajeshwar Singh Commissioner") is split at
the first post word (POST_START). Every cell is kept in "cells".
Records (_state.rec): level state (the payload's "level" may say otherwise), body / body_kind / department from the payload,
dept from the payload or from the body name; phone (telephone + mobile), mobile, fax, email, room, ip (intercom).
src_pos {"table", "row"}. Ids: dept:st_html_tables:<payload key>:<table>:<row>.
One queue item = one page (1 GET). Payload: url, key, state, body, body_kind, department, dept, level, post_kinds ({post as the page writes it: rank key}, for posts
whose rank the words do not tell: the SEC's "Commissioner" is the State Election Commissioner).
"""
import re

from dforms import _esw, _state

METHOD = "html table (innermost tables, header row found by its words)"
MODULE = "st_html_tables"

HEAD = [
    ("name_post", r"(?i)name\s*(and|&|/)\s*designation|नाम\s*(एवं|व|और|/)\s*पद"),
    ("post", r"(?i)designation|^post$|^पद|पदनाम"),
    ("name", r"(?i)^name\b|name of|नाम"),
    ("mobile", r"(?i)mobile|मोबाइल|मो\."),
    ("fax", r"(?i)\bfax|फैक्स"),
    ("email", r"(?i)e-?\s*mail|mail id|ई-?\s*मेल"),
    ("phone", r"(?i)telephone|phone|contact|landline|दूरभाष|फोन"),
    ("room", r"(?i)room|कक्ष"),
    ("ip", r"(?i)\bip\b|intercom|epabx"),
    ("address", r"(?i)address|पता"),
    ("sno", r"(?i)^s\.?\s*no|^sl|^sr|क्र"),
    ("photo", r"(?i)photo|image|picture|फोटो"),
]
POST_START = re.compile(r"(?i)\b(state election commissioner|commissioner|chief|secretary|chairperson|chairman|chair|member|deputy|"
                        r"joint|additional|assistant|under|director|registrar|officer|controller|private secretary|p\.?s\.?|"
                        r"stenographer|section officer|accounts?|law|programmer|superintendent)\b")


def kind(h):
    h = _esw.clean(h)
    for k, rx in HEAD:
        if re.search(rx, h):
            return k
    return ""


def header(row):
    ks = [kind(c) for c in row]
    if ("name" in ks or "name_post" in ks) and len(row) <= 14 and sum(1 for k in ks if k) >= 2:
        return ks
    return None


def split_name_post(s):
    """"Shri Rajeshwar Singh Commissioner" -> ("Shri Rajeshwar Singh", "Commissioner"); "Sh. Rajesh Verma, IAS Secretary" ->
    ("Sh. Rajesh Verma, IAS", "Secretary"). The split is at the first post word after the first two words."""
    s = _esw.clean(s)
    if "|" in s:                     # name and post on two lines of the cell
        parts = [x.strip() for x in s.split("|") if x.strip()]
        return parts[0], " ".join(parts[1:])
    for m in POST_START.finditer(s):
        if len(s[: m.start()].split()) >= 2:
            return s[: m.start()].strip(" ,"), s[m.start():].strip(" ,")
    return s, ""


def parse(html, p, url):
    soup = _esw.soup(html)
    out = []
    for t in soup.find_all("table"):
        if t.find("table"):
            continue
        pos = []
        rows = _esw.grid(t, pos=pos)
        ks = None
        for row, ps in zip(rows, pos):
            h = header(row)
            if h:
                ks = h
                continue
            if not ks:
                continue
            f = {}
            for k, v in zip(ks, row):
                v = _esw.clean(v)
                if k and v and k not in f:
                    f[k] = v
            if "name_post" in f:
                f.setdefault("name", ""), f.setdefault("post", "")
                f["name"], f["post"] = split_name_post(f["name_post"])
            name, post = re.sub(r"\s*\|\s*", " ", f.get("name", "")), re.sub(r"\s*\|\s*", " ", f.get("post", ""))
            if not (name or post) or (name and _esw.clean(name).lower() in ("name", "नाम")):
                continue
            phone = _esw.phones(f.get("phone", ""))
            mobile = _esw.phones(f.get("mobile", ""))
            out.append(_state.rec(
                MODULE, f"{p['key']}:{ps['table']}:{ps['row']}", state=p["state"], level=p.get("level", "state"), post=post,
                post_kind=(p.get("post_kinds") or {}).get(post) or None,
                name=name, body=p.get("body", ""), body_kind=p.get("body_kind", ""), department=p.get("department", ""),
                dept=p.get("dept"), phone=", ".join(x for x in (phone, mobile) if x), mobile=mobile or None,
                fax=f.get("fax"), email=_esw.emails(f.get("email", "") + " " + f.get("phone", "")), room=f.get("room"),
                ip=f.get("ip"), address=f.get("address", ""), cells=row, source=url, src_url=url, src_pos=ps))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p, p["url"])
    return recs, [_esw.keep(MODULE, p["key"], r.content)], "" if recs else "no rows"
