"""Karnataka: members of the Karnataka Legislative Council (MLCs) with addresses and phones, from the Council's contact
directory "Address & Contact Numbers" (kla.kar.nic.in/council/members/mcontact/mcontact<DDMMYYYY>.pdf, linked as "Latest
Contacts" on council/members/memberslist.htm; 13 pages, 70 members on 18-08-2026).

The PDF is a Word document set in the legacy Nudi font (Nudi01e): its text layer is Latin-1 letters ("²æÃ ¸À°ÃA CºÀäzï"),
converted to Unicode Kannada with cforms/cn_nudi.py ("ಶ್ರೀ ಸಲೀಂ ಅಹ್ಮದ್"). Digits are plain. pdftotext -raw keeps each member's
lines in order: "<n>. <name>", the post ("ಮಾನ್ಯ ಸಭಾಪತಿಯವರು," / "ಶಾಸಕರು, ವಿಧಾನ ಪರಿಷತ್ತು,"), one or two addresses (the second
starts with the name again or with "ಪತ್ರ ವ್ಯವಹಾರ" = address for letters), then labelled numbers: ಮೊಬೈಲ್ (mobile), ಕಛೇರಿ (office),
ನಿವಾಸ (residence), ಫ್ಯಾಕ್ಸ್ (fax), ಶಾಭ (Shasakara Bhavana, the MLAs' hostel). A label's extra numbers follow on their own lines.
The list gives no constituency and no party; names are in Kannada only (name = name_regional; record keys use a Latin
transliteration of the name).

kla.kar.nic.in answered GitHub runners abroad (archive.s1d.me pool copies 2026-11-05..08) but not dev-vps-2 / dev-vps-3:
the item runs abroad (archive-first projects can read the saved copy). One item: the list page, then the PDF (kept in the
bucket). Needs poppler (pdftotext). Record ids: dept:leg_kalc:KA-LC-<transliterated name>.
"""
import re
import subprocess

from cforms import cn_nudi
from dforms import _esw, _leg, _pdfcells

METHOD = 'pdf text (pdftotext -raw) + Nudi map'     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_kalc"
LIST = "https://kla.kar.nic.in/council/members/memberslist.htm"
BASE = "https://kla.kar.nic.in/council/members/"
LABELS = (("mobile", r"ಮೊಬೈಲ್|ಮೊಬೈಲ|ಮೊ\s*:"), ("phone_office", r"ಕಛೇರಿ|ಕಚೇರಿ"), ("phone_residence", r"ನಿವಾಸ"),
          ("fax", r"ಫ್ಯಾಕ್ಸ್|ಫ್ಯಾಕ್ಸ"), ("phone_hostel", r"ಶಾಭ|ಶಾಸಕರ\s*ಭವನ"))
HONORIFIC = re.compile(r"^(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಡಾ\s*[:.]|ಡಾ\.?|ಕುಮಾರಿ|ಪ್ರೊ\s*[:.])\s*")
POSTLINE = re.compile(r"ಪರಿಷತ್ತು|ಪರಿಷತ್|ಸಭಾಪತಿ|ಸಭಾನಾಯಕ|ಸಚೇತಕ|ವಿರೋಧ\s*ಪಕ್ಷ|ಸಚಿವ|ಮಂತ್ರಿ|ಮಾನ್ಯ")
LETTERS = re.compile(r"ಪತ್ರ\s*ವ್ಯವಹಾರ")
TITLE = re.compile(r"ವಿಳಾಸ\s*ಹಾಗೂ\s*$|ದೂರವಾಣಿ\s*ವಿವರಗಳ|ರಲ್ಲಿದ್ದಂತೆ|ಶಾಸಕರುಗಳ\s*ವಿಳಾಸ")

# Kannada -> Latin, only for stable record keys
_V = {"ಅ": "a", "ಆ": "aa", "ಇ": "i", "ಈ": "ii", "ಉ": "u", "ಊ": "uu", "ಋ": "ru", "ಎ": "e", "ಏ": "ee", "ಐ": "ai", "ಒ": "o", "ಓ": "oo",
      "ಔ": "au"}
_S = {"ಾ": "aa", "ಿ": "i", "ೀ": "ii", "ು": "u", "ೂ": "uu", "ೃ": "ru", "ೆ": "e", "ೇ": "ee", "ೈ": "ai", "ೊ": "o", "ೋ": "oo",
      "ೌ": "au", "ಂ": "m", "ಃ": "h", "್": ""}
_C = dict(zip("ಕಖಗಘಙಚಛಜಝಞಟಠಡಢಣತಥದಧನಪಫಬಭಮಯರಲವಶಷಸಹಳ",
              ["k", "kh", "g", "gh", "n", "ch", "chh", "j", "jh", "n", "t", "th", "d", "dh", "n", "t", "th", "d", "dh", "n",
               "p", "ph", "b", "bh", "m", "y", "r", "l", "v", "sh", "sh", "s", "h", "l"]))


def latin(s):
    out = []
    for i, ch in enumerate(s or ""):
        if ch in _C:
            nxt = s[i + 1] if i + 1 < len(s) else ""
            out.append(_C[ch] + ("" if nxt in _S else "a"))
        elif ch in _S:
            out.append(_S[ch])
        elif ch in _V:
            out.append(_V[ch])
        else:
            out.append(ch)
    return "".join(out)


def items(get=None):
    return [{"key": "leg_kalc-list", "payload": {"reader": MODULE, "url": LIST, "state": "KA", "kind": "LC",
                                                 "house_name": "Karnataka Legislative Council", "india_only": False}}]


def latest_pdf(html):
    """The newest mcontact<DDMMYYYY>.pdf named on the list page (absolute url), or None."""
    found = set(re.findall(r"mcontact/mcontact(\d{8})\.pdf", html or "", re.I))
    if not found:
        return None
    best = max(found, key=lambda d: (d[4:], d[2:4], d[:2]))
    return f"{BASE}mcontact/mcontact{best}.pdf"


def raw_text(content):
    r = subprocess.run(["pdftotext", "-raw", "-enc", "UTF-8", "-", "-"], input=content, capture_output=True, timeout=180)
    return r.stdout.decode("utf-8", "replace")


def kn(line):
    return cn_nudi.convert(line) if cn_nudi.is_nudi(line) else _esw.clean(line)


def blocks(text):
    """[(serial, [lines])] of the members, in order."""
    parts = re.split(r"(?m)^\f?\s*(\d{1,3})\.\s+", text)
    out = []
    for i in range(1, len(parts) - 1, 2):
        lines = [l.strip() for l in parts[i + 1].replace("\f", "\n").splitlines() if l.strip()]
        out.append((int(parts[i]), lines))
    return out


def member(serial, lines):
    """Fields of one member block (Nudi lines)."""
    d = {"serial": serial, "phones": {}, "addresses": [[]], "post": []}
    name_raw = lines[0] if lines else ""
    name = kn(name_raw).strip(" ,")
    last = None
    for ln in lines[1:]:
        u = kn(ln)
        lab = next((k for k, rx in LABELS if re.search(rx, u)), None)
        nums = _esw.phones(re.sub(r"^[^:]*:", " ", u) if lab else u)
        if lab:
            d["phones"].setdefault(lab, []).append(nums)
            last = lab
            continue
        if last and nums and not re.search(r"[ಀ-೿A-Za-z]", u):       # a further number of the last label
            d["phones"][last].append(nums)
            continue
        last = None
        if TITLE.search(u):                                                  # the directory's title at a page top
            continue
        if ln.strip() == name_raw.strip() or kn(ln).strip(" ,") == name or LETTERS.search(u):
            d["addresses"].append([])                                        # second address (for letters / in Bengaluru)
            continue
        if not any(d["addresses"]) and len(d["addresses"]) == 1 and POSTLINE.search(u) and len(d["post"]) < 3 and \
                not re.search(r"\d", u):
            d["post"].append(u.strip(" ,"))
            continue
        if len(d["addresses"]) > 1 and not d["addresses"][-1] and POSTLINE.search(u) and not re.search(r"\d", u):
            continue                                                         # the post again, above the second address
        d["addresses"][-1].append(u.strip())
    d["name_regional"] = name
    d["name"] = HONORIFIC.sub("", name).strip(" ,")
    return d


def parse(content, url, as_on=None):
    return parse_text(raw_text(content), url, as_on)


def parse_text(text, url, as_on=None):
    """Records from the PDF's pdftotext -raw text."""
    recs = []
    for serial, lines in blocks(text):
        d = member(serial, lines)
        if not d["name"]:
            continue
        ph = {k: ", ".join(x for x in v if x) for k, v in d["phones"].items()}
        addrs = [", ".join(a).replace(",,", ",") for a in d["addresses"] if a]
        extra = {k: v for k, v in ph.items() if k in _leg.PHONE_KEYS and v}
        rid, rec = _leg.member(MODULE, "KA", "LC", None, d["name"], source=url, post="Member of Legislative Council",
                               address=addrs[0] if addrs else "", name_regional=d["name_regional"],
                               designation=", ".join(d["post"]), second_address=addrs[1] if len(addrs) > 1 else "",
                               fax=ph.get("fax", ""), phone_hostel=ph.get("phone_hostel", ""), serial=serial,
                               last_updated=as_on, **extra)
        if ph.get("phone_hostel"):
            rec["phone"] = _leg._join(rec.get("phone", ""), ph["phone_hostel"])
        key = f"KA-LC-{_esw.slug(latin(d['name'])) or serial}"
        rec["office_id"] = key
        recs.append((f"dept:{MODULE}:{key}", rec))
    seen = {}
    out = []
    for rid, rec in recs:                                                    # two members with one transliteration
        seen[rid] = seen.get(rid, 0) + 1
        out.append((rid if seen[rid] == 1 else f"{rid}-{seen[rid]}", rec))
    return out


def fetch(p, get):
    if not _pdfcells.ensure_poppler():
        return [], [], "poppler (pdftotext) not available"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (list page)"
    files = [_leg.keep(MODULE, "memberslist", r.content)]
    pdf = p.get("pdf") or latest_pdf(r.text)
    if not pdf:
        return [], files, "no contact directory link on the list page"
    r2 = get(pdf)
    if r2 is None or r2.content[:5] != b"%PDF-":
        return [], files, "no answer (contact directory PDF)"
    files.append(_leg.keep(MODULE, pdf.rsplit("/", 1)[-1][:-4], r2.content, "pdf"))
    m = re.search(r"mcontact(\d{2})(\d{2})(\d{4})", pdf)
    recs = parse(r2.content, pdf, f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None)
    return recs, files, "" if recs else "no members in the PDF"
