"""Town heads named on district portals (S3WaaS / NIC district sites): the Chief Municipal Officer (Madhya Pradesh), the Chief
Officer or Commissioner (Maharashtra) of each town body of one district, with the person's name, mobile and the post's mailbox.

Why: the state directories of town bodies name no person (ulb2_mp: MP UADD directory, mailbox + office phone only; ulb_mh:
Maharashtra DMA has no list of chief officers). Some district sites list the town heads by name in their telephone / e-mail
directory or on a department page. The generic directory readers keep such rows on the district (civic-india sql/40: district
site rows never carry a body code), so the towns stay without a named head. This reader takes only the town-head rows of such a
page and ties each to its LGD local body code.

One queue item per page (payload: url, state, district). Two table layouts, found by the reader on each table:
- "row": one row per officer, one cell holds the post ("मुख्य नगर पालिका अधिकारी इन्दरगढ", "CMO, Nagar Palika Parishad, Hatta",
  "सी.एम.ओ., नगर पालिका, सीधी", "श्री नरेंद्र जाटव, मुख्य नगरपालिका अधिकारी (CMO) नगरपालिका श्योपुर"); the name is the cell that starts
  with an honorific (श्री, श्रीमती, Shri, Mr ...) or the text before the post in the post cell; the body is the text after the post,
  else an address cell that names a town body ("नगर पालिका परिषद बड़वाह,जिला खरगोन म.प्र.", "मुख्य नगरपालिका कार्यालय झाबुआ"),
  else the town of the mailbox (cmo<town>@mpurban.gov.in, through dforms/ulb2_mp_lgd.json).
  Damoh, Datia, Jhabua, Khargone, Sheopur, Sidhi, Umaria (MP), 2026-11-05..10 archive.s1d.me copies.
- "head": a heading row with a body column and a column for the head's name ("आयुक्त / मुख्याधिकारी नाव"), phone and e-mail columns.
  Ahilyanagar (MH) "नगर परिषद प्रशासन" page, "शेवटचे अद्यावत: 18.03.2025": 1 corporation, 11 councils, 4 nagar panchayats.
  Dharashiv (MH) "शासकीय विभाग संपर्क" (row layout, the post and office phone/mail of 8 councils, no names) and Palghar's Talasari
  tehsil page (Talasari Nagar Panchayat's chief officer, office phone, no name) give contacts of bodies that had none.
Rows about other CMOs are left out: the Chief Medical (and Health) Officer ("C.M.H.O.", "Health -CMO").

Records (dept_office, dept town_body, level body, via _ulb.record): post "Chief Municipal Officer" (MP) / "Chief Officer" (MH), or
"Commissioner" for a corporation (नगर निगम, महानगरपालिका, Municipal Corporation) or when the page writes आयुक्त / Commissioner;
post_as_written; name as written (honorific kept); phone (mobile and office numbers of the row), email (deobfuscated); charge
"additional charge" when the page writes प्रभारी / अतिरिक्त प्रभार / Incharge; district = the payload's district; lgd_code from
dforms/th_dist_lgd.json (LGD bodies of the district: the Hindi / Marathi name or a Latin form of it, tied when exactly one body fits;
alias table for names LGD writes in another way) or from the MP mailbox table; area_latin = the LGD name. last_updated = the page's
"Last Updated" date when shown. src_pos = {table, row} of the row.
Route: the seven MP NIC hosts and palghar.gov.in answered the GitHub runners abroad (archive vantage "pool", HTTP 200);
ahilyanagar.maharashtra.gov.in and dharashiv.maharashtra.gov.in answered only the Indian server: those two items carry india_only.
"""
import json
import re
from pathlib import Path

from dforms import _esw, _ulb
from dforms.ulb_mh import latin

METHOD = "html table (row: post cell; head: heading columns)"     # source trail (provenance.py)
MODULE = "th_dist"

PAGES = (  # key, state, district (LGD spelling), url
    ("mp-damoh", "MP", "Damoh", "https://damoh.nic.in/en/telephone-directory-new/"),
    ("mp-datia", "MP", "Datia", "https://datia.nic.in/?p=25271"),
    ("mp-jhabua", "MP", "Jhabua", "https://jhabua.nic.in/?p=18609"),
    ("mp-khargone", "MP", "Khargone", "https://khargone.nic.in/?p=18609"),
    ("mp-sheopur", "MP", "Sheopur", "https://sheopur.nic.in/?p=28871"),
    ("mp-sidhi", "MP", "Sidhi", "https://sidhi.nic.in/en/telephone-directory/"),
    ("mp-umaria", "MP", "Umaria", "https://umaria.nic.in/?p=18609"),
    ("mh-ahilyanagar", "MH", "Ahilyanagar",
     "https://ahilyanagar.maharashtra.gov.in/%e0%a4%a8%e0%a4%97%e0%a4%b0-%e0%a4%aa%e0%a4%b0%e0%a4%bf%e0%a4%b7%e0%a4%a6-"
     "%e0%a4%aa%e0%a5%8d%e0%a4%b0%e0%a4%b6%e0%a4%be%e0%a4%b8%e0%a4%a8/"),
    ("mh-dharashiv", "MH", "Dharashiv",
     "https://dharashiv.maharashtra.gov.in/mr/%e0%a4%b6%e0%a4%be%e0%a4%b8%e0%a4%95%e0%a5%80%e0%a4%af-%e0%a4%b5%e0%a4%bf%e0%a4%ad%e0%a4%97-"
     "%e0%a4%b8%e0%a4%82%e0%a4%aa%e0%a4%b0%e0%a5%8d%e0%a4%95-2/"),
    ("mh-palghar", "MH", "Palghar", "https://palghar.gov.in/en/talasari-tehsil/"),
)

_HERE = Path(__file__).parent
LGD = json.loads((_HERE / "th_dist_lgd.json").read_text())
MP_MAIL = json.loads((_HERE / "ulb2_mp_lgd.json").read_text())["rows"]

# the head's post. MP: CMO / मुख्य नगर पालिका अधिकारी / सी.एम.ओ. / मु.न.पा.अ.; MH: मुख्याधिकारी / Chief Officer; both: commissioner of a town
POST = re.compile(r"(प्रभारी\s*|अतिरिक्त\s*प्रभार\s*,?\s*|addl\.?\s*[।.]?\s*incharge\s*,?\s*|incharge\s*)?"
                  r"(मुख्य\s*नगर\s*पालिका\s*अधिकारी|मुख्य\s*नगरपालिका\s*अधिकारी|सी\s*\.?\s*एम\s*\.?\s*ओ\s*\.?|मु\.\s*न\.\s*पा\.\s*अ(?:धिकारी|\.)|"
                  r"\bC\.?\s?M\.?\s?O\b\.?|chief\s+municipal\s+officer|मुख्याधिकारी|\bchief\s+officer\b)(\s*\((?:CMO|सी\.?एम\.?ओ\.?)\))?", re.I)
NOT_TOWN = re.compile(r"(?i)(c\.?\s?m\.?\s?h\.?\s?o|health|स्वास्थ्य|चिकित्सा|medical|hospital|janpad|जनपद|cantonment|छावनी)")
HON = re.compile(r"^(?:श्रीमती|श्रीमति|श्री|सुश्री|कु|सौ|डॉ|shri|smt|mr|mrs|ms|miss|dr|sh)(?=[\s.]|$)\.?\s*", re.I)
TYPES = r"(नगर\s*पालिक\s*निगम|नगर\s*निगम|महानगर\s*पालिका|महानगरपालिका|नगर\s*पालिका\s*परिषद्?|नगरपालिका\s*परिषद्?|नगर\s*परिषद्?|नगरपरिषद|नगर\s*पंचायत|नगरपंचायत|" \
        r"नगर\s*पालिका|नगरपालिका|municipal\s+corporation|nagar\s+nigam|nagar\s+palika\s+parishad|nagar\s+parishad|nagar\s+panchayat|nagar\s+palika|" \
        r"municipal\s+council|municipality)"
CORP = re.compile(r"(?i)(निगम|महानगर|corporation)")
OFFICE = re.compile(r"(?i)(कार्यालय|office|अधिकारी|मुख्य|\bp\.?\s?o\.?\s*duda\b|पी\.?\s?ओ\.?\s*डू\.?\s?डा\.?)")
DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
MAIL_TOWN = re.compile(r"(?i)\bcmo([a-z]+)\s*@")


def blank(s):
    s = _esw.clean(s).strip(" |,.;:-–—")
    return "" if re.fullmatch(r"[-–—.\s|]*", s) else s


def key(s):
    """A loose Latin key of a town name: Devanagari through ulb_mh.latin, letters only, h dropped, w as v, z as j, ee/oo as i/u, no
    doubled letters, a final a dropped ("बड़वाह" -> "badva", "Badwah" -> "badva")."""
    s = latin(s or "").lower()
    s = re.sub(r"[^a-z]", "", s.replace("ee", "i").replace("oo", "u"))
    s = s.replace("h", "").replace("w", "v").replace("z", "j").replace("q", "k")
    s = re.sub(r"(.)\1+", r"\1", s)
    return re.sub(r"a+$", "", re.sub(r"aa+", "a", s))


def body_of(text):
    """The town in a post or address text, without type, office, district and state words."""
    t = _esw.clean(text)
    t = re.split(r"(?i)[,\s]+(?:जिला|जि\.|district|dist\.)\s", t)[0]
    t = re.sub(r"(?i)\(?\s*(म\.?\s?प्र\.?|m\.?\s?p\.?|madhya\s+pradesh|महाराष्ट्र)\s*\)?\.?$", "", t)
    t = re.sub(TYPES, " ", t, flags=re.I)
    t = OFFICE.sub(" ", POST.sub(" ", t))
    t = re.sub(r"(?i)\b(e\.?\s?o|ward|वार्ड)\b.*$", "", t)
    return blank(re.sub(r"\s+", " ", t.replace(",", " ")))


def lgd_of(state, district, body, email=""):
    """LGD local body code of a town named on the page: the alias table, then the MP mailbox, then a unique name match in the
    district (Hindi/Marathi local name or LGD name; prefix match when one key starts the other and is 4+ letters)."""
    a = LGD["alias"].get(f"{state}|{district}|{body}")
    if a:
        return a
    if state == "MP" and email:
        for e in re.split(r",\s*", email):
            if e in MP_MAIL:
                return MP_MAIL[e]
            m = MAIL_TOWN.search(e)                       # a misspelt domain ("mpuraban"): the mailbox's own name
            if m:
                hit = [c for k, c in MP_MAIL.items() if k.startswith(f"cmo{m.group(1).lower()}@")]
                if len(hit) == 1:
                    return hit[0]
    k = key(body)
    if len(k) < 2:
        return None
    cands = [(c, v) for c, v in LGD["lgd"].items() if v[0] == state and v[1] == district]
    exact = {c for c, v in cands if k in (key(v[2]), key(v[3]))}
    if len(exact) == 1:
        return exact.pop()
    if not exact:
        pre = {c for c, v in cands for x in (key(v[2]), key(v[3])) if len(x) >= 4 and len(k) >= 4 and (x.startswith(k) or k.startswith(x))}
        if len(pre) == 1:
            return pre.pop()
        sk = skel(k)                                              # consonants only ("श्योपुर" / "Sheopur", "बड़ौदा" / "Badoda")
        bare = {c for c, v in cands if sk and sk in (skel(key(v[2])), skel(key(v[3])))}
        if len(sk) >= 3 and len(bare) == 1:
            return bare.pop()
    return None


def skel(k):
    return re.sub(r"(.)\1+", r"\1", re.sub(r"[aeiouy]", "", k or ""))


def person(cell):
    """A cell that starts with an honorific and is short enough to be a name (a land order's "श्री. छत्रपती शिवाजी महाराज यांचा
    अश्वारुढ पुतळा ..." is not)."""
    s = blank(cell)
    return s if s and HON.match(s) and len(s.split()) <= 6 else ""


def updated(html):
    t = _esw.clean(re.sub(r"<[^>]+>", " ", html))
    m = re.search(r"(?:Last\s*Updated|शेवटचे\s*अद्यावत|अंतिम\s*अद्यतन)\s*:?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", t, re.I)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def default_post(state, body_text, written):
    if CORP.search(body_text or "") or re.search(r"(?i)(आयुक्त|commissioner)", written or ""):
        if CORP.search(body_text or ""):
            return "Commissioner"
    return "Chief Municipal Officer" if state == "MP" else "Chief Officer"


def charge_of(text):
    return "additional charge" if re.search(r"(?i)(प्रभारी|प्रभार|incharge|in-charge)", text or "") else None


HEAD_COLS = (  # key, heading regex, must not match
    ("name", r"(आयुक्त|मुख्याधिकारी|chief\s*officer|मुख्य\s*नगर\s*पालिका\s*अधिकारी|c\.?m\.?o).*(नाव|नाम|name)|^(नाव|नाम|name)$", r"(नगर\s*परिषद|नगरपंचायत).*चे\s*नाव"),
    ("phone", r"(दूरध्वनी|भ्रमणध्वनी|मोबाइल|मोबाईल|फोन|mobile|phone|contact)", None),
    ("email", r"(e-?\s*mail|ई\s*-?\s*मेल|ईमेल)", None),
    ("body", r"(महानगरपालिका|नगर\s*परिषद|नगरपरिषद|नगर\s*पंचायत|नगरपंचायत|निकाय|municipal|body|ulb)", None),
)


def columns(head):
    out = {}
    for i, h in enumerate(head):
        h = _esw.clean(h).lower()
        for k, rx, no in HEAD_COLS:
            if k not in out and re.search(rx, h, re.I) and not (no and re.search(no, h, re.I)):
                out[k] = i
                break
    return out if {"name", "body"} <= out.keys() else None


def rec(state, district, body, post_written, seen, url, up, pos, name="", phone="", email="", charge=None, body_type=None):
    code = lgd_of(state, district, body, email)
    lg = LGD["lgd"].get(code) if code else None
    post = default_post(state, (body_type or "") + " " + (lg[4] if lg else ""), post_written)
    return _ulb.record(MODULE, state, body, post, seen, name=name, phone=phone.translate(DIGITS), email=email, district=district,
                       body_type=body_type, source=url, latin=lg[2] if lg else latin(body), lgd_code=code,
                       area_latin=lg[2] if lg else None, post_as_written=post_written, charge=charge, last_updated=up,
                       src_pos=pos, page=url)


def parse(html, url, state, district):
    recs, seen = [], set()
    up = updated(html)
    for t in _esw.soup(html).find_all("table"):
        tp = []
        rows = _esw.grid(t, pos=tp)
        if not rows:
            continue
        col = columns(rows[0])
        if col:                                                        # "head" layout
            for row, pos in zip(rows[1:], tp[1:]):
                c = {k: (row[i] if i < len(row) else "") for k, i in col.items()}
                body_cell = blank(c["body"])
                body = body_of(body_cell)
                if not body or re.fullmatch(r"[\d\s.]+", body):
                    continue
                name, phone, email = blank(c["name"]), _esw.phones(c.get("phone", "").translate(DIGITS)), _esw.emails(c.get("email", "").translate(DIGITS))
                if not (name or phone or email):
                    continue
                btype = (re.search(TYPES, body_cell, re.I) or [None])[0]
                recs.append(rec(state, district, body, blank(rows[0][col["name"]]), seen, url, up, pos, name=name, phone=phone,
                                email=email, charge=charge_of(name), body_type=btype))
            continue
        for row, pos in zip(rows, tp):                                 # "row" layout
            cells = [blank(x) for x in row]
            pi = next((i for i, x in enumerate(cells) if POST.search(x)), None)
            if pi is None or NOT_TOWN.search(" ".join(cells)):
                continue
            pc = cells[pi]
            m = POST.search(pc)
            before, after = blank(pc[:m.start()]), blank(pc[m.end():])
            name = person(before) or next((person(x) for i, x in enumerate(cells) if i != pi and person(x)), "")
            email = _esw.emails(" ".join(cells).translate(DIGITS))
            body_src = after if body_of(after) else next((x for i, x in enumerate(cells) if i != pi and not person(x) and "@" not in _esw.deob(x)
                                                         and re.search(TYPES + r"|कार्यालय", x, re.I) and body_of(x)), "")
            body = body_of(body_src)
            if not body and email:                                     # the mailbox's town
                code = lgd_of(state, district, "", email)
                body = LGD["lgd"][code][3] or LGD["lgd"][code][2] if code else ""
            if not body:
                continue
            phone = _esw.phones(*[x.translate(DIGITS) for i, x in enumerate(cells) if i != pi and "@" not in _esw.deob(x)
                                  and not re.fullmatch(r"\d{1,4}", x)])
            if not (name or phone or email):
                continue
            btype = (re.search(TYPES, body_src, re.I) or [None])[0]
            recs.append(rec(state, district, body, blank(m.group(0)), seen, url, up, pos, name=name, phone=phone, email=email,
                            charge=charge_of(pc), body_type=btype))
    return recs


# hosts that answered only from India in the archive (2026-11-05..13: GitHub runners got no answer, the Indian server got 200)
INDIA_ONLY = ("ahilyanagar.maharashtra.gov.in", "dharashiv.maharashtra.gov.in")


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": url, "state": st, "district": dist,
                                                  "india_only": url.split("/")[2] in INDIA_ONLY}} for k, st, dist, url in PAGES]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    name = re.sub(r"[^a-z0-9]+", "-", re.sub(r"^https?://", "", p["url"]).lower()).strip("-")[:80]
    recs = parse(r.text, p["url"], p["state"], p["district"])
    return recs, [_esw.keep(MODULE, name, r.content)], "" if recs else "no rows"
