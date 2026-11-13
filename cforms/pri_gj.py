"""Gujarat: elected Panchayati Raj representatives (district panchayat, taluka panchayat, gram panchayat) from the open pages of
the 33 district panchayat portals <district>dp.gujarat.gov.in (one ASP.NET MVC template, Gujarati; the same portals as
dforms/gp_gj_tcm.py, which reads the Talati-cum-Mantri lists).

Why these portals: the State Election Commission publishes no seat-wise winners as open pages or files. Its result portal
sec-poll.gujarat.gov.in asks for a captcha (not automated); its "District / Taluka Panchayat 2020" pages hold scanned seat
rotation orders, not results (checked on archive.s1d.me copies of 2026-11-05).

Structure (archive.s1d.me copies 2026-11-05..11 and live pages 2026-11-13, from Mumbai):
- district menu: "પદાધિકારીશ્રીઓની માહિતી" (/gu/Information-of-office-bearers, /gu/members-list, /gu/Padadhikari-list,
  /gu/List-of-Office-Bearers), "elected-members-..." (Dang, Navsari), /gu/Names-of-DistrictPanchayatMembers (Vadodara),
  /gu/President-Vice-President-Members (Tapi), "વિવિઘ સમિતીઓના અઘ્યક્ષશ્રીઓની માહીતી" (committee chairs), "પ્રમુખ વિષે"
  (/gu/About-President[/<id>]: one div.contact-box: h5 name, "Designation :", "Mobile No :", "E-mail :");
- taluka pages /gu/taluka/<Taluka>/...: "સદસ્યશ્રીઓની યાદી" (Sadaya-List), "પદાધિકારી માહિતી" (member-list), "સરપંચશ્રીઓની
  વિગત" (Sarpanch-Details), Sarpanch-List, list-of-members, About-President;
- some districts link PDFs instead (sarpanch lists, member lists; often on panchayat.gujarat.gov.in; mostly scans).
Tables: header row = the first of the first 4 rows with a name / sarpanch column and a mobile, designation or seat column.
Column roles from header words: seat (મતદાર મંડળ / સીટ / બેઠક: "૧-ભાંથલા" = seat 1, Bhanthala), name (નામ), designation
(હોદ્દો: પ્રમુખ, ઉપપ્રમુખ, કારોબારી અધ્યક્ષ, સભ્ય ...), sarpanch (સરપંચ), gram panchayat / village, taluka, district, address,
mobile, email, party. TCM / VCE columns (officers) and their mobiles are left out. Gujarati digits are read as digits.
Levels: a row with a Sarpanch name -> gp (head); else a page under /gu/taluka/<T>/ -> ps; else a table with a taluka column on a
page whose address or link text names taluka panchayats -> ps; else zp. A designation that names "તાલુકા પંચાયત" / "જિલ્લા
પંચાયત" decides it for that row. Rows whose designation names an officer (અધિકારી, મંત્રી, TDO ...) are left out.
The lists are as the portal shows them on the fetch date: some are older than the latest poll (field "listed_as" keeps the
page's own words; "election" says "as listed on the district panchayat website").

One queue item = one district: payload {"kind": "form-pri_gj", "state": "GJ", "url" (https://<host>/), "host", "district"
(LGD name), "lgd_code" (district panchayat), "level": "zp+ps+gp", "election", "route"}; optional "talukas": [English names] to
read only those talukas. About 1 + talukas + 2-6 GETs per taluka (30-70 requests).
Record ids: pri:GJ:<level>:<LGD code or names>:<head | vice | w<seat> | r<table>-<row>>; files: pri_gj/<district slug>/... .
"""
import hashlib
import re
import unicodedata
from urllib.parse import urljoin, urlparse

from cforms import _pri
from dforms import _esw
from dforms.gp_gj_tcm import HOSTS, talukas
import provenance

METHOD = "html table (district panchayat portal member / sarpanch pages, header words -> columns) and div.contact-box (About-President)"
STATE = "GJ"
ELECTION = "Gujarat panchayat bodies, as listed on the district panchayat website"
GU_DIGITS = str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789")

LINK = re.compile(r"(?i)member|sabhy|sadas|sadaya|padadhik|bearer|president|pramukh|elected|chutayel|chairperson|sarpanch|"
                  r"સભ્ય|સદસ્ય|પદાધિકારી|પ્રમુખ|સરપંચ|ચૂંટાયેલ")
NOT_LINK = re.compile(r"(?i)gram-?sabha|gramsabha|ગ્રામસભા|irrigation|e-gram|team|women|મહિલા|yojna|yojana|award|પુરસ્|"
                      r"about-ddo/(?!about-president|members|information)|activities|introduction|organization|address|"
                      r"minister|committees$|details-of-officers")
PDF_HOSTS = ("panchayat.gujarat.gov.in",)

SNO_H = re.compile(r"(?i)^(ક્રમ|અ\.?\s*નં\.?|ક્રમ\s*(નં|નંબર|ાંક)\.?|ક્રમાંક|sr\.?\s*no\.?|s\.?\s*no\.?|no\.?)$")
MOBILE_H = re.compile(r"(?i)મોબા|mobile|સંપર્ક|contact|ફોન|phone|contect")
EMAIL_H = re.compile(r"(?i)e-?mail|ઇ-?મેઇલ|ઈ-?મેલ")
SARPANCH_H = re.compile(r"(?i)સરપંચ|sarpanch")
OFFICER_H = re.compile(r"(?i)તલાટી|ત\.\s*ક|tcm|talati|vce|વી\.?સી\.?ઇ|regular|charge|અધિકારી")
DESIG_H = re.compile(r"(?i)હોદ્દો|હોદો|designation|post\b")
SEAT_H = re.compile(r"(?i)મતદાર\s*મંડળ|સીટ|બેઠક|seat|constituency|વોર્ડ|ward|મત\s*વિભાગ")
ADDR_H = re.compile(r"(?i)સરનામ|address")
DIST_H = re.compile(r"(?i)જિલ્લ|જીલ્લ|district")
TALUKA_H = re.compile(r"(?i)તાલુક|taluka")
GP_H = re.compile(r"(?i)ગ્રામ\s*પંચાયત|ગામ|village|gram|panchayat")
PARTY_H = re.compile(r"(?i)પક્ષ|party")
PIN_H = re.compile(r"(?i)pin|પિન")
NAME_H = re.compile(r"(?i)નામ|name")
OFFICER_POST = re.compile(r"(?i)અધિકારી|officer|મંત્રી|ડી\.?\s*ડી\.?\s*ઓ|t\.?d\.?o|d\.?d\.?o|ક્લાર્ક|clerk|ઇજનેર|engineer|"
                          r"તલાટી|મામલતદાર|કચેરી\s*અધિક્ષક")
ELECTED_POST = re.compile(r"(?i)પ્રમુખ|સભ્ય|સદસ્ય|સ્ભ્ય|અધ્યક્ષ|ચેરમેન|સરપંચ|નેતા|દંડક|member|president|chair|sarpanch|leader|whip")


def text(s):
    return _esw.clean(unicodedata.normalize("NFC", s or "").translate(GU_DIGITS))


def roles(header):
    out = {}
    for i, h in enumerate(header):
        h = text(h)
        if not h:
            continue
        if SNO_H.match(h):
            r = "sno"
        elif MOBILE_H.search(h) and not NAME_H.search(h):
            r = "mobile"
        elif EMAIL_H.search(h):
            r = "email"
        elif SARPANCH_H.search(h):
            r = "sarpanch"
        elif OFFICER_H.search(h):
            r = "officer"
        elif DESIG_H.search(h):
            r = "designation"
        elif SEAT_H.search(h):
            r = "seat"
        elif ADDR_H.search(h):
            r = "address"
        elif PIN_H.search(h):
            r = "pin"
        elif DIST_H.search(h):
            r = "district"
        elif TALUKA_H.search(h):
            r = "taluka"
        elif GP_H.search(h):
            r = "gp"
        elif PARTY_H.search(h):
            r = "party"
        elif NAME_H.search(h):
            r = "name"
        else:
            continue
        if r == "name" and "name" in out.values():
            r = "name2"
        out[i] = r
    return out


def post_of(desig, sarpanch_row=False):
    """(post in English, head rank 1/2 or 0) from a designation as written."""
    d = text(desig).replace(" ", "")
    if re.search(r"(?i)ઉપ-?સરપંચ|deputysarpanch|upsarpanch", d):
        return "Deputy Sarpanch", 2
    if re.search(r"(?i)સરપંચ|sarpanch", d) or (sarpanch_row and not d):
        return "Sarpanch", 1
    if re.search(r"(?i)ઉપ-?પ્રમુખ|vice-?president|upp?ramukh", d):
        return "Vice President", 2
    if re.search(r"(?i)કારોબારી|executive", d) and re.search(r"(?i)અધ્યક્ષ|ચેરમેન|chair", d):
        return "Chairman, Executive Committee", 0
    if re.search(r"(?i)પ્રમુખ|president|pramukh", d):
        return "President", 1
    if re.search(r"(?i)અધ્યક્ષ|ચેરમેન|chair", d):
        return "Committee Chairman", 0
    if re.search(r"(?i)નેતા|leader", d):
        return "Leader", 0
    if re.search(r"(?i)દંડક|whip", d):
        return "Whip", 0
    if re.search(r"(?i)સભ્ય|સદસ્ય|સ્ભ્ય|member", d) or not d:
        return "Member", 0
    return text(desig), 0


def seat_of(s):
    """("12", "Bhanthala") from "૧૨-ભાંથલા" / "12 ભાંથલા"; ("", text) when it does not start with a number."""
    t = text(s)
    m = re.match(r"^\s*(\d{1,3})\s*[-–.)/ ]\s*(.*)$", t)
    if m:
        return m.group(1), m.group(2).strip(" -")
    return (t, "") if t.isdigit() else ("", t)


_GJ_DROP = re.compile(r"ગ્રામ\s*પંચાયત|ગ્રા\.?\s*પં\.?|જૂથ|\(.*?\)|[\s‌‍.,'\"()\-–/]")


def gkey(s):
    """Gujarati name key: no spaces, punctuation, zero-width joiners, "ગ્રામ પંચાયત" or "(જૂથ)"; nukta and vowel-sign variants kept."""
    return _GJ_DROP.sub("", unicodedata.normalize("NFC", s or ""))


class Lgd:
    """LGD lookups for Gujarat (cforms/pri_lgd/gj.json.gz): district panchayat, taluka panchayat by English name, gram panchayat
    by the LGD local (Gujarati) name among the gram panchayats of one taluka panchayat."""

    def __init__(self):
        self.l = _pri.Lgd(STATE)
        self.children = {}
        for code, lev, name, local, parent in self.l.rows:
            self.children.setdefault(parent, []).append((code, lev, name, local))

    def zp(self, district):
        return self.l.match("zp", district)

    def ps(self, taluka, district):
        return self.l.match("ps", taluka, district=district) if taluka else ""

    def gp(self, name, ps_code, district="", taluka=""):
        if not name:
            return ""
        if ps_code:
            k = gkey(name)
            hits = [c for c, lev, n, loc in self.children.get(ps_code, []) if lev == "gp" and k and gkey(loc) == k]
            if len(hits) == 1:
                return hits[0]
            n = _pri.norm(name)
            hits = [c for c, lev, en, loc in self.children.get(ps_code, []) if lev == "gp" and n and _pri.norm(en) == n]
            if len(hits) == 1:
                return hits[0]
        return self.l.match("gp", name, district=district, block=taluka) if re.search(r"[A-Za-z]", name) else ""


_LGD = None


def lgd():
    global _LGD
    if _LGD is None:
        _LGD = Lgd()
    return _LGD


def table_rows(g, pos):
    """[(row dict, src_pos)] for one table grid, or [] when it is not a list of elected members / sarpanchs."""
    hi = None
    for i, r in enumerate(g[:4]):
        rl = roles(r)
        vals = set(rl.values())
        if ({"name", "sarpanch"} & vals) and ({"mobile", "designation", "seat", "sarpanch"} & vals):
            hi = i
            break
    if hi is None:
        return [], {}
    header = [text(c) for c in g[hi]]
    rl = roles(header)
    # mobiles: the nearest person column on the left (officer columns' mobiles are dropped)
    owner, last = {}, None
    for i in range(len(header)):
        if rl.get(i) in ("name", "sarpanch", "officer"):
            last = rl[i]
        elif rl.get(i) == "mobile":
            owner[i] = last or "name"
    out = []
    for r, sp in zip(g[hi + 1:], pos[hi + 1:]):
        cells = [text(c) for c in r]
        if not any(cells) or cells == header[:len(cells)]:
            provenance.skip_row(r, 'skip: not any(cells) or cells == header[:len(cells)]')
            continue
        row = {"cells": {header[i] or f"col{i + 1}": c for i, c in enumerate(cells) if c and i < len(header)}}
        for i, c in enumerate(cells):
            role = rl.get(i)
            if role == "mobile":
                role = owner[i] + "_phone"
            if role and c:
                row.setdefault(role, []).append(c)
        out.append((row, sp))
    return out, rl


def j(row, role):
    v = row.get(role)
    return " | ".join(v) if v else ""


def body_level(url, link_text, rl, desig):
    d = text(desig)
    if re.search(r"તાલુકા\s*પંચાયત|taluka\s*panchayat", d, re.I):
        return "ps"
    if re.search(r"જિલ્લા\s*પંચાયત|જીલ્લા\s*પંચાયત|district\s*panchayat", d, re.I):
        return "zp"
    if "/taluka/" in url.lower():
        return "ps"
    if "taluka" in rl.values() and re.search(r"(?i)taluka|તાલુકા", url + " " + (link_text or "")):
        return "ps"
    return "zp"


def page_taluka(url):
    m = re.search(r"/taluka/([^/]+)/", url, re.I)
    return m.group(1) if m else ""


class Ids:
    def __init__(self):
        self.seen = set()
        self.heads = set()      # (record id, name): one About-President page is often linked twice (/About-President and /<id>)

    def take(self, rid, sp):
        if rid in self.seen:
            rid = f"{rid}-t{sp.get('table')}r{sp.get('row')}"
        self.seen.add(rid)
        return rid


def table_records(html, url, p, link_text, ids, taluka_names):
    soup = _esw.soup(html)
    recs = []
    L = lgd()
    dist = p["district"]
    tal_url = page_taluka(url)
    tal_en = next((t for t in taluka_names if t.replace(" ", "").lower() == tal_url.lower()), tal_url)
    for t in soup.find_all("table"):
        pos = []
        g = _esw.grid(t, pos=pos)
        rows, rl = table_rows(g, pos)
        for row, sp in rows:
            sar = j(row, "sarpanch")
            desig = j(row, "designation")
            name = sar or j(row, "name")
            if not name or re.fullmatch(r"[-–\s.\"”“'’〃]*|vacant|ખાલી", name, re.I):
                provenance.skip_row(row, 'skip: not name or re.fullmatch(r"[-–\\s.\\"”“\'’〃]*|vacant|ખાલી", name, re.I)')
                continue
            if desig and OFFICER_POST.search(desig) and not ELECTED_POST.search(desig):
                provenance.skip_row(row, 'skip: desig and OFFICER_POST.search(desig) and not ELECTED_POST.search(de...')
                continue
            if sar or re.search(r"સરપંચ|sarpanch", desig, re.I):
                level = "gp"
            else:
                level = body_level(url, link_text, rl, desig)
            post, rank = post_of(desig, sarpanch_row=bool(sar))
            seat_no, seat_name = seat_of(j(row, "seat"))
            taluka_txt = j(row, "taluka")
            phone = _esw.phones(*(row.get(("sarpanch" if sar else "name") + "_phone") or []))
            ps_code = L.ps(tal_en, dist) if tal_en else ""
            f = dict(district=dist, district_regional=j(row, "district"), post=post, post_regional=desig or None, name=name,
                     name2=j(row, "name") if sar else j(row, "name2"), phone=phone, email=_esw.emails(j(row, "email")),
                     party=j(row, "party"), address=j(row, "address"), seat=j(row, "seat"), ward_no=seat_no, ward_name=seat_name,
                     taluka_regional=taluka_txt, list_no=j(row, "sno"), cells=row["cells"], election=ELECTION, url=url,
                     src_url=url, src_pos=sp, listed_as=link_text, portal=p["host"])
            if rank:
                f.update(head=True, head_rank=rank)
            if level == "gp":
                gpn = j(row, "gp") or (j(row, "name") if sar else "")
                code = L.gp(gpn, ps_code, dist, tal_en)
                f.update(level_body="gram panchayat", body=gpn, block=tal_en or taluka_txt, lgd_code=code, ps_lgd_code=ps_code)
                if not gpn:
                    f["body"] = None
                bkey = code or f"{_esw.slug(dist)}~{_esw.slug(tal_en or taluka_txt)}~{gkey(gpn) or 'r' + str(sp['row'])}"
            elif level == "ps":
                tal = tal_en or taluka_txt
                code = L.ps(tal_en, dist) if tal_en else ""
                f.update(body=f"{tal} Taluka Panchayat" if tal else None, block=tal, lgd_code=code)
                bkey = code or f"{_esw.slug(dist)}~{_esw.slug(tal) or 'taluka'}"
            else:
                code = p.get("lgd_code") or L.zp(dist)
                f.update(body=f"{dist} District Panchayat", lgd_code=code)
                bkey = code or _esw.slug(dist)
            if rank:
                pkey = "head" if rank == 1 else "vice"
            elif seat_no and level != "gp":
                pkey = "w" + seat_no
            else:
                pkey = f"r{sp['table']}-{sp['row']}"
            rid, d = _pri.record(STATE, level, body_key=bkey, pkey=pkey, **f)
            recs.append((ids.take(rid, sp), d))
    return recs


LABELS = (("designation", r"Designation"), ("address", r"Address"), ("phone_office", r"Phone\s*No"), ("mobile", r"Mobile\s*No"),
          ("email", r"E-?mail"))


def president_records(html, url, p, ids, taluka_names):
    """div.contact-box of an About-President page: one head record."""
    soup = _esw.soup(html)
    out = []
    L = lgd()
    for n, box in enumerate(soup.select("div.contact-box"), 1):
        h5 = box.find("h5")
        para = box.find("p")
        if not h5 or not para:
            continue
        vals = {}
        for sp_ in para.find_all("span"):
            lab = " ".join(sp_.get_text(" ").split())
            key = next((k for k, rx in LABELS if re.match(rx, lab, re.I)), None)
            if not key:
                continue
            parts = []
            for sib in sp_.next_siblings:
                if getattr(sib, "name", None) == "span":
                    break
                parts.append(sib.get_text(" ") if hasattr(sib, "get_text") else str(sib))
            vals[key] = text(" ".join(parts))
        desig = vals.get("designation", "")
        desig = re.split(r"\(", desig)[0].strip()
        if not desig or not re.search(r"પ્રમુખ|president|pramukh|સરપંચ", desig, re.I):
            continue
        name = text(h5.get_text(" "))
        name = re.sub(r"\s*,\s*(ઉપ\s*)?પ્રમુખ(શ્રી)?\s*$", "", name)
        post, rank = post_of(desig)
        tal_url = page_taluka(url)
        tal_en = next((t for t in taluka_names if t.replace(" ", "").lower() == tal_url.lower()), tal_url)
        dist = p["district"]
        f = dict(district=dist, post=post, post_regional=desig, name=name, phone=_esw.phones(vals.get("mobile", "")),
                 phone_text=vals.get("mobile"), phone_office=_esw.phones(vals.get("phone_office", "")),
                 email=_esw.emails(vals.get("email", "")), address=vals.get("address"), election=ELECTION, url=url, src_url=url,
                 src_pos={"selector": "div.contact-box", "box": n}, listed_as="About-President", portal=p["host"],
                 head=True, head_rank=rank or 1)
        if tal_url:
            code = L.ps(tal_en, dist)
            f.update(body=f"{tal_en} Taluka Panchayat", block=tal_en, lgd_code=code)
            level, bkey = "ps", code or f"{_esw.slug(dist)}~{_esw.slug(tal_en)}"
        else:
            code = p.get("lgd_code") or L.zp(dist)
            f.update(body=f"{dist} District Panchayat", lgd_code=code)
            level, bkey = "zp", code or _esw.slug(dist)
        rid, d = _pri.record(STATE, level, body_key=bkey, pkey="head" if (rank or 1) == 1 else "vice", **f)
        if (rid, name) in ids.heads:
            continue
        ids.heads.add((rid, name))
        # the About-President page and the members table can both name the president: keep both (the page id ends in -p)
        out.append((ids.take(rid + "-p", {"table": "box", "row": n}), d))
    return out


def links(html, base, host, taluka=None):
    """[(url, text)] of member / president / sarpanch pages (same host) and PDFs (same host or panchayat.gujarat.gov.in)."""
    out = []
    for a in _esw.soup(html).find_all("a", href=True):
        href, label = a["href"].strip(), text(a.get_text(" "))
        if href.startswith(("javascript", "#", "mailto")):
            continue
        u = urljoin(base, href)
        hay = f"{href} {label}"
        if not LINK.search(hay) or NOT_LINK.search(urlparse(u).path) or NOT_LINK.search(label):
            continue
        h = urlparse(u).hostname or ""
        is_pdf = urlparse(u).path.lower().endswith(".pdf")
        if h != host and not (is_pdf and h in PDF_HOSTS):
            continue
        low = urlparse(u).path.lower()
        if not is_pdf:
            if taluka is None and "/taluka/" in low:
                continue
            if taluka is not None and f"/taluka/{taluka.replace(' ', '').lower()}/" not in low:
                continue
        if u not in [x for x, _ in out]:
            out.append((u, label))
    return out


def items(get=None):
    L = lgd()
    out = []
    for label, district in sorted(HOSTS.items()):
        out.append({"key": f"pri_gj:{label}", "payload": {
            "kind": "form-pri_gj", "state": STATE, "url": f"https://{label}.gujarat.gov.in/", "host": f"{label}.gujarat.gov.in",
            "district": district, "lgd_code": L.zp(district), "level": "zp+ps+gp", "election": ELECTION,
            "india_only": True, "route": "direct"}})
    return out


def fetch(p, get):
    host = p["host"]
    r = get(p["url"])
    if r is None:
        return [], [], "district home did not answer"
    home = r.content.decode("utf-8", "replace")
    dslug = _esw.slug(p["district"])
    tals = talukas(home)
    names = [n for _, n in tals]
    only = {t.lower() for t in p.get("talukas") or []}
    pages = [(u, t, "") for u, t in links(home, p["url"], host)] if not only else []
    notes = []
    for _, name in tals:
        if only and name.lower() not in only:
            continue
        th_url = f"https://{host}/gu/taluka/{name.replace(' ', '')}/home"
        th = get(th_url)
        if th is None:
            notes.append(f"taluka home {name}: no answer")
            continue
        for u, label in links(th.content.decode("utf-8", "replace"), th_url, host, taluka=name)[:6]:
            pages.append((u, label, name))
    files, recs, seen, ids = [], [], set(), Ids()
    for u, label, taluka in pages:
        if u in seen:
            continue
        seen.add(u)
        if urlparse(u).path.lower().endswith(".pdf"):
            f = get(u)
            ok = f is not None and f.content[:5] == b"%PDF-"
            h = hashlib.sha1(u.encode()).hexdigest()[:12]
            path = f"pri_gj/{dslug}/{h}.pdf" if ok else None
            if ok:
                files.append((path, f.content, "application/pdf"))
            recs.append((f"pri-file:GJ:{dslug}:{h}", {
                "type": "source_file", "state": STATE, "url": u, "label": label, "stored": path, "fetched": ok,
                "bytes": len(f.content) if ok else None, "district": p["district"], "taluka": taluka or None, "portal": host,
                "purpose": "pri_member list (scan or text: read later, OCR on the runners)",
                **({"src_url": u, "method": "file saved to the bucket (pdf)"} if ok else {})}))
            continue
        g = get(u)
        if g is None:
            continue
        html = g.content.decode("utf-8", "replace")
        got = president_records(html, u, p, ids, names) if re.search(r"(?i)about-president|president-about", u) else []
        got += table_records(html, u, p, label, ids, names)
        recs.extend(got)
        if got:
            files.append(_esw.keep("pri_gj", f"{dslug}/{_esw.slug(urlparse(u).path)}", g.content, "html"))
    if not any(d.get("type") == "pri_member" for _, d in recs):
        return recs, files, "no member table" + (f" ({'; '.join(notes[:3])})" if notes else "")
    return recs, files, ""
