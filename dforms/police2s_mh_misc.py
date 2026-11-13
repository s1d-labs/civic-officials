"""Maharashtra police sites on their own CMS (not the state Next.js template of police2s_mh), all server rendered, all with the
officer's name. Payload "kind":
- "labels": label / value blocks in the page text. Amravati City (amravaticitypolice.gov.in/designations_spi.php = senior PIs of
  the stations, designations11.php?rank_name=ACP|DCP: "Rank: | Name: | Office phone no.: | Contact no: | Email ID:"), Sangli
  (www.sanglipolice.gov.in/<name>-police-station/: "Police Station Incharge | NAME | Email | : x | Landline | :.. | Mobile | :.."),
  Nagpur Rural (nagpurgraminpolice.gov.in/contact-list/: "<station> | Name of Incharge | .. | Designation | .. | Contact Number"
  and the same in Marathi: "<स्टेशन> | पत्ता | .. | पदनाम | .. | लँडलाइन नंबर | .. | प्रभारीचे नाव | .. | मोबाईल नंबर"). English and
  Marathi blocks with the same mobile are one record (Marathi text in *_regional).
- "ranked": Yavatmal (yavatmalpolice.gov.in/officers/police-station-incharge): under "<X> Sub Division" headings, one line
  "PI|API|PSI <name>", then the station, the mobile and the email.
- "table": Amravati City contacts.php (Designation | Name | Office contact | Mobile | Office Email): parsed by police_s3waas.
Digits in Devanagari become ASCII. Works from outside India (archive copies saved 2026-11-05..07; the hosts answer abroad).
One queue item = one page. Record id dept:police2s_mh_misc:<site>:<slug of station or post>."""
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from dforms import police_s3waas
from dforms._police import ascii_digits, clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police2s_mh_misc"
DEV = re.compile(r"[ऀ-ॿ]")
LABELS = {
    "name": {"name", "name of incharge", "प्रभारीचे नाव", "police station incharge", "officer name", "incharge"},
    "station": {"police station", "पोलीस स्टेशन", "police station name"},
    "rank": {"rank", "designation", "पदनाम"},
    "office": {"office phone no.", "landline", "लँडलाइन नंबर", "office phone", "office contact"},
    "mobile": {"contact no", "mobile", "contact number", "संपर्क क्रमांक", "मोबाईल नंबर", "mobile no"},
    "email": {"email id", "email", "e-mail", "ईमेल"},
    "address": {"पत्ता", "address"},
    "division": {"विभाग", "division", "sub division"},
}
LABEL_OF = {v: k for k, vs in LABELS.items() for v in vs}
STATION_TOKEN = re.compile(r"(?:police|पोलीस|पोलिस)\s*(?:station|स्टेशन|ठाणे)\s*$", re.I)
RANK_LINE = re.compile(r"^(S?PI|API|PSI|ASI|P\.?I\.?|A\.?P\.?I\.?|P\.?S\.?I\.?)\s+(.+)$")
SUBDIV_HEAD = re.compile(r"^(.+?)\s+Sub[- ]?Division$", re.I)
ACP_RANK = re.compile(r"\bACP\b|Assistant Commissioner|SDPO|DySP", re.I)
DCP_RANK = re.compile(r"\bDCP\b|Deputy Commissioner", re.I)
CP_RANK = re.compile(r"Commissioner of Police|\bCP\b|\bS\.?P\b|Superintendent", re.I)


def label(tok):
    t = (clean(tok) or "").strip().rstrip(":").strip().lower()
    return LABEL_OF.get(t)


def tokens(html):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        t.decompose()
    out = []
    for s in soup.stripped_strings:
        s = clean(ascii_digits(s))
        if s and s != ":":
            out.append(s)
    return out


def label_blocks(toks):
    """[{field: value}] from a token stream of labels and values."""
    blocks, cur = [], {}
    i = 0
    while i < len(toks):
        t = toks[i]
        k = label(t)
        if k is None and STATION_TOKEN.search(t) and i + 1 < len(toks) and label(toks[i + 1]):
            if cur:
                blocks.append(cur)
            cur = {"station": t}
            i += 1
            continue
        if k is None:
            m = re.match(r"^([^:]{2,30}):\s*(.+)$", t)        # "Name: X" in one token
            if m and label(m.group(1)):
                k, t = label(m.group(1)), None
                val = m.group(2)
            else:
                i += 1
                continue
        else:
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            val = None if label(nxt) or (STATION_TOKEN.search(nxt) and k != "station" and i + 2 < len(toks) and label(toks[i + 2])) else nxt
            if val is not None:
                i += 1
        val = (val or "").lstrip(": ").strip() or None
        if k in cur and k in ("name", "rank", "station"):
            blocks.append(cur)
            cur = {}
        if val is not None:
            cur[k] = val
        else:
            cur.setdefault(k, None)
        i += 1
    if cur:
        blocks.append(cur)
    return [b for b in blocks if b.get("name") or b.get("mobile")]


def level_of(rank, station):
    r = rank or ""
    if station:
        return "police_station", "police station"
    if ACP_RANK.search(r):
        return "subdivision", "office"
    if DCP_RANK.search(r):
        return "zone", "office"
    if CP_RANK.search(r):
        return "district", "office"
    return "district", "unit"


def merge_scripts(blocks):
    """An English and a Marathi block with the same mobile: one block, Marathi text kept as *_mr."""
    out, by_mob = [], {}
    for b in blocks:
        mob = phones(b.get("mobile")) or ""
        dev = bool(DEV.search(" ".join(str(v) for v in b.values() if v)))
        o = by_mob.get(mob) if mob else None
        if o is not None and o["_dev"] != dev:
            src, dst = (b, o) if dev else (o, b)
            for k in ("name", "station", "rank"):
                if src.get(k):
                    dst[k + "_mr"] = src[k]
            if dev:
                provenance.skip_row(b, 'skip: dev')
                continue
            out[out.index(o)] = b
            by_mob[mob] = b
            b["_dev"] = False
            continue
        b["_dev"] = dev
        if mob and mob not in by_mob:
            by_mob[mob] = b
        out.append(b)
    return out


def site(url, p):
    return p.get("site") or urlparse(url).hostname.replace("www.", "").split(".")[0]


def from_labels(html, url, p):
    recs = []
    for b in merge_scripts(label_blocks(tokens(html))):
        station = b.get("station") or p.get("station")
        rank = b.get("rank")
        level, otype = level_of(rank, station)
        area = station or rank or p.get("area")
        if not area:
            continue
        name, name_mr = b.get("name"), b.get("name_mr")
        if name and DEV.search(name) and not name_mr:
            name_mr = name
        recs.append(rec(M, f"{slug(site(url, p))}:{slug(area)}", level=level, office_type=otype, area=area,
                        area_regional=b.get("station_mr") or (area if DEV.search(area) else None),
                        post=rank or ("Police Station Incharge" if station else None), post_regional=b.get("rank_mr"),
                        name=name, name_regional=name_mr, phone=phones(b.get("mobile"), b.get("office")), email=email(b.get("email")),
                        address=b.get("address"), subdivision=b.get("division") if level == "police_station" else None,
                        state="MH", district=p.get("district"), source=url))
    return recs


def from_ranked(html, url, p):
    toks, recs, sub = tokens(html), [], None
    i = 0
    while i < len(toks):
        t = toks[i]
        h = SUBDIV_HEAD.match(t)
        if h and not (i + 1 < len(toks) and SUBDIV_HEAD.match(toks[i + 1])):
            sub = h.group(1)
        m = RANK_LINE.match(t)
        if m and i + 1 < len(toks) and STATION_TOKEN.search(toks[i + 1]):
            station = toks[i + 1]
            j, nums, mail = i + 2, [], None
            while j < len(toks) and not RANK_LINE.match(toks[j]) and j < i + 6:
                if "@" in toks[j]:
                    mail = mail or email(toks[j])
                elif re.search(r"\d{3}", toks[j]):
                    nums.append(toks[j])
                j += 1
            recs.append(rec(M, f"{slug(site(url, p))}:{slug(station)}", area=station, post=m.group(1), name=m.group(2),
                            phone=phones(*nums), email=mail, subdivision=sub, office_type="police station", state="MH",
                            district=p.get("district"), source=url))
            i = j
            continue
        i += 1
    return recs


def fetch(p, get):
    kind, url = p.get("kind", "labels"), p["url"]
    if kind == "table":
        recs, files, why = police_s3waas.fetch({"state": "MH", **p}, get, M)
        for _, d in recs:
            lv, ot = level_of(d.get("post") or d.get("area"), None)
            d["level"], d["office_type"] = lv, ot
        return recs, files, why
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [gz(M, f"{slug(re.sub(r'^https?://', '', url))[:80]}.html", r.content)]
    recs = uniq((from_ranked if kind == "ranked" else from_labels)(r.text, url, p))
    return recs, files, "" if recs else "no officers on the page"
