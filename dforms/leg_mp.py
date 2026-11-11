"""Madhya Pradesh: MLAs of the 16th MP Vidhan Sabha (2023-) from the assembly's district-wise member list
(mpvidhansabha.nic.in/sadasyasuchi16vs.pdf, 33 pages, printed from frm_add_distwise.aspx on 2026-08-03; in Hindi only).
The site answers from Germany too, but the item is india_only: the India pool servers have poppler's pdftotext, which reads
this PDF's Nirmala UI text well; pypdf (the fallback on GitHub runners) loses most conjuncts (" ी" for "श्री"), so the reader
refuses to read the PDF without pdftotext.

Layout: a district heading "जिला - श्योपुर", then per member a header line "श्री बाबू जन्डेल, इं.ने.कां. , 1-श्योपुर"
(name, party, AC number - constituency), an optional post line (मंत्री, अध्यक्ष ...), then two columns: left = Bhopal address,
"मोबाइल-", "दूरभाष-" (Bhopal phone), "ई मेल -"; right = permanent address and its "दूरभाष-". pdftotext puts a space after some
vowel signs ("मुके श" for "मुकेश"); the reader removes spaces only before vowel signs and virama, so a few names keep such a space.
Fields: name (Hindi, as printed), party (INC / BJP / BAP from the Hindi abbreviation; party_regional = as printed), mobile,
phone_residence (Bhopal), residence_address (Bhopal), permanent_address, phone_constituency (permanent column's phone), email,
designation. No constituency office. One queue item = the whole PDF.
"""
import re

from dforms import _leg

MODULE = "leg_mp"
URL = "https://mpvidhansabha.nic.in/sadasyasuchi16vs.pdf"
PARTY = {"इं.ने.कां.": "INC", "भा.ज.पा.": "BJP", "भा.आ.पा.": "BAP"}
HEAD = re.compile(r"^(?P<name>\S.*?)\s*,\s*(?P<party>" + "|".join(re.escape(k) for k in PARTY) +
                  r")\s*,\s*(?P<no>\d{1,3})\s*-\s*(?P<cons>.+)$")
DIST = re.compile(r"^जिला\s+-\s+(\S.*)$")
MARK = re.compile(r"\s+(?=[ऀ-ःऺ-्॑-ॗॢॣ])")      # space before a vowel sign / virama
PHONE = re.compile(r"दू\s?रभाष\s*-?")
MOBILE = re.compile(r"मोबाइल\s*-?")
EMAIL = re.compile(r"ई\s?-?\s?मेल\s*-?")


def items(get=None):
    return [{"key": "leg_mp-list", "payload": {"reader": MODULE, "url": URL, "state": "MP", "india_only": True}}]


def fix(s):
    return MARK.sub("", _leg.clean(s.replace("‍", "").replace("‌", "")))


def split(line):
    """(left, right) column text of one layout line."""
    if not line.strip():
        return "", ""
    lead = len(line) - len(line.lstrip())
    if lead >= 30:
        return "", line.strip()
    m = re.search(r"\S(\s{4,})\S", line)
    if m:
        return line[:m.start(1)].strip(), line[m.end(1):].strip()
    return line.strip(), ""


def _block(head, lines, district, url):
    left, right = [], []
    for ln in lines:
        lt, rt = split(ln)
        if lt:
            left.append(fix(lt))
        if rt:
            right.append(fix(rt))
    f = {"mobile": [], "phone_residence": [], "email": [], "addr": [], "designation": ""}
    for i, t in enumerate(left):
        if MOBILE.match(t):
            f["mobile"].append(MOBILE.sub("", t, 1))
        elif PHONE.match(t):
            f["phone_residence"].append(PHONE.sub("", t, 1))
        elif EMAIL.match(t):
            f["email"].append(EMAIL.sub("", t, 1))
        elif i == 0 and not re.search(r"\d|भोपाल|विश्राम|बंगले|कॉलोनी|नगर", t) and len(t) < 45:
            f["designation"] = t
        else:
            f["addr"].append(t)
    perm, pphone = [], []
    for t in right:
        (pphone if PHONE.match(t) else perm).append(PHONE.sub("", t, 1) if PHONE.match(t) else t)
    no = int(head.group("no"))
    cons = fix(head.group("cons"))
    seat, note = _leg.ac_seat("MP", no, cons)
    party = head.group("party")
    return _leg.member(MODULE, "MP", "AC", seat, fix(head.group("name")), constituency=cons, party=PARTY.get(party, party),
                       source=url, mobile=", ".join(f["mobile"]), phone_residence=", ".join(f["phone_residence"]),
                       email=" ".join(f["email"]), residence_address=" ".join(f["addr"]), permanent_address=" ".join(perm),
                       phone_constituency=", ".join(pphone), designation=f["designation"], party_regional=party,
                       district=district, seat_no=no, note=note)


def parse(pages, url=URL):
    recs, district, head, lines = [], "", None, []
    for page in pages:
        for ln in page.splitlines():
            lt, rt = split(ln)
            d = DIST.match(fix(rt)) if not lt and rt else None
            h = HEAD.match(fix(lt)) if lt and not rt else None
            if d or h:
                if head:
                    recs.append(_block(head, lines, district, url))
                head, lines = None, []
                if d:
                    district = d.group(1)
                else:
                    head = h
                continue
            if head:
                lines.append(ln)
    if head:
        recs.append(_block(head, lines, district, url))
    return recs


def fetch(p, get):
    from dforms import _pdftext
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "sadasyasuchi16vs", r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    pages, engine = _pdftext.layout_pages(r.content)
    if engine != "pdftotext":
        return [], files, "needs pdftotext: pypdf loses the Hindi conjuncts of this PDF"
    recs = parse(pages, p["url"])
    return recs, files, "" if recs else "no members"
