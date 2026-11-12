"""Gujarat Police unit sites (one CMS for every commissionerate and district SP unit): https://<unit>.gujarat.gov.in/<unit>/
CMS.aspx?orgchart=true is a tree of designations (links CMS.aspx?orgchart=true&designation_id=N, tree depth = the tree
images before the link). Each designation page has an 'ઓફિસ સંપર્ક' (office contact) table: uc_clp_name, uc_clp_designation,
uc_clp_pres_address, uc_clp_pers_phone, uc_clp_pers_mobile, uc_clp_pers_fax, uc_clp_ancEmail ([at]/[dot] masked). Text and
digits are Gujarati; digits become ASCII here, the text stays Gujarati. India only (all *.gujarat.gov.in police hosts time out
from Germany). One queue item = one unit (its org chart + one page per kept designation, ~100-160 requests).
Kept: station posts (PI / PSI of a police station; level police_station), circle inspectors (circle), ACP / DySP divisions
(subdivision), DCP zones (zone), CP / SP / joint and additional CPs (district). Branch posts (LCB, SOG, traffic, reader, ...)
are left out. Record id dept:police_gj:<unit>:<designation id>."""
import re

from bs4 import BeautifulSoup

from dforms._police import ascii_digits, clean, email, gz, phones, rec, uniq

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

M = "police_gj"
ORG = "https://{u}.gujarat.gov.in/{u}/CMS.aspx?orgchart=true"
ZWJ = re.compile("[‌‍]")
INSPECTOR = re.compile(r"(ઇ|ઈ)ન્સ?્?પે?ક|ઇન્સપે|Inspector|\bP\.?S\.?I\b|\bP\.?I\b", re.I)
SUB = re.compile(r"સબ\s*(ઇ|ઈ)ન્|\bP\.?S\.?I\b", re.I)
STATION = re.compile(r"પોલીસ\s*સ્ટેશન|પો\.?\s*સ્ટે|થાણું|\bP\.?\s?S\b", re.I)
BRANCH = re.compile(r"શાખા|વિભાગ|સેલ|યુનિટ|બ્રાન્ચ|એલ\.?\s?સી\.?\s?બી|એલ\.?\s?આઇ\.?\s?બી|એસ\.?\s?ઓ\.?\s?જી|ટ્રાફ|રીડર|વાયરલેસ|કંટ્રોલ|"
                    r"ક્રાઇમ|ક્રાઈમ|મુખ્ય\s*મથક|રીઝર્વ|માઉન્ટેડ|બેન્ડ|એમ\.?\s?ટી|એમ\.?\s?ઓ\.?\s?બી|કોમ્પ્યુટર|ગુજકોપ|પાસપોર્ટ|"
                    r"સ્પેશ્યલ|સાયબર ક્રાઇમ સેલ|ટ્રેનીંગ|મોટર|LCB|SOG|LIB|Traffic|Branch|Cell|Control|Wireless|Reader|HQ", re.I)
CIRCLE = re.compile(r"સર્કલ|સી\.?\s?પી\.?\s?આઇ|C\.?P\.?I\b", re.I)
DIVISION = re.compile(r"મદદનીશ\s*પોલીસ\s*કમિશ્|નાયબ\s*પોલીસ\s*અધિક્ષક|A\.?C\.?P|Dy\.?\s?S\.?P|ડીવીઝન", re.I)
ZONE = re.compile(r"નાયબ\s*પોલીસ\s*કમિશ્|D\.?C\.?P|ઝોન", re.I)
TOP = re.compile(r"^(પોલીસ\s*કમિશ(્)?નર|પોલીસ\s*અધિક્ષક|સંયુક્ત\s*પોલીસ\s*કમિશ|અધિક\s*પોલીસ\s*કમિશ|અધિક\s*પોલીસ\s*અધિક્ષક)", re.I)


def norm(s):
    return clean(ZWJ.sub("", s or ""))


def level(desig):
    """Level of a designation text, or None for a branch post / a post not tied to an area."""
    d = norm(desig)
    if not d or d == "-":
        return None
    branch = BRANCH.search(d) or re.search(r"EOW|ઇકોનોમિક|સ્પેશિયલ|વિશેષ|ઇમીગ્રેશન|ઈમીગ્રેશન|વહીવટ|વહિવટ|તાલીમ|કંન્ટ્રોલ|ફીલ્ડ|મહિલા\s*સેલ", d)
    if ZONE.search(d) and not DIVISION.search(d.replace("ઝોન", "")):
        return "zone" if "ઝોન" in d and not branch else None
    if DIVISION.search(d):
        return "subdivision" if not branch or "ડીવીઝન" in d else None
    if TOP.search(d):
        return "district" if not branch else None
    if INSPECTOR.search(d) or re.search(r"સબ\s*-?\s*ઇન્સ\.", d):
        if CIRCLE.search(d):
            return "circle"
        if branch and not STATION.search(d):
            return None
        if STATION.search(d) or re.search(r"\(.+", d) or re.search(r"(,|ઇન્સ\.)\s*\S", d):
            return "police_station"
    return None


def area_of(desig):
    """'પોલીસ ઇન્સપેકટર-૧ (નવરંગપુરા)' -> 'નવરંગપુરા'; 'પોલીસ સબ ઇન્સ્પેક્ટર, ઘોઘા પોલીસ સ્ટેશન' -> 'ઘોઘા'."""
    d = norm(desig)
    m = (re.search(r"\(([^()]+)\)", d) or re.search(r"\(([^()]+)$", d) or re.search(r",\s*\(?\s*([^,()]+)\)?\s*$", d)
         or re.search(r"ઇન્સ\.\s*(\S.*)$", d))
    a = m.group(1) if m else d
    a = re.sub(r"\s*(પોલીસ\s*સ્ટેશન|પોલીસ\s*સ્ટ\S*|પો\.?\s*સ્ટે?\.?|પોલ)\s*$", "", a.strip())
    return clean(a) or d


def orgchart(html):
    """[(designation id, text, depth, parent texts)] in tree order."""
    soup = BeautifulSoup(html, "lxml")
    out, stack = [], []
    for a in soup.find_all("a", href=re.compile(r"designation_id=\d+")):
        did = re.search(r"designation_id=(\d+)", a["href"]).group(1)
        td = a.find_parent("td")
        depth = len(td.find_all("img")) if td else 0
        text = norm(a.get_text(" ", strip=True))
        while stack and stack[-1][0] >= depth:
            stack.pop()
        out.append((did, text, depth, [t for _, t in stack]))
        stack.append((depth, text))
    seen, uniq_out = set(), []
    for row in out:
        if row[0] not in seen:
            seen.add(row[0])
            uniq_out.append(row)
    return uniq_out


def contact(html):
    soup = BeautifulSoup(html, "lxml")

    def val(i):
        el = soup.find(id=i)
        return norm(el.get_text(" ", strip=True)) if el else None
    a = soup.find(id="uc_clp_ancEmail")
    return {"name": val("uc_clp_name"), "designation": val("uc_clp_designation"), "address": val("uc_clp_pres_address"),
            "phone": ascii_digits(val("uc_clp_pers_phone") or ""), "mobile": ascii_digits(val("uc_clp_pers_mobile") or ""),
            "fax": ascii_digits(val("uc_clp_pers_fax") or ""), "email": email(a.get_text(" ", strip=True)) if a else None}


def fetch(p, get):
    unit = p["unit"]
    url = p.get("url") or ORG.format(u=unit)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [gz(M, f"{unit}/orgchart.html", r.content)]
    base = url.split("CMS.aspx")[0]
    recs = []
    for did, text, _, parents in orgchart(r.text):
        lv = level(text)
        if not lv:
            continue
        durl = f"{base}CMS.aspx?orgchart=true&designation_id={did}"
        x = get(durl)
        if x is None:
            continue
        files.append(gz(M, f"{unit}/designation-{did}.html", x.content))
        c = contact(x.text)
        desig = c["designation"] or text
        div = next((t for t in reversed(parents) if level(t) == "subdivision"), None)
        zone = next((t for t in reversed(parents) if level(t) == "zone"), None)
        mob, land = phones(c["mobile"]), phones(c["phone"])
        recs.append(rec(M, f"{unit}:{did}", level=lv, area=area_of(desig) if lv in ("police_station", "circle") else desig,
                        post=desig, name=c["name"], phone=phones(mob, land), mobile=mob, landline=land, fax=phones(c["fax"]),
                        email=c["email"], address=re.sub(r"\s*,(\s*,)+", ",", c["address"] or "").strip(" ,"), subdivision=div, zone=zone, unit=unit,
                        district=p.get("district"), state="GJ", office_id=did, source=durl))
    return uniq(recs), files, "" if recs else "no station posts in the org chart"
