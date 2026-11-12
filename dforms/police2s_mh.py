"""Maharashtra Police district and commissionerate sites on the new state template (Next.js, server rendered, 2026):
https://<host>/en/about/police-station-incharge (one card per station: name linked to /about/police-station-incharge/<uuid>,
rank, the station ("Currently Posted"), "• <sub division>", tel: links, mailto: link) and https://<host>/en/about/senior-officers
(SP, Addl. SP, SDPO / ACP, DCP cards, the same layout). The /mr/ copy of the same page gives the Marathi names and station names
(name_regional, area_regional); cards are matched by uuid. Emails are sometimes written "xdotyatmahapolicedotgovdotin".
Sites move to this template one by one (2026-11: Dhule, Kolhapur, Solapur Rural, Thane Rural, Akola, Pune Railway ...; Latur
showed "Website Under Maintenance"; the older static template (/police-station-incharge, data loaded by JavaScript) has no
data in the HTML). The pages answer from outside India (Kolhapur, Dhule); Navi Mumbai answers 403 abroad (india_only).
One queue item = one page in English + its Marathi copy (2 requests). Record id dept:police2s_mh:<host key>:<uuid>."""
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

import provenance
from dforms._police import clean, email, gz, phones, rec, slug, uniq

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

M = "police2s_mh"
UUID = re.compile(r"/about/(police-station-incharge|senior-officers)/([0-9a-f-]{36})")
LABEL = re.compile(r"^(?:Currently Posted|कार्यरत पोलीस ठाणे|कार्यरत|Posted at|•)$", re.I)
SUBDIV = re.compile(r"\b(?:SDPO|S\.D\.P\.O|Sub[- ]?Divisional?|Sub[- ]?Division|ACP|Assistant Commissioner|Dy\.?\s?S\.?P|DYSP|"
                    r"Deputy Superintendent)\b|उपविभागीय|सहायक पोलीस आयुक्त", re.I)
ZONE = re.compile(r"\b(?:DCP|Deputy Commissioner)\b|पोलीस उपायुक्त", re.I)
DISTRICT = re.compile(r"\b(?:S\.?P|Superintendent|Commissioner|Addl\.?|Additional|Add\.)\b|पोलीस अधीक्षक|पोलीस आयुक्त", re.I)
HQ = re.compile(r"\((?:HQ|Home|Hq)\)|\bHQ\b|Headquarter|मुख्यालय|\bHome\b|Crime|Special|Traffic|EOW|LCB", re.I)


def cards(html):
    """{uuid: {"section", "name", "rank", "area", "subdivision", "phones", "email", "texts"}} of one listing page."""
    soup = BeautifulSoup(html, "lxml")
    out = {}
    for a in soup.find_all("a", href=UUID):
        m = UUID.search(a["href"])
        sec, uid = m.group(1), m.group(2)
        if uid in out or not clean(a.get_text(" ", strip=True)):
            continue
        box = a
        for _ in range(8):           # the smallest block that still holds only this card
            up = box.parent
            if up is None or len({UUID.search(x["href"]).group(2) for x in up.find_all("a", href=UUID)}) > 1:
                break
            box = up
        texts = [clean(t) for t in box.stripped_strings]
        texts = [t for t in texts if t]
        name = clean(a.get_text(" ", strip=True))
        i = texts.index(name) + 1 if name in texts else 0
        rest = [t for t in texts[i:] if not LABEL.match(t)]
        words = [t for t in rest if not re.search(r"\d{6,}|@|dot\w*at\w*dot|^Mob", t, re.I)]
        rank = words[0] if words else None
        area = words[1] if len(words) > 1 and sec == "police-station-incharge" else None
        sub = None
        if "•" in texts:
            j = texts.index("•")
            sub = texts[j + 1] if j + 1 < len(texts) else None
        tel = [x["href"][4:] for x in box.select('a[href^="tel:"]')]
        mail = next((x["href"][7:] for x in box.select('a[href^="mailto:"]')), None)
        if not mail:
            mail = next((t for t in rest if "@" in t or re.search(r"dot\w*at\w*dot", t)), None)
        out[uid] = {"section": sec, "name": name, "rank": rank, "area": area, "subdivision": sub,
                    "phones": phones(*tel, *[t for t in rest if re.search(r"\d{6,}", t)]), "email": email(undot(mail))}
    return out


def undot(s):
    """'sdpodotbarshidotdivatmahapolicedotgovdotin' -> 'sdpo.barshi.div@mahapolice.gov.in'."""
    s = clean(s) or ""
    if "@" in s or not re.search(r"dot", s):
        return s
    m = re.match(r"^(.+?)at(mahapolice|gmail|nic|gov)(dot.+)$", s)
    if not m:
        return s
    return m.group(1).replace("dot", ".") + "@" + m.group(2) + m.group(3).replace("dot", ".")


def level_of(c):
    t = " ".join(x for x in (c["rank"], c["area"]) if x)
    if c["section"] == "police-station-incharge":
        return "police_station", "police station"
    if SUBDIV.search(t) and not HQ.search(t):
        return "subdivision", "office"
    if ZONE.search(t):
        return "zone", "office"
    if DISTRICT.search(t) or SUBDIV.search(t):
        return "district", "office" if not HQ.search(t) else "unit"
    return "district", "unit"


def sub_area(rank):
    """'Sub-Division Police Officer, Karmala' / 'SDPO Murbad Division' -> 'Karmala' / 'Murbad'."""
    r = clean(rank) or ""
    m = re.search(r"(?:Officer|SDPO|ACP|DYSP|Dy\.?\s?SP)[,.\s-]+(.+?)\.?$", r, re.I)
    a = m.group(1) if m else r
    return re.sub(r"\s*(?:Sub[- ]?)?Division$", "", a, flags=re.I).strip(" ,.-") or r


def fetch(p, get):
    url = p["url"]
    host = urlparse(url).hostname
    r = get(url)
    if r is None:
        return [], [], "no answer"
    name = slug(re.sub(r"^https?://", "", url))[:80]
    files = [gz(M, f"{name}.html", r.content)]
    en = cards(r.text)
    if not en:
        why = "site under maintenance" if "Under Maintenance" in r.text else "no officer cards on the page (old template?)"
        return [], files, why
    mr = {}
    if p.get("marathi", True):
        x = get(url.replace("/en/", "/mr/", 1))
        if x is not None:
            files.append(gz(M, f"{name}-mr.html", x.content))
            mr = cards(x.text)
    recs = []
    for uid, c in en.items():
        m = mr.get(uid, {})
        level, otype = level_of(c)
        if level == "police_station":
            area, area_mr, post = c["area"], m.get("area"), c["rank"]
        elif level == "subdivision":
            area, area_mr, post = sub_area(c["rank"]), None, c["rank"]
        else:
            area, area_mr, post = c["rank"], m.get("rank"), c["rank"]
        recs.append(rec(M, f"{slug(p.get('key') or host.split('.')[0])}:{uid}", level=level, office_type=otype, area=area,
                        area_regional=area_mr if area_mr != area else None, post=post, post_regional=m.get("rank"),
                        name=c["name"], name_regional=m.get("name") if m.get("name") != c["name"] else None,
                        phone=c["phones"] or m.get("phones"), email=c["email"] or m.get("email"),
                        subdivision=c["subdivision"] if level == "police_station" else None,
                        state="MH", district=p.get("district"), office_id=uid, source=f"https://{host}/en/about/{c['section']}/{uid}",
                        # English listing page; the Marathi fields (*_regional) from the same card on the /mr/ page
                        **provenance.at(r, url), src_pos={"card_link_uuid": uid, **({"regional_from": url.replace("/en/", "/mr/", 1)} if m else {})}))
    return uniq(recs), files, ""
