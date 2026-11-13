"""Kerala: the village office of each revenue village (Village Officer: official mobile 85476xxxxx, office phone, e-mail) and
the Grama Panchayat secretary / president mobiles, from the 14 district portals (S3WaaS, English pages).

Pages (measured 2026-11-13 on the archive.s1d.me copies of 2026-11-05 .. 11-11):
  village offices: alappuzha.nic.in/en/villages/ (one table per taluk: Villages, Village Office Number, Village Officer Number),
  kozhikode.nic.in/en/about-district/adminstration/villages/ (Village Name, Mobile Number, Email ID), palakkad.nic.in/en/villages/
  (Village Name, Contact No.), idukki.nic.in/en/revenue/ (Name of Village, Telephone, Mobile, Email), ernakulam.nic.in/en/revenue/
  (Village Name, Mobile, Tel.Office, Email), thrissur.nic.in/en/villages-255/ ("Localbody" = the village, Phone Number, Email
  votsr...), trivandrum.nic.in/en/villages/ (Taluk Name, Village Name, Phone Number, Mobile Number), kollam.nic.in/en/revenue-
  officers/ (one table per taluk; rows "Village Officer, <village>" | mobile, with the Tahsildar rows above them).
  grama panchayats: <district>/en/village-panchayats/ (Kasaragod: LB Name, Phone, Mobile Secretary, Mobile President, email).
No page names the officer: the record is the post of the village (the official mobile goes with the post, not the person).
Columns come from the header words; the taluk from a "Taluk" column, the table's caption / heading / tab label ("Villages of
Kozhikode Taluk", "Revenue Division – Alappuzha, Taluk – Cherthala"), or a "<X> TALUK" header cell (Kollam). E-mails written
as "[dot]" / "[at]" / "(at)" are read as "." / "@".

Records: village office -> dept revenue, level village, post "Village Officer", post_regional "വില്ലേജ് ഓഫീസർ", area = village,
phone = officer mobile then office phone, phone_office, email, taluk, district (payload). Grama panchayat -> dept
rural_development, level gram_panchayat, post "Grama Panchayat Secretary" (and "Grama Panchayat President", kind elected, when
the page gives the president's mobile), area = panchayat name. Other rows of the same pages (Tahsildar, Collector, taluk
counts) are left out: other readers take the district and taluk offices.
One queue item per page. Ids dept:vil_kl_s3waas:<host>:<table>-<row>[:p].
"""
import re
from urllib.parse import urlparse

from dforms import _esw
import provenance

METHOD = "html table (header words -> columns; taluk from caption / heading / tab label)"

MODULE = "vil_kl_s3waas"
VO_POST, VO_ML = "Village Officer", "വില്ലേജ് ഓഫീസർ"

AREA_H = re.compile(r"(?i)village|office name|localbody|local body|lb name|panchayat|name of (the )?gp")
TALUK_H = re.compile(r"(?i)taluk")
SNO_H = re.compile(r"(?i)^(sl\.?\s*no\.?|s\.?\s*no\.?|sino|no\.?|sr\.?\s*no\.?)$")
EMAIL_H = re.compile(r"(?i)e-?mail")
SEC_H = re.compile(r"(?i)secretary")
PRES_H = re.compile(r"(?i)president")
OFFICE_H = re.compile(r"(?i)office number|tel\.?\s*office|telephone|land ?phone|landline|phone no\b|^phone$")
MOBILE_H = re.compile(r"(?i)officer number|mobile|contact|phone number|cug")
VO_ROW = re.compile(r"(?i)^village\s+officer\s*[,:-]\s*(.+)$")
TALUK_TXT = re.compile(r"(?i)taluk\s*[–:-]?\s*([A-Za-z][A-Za-z .]+?)\s*$|([A-Za-z][A-Za-z .]+?)\s*(tribal\s+)?taluk\b")


def email_of(s):
    s = re.sub(r"\s*[\[(]\s*dot\s*[\])]\s*", ".", s or "", flags=re.I)
    s = re.sub(r"\s*[\[(]\s*at\s*[\])]\s*", "@", s, flags=re.I)
    return ", ".join(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", s))


def taluk_of(text):
    t = _esw.clean(text)
    if not t or not re.search(r"(?i)taluk", t):
        return None
    m = TALUK_TXT.search(t)
    if not m:
        return None
    v = (m.group(1) or m.group(2) or "").strip()
    v = re.sub(r"(?i)^(villages?|village offices?)\s+(of|in)\s+", "", v).strip(" ,.-")
    return v.title() if v.isupper() else v or None


def caption(t):
    """Taluk words near the table: caption, the nearest heading before it, or the label of the tab that holds it."""
    c = t.find("caption")
    if c and taluk_of(c.get_text(" ")):
        return taluk_of(c.get_text(" "))
    for par in t.parents:
        pid = par.get("id") if hasattr(par, "get") else None
        if pid:
            a = t.find_parent("html").find("a", href="#" + pid) if t.find_parent("html") else None
            if a and taluk_of(a.get_text(" ") + " taluk"):
                return taluk_of(a.get_text(" ") + " taluk")
    h = t.find_previous(["h1", "h2", "h3", "h4", "h5", "strong", "p"])
    for _ in range(4):
        if h is None:
            break
        tk = taluk_of(h.get_text(" "))
        if tk:
            return tk
        if h.find_previous("table") is not None and h.find_previous("table") is not t and h.find_previous("table") in t.find_all_previous("table")[:1]:
            break
        h = h.find_previous(["h1", "h2", "h3", "h4", "h5", "strong", "p"])
    return None


def roles(head):
    out = {}
    for i, h in enumerate(head):
        h = _esw.clean(h)
        if not h:
            continue
        if SNO_H.match(h):
            out[i] = "sno"
        elif EMAIL_H.search(h):
            out[i] = "email"
        elif SEC_H.search(h):
            out[i] = "sec_phone"
        elif PRES_H.search(h):
            out[i] = "pres_phone"
        elif TALUK_H.search(h) and not re.search(r"(?i)village", h):
            out[i] = "taluk"
        elif OFFICE_H.search(h):
            out[i] = "office_phone"
        elif MOBILE_H.search(h):
            out[i] = "mobile"
        elif AREA_H.search(h):
            out[i] = "area"
    mob = [i for i, k in out.items() if k == "mobile"]
    if len(mob) > 1:        # "Phone Number" + "Mobile Number": the first is the office line
        for i in mob:
            if not re.search(r"(?i)mobile|officer|cug", head[i]):
                out[i] = "office_phone"
    return out


def _head(t):
    return [_esw.clean(c.get_text(" ")) for c in (t.find("tr").find_all(["td", "th"]) if t.find("tr") else [])]


def _is_list(t):
    """A village / panchayat list table (not the taluk count table)."""
    hd = _head(t)
    rl = roles(hd)
    return ("area" in rl.values() and bool({"mobile", "office_phone", "email", "sec_phone"} & set(rl.values()))
            and not any(re.fullmatch(r"(?i)taluks?", h) for h in hd))


def records(html, url, p):
    soup = _esw.soup(html)
    host = urlparse(url).netloc
    kind = p.get("kind") or "village_office"
    dist = p.get("district")
    recs = []
    tables = soup.find_all("table")
    order = []
    for t in tables:
        hd = [_esw.clean(c.get_text(" ")) for c in (t.find("tr").find_all(["td", "th"]) if t.find("tr") else [])]
        if any(re.fullmatch(r"(?i)taluks?", h) for h in hd) and any(re.fullmatch(r"(?i)villages?", h) for h in hd):
            ci = next(i for i, h in enumerate(hd) if re.fullmatch(r"(?i)taluks?", h))
            order = [_esw.clean(r.find_all(["td", "th"])[ci].get_text(" ")).title() for r in t.find_all("tr")[1:]
                     if len(r.find_all(["td", "th"])) > ci]
            order = [o for o in order if o and not re.fullmatch(r"(?i)total", o)]
            break
    vtab = 0
    for ti, t in enumerate(tables, 1):
        rows = [[_esw.clean(c.get_text(" ")) for c in r.find_all(["td", "th"])] for r in t.find_all("tr")]
        rows = [r for r in rows if any(r)]
        if len(rows) < 2:
            continue
        head = rows[0]
        rl = roles(head)
        cap = caption(t)
        kollam = len(head) >= 2 and re.fullmatch(r"[A-Z][A-Z .]+ TALUK", head[0] or "") and "area" not in rl.values()
        if kollam:
            cap = taluk_of(head[0]) or cap
        elif "area" not in rl.values() or not ({"mobile", "office_phone", "email", "sec_phone"} & set(rl.values())):
            continue
        else:
            vtab += 1
            if not cap and order and len(order) == sum(1 for x in tables if _is_list(x)):
                cap = order[vtab - 1]
        for ri, r in enumerate(rows[1:], 2):
            cell = {}
            for i, c in enumerate(r):
                k = "area" if kollam and i == 0 else ("mobile" if kollam and i == 1 else rl.get(i))
                if k and c and c not in ("-", "–", "—"):
                    cell.setdefault(k, c)
            area = cell.get("area", "")
            if kollam:
                m = VO_ROW.match(area)
                if not m:
                    provenance.skip_row(r, 'skip: not m')
                    continue
                area = m.group(1)
            if not area or re.fullmatch(r"(?i)total|grand total", area):
                provenance.skip_row(r, 'skip: not area or re.fullmatch(r"(?i)total|grand total", area)')
                continue
            if re.fullmatch(r"\d+", area):
                provenance.skip_row(r, 'skip: re.fullmatch(r"\\d+", area)')
                continue        # a count column read as an area
            raw = {(head[i] if i < len(head) and head[i] else f"col{i + 1}"): c for i, c in enumerate(r) if c}
            pos = {"table": ti, "row": ri, "cells": r}
            tk = cell.get("taluk") or cap or p.get("taluk")
            key = f"{host}:{ti}-{ri}"
            common = dict(state="KL", district=dist, taluk=tk, area=area, source=url, src_url=url, src_pos=pos, table_row=raw,
                          serial=cell.get("sno"), email=email_of(cell.get("email")), method=METHOD, last_updated=p.get("last_updated"),
                          tls_unverified=p.get("tls_unverified"))
            if kind == "gram_panchayat":
                sec = _esw.phones(cell.get("sec_phone", "")) or (_esw.phones(cell.get("mobile", "")) if "sec_phone" not in rl.values() else "")
                office = _esw.phones(cell.get("office_phone", ""))
                if sec or office or common["email"]:
                    recs.append(_esw.record(MODULE, key, dept="rural_development", level="gram_panchayat",
                                            post="Grama Panchayat Secretary", post_regional="ഗ്രാമപഞ്ചായത്ത് സെക്രട്ടറി",
                                            phone=", ".join(x for x in (sec, office) if x), phone_office=office or None,
                                            office_id=f"{host}:gp:{_esw.slug(area)}", **common))
                pres = _esw.phones(cell.get("pres_phone", ""))
                if pres:
                    c2 = dict(common, email=None)
                    recs.append(_esw.record(MODULE, key + ":p", dept="rural_development", level="gram_panchayat",
                                            post="Grama Panchayat President", post_regional="ഗ്രാമപഞ്ചായത്ത് പ്രസിഡന്റ്",
                                            kind="elected", phone=pres, office_id=f"{host}:gp:{_esw.slug(area)}", **c2))
            else:
                mob = _esw.phones(cell.get("mobile", ""))
                office = _esw.phones(cell.get("office_phone", ""))
                if not (mob or office or common["email"]):
                    provenance.skip_row(r, 'skip: not (mob or office or common["email"])')
                    continue
                recs.append(_esw.record(MODULE, key, dept="revenue", level="village", post=VO_POST, post_regional=VO_ML,
                                        phone=", ".join(x for x in (mob, office) if x), phone_mobile=mob or None,
                                        phone_office=office or None, office_id=f"{host}:vo:{_esw.slug(area)}", **common))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    host = urlparse(p["url"]).netloc
    files = [_esw.keep(MODULE, f"{host}-{_esw.slug(urlparse(p['url']).path)[-50:] or 'page'}", r.content, "html")]
    recs = records(r.text, p["url"], p)
    return recs, files, "" if recs else "no village office / panchayat table"


def items(get=None):
    from dforms import _field
    return _field.seed(MODULE)
