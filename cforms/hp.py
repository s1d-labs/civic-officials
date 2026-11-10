"""Himachal Pradesh: SEC DPMIS "Elected Representatives" (sechimachal.hp.gov.in/dpmis/repList.aspx, ASP.NET WebForms). India only.

One queue item = one urban body. The page is switched to English (district and body names in English; member names stay in
Devanagari), then the postbacks a browser makes: language, level, district, then "View List" with post W (ward members).
- level 002 = municipal councils and nagar panchayats: the body is the ddlPanch choice ("all bodies" answers nothing).
- level 003 = municipal corporations: the body is the ddlBlk choice (one more postback), ddlPanch "00" = all wards.
Term "all": when a body lists more than one term, the latest term is kept. No party column. MC Shimla (2023) has no rows here.
`python -m cforms.hp > seeds/councillors_hp.json` makes the queue items (run from India).
"""
import gzip
import json
import re

from bs4 import BeautifulSoup

from forms.aspnet import hidden, options

URL = "https://sechimachal.hp.gov.in/dpmis/repList.aspx"
P = "ctl00$ContentPlaceHolder1$"
LEVELS = {"002": "Municipal Council / Nagar Panchayat", "003": "Municipal Corporation"}
COLS = ("term", "term_start", "ward", "name", "gender", "age", "address", "phone")


def form(html):
    """The fields a browser sends: hidden inputs, checked radios, the selected option of each select."""
    soup = BeautifulSoup(html, "lxml")
    d = hidden(html)
    for i in soup.select("input[type=radio][checked]"):
        d[i["name"]] = i.get("value")
    for sel in soup.select("select[name]"):
        o = sel.find("option", selected=True) or sel.find("option")
        if o is not None:
            d[sel["name"]] = o.get("value")
    return d


def post(get, html, target, fields):
    """A postback (autopostback control `target`); returns the new page or None."""
    if html is None:
        return None
    d = form(html)
    d.pop(P + "btnShow", None)
    d.update(fields)
    d.update({"__EVENTTARGET": target, "__EVENTARGUMENT": ""})
    r = get(URL, method="POST", data=d)
    return r.text if r is not None else None


def choices(html, name):
    return [(v, t) for v, t in options(html or "", name) if len(v) > 2]          # not "00" (all) or "13" (all districts)


def walk(get, lvl, dis=None, lang="en-GB"):
    """Language, level and (unless None) district chosen; returns (page, fields so far)."""
    r = get(URL)
    f = {"ctl00$ddllang": lang}
    h = post(get, r.text if r is not None else None, "ctl00$ddllang", f)
    f[P + "rbPriPost"] = lvl
    h = post(get, h, P + "rbPriPost$" + str(int(lvl) - 1), f)
    if dis is None:
        return h, f
    f[P + "ddlDis"] = dis
    return post(get, h, P + "ddlDis", f), f


def rows(html):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tr in soup.select("#ContentPlaceHolder1_gvNominationList tr"):
        tds = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]
        if len(tds) == len(COLS):
            out.append(dict(zip(COLS, tds)))
    return out


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def record(p, x):
    m = re.match(r"(\d+)\s*-\s*(?:\d+\b\s*)?(.*)$", x["ward"])    # "1 - 1 ढाबो" (councils), "1 - FORSYTHGANJ" (corporations)
    ward_no = m.group(1) if m else x["ward"]
    started = re.match(r"(\d\d-\d\d-\d{4})", x["term_start"])
    d = {"type": "councillor", "state": "HP", "body": p["body"], "body_hi": p.get("body_hi"), "body_id": p["body_id"],
         "body_type": LEVELS.get(p["level"]), "district": p["district"], "district_hi": p.get("district_hi"),
         "ward_no": ward_no, "ward_name": m.group(2).strip() if m else None, "ward": x["ward"], "name": x["name"],
         "gender": x["gender"], "age": x["age"], "address": x["address"], "phone": x["phone"], "term": x["term"],
         "term_start": started.group(1) if started else x["term_start"], "election": f"Himachal Pradesh {x['term'][:4]}", "url": URL}
    return f"councillor:HP:{slug(p['body'])}:{ward_no}", {k: v for k, v in d.items() if v not in (None, "")}


def fetch(p, get):
    html, f = walk(get, p["level"], p["district_id"])
    if p["level"] == "003":
        f[P + "ddlBlk"] = p["body_id"]
        html = post(get, html, P + "ddlBlk", f)
        f[P + "ddlPanch"] = "00"
    else:
        f[P + "ddlPanch"] = p["body_id"]
    if html is None:
        return [], [], "no answer"
    d = form(html)
    d.pop("__EVENTTARGET", None)
    d.update(f)
    d.update({P + "rbPost": "W", P + "btnShow": "View List"})
    r = get(URL, method="POST", data=d)
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/HP/body-{p['body_id']}.html.gz", gzip.compress(r.content), "application/gzip")]
    got = rows(r.text)
    if not got:
        return [], files, "no members listed" if "Could Not Find" in r.text else "no member table"
    latest = max(x["term"] for x in got)
    return [record(p, x) for x in got if x["term"] == latest], files, ""


def bodies(get, lang):
    """{(level, district id, body id): (district name, body name)} in one language."""
    out = {}
    for lvl in LEVELS:
        first, _ = walk(get, lvl, None, lang)
        for dis, dname in choices(first, "ddlDis"):
            h, f = walk(get, lvl, dis, lang)
            for bid, bname in choices(h, "ddlBlk" if lvl == "003" else "ddlPanch"):
                out[(lvl, dis, bid)] = (dname, bname)
    return out


def items(get):
    en, hi = bodies(get, "en-GB"), bodies(get, "hi-IN")
    return [{"key": f"hp-{bid}", "payload": {
        "kind": "form-hp", "state": "HP", "url": URL, "level": lvl, "district_id": dis, "district": n[0],
        "district_hi": hi.get(k, (None,))[0], "body_id": bid, "body": n[1], "body_hi": hi.get(k, (None, None))[1]}}
        for k, n in sorted(en.items()) for lvl, dis, bid in [k]]


if __name__ == "__main__":
    import time

    from forms.aspnet import session
    s = session()

    def get(url, method="GET", data=None, headers=None):
        r = s.request(method, url, data=data, headers=headers, timeout=(20, 90))
        time.sleep(1)
        return r if r.status_code == 200 else None
    print(json.dumps(items(get), ensure_ascii=False, indent=1))
