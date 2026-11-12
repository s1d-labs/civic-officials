"""Town bodies on the "Public Utilities -> Municipalities" pages of S3WaaS district portals (all states): one card per urban body.

Pages: /public-utility-category/<slug>/ with an English slug (municipality, municipalities, municipal-corporation, nagar-panchayat,
urban-local-bodies ...) or a regional one (नगर-पालिका, नगरपालिका, ಪುರಸಭೆಗಳು, নগরপালিকা, পৌরসভা, நகராட்சிகள், పురపాలక,
નગરપાલિકાઓ, ਨਗਰ-ਪਾਲਿਕਾਵਾਂ, നഗരസഭകള് ...), 10 cards a page, paged with /page/N/. 407 district sites have such pages in
archive.s1d.me (scan of ~/data/civic-india/pu_all.tsv, saves of 2026-11-05 to 2026-11-10): 869 pages with 3,802 cards.
A card: heading = the body ("Nagar Palika Parishad Neemuch", "ಗಂಗಾವತಿ ನಗರಸಭೆ", sometimes a post: "Commissioner, Pollachi"),
an address line, and labelled lines Phone / Email / Website Link / Pincode / Category (labels in the page language).
officials.py reads some of these pages too, as "District administration" rows (213 rows on 2026-11-11, none tied to a body by
civic-india sql/87). This module reads them as town_body records (dept town_body, level body), so sql/87 ties them to the body.

The post of a record, first that holds:
- the heading starts with a post ("Commissioner, Mettupalayam"): post_from "title";
- the address starts with a post, or with a person's name and then a post ("Executive Officer, Municipal Council Dehra ...",
  "Office of The Chief Municipal Officer, Nagar Panchayat Aamdi", "Rahul Kumar Executive Officer Nagar panchayat Ramgarh",
  "श्रीमती अर्चना कुमारी, चेयरमैन"): post_from "address", and name = the words before the post when they look like a name;
- the mailbox names a post (cmo<town>@mpurban.gov.in = Chief Municipal Officer, commr.<town>@tn.gov.in = Commissioner,
  eo..., secy..., chairman...): post_from "email";
- else "Office" (role staff).
A post without a name still marks who answers the office phone and mailbox (as dforms/ulb_pb.py does for the EO mailboxes).
Phone numbers written in the address ("E.O. Babhanan Nagar Panchayat Mobile : 9565897740") go on the record too.

The body tie: dforms/ulb2_s3waas_lgd.json maps <host> -> <title key> -> LGD local body code, made offline from the archive copies
(the card title, or the address when the title gives no name, matched to civic.ulb in the site's district by name key, sound key
(civic.skel) or a voicing-free sound key, after a rough transliteration of the regional scripts; only unique matches). The code
goes in lgd_code; area_latin carries the transliterated name for sql/87 when the lookup has no entry.

Seed: seeds/dept_ulb2_s3waas.json, one item per category page (for each site the language version with the most cards; Satara is
read by dforms/ulb_mh.py and left out). Payload: url, state, district (sites.csv name), india_only false (NIC/S3WaaS sites answer
from abroad, as for civic_post_s3waas), max_pages.
"""
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from dforms import _civic, _esw, _ulb
from dforms.police_s3waas import cards as _cards, last_updated

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_s3waas"
MAX_PAGES = 30
HERE = Path(__file__).resolve().parent
_LGD = None

# ---------------------------------------------------------------- transliteration (rough, for name keys only)
# Brahmic blocks share the Devanagari layout: offset of a letter from its block start -> Latin
_BLOCKS = (0x0900, 0x0980, 0x0A00, 0x0A80, 0x0B00, 0x0B80, 0x0C00, 0x0C80, 0x0D00)
_VOW = {0x05: "a", 0x06: "aa", 0x07: "i", 0x08: "ii", 0x09: "u", 0x0A: "uu", 0x0B: "ri", 0x0C: "li", 0x0D: "e", 0x0E: "e", 0x0F: "e",
        0x10: "ai", 0x11: "o", 0x12: "o", 0x13: "o", 0x14: "au", 0x60: "ri", 0x61: "li"}
_CON = dict(zip(range(0x15, 0x3A), "k kh g gh n c ch j jh n t th d dh n t th d dh n n p ph b bh m y r r l l l v sh sh s h".split()))
_CON.update({0x58: "q", 0x59: "kh", 0x5A: "g", 0x5B: "z", 0x5C: "r", 0x5D: "rh", 0x5E: "f", 0x5F: "y"})
_MAT = {0x3E: "aa", 0x3F: "i", 0x40: "ii", 0x41: "u", 0x42: "uu", 0x43: "ri", 0x44: "ri", 0x45: "e", 0x46: "e", 0x47: "e", 0x48: "ai",
        0x49: "o", 0x4A: "o", 0x4B: "o", 0x4C: "au", 0x57: "au", 0x62: "li", 0x63: "li"}
_SIGN = {0x01: "n", 0x02: "n", 0x03: "h", 0x70: "n"}          # candrabindu, anusvara, visarga, Gurmukhi tippi
_CHILLU = {0x0D7A: "n", 0x0D7B: "n", 0x0D7C: "r", 0x0D7D: "l", 0x0D7E: "l", 0x0D7F: "k", 0x09CE: "t"}


def _off(ch):
    o = ord(ch)
    for b in _BLOCKS:
        if b <= o < b + 0x80:
            return o - b
    return None


def latin(s):
    """A rough Latin form of a name in an Indian script ("नगर पंचायत रामगढ़" -> "nagara pancaayata raamagarha"); Latin text stays."""
    s = unicodedata.normalize("NFC", s or "")
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        o = _off(ch)
        if ord(ch) in _CHILLU:
            out.append(_CHILLU[ord(ch)])
        elif o is None:
            out.append(ch)
        elif o in _CON:
            j = i + 1
            while j < len(s) and _off(s[j]) == 0x3C:              # nukta
                j += 1
            c = _CON[o]
            if j > i + 1 and c in ("d", "dh"):
                c = "r" if c == "d" else "rh"
            nxt = _off(s[j]) if j < len(s) else None
            if nxt in _MAT:
                out.append(c + _MAT[nxt]); j += 1
            elif nxt == 0x4D:                                     # virama
                out.append(c); j += 1
            else:
                out.append(c + "a")
            i = j
            continue
        elif o in _VOW:
            out.append(_VOW[o])
        elif o in _MAT:
            out.append(_MAT[o])
        elif o in _SIGN:
            out.append(_SIGN[o])
        elif 0x66 <= o <= 0x6F:
            out.append(str(o - 0x66))
        i += 1
    return "".join(out)


# type words in the scripts (stripped before the name key); Latin type words are in TYPE_LATIN
TYPE_NATIVE = re.compile(
    r"(महानगर\s*पालिका|महानगरपालिका|नगर\s*पालिका\s*परिषद्?|नगरपालिका\s*परिषद्?|नगर\s*पालिका|नगरपालिका|नगर\s*पंचायत|नगरपंचायत|नगर\s*परिषद्?|"
    r"नगरपरिषद|नगर\s*निकाय|नगर\s*पालिक\s*(?:निगम|परिषद्?)|नगर\s*निगम|नगरनिगम|नगर\s*परिशद|नगरीय\s*निकाय|शहरी\s*निकाय|टाउन\s*एरिया|नगर\s*प\.?|कार्यालय|"
    r"ಅಧಿಸೂಚಿತ\s*ಪ್ರದೇಶ\s*ಸಮಿತಿ|ಮಹಾನಗರ\s*ಪಾಲಿಕೆ|ನಗರ\s*ಸಭೆ|ನಗರಸಭೆ|ಪುರಸಭೆ|ಪಟ್ಟಣ\s*ಪಂಚಾಯ(ತ್|ತಿ|ತ)|ಪಟ್ಟಣ|ಪಂಚಾಯತ್|ಪಂಚಾಯತಿ|"
    r"மாநகராட்சி|நகராட்சி|பேரூராட்சி|நகர்மன்றம்|"
    r"మునిసిపల్\s*కార్పొరేషన్|మున్సిపల్\s*కార్పొరేషన్|నగరపాలక\s*సంస్థ|మునిసిపాలిటీ|మున్సిపాలిటీ|పురపాలక\s*సంఘం|పురపాలక|నగర\s*పంచాయతీ|"
    r"পৌরসভা|পুরসভা|পৌর\s*নিগম|পুর\s*নিগম|নগর\s*পঞ্চায়েত|"
    r"મહાનગરપાલિકા|મહાનગર\s*પાલિકા|નગરપાલિકા|નગર\s*પાલિકા|"
    r"ਨਗਰ\s*ਨਿਗਮ|ਨਗਰ\s*ਕੌਂਸਲ|ਨਗਰ\s*ਪੰਚਾਇਤ|ਨਗਰ\s*ਪਾਲਿਕਾ|ਨਗਰ\s*ਸੁਧਾਰ\s*ਟਰੱਸਟ|"
    r"മുനിസിപ്പൽ\s*കോർപ്പറേഷൻ|മുനിസിപ്പാലിറ്റി|നഗരസഭ|കോർപ്പറേഷൻ|"
    r"ପୌରପାଳିକା|ପୌର\s*ପରିଷଦ|ବିଜ୍ଞାପିତ\s*ଅଞ୍ଚଳ\s*ପରିଷଦ|ମହାନଗର\s*ନିଗମ)")
TYPE_LATIN = re.compile(
    r"(?i)\b(ward\s*no\.?\s*\d+|office\s+of(\s+the)?|municipal(ity|ty|ities)?|municiple|municupal|muncipal(ity)?|minicipal|municiapal|"
    r"councils?|counicl|committee|corporation|prishad|town\s*area|mahanagara?\s*palike|palike|mahanagar\s*palika|nagar\s*(panchayat|panchayath|panchyat|"
    r"palika|parishad|parisad|nigam)|nagarpalika|nagarpanchayat|nagarparishad|nagarnigam|town\s*(panchayat|panchayath|committee|"
    r"council|municipal\s*council)?|city|notified\s*area|cantonment|board|parishad|parisad|panchayath?|panchyat|palika|nigam|"
    r"np|npp|nn|npr|mc|mcl|mcorp|cmc|tmc|tp|cb|nac|mb|m|corp|cant|tc|na|bmc|gmc|cg|mp|up|hp|the|of|and|grade|selection|special|"
    r"first|second|1st|2nd|3rd|i/c)\b")


def name_key(s):
    """civic.name_key() in Python, after the script type words are cut and the rest transliterated."""
    s = TYPE_NATIVE.sub(" ", s or "")
    s = unicodedata.normalize("NFKD", latin(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = TYPE_LATIN.sub(" ", s)
    return " ".join(re.sub(r"[^a-z]+", " ", s).split())


def skel(t):
    """civic.skel() in Python: the sound key of a name."""
    s = re.sub(r"[^a-z]", "", (t or "").lower())
    s = s.replace("garh", "gad").replace("gada", "gad").replace("gadh", "gad")
    s = re.sub(r"([tdkgbps])h", r"\1", s)
    s = re.sub(r"[cq]", "k", s)
    s = re.sub(r"[wv]", "b", s)
    s = s.replace("h", "")
    s = s[:1] + re.sub(r"[aeiouy]", "", s[1:])
    return re.sub(r"(.)\1+", r"\1", s)


def loose(t):
    """skel() without voicing (Tamil writes k/g, t/d, p/b, c/j with one letter)."""
    s = skel(t)
    return s.translate(str.maketrans("gdbjzf", "ktpksp"))


def title_key(title):
    """The lookup key of a card heading: NFC, lower case, words of letters and digits."""
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFC", title or "").lower()))


# ---------------------------------------------------------------- posts and names
POST = (r"(?:(?:municipal|minicipal|muncipal|nigam|city|nagar)\s+)?commissioner|executive\s*officer(?:\s*\(i/c\))?|"
        r"e\s?\.\s?o\b\.?|\beo\b|chief\s+municipal\s+officer|c\s?\.\s?m\s?\.\s?o\b\.?|\bcmo\b|chief\s+officer|secretary|"
        r"president|chair\s*(?:man|person|woman)|mayor|administrator|special\s+officer|"
        r"मुख्य\s*नगर\s*पालिका\s*अधिकारी|कार्यपालक\s*पदाधिकारी|अधिशासी\s*अधिकारी|अधिशाषी\s*अधिकारी|कार्यकारी\s*अधिकारी|निगम\s*आयुक्त|"
        r"नगर\s*आयुक्त|आयुक्त|सचिव|अध्यक्ष|चेयरमैन|चेयरमेन|महापौर|मुख्याधिकारी|प्रशासक|"
        r"ஆணையர்|செயல்\s*அலுவலர்|ಮುಖ್ಯಾಧಿಕಾರಿ|ಪೌರಾಯುಕ್ತ(?:ರು)?|ಪೌರ\s*ಆಯುಕ್ತ(?:ರು)?|ಆಯುಕ್ತ(?:ರು)?|ಅಧ್ಯಕ್ಷ(?:ರು)?|కమిషనర్|"
        r"চেয়ারম্যান|এক্সিকিউটিভ\s*অফিসার|পৌরপ্রধান|ચીફ\s*ઓફિસર|પ્રમુખ|ਕਾਰਜ\s*ਸਾਧਕ\s*ਅਫ਼?ਸਰ|ਪ੍ਰਧਾਨ")
LEAD = r"(?:the\s+|office\s+of\s+(?:the\s+)?|o/o\s+(?:the\s+)?|कार्यालय\s*,?\s*)?"
POST_AT_START = re.compile(r"(?i)^\W*" + LEAD + r"(" + POST + r")(?=$|[\s,.:;\-–(/])")
HONOUR = r"(?:shrimati|shri|smt|sri|mrs|mr|ms|dr|kumari|km|श्रीमती|सुश्री|श्री|डॉ|कु)\.?"
# words that are not part of a person's name (an address or a body)
NOT_NAME = re.compile(r"(?i)\b(office|near|road|the|of|nagar|municipal|council|panchayat|town|city|district|block|new|old|building|"
                      r"bhawan|bhavan|ward|tehsil|post|main|opp|opposite|behind|plot|no|street|market|bus|stand|station)\b|"
                      r"कार्यालय|नगर|भवन|जिला|मार्ग|रोड|पंचायत|परिषद|पालिका|निगम|के|पास|समीप|सामने|ಕಚೇರಿ|ಪೌರ|அலுவலகம்")
NAME_THEN_POST = re.compile(r"(?i)^\W*(" + HONOUR + r"\s*)?([^\d,;:()|]{3,50}?)\s*,?\s*(" + POST + r")(?=$|[\s,.:;\-–(/])")
MAILBOX = ((r"^cmo", "Chief Municipal Officer"), (r"^(commr|commissioner|comm(?!unit|ittee|unic)|com[._]?mc)", "Commissioner"),
           (r"^eo(?![a-z]{4,}$)|^eonp", "Executive Officer"), (r"^(secy|secret)", "Secretary"), (r"^chairm", "Chairman"),
           (r"^mayor", "Mayor"), (r"^(chiefofficer|chief\.officer)", "Chief Officer"))


def post_of_text(text):
    """(post, name) when the text starts with a post, or with a name and then a post; else None."""
    t = _esw.clean(text)
    m = POST_AT_START.match(t)
    if m:
        return _esw.clean(m.group(1)).strip(" .,"), ""
    m = NAME_THEN_POST.match(t)
    if m:
        name = _esw.clean(m.group(2)).strip(" .,")
        words = name.split()
        if 1 <= len(words) <= 5 and not NOT_NAME.search(name) and not re.search(r"\d", name):
            hon = _esw.clean(m.group(1) or "")
            return _esw.clean(m.group(3)).strip(" .,"), _esw.clean(f"{hon} {name}")
    return None


# posts in the regional scripts that _ulb.role_of() does not know (it reads Latin and Hindi words): head or chair
ROLE_EXTRA = (("head", r"ஆணையர்|செயல்\s*அலுவலர்|ಮುಖ್ಯಾಧಿಕಾರಿ|ಪೌರಾಯುಕ್ತ|ಆಯುಕ್ತ|కమిషనర్|এক্সিকিউটিভ|ચીફ\s*ઓફિસર|ਕਾਰਜ\s*ਸਾਧਕ|"
                       r"कार्यकारी\s*अधिकारी|अधिशाषी\s*अधिकारी|सचिव|प्रशासक|^Chief Officer"),
              ("chair", r"ಅಧ್ಯಕ್ಷ|চেয়ারম্যান|পৌরপ্রধান|પ્રમુખ|ਪ੍ਰਧਾਨ|चेयरमैन|चेयरमेन"))
# a heading that starts with a person ("श्री राजेश भगत ,मुख्याधिकारी नगर परिषद वर्धा", Wardha): name, then post or body
PERSON_TITLE = re.compile(r"(?i)^\W*(" + HONOUR + r")\s*([^,]+?)\s*(?:,|(?=" + POST + r")|(?=नगर|नगरपंचायत|नगरपालिका|nagar|municipal))\s*(.*)$")


def role(post):
    r = _ulb.role_of(post)
    if r == "staff":
        for name, rx in ROLE_EXTRA:
            if re.search(rx, post or ""):
                return name
    return r


def post_of_email(email):
    for e in (email or "").split(", "):
        lp = e.split("@")[0].lower()
        for rx, post in MAILBOX:
            if re.search(rx, lp):
                return post
    return None


LABELS = (("email", r"mail|ईमेल|ಇಮೇಲ್|ಮಿಂಚಂಚೆ|ઇમેઇલ|ਈ-ਮੇਲ|মেইল|ইমেল|மின்னஞ்சல்|ఇమెయిల్|മെയില്"),
          ("phone", r"phone|mobile|फोन|फ़ोन|दूरध्वनी|दूरभाष|ದೂರವಾಣಿ|ફોન|தொலைபேசி|ਫ਼ੋਨ|ਫੋਨ|ফোন|ఫోన్|ഫോണ്"),
          ("pincode", r"pin|पिन|ಪಿನ್|পিন|పిన్|ਪਿਨ|அஞ்சல்"),
          ("website", r"website|वेबसाइट|ವೆಬ್|વેબસાઇટ|இணையதள|వెబ్సైట్|ওয়েবসাইট|വെബ്സൈറ്റ്|ਵੈੱਬਸਾਈਟ"),
          ("type", r"category|श्रेणी|ವರ್ಗ|કેટેગરી|வகை|వర్గం|শ্রেণী|ক্যাটাগরি|ਵਰਗ|വിഭാഗം"))


def card_fields(c):
    """police_s3waas.cards() keeps labels in the page language ("ईमेल", "ದೂರವಾಣಿ"): fold them to email / phone / pincode / website."""
    d = {"title": c.get("title"), "address": c.get("address") or ""}
    for k, v in c.items():
        if k in ("title", "address"):
            continue
        for name, rx in LABELS:
            if re.search(rx, k, re.I):
                d[name] = _esw.clean(f"{d.get(name, '')} {v}")
                break
    return d


TYPE_WORDS = re.compile(
    r"(?i)(municipal\s+corporation|city\s+municipal\s+council|town\s+municipal\s+council|municipal\s+council|municipal\s+committee|"
    r"town\s+panchayath?|notified\s+area\s+council|nagar\s+palika\s+parishad|nagar\s+panchayat|nagar\s+parishad|nagar\s+palika|"
    r"nagar\s+nigam|municipality|corporation|मुन्सिपल\s*कमेटी|नगर\s*पालिका\s*परिषद्?|नगर\s*पंचायत|नगर\s*परिषद्?|नगर\s*पालिका|नगरपालिका|"
    r"नगर\s*निगम|नगरपंचायत|नगरपरिषद|महानगरपालिका|ಪಟ್ಟಣ\s*ಪಂಚಾಯ(?:ತ್|ತಿ|ತ)|ನಗರಸಭೆ|ಪುರಸಭೆ|ಮಹಾನಗರ\s*ಪಾಲಿಕೆ|மாநகராட்சி|நகராட்சி|"
    r"பேரூராட்சி|మునిసిపాలిటీ|మున్సిపాలిటీ|నగరపాలక\s*సంస్థ|পৌরসভা|পুরসভা|નગરપાલિકા|નગર\s*પાલિકા|ਨਗਰ\s*ਕੌਂਸਲ|ਨਗਰ\s*ਪੰਚਾਇਤ|"
    r"ਨਗਰ\s*ਨਿਗਮ|നഗരസഭ|\btmc\b|\bcmc\b|\bnac\b)")


def lgd_table():
    global _LGD
    if _LGD is None:
        f = HERE / "ulb2_s3waas_lgd.json"
        _LGD = json.loads(f.read_text()) if f.exists() else {}
    return _LGD


def record_of(c, p, url, host, seen, lu=None):
    """One dept_office record for one card (None when the card names no body)."""
    d = card_fields(c)
    title, addr = _esw.clean(d["title"]), _esw.clean(d["address"])
    if not title:
        return None
    email = _esw.emails(d.get("email") or "") or _esw.emails(addr)
    phone = _esw.phones(d.get("phone") or "")
    if re.search(r"(?i)mob|मोबाइल|फोन", addr) and not phone:
        phone = _esw.phones(re.sub(r"\b\d{6}\b", " ", addr))
    body, post, name, how = title, None, "", None
    note = None
    pm = PERSON_TITLE.match(title)
    if pm and pm.group(3).strip(" ,.()") and len(pm.group(2).strip(" .")) >= 3 and not re.search(POST, pm.group(2), re.I) \
            and name_key(re.sub(POST, " ", pm.group(3), flags=re.I)):
        name, rest = _esw.clean(f"{pm.group(1)} {pm.group(2)}"), pm.group(3)
        ad = re.search(r"\((अति\.?\s*कार्यभार|additional\s+charge)[^)]*\)", rest, re.I)
        if ad:
            note, rest = "additional charge", rest.replace(ad.group(0), " ")
        pp = POST_AT_START.match(rest)
        post = _esw.clean(pp.group(1)) if pp else ("Chief Officer" if p.get("state") == "MH" else "Officer")
        body = _esw.clean(rest[pp.end():] if pp else rest).strip(" ,.:-")
        how = "title" if pp else "title-name"
    pt = None if post else post_of_text(title)
    if pt and pt[0]:
        rest = _esw.clean(title[POST_AT_START.match(title).end():] if POST_AT_START.match(title) else "").strip(" ,.:-")
        rest = re.sub(r"(?i)^(office|कार्यालय)\W+", "", rest)
        if rest:
            body, post, name, how = rest, pt[0], pt[1], "title"
    if not post:
        pa = post_of_text(addr)
        if pa:
            post, name, how = pa[0], pa[1], "address"
    if not post:
        pe = post_of_email(email)
        if pe:
            post, how = pe, "email"
    post = post or "Office"
    body = body or title
    m = TYPE_WORDS.search(title)
    lgd = (lgd_table().get(host) or {}).get(title_key(body))
    lat = latin(body) if re.search(r"[ऀ-෿]", body) else None
    rid, data = _ulb.record(MODULE, p["state"], body, post, seen, name=name, phone=phone, email=email, district=p.get("district"),
                            body_type=m.group(1) if m else None, source=url, latin=lat or None, area_latin=lat, lgd_code=lgd,
                            address=addr or None, pincode=re.sub(r"\D", "", d.get("pincode") or "")[:6] or None,
                            website=d.get("website") or None, post_from=how, last_updated=lu, site=host, notes=note)
    data["role"] = role(post)
    return rid, data


def records(pages, p):
    host = urlparse(p["url"]).netloc
    lu = next((last_updated(h) for _, h in pages if last_updated(h)), None)
    recs, seen = [], set()
    for url, html in pages:
        for c in _cards(html):
            r = record_of(c, p, url, host, seen, lu)
            if r:
                recs.append(r)
    return recs


def items(get=None):
    """The seed file is the list (built from archive.s1d.me, not from a request)."""
    return json.loads((HERE.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def fetch(p, get):
    pages, files = _civic.s3waas_pages(p, get, MODULE, p.get("max_pages", MAX_PAGES))
    if pages is None:
        return [], [], "no answer"
    recs = records(pages, p)
    return recs, files, "" if recs else "no cards"
