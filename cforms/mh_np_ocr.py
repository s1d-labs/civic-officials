"""Maharashtra nagar panchayats, general election 2021-22: the collectors' notices of the elected councillors (and the
group registers under the Local Authority Members' Disqualification Rules, 1987) in the divisional "Part -1 A" supplements
of the Government e-Gazette, where the notice has no usable text layer: Marathi in legacy fonts (DV-TTYogesh, DVB-TTYogesh,
DV-TTSurekh: the text layer is glyph codes), text layers that drop conjuncts, and image-only scans (Raigad, Ratnagiri,
Satara). cforms/mh_np.py reads the notices that repeat the order in English with a plain text layer; this reader OCRs the rest.

The PDF is the copy that an earlier item saved in the bucket (payload "stored"): no request goes to the gazette, so the items
run on any GitHub runner, with no proxy (project councillors-ocr-b). Each page is rendered at 300 dpi (grey), turned upright
when the payload says so ("rotate": 90 / 270, "rotate_pages": [first, last]) and read by Tesseract (mar+eng, psm 6, TSV word
boxes with confidences). The words are then read as a table, with no fixed layout:
- The table's columns come from its column-number row ("(१) (२) (३) (४)", "1 2 3 4 5 6"), else from the head phrases
  (a line with a name and a ward / serial word, and the head lines next to it). The column borders are the white gaps
  between the column centres over the table's lines.
- Each column's role comes from its head words (serial, body, name, ward, reservation, address, party, group ...). A table that
  continues on the next page ("अनुसूची—चालू", a repeated column-number row only) keeps the roles of the table before it.
- A row starts on a line with a number in the serial column (or the ward column when there is no serial column; in a table
  without either, after a wide gap); the lines below it (wrapped names, addresses, "(महिला)") belong to it.
- Rows split into blocks (one body each) at a new notice ("आदेश", "Order", "अधिसूचना"), where the ward number starts again, or
  where the body column names another body. A block's body is the payload body (LGD code, English and Marathi names) that its
  body column, its ward cells ("Lonand Nagarpanchayat Prabhag No. 4") or else its notice text names; else the only payload body.
- When a notice repeats the list in English (Raigad, Ratnagiri, Thane), the English row gives "name" and the Marathi row of the
  same ward gives "name_local".
Group registers (Konkan "गटातील नगरसेवकांची नावे", Soyagaon "परिशिष्ट अ") have no ward column: their rows are kept with the
group name ("group"; with a member-count column, the merged group cell is given to every row up to the next count; a
serial written in the name cell, "१. अक्षय" / "१०.आशियाना", starts a row) and record id councillor:MH:<LGD code>:grp-<notice>-<serial>; the ward results are councillor:MH:<LGD
code>:<ward> (the same ids as cforms/mh_np.py). Every record keeps the page, its row, the OCR line, the mean word confidence
and the row's box in pixels (300 dpi) in "src_pos", and the bucket copy (sha256, gazette url, key) in "src".
One queue item = one notice and up to 6 pages ("first", "last"); OCR runs on the GitHub runners only.
"""
import concurrent.futures
import difflib
import os
import re
import shutil
import statistics
import subprocess
import tempfile
import time

from cforms import gj, mh, mh_np, mh_scan
import provenance

METHOD = ("ocr tesseract mar+eng (300 dpi, psm 6, word boxes) of the saved gazette notice; columns from the table's "
          "column-number row or head, borders at the white gaps")
ELECTION = mh_np.ELECTION
DPI = 300
NUM = re.compile(r"^[(\[{|]*([0-9०-९]{1,3})[)\]}|.,:;]*$")
START = re.compile(r"^(आदेश|अधिसूचना|Order|ORDER|Orcer|Notification|NOTIFICATION)(\W+(आदेश|अधिसूचना|Order|ORDER|Notification|"
                   r"NOTIFICATION))*\W*$|BY\s+(THE\s+)?COLLECTOR")    # a page in two columns: "अधिसूचना अधिसूचना"
STOP = re.compile(r"भाग\s*[१1]\s*-\s*अ\s*\(|ठिकाण|स्थळ|^दिनांक|^दि\.\s*[0-9०-९]|जिल्हाधिकारी|Collector|^Place|^Dated?\b|स्वाक्षरी|शासन\s*राजपत्र|"
                  r"ON BEHALF|GOVERNMENT|^भाग\s*एक|^आदेश|^अधिसूचना|^Order\W*$|NOTIFICATION|COLLECTOR|^[A-Z][a-z]+,\s*$")
CONT = re.compile(r"चालू|contd|Contd")
TITLE = re.compile(r"^\W*(अनुसूची|Schedule|SCHEDULE)\W*$")      # (not "परिशिष्ट": group registers start their head there)
LETTERS = re.compile(r"[A-Za-zऀ-ॣॱ-ॿ]")
ROLES = (("group_leader", re.compile(r"गटनेत")), ("ward", re.compile(r"Constituency", re.I)),
         ("name", re.compile(r"(सदस्य|नगरसेवक|उमेदवार|Councillor|Candidate|Member|Elected).*(नाव|नांव|नावे|Name)|"
                             r"(नाव|नांव|नावे|Name).*(सदस्य|नगरसेवक|उमेदवार|Councillor|Candidate|Member|Elected)", re.I)),
         ("seats", re.compile(r"एकूण|संख्या")),           # before group: "गटाची / आघाडीची एकूण सदस्य संख्या" (Soyagaon)
         ("group", re.compile(r"गटा|आघाडी|Group", re.I)),
         ("ward", re.compile(r"प्रभाग|Ward|Constituency|वार्ड", re.I)),
         ("party", re.compile(r"पक्ष|Party|Front", re.I)),
         ("reservation", re.compile(r"शेरा|आरक्षण|प्रवर्ग|राखीव|तपशील|Remark|Category|reserved|जागा", re.I)),
         ("address", re.compile(r"पत्ता|Address", re.I)),
         ("father", re.compile(r"Father|Husband|वडिलांचे|पतीचे", re.I)),
         ("date", re.compile(r"Date|दिनांक", re.I)),
         ("body", re.compile(r"पंचायत|Nagar|नगर", re.I)),
         ("serial", re.compile(r"अ\s*\.?\s*क्र|अनु|^\s*क्र|Sr\b|S\.?\s*No|^\s*No\b", re.I)),
         ("name", re.compile(r"नाव|नांव|Name", re.I)))
HEAD_HINT = re.compile(r"नाव|नांव|Name|प्रभाग|Ward|अ\.\s*क्र|Sr\.|शेरा|Remark", re.I)
SERIAL_IN = re.compile(r"^[0-9०-९]{1,3}[.)]")       # "१." / "१०.आशियाना": a serial written in the name cell
HONORIFIC = re.compile(r"^(श्रीमती|श्रीम\.?|श्री\.?|सौ\.?|कु\.?|Shri\.?|Smt\.?|Mrs?\.?|Ms\.?)\s+")


def tools():
    """Tesseract with Marathi (and English) and poppler; installs them on a GitHub runner (sudo without password)."""
    def ok():
        if not (shutil.which("tesseract") and shutil.which("pdftoppm")):
            return False
        r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
        have = (r.stdout + r.stderr).split()
        return "mar" in have and "eng" in have
    if ok():
        return True
    # a runner job runs two processes: while one installs, the other waits for the apt lock
    cmd = ("sudo -n apt-get -o DPkg::Lock::Timeout=600 update -q && sudo -n apt-get -o DPkg::Lock::Timeout=600 install -y -q "
           "tesseract-ocr tesseract-ocr-mar tesseract-ocr-eng poppler-utils")
    for _ in range(3):
        subprocess.run(cmd, shell=True, capture_output=True)
        if ok():
            return True
        time.sleep(30)
    return ok()


# ---------------------------------------------------------------- OCR words and lines

def tsv_words(tsv):
    """Tesseract TSV -> words [{"x0", "y0", "x1", "y1", "text", "conf", "key"}] (level 5 rows with text)."""
    out = []
    for ln in tsv.splitlines()[1:]:
        f = ln.split("\t")
        if len(f) < 12 or f[0] != "5" or not f[11].strip():
            provenance.skip_line(ln, 'skip: len(f) < 12 or f[0] != "5" or not f[11].strip()')
            continue
        x, y, w, h = map(int, f[6:10])
        out.append({"x0": x, "y0": y, "x1": x + w, "y1": y + h, "text": f[11].strip(), "conf": float(f[10]),
                    "key": (int(f[2]), int(f[3]), int(f[4]))})
    return out


def lines_of(words):
    """Words -> lines (top to bottom), each {"y0", "y1", "yc", "words" (left to right), "text"}. Tesseract's own lines are
    joined when their middles are closer than half a text height (psm 6 can split one table row in two)."""
    if not words:
        return []
    hs = sorted(w["y1"] - w["y0"] for w in words)
    h = hs[len(hs) // 2] or 1
    groups = {}
    for w in words:
        groups.setdefault(w["key"], []).append(w)
    ls = []
    for ws in groups.values():
        yc = statistics.median((w["y0"] + w["y1"]) / 2 for w in ws)
        ls.append({"yc": yc, "words": ws})
    ls.sort(key=lambda l: l["yc"])
    out = []
    for l in ls:
        if out and abs(l["yc"] - out[-1]["yc"]) < 0.5 * h:
            out[-1]["words"] += l["words"]
            n = len(out[-1]["words"])
            out[-1]["yc"] = (out[-1]["yc"] * (n - len(l["words"])) + l["yc"] * len(l["words"])) / n
        else:
            out.append(l)
    figs = [m.group(2) for m in (FIGWORD.match(w["text"]) for w in words) if m]
    page_dev = sum(1 for f in figs if re.search(r"[०-९]", f)) > 0.7 * len(figs) if len(figs) >= 10 else False
    for l in out:
        l["words"].sort(key=lambda w: w["x0"])
        fix_digits(l["words"], page_dev)
        l["y0"] = min(w["y0"] for w in l["words"])
        l["y1"] = max(w["y1"] for w in l["words"])
        l["text"] = gj.norm(" ".join(w["text"] for w in l["words"]))
    return out


# Tesseract (mar) reads some Devanagari figures of a clean table as Latin look-alikes: १ as "q", ६ as "&", ५ as "4" or "षु",
# ७ as "9" or "0". (Nagpur notices in DV-TTYogesh, e.g. Bhandara Ex-3: "४. ४ १", then "षु. 4 १", "६. & q", "0. 9 q".) In a line
# that has Devanagari figures (or "q" / "&" alone), a figure-only word is read in Devanagari. ocr-gap round 2026-11-15.
FIGWORD = re.compile(r"^([(\[{|]*)([0-9०-९q&]{1,3}|षु)([)\]}|.,:;]*)$")
LOOKALIKE = str.maketrans({"q": "१", "&": "६", "4": "५", "9": "७", "0": "०", "1": "१", "2": "२", "3": "३", "5": "५", "6": "६",
                           "7": "७", "8": "८"})


def fix_digits(words, page_dev=False):
    """page_dev: most figure words of the page are Devanagari (then a line of Latin look-alikes only, "4 4", is read too)."""
    figs = [FIGWORD.match(w["text"]) for w in words]
    if not page_dev and not any(m and (re.search(r"[०-९]", m.group(2)) or m.group(2) in ("q", "&", "षु")) for m in figs):
        return
    for w, m in zip(words, figs):
        if not m:
            continue
        core = m.group(2)
        core = "५" if core == "षु" else ("७" if core == "0" else core.translate(LOOKALIKE))
        w["text"] = m.group(1) + core + m.group(3)


def _num(t):
    m = NUM.match(t or "")
    return int(mh.num(m.group(1))) if m else None


def col_row(line):
    """A column-number row ("(१) (२) (३) (४)", "1 2 3 4 5 6") -> [x centre per column], else None."""
    nums, other = [], 0
    for w in line["words"]:
        n = _num(w["text"])
        if n is None:
            if re.search(r"\w", w["text"]):
                other += 1
            continue
        nums.append((n, (w["x0"] + w["x1"]) / 2))
    if other > 1 or len(nums) < 3:
        return None
    vals = [n for n, _ in nums]
    if vals[0] not in (1, 2) or any(b <= a for a, b in zip(vals, vals[1:])) or vals[-1] > 14 or len(vals) < 0.6 * vals[-1]:
        return None
    return [x for _, x in nums]


def role_of(text):
    for role, rx in ROLES:
        if rx.search(text or ""):
            return role
    return ""


def roles_of(bs, head_lines, h):
    """Head lines -> role per column: the head words of each line join into phrases (gaps under 1.2 text heights), and a
    phrase goes to the column its middle falls in (between the borders)."""
    texts = [[] for _ in range(len(bs) + 1)]
    for l in head_lines:
        ph = []
        rule = False
        col = lambda w: sum(1 for x in bs if (w["x0"] + w["x1"]) / 2 > x)   # noqa: E731
        last = None
        for w in l["words"]:
            if w["text"] in ("|", "||", "।", "|।"):
                rule = True                      # a column rule read as a word: the phrase ends here
                continue
            # a phrase also ends where the next word stands in another column: tight heads ran "नगर पंचायतचे" and "प्रभाग
            # क्र." together, and the joined phrase made the body column the ward column (Bhandara Ex-3, ocr-gap 2026-11-15)
            if ph and w["x0"] - ph[-1][1] < 1.2 * h and not rule and (last is None or col(w) == col(last)
                                                                        or w["x0"] - ph[-1][1] < 0.25 * h):
                ph[-1] = (ph[-1][0], w["x1"], ph[-1][2] + " " + w["text"])
            else:
                ph.append((w["x0"], w["x1"], w["text"]))
            rule = False
            last = w
        for a, b, t in ph:
            texts[sum(1 for x in bs if (a + b) / 2 > x)].append(t)
    roles, used = [], set()
    for t in texts:
        r = role_of(" ".join(t))
        if r and r in used and r != "date":
            r = ""
        used.add(r)
        roles.append(r)
    return roles


RESV_WORDS = re.compile(mh.RESV.pattern + r"|General|Scheduled|Woman|Women|Open|S\.?C\.?\b|S\.?T\.?\b|O\.?B\.?C", re.I)


def fill_roles(roles, data, bs):
    """Roles the head did not give, from what the columns hold (the head of a scan can be unreadable): the column with the
    most words of letters = name; reservation words = reservation; number-only columns = serial (first column) and ward."""
    roles = list(roles)
    n = len(roles)
    cols = [[] for _ in range(n)]
    for l in data:
        for c, ws in enumerate(split(l, bs)):
            if ws:
                cols[c].append(" ".join(w["text"] for w in ws))
    def frac(c, f):
        return sum(1 for v in cols[c] if f(v)) / max(1, len(cols[c]))
    numeric = [frac(c, lambda v: all(_num(t) is not None for t in v.split())) for c in range(n)]
    resv = [frac(c, lambda v: bool(RESV_WORDS.search(v))) for c in range(n)]
    words = [sum(len([t for t in v.split() if LETTERS.search(t)]) for v in cols[c]) / max(1, len(cols[c])) for c in range(n)]
    if "reservation" not in roles:
        cand = [c for c in range(n) if not roles[c] and resv[c] > 0.5]
        if cand:
            roles[max(cand, key=lambda c: resv[c])] = "reservation"
    if "name" not in roles:
        cand = [c for c in range(n) if roles[c] in ("", "body") and words[c] >= 1.5 and numeric[c] < 0.3]
        if cand:
            roles[max(cand, key=lambda c: words[c])] = "name"
    for c in range(n):
        if not roles[c] and numeric[c] > 0.6 and len(cols[c]) >= 2:
            if c == 0 and "serial" not in roles:
                roles[c] = "serial"
            elif "ward" not in roles:
                roles[c] = "ward"
    return roles


def head_clusters(head_lines, h):
    """Head lines of a table without a column-number row -> column centres from the x ranges of the head words."""
    spans = sorted((w["x0"], w["x1"]) for l in head_lines for w in l["words"] if re.search(r"\w", w["text"]))
    # a rule "|" that Tesseract read between two head words is a column border ("नगर पंचायतीचे | गटातील ... सदस्यांचे")
    rules = [(w["x0"] + w["x1"]) / 2 for l in head_lines for w in l["words"] if w["text"] in ("|", "||", "।", "|।")]
    cl = []
    for a, b in spans:
        if cl and a - cl[-1][1] < 1.2 * h and not any(cl[-1][1] <= x <= a for x in rules):
            cl[-1][1] = max(cl[-1][1], b)
        else:
            cl.append([a, b])
    return [(a + b) / 2 for a, b in cl]


def borders(centres, data_lines):
    """The x between each two column centres that the fewest data words cover (ties: nearest the middle)."""
    out = []
    for a, b in zip(centres, centres[1:]):
        best = None
        for x in range(int(a) + 1, int(b), 4):
            cover = sum(1 for l in data_lines for w in l["words"] if w["x0"] < x < w["x1"])
            key = (cover, abs(x - (a + b) / 2))
            if best is None or key < best[0]:
                best = (key, x)
        out.append(best[1] if best else (a + b) / 2)
    return out


def split(line, bs):
    """Words of a line -> [list of words per column] by the borders."""
    cells = [[] for _ in range(len(bs) + 1)]
    for w in line["words"]:
        xc = (w["x0"] + w["x1"]) / 2
        cells[sum(1 for b in bs if xc > b)].append(w)
    return cells


# ---------------------------------------------------------------- tables of one page

def page_tables(page, lines, state):
    """One page's lines -> table segments [{"page", "roles", "rows", "notice", "intro"}]; state carries the notice count, the
    notice text and the last table's roles over pages."""
    if not lines:
        return []
    hs = sorted(l["y1"] - l["y0"] for l in lines)
    h = hs[len(hs) // 2] or 1
    segs, i = [], 0
    while i < len(lines):
        l = lines[i]
        cs = col_row(l)
        head = []
        if cs is None and HEAD_HINT.search(l["text"]) and role_of(l["text"]) and len(l["words"]) < 20 \
                and not START.search(l["text"]) and _num(l["words"][0]["text"]) is None \
                and not any(TITLE.search(x["text"]) for x in lines[i + 1:i + 4]):     # notice text above "अनुसूची"
            # a head line: with a name word and a ward or serial word somewhere in the head lines around it
            k0, k1 = i, i
            while k0 > 0 and lines[k0 - 1]["y1"] > l["y0"] - 2.5 * h and len(lines[k0 - 1]["words"]) < 20 \
                    and not START.search(lines[k0 - 1]["text"]) and not TITLE.search(lines[k0 - 1]["text"]) and i - k0 < 2:
                k0 -= 1
            while k1 + 1 < len(lines) and lines[k1 + 1]["y0"] < lines[k1]["y1"] + 1.8 * h and k1 - i < 6 \
                    and _num(lines[k1 + 1]["words"][0]["text"]) is None and not col_row(lines[k1 + 1]) \
                    and not any(SERIAL_IN.match(w["text"]) for w in lines[k1 + 1]["words"][:3]):
                k1 += 1                          # (a line with "१." in its first words is the first data row: "सोयगाव १. अक्षय")
            ht = " ".join(x["text"] for x in lines[k0:k1 + 1])
            # a group register without a serial column (Soyagaon "परिशिष्ट अ": the serial is in the members' name cell)
            # names the group: "गटातील / आघाडीतील सदस्यांचे नाव"
            if re.search(r"नाव|नांव|Name", ht, re.I) and re.search(r"प्रभाग|Ward|अ\.?\s*क्र|Sr\.|अनुक्र|गटातील|आघाडीतील", ht, re.I):
                head = lines[k0:k1 + 1]
                cs = head_clusters(head, h)
                i = k1
                if i + 1 < len(lines) and col_row(lines[i + 1]):
                    i += 1
                    cs = col_row(lines[i])
                if len(cs) < 3:
                    cs, head = None, []
        elif cs is not None:
            k = i
            while k > 0 and lines[k - 1]["y1"] > lines[k]["y0"] - 2.5 * h and len(lines[k - 1]["words"]) < 20 \
                    and not START.search(lines[k - 1]["text"]) and i - k < 5:
                k -= 1
                if TITLE.search(lines[k]["text"]):
                    k += 1                       # the schedule title: the notice text above it is no head (its "सदस्य ...
                    break                        # म्हणून" made the body column the name column, Gondia Ex-6)
                if STOP.search(lines[k]["text"]) or CONT.search(lines[k]["text"]):
                    break
            head = [x for x in lines[k:i] if not STOP.search(x["text"]) and not CONT.search(x["text"])]
        if cs is None:
            if START.search(l["text"]):
                state["notice"] += 1
                state["intro"] = ""
            else:
                state["intro"] += " " + l["text"]
            i += 1
            continue
        data, j = [], i + 1
        while j < len(lines) and not STOP.search(lines[j]["text"]) and not START.search(lines[j]["text"]) \
                and not col_row(lines[j]):
            data.append(lines[j])
            j += 1
        bs = borders(cs, data)
        roles = roles_of(bs, head, h)
        if "name" not in roles and state.get("roles") and len(state["roles"]) == len(cs):
            roles = list(state["roles"])          # a table continued from the page before
        roles = fill_roles(roles, data, bs)
        state["roles"] = roles
        segs.append({"page": page, "roles": roles, "notice": state["notice"], "intro": state["intro"],
                     "rows": rows_of(data, bs, roles, h)})
        i = j
    return segs


def rows_of(data, bs, roles, h):
    """Data lines -> rows [{"cells": {role or col: text}, "words", "line": index of first line, "lines": [text]}]."""
    key = "serial" if "serial" in roles else ("ward" if "ward" in roles else None)
    rows, cur, last_y1 = [], None, None
    for li, l in enumerate(data):
        cells = split(l, bs)
        named = {}
        for c, ws in enumerate(cells):
            if ws:
                named[roles[c] or f"c{c + 1}"] = ws
        if not named:
            provenance.skip_row(l, 'skip: not named')
            continue
        t = lambda r: gj.norm(" ".join(w["text"] for w in named.get(r, [])))  # noqa: E731
        name_ws = named.get("name", [])
        lead = None
        if name_ws and key is None:
            lead = _num(name_ws[0]["text"])
            if lead is None and SERIAL_IN.match(name_ws[0]["text"]) and LETTERS.search(name_ws[0]["text"]):
                lead = 1                         # "१०.आशियाना": serial and name in one word
        if key and named.get(key) and re.search(r"[0-9०-९]", t(key)) and _num(named[key][0]["text"]) is not None:
            start = True
        elif lead is not None:
            start = True                         # "१. अक्षय विनायक काळे": the serial inside the name cell
        elif "serial" not in roles and name_ws and (cur is None or l["y0"] - last_y1 > 1.6 * h):
            start = True                         # no serial column (Satara Form IV): rows apart by a wider gap
        else:
            start = False
        if start:
            cur = {"cells": {}, "words": [], "line": li, "lines": [], "y0": l["y0"]}
            rows.append(cur)
        elif cur is None or l["y0"] - last_y1 > 3 * h:
            cur = None
            continue
        elif not LETTERS.search(l["text"]):
            provenance.skip_row(l, 'skip: not LETTERS.search(l["text"])')
            continue                             # a page number "(१)" under the table
        for r, ws in named.items():
            cur["cells"][r] = gj.norm(cur["cells"].get(r, "") + " " + " ".join(w["text"] for w in ws))
        cur["words"] += [w for ws in named.values() for w in ws]
        cur["lines"].append(l["text"])
        last_y1 = l["y1"]
    return rows


# ---------------------------------------------------------------- bodies

def dnorm(s):
    """Devanagari / Latin text for loose matching: no nukta, candrabindu, anusvara, joiners, spaces or punctuation; long
    vowels as short; Latin lower case."""
    s = (s or "").lower()
    for a, b in (("ी", "ि"), ("ू", "ु"), ("ँ", ""), ("ं", ""), ("़", ""), ("ॅ", ""), ("ॉ", "ा"), ("ऑ", "आ"),
                 ("‌", ""), ("‍", "")):
        s = s.replace(a, b)
    return re.sub(r"[\s.,:;!?()\[\]{}'\"/\\|_\-–—‘’“”]+", "", s)     # (\W would drop the vowel signs)


def names_of(b):
    out = [n for n in (b.get("en") or []) if n] + [b.get("local", "")] + list(b.get("local_alt") or [])
    out = [re.sub(r"\s*नगर\s*पंचायत\s*$", "", n).strip() for n in out]
    return [n for n in out if n]


def scores(text, bodies):
    """How often the text names each body. Longer names count first and their matches are blanked, so "सडक अर्जुनी" is not
    also "अर्जुनी". Without any exact match, one loose match (ratio >= 0.8 over a window of the name's length) counts 1."""
    t = dnorm(text)
    names = sorted(((dnorm(n), i) for i, b in enumerate(bodies) for n in names_of(b)), key=lambda x: -len(x[0]))
    sc = [0] * len(bodies)
    for k, i in names:
        if len(k) >= 3 and k in t:
            # a name next to "नगरपंचायत" / "Nagar Panchayat" counts three times ("लोणंद नगरपंचायत, तालुका खंडाळा")
            sc[i] += t.count(k) + 2 * sum(t.count(a) for a in (k + "नगरप", k + "nagarp", "नगरपचायत" + k, "nagarpanchayat" + k,
                                                                   k + "np", k + "नप"))
            t = t.replace(k, "#")
    if any(sc):
        return sc
    for k, i in names:
        if len(k) >= 4 and any(difflib.SequenceMatcher(None, t[j:j + len(k)], k).ratio() >= 0.8
                               for j in range(0, max(1, len(t) - len(k) + 1))):
            sc[i] = max(sc[i], 1)
    return sc


def body_in(text, bodies):
    """The one body the text names most often, else None (ties: None)."""
    if not text or not text.strip() or not bodies:
        return None
    sc = sorted(((v, i) for i, v in enumerate(scores(text, bodies))), reverse=True)
    if sc[0][0] == 0 or (len(sc) > 1 and sc[1][0] == sc[0][0]):
        return None
    return bodies[sc[0][1]]


# ---------------------------------------------------------------- records

def ward_of(t):
    m = re.search(r"(?:Prabhag|Ward|प्रभाग)\D{0,12}?([0-9०-९]{1,3})", t or "", re.I)
    return mh.num(m.group(1)) if m else mh.num(t)


def blocks_of(segs):
    """Table segments -> blocks of rows (one body each)."""
    blocks, cur, prev_ward, notice = [], None, None, None
    for s in segs:
        for k, r in enumerate(s["rows"]):
            ward = ward_of(r["cells"].get("ward", "")) if "ward" in s["roles"] else ""
            new = cur is None or s["notice"] != notice or (ward and prev_ward and int(ward) <= int(prev_ward))
            if new:
                cur = {"rows": [], "intro": s["intro"], "has_ward": "ward" in s["roles"], "notice": s["notice"]}
                blocks.append(cur)
                notice = s["notice"]
            r["page"], r["row"], r["ward"] = s["page"], k + 1, ward
            cur["rows"].append(r)
            if ward:
                prev_ward = ward
    return blocks


def split_by_body(blocks, bodies):
    """A block whose body column names two bodies (merged cell repeated on a later row) splits there."""
    out = []
    for blk in blocks:
        cur, cur_b = None, None
        for r in blk["rows"]:
            b = body_in(r["cells"].get("body", ""), bodies) if r["cells"].get("body") else None
            if cur is None or (b and cur_b and b is not cur_b):
                cur = {**blk, "rows": []}
                out.append(cur)
                cur_b = None
            cur_b = cur_b or b
            cur["rows"].append(r)
    return out


OTHER_NP = re.compile(r"[ऀ-ॿ]{2,}\.?\)?\s*(नगरपंचायतीच्या|नगर\s*पंचायतीच्या|नगरपंचायतीचे)")


def block_body(blk, bodies):
    for field in ("body", "ward"):
        b = body_in(" ".join(r["cells"].get(field, "") for r in blk["rows"]), bodies)
        if b:
            return b, field
    b = body_in(blk["intro"], bodies)
    if b:
        return b, "notice text"
    if OTHER_NP.search(blk["intro"] or ""):
        return None, ""            # the notice names a nagar panchayat that is not one of the item's (a notice of another
        #                            collector further down the gazette part: Soyagaon notice 177 page 3, Osmanabad)
    if len(bodies) == 1:
        return bodies[0], "only body of the item"
    return None, ""


def clean_name(t):
    t = re.sub(r"\.{2,}|…|_+|\|", " ", t or "")
    t = re.sub(r"^[0-9०-९]{1,3}\s*[.)]\s*", "", gj.norm(t))
    t = HONORIFIC.sub("", t).strip(" .,:;-–—'\"")
    return gj.norm(t)


def records(segs, p):
    bodies = p.get("bodies") or []
    blocks = split_by_body(blocks_of(segs), bodies)
    out, why, by_ward = [], [], {}
    for bi, blk in enumerate(blocks, 1):
        b, how = block_body(blk, bodies)
        if not blk["has_ward"] and any(r["cells"].get("seats") for r in blk["rows"]):
            # group register with a member count: the group cell spans the group's rows (one merged cell, its text wrapped
            # over the first rows): every row up to the next count gets the whole group name
            grp, cur = [], None
            for r in blk["rows"]:
                if r["cells"].get("seats") or cur is None:
                    cur = []
                    grp.append(cur)
                cur.append(r)
            for g in grp:
                name_g = gj.norm(" ".join(r["cells"].get("group", "") for r in g))
                for r in g:
                    r["cells"]["group"] = name_g
                    r["cells"].setdefault("seats", g[0]["cells"].get("seats", ""))
        named = [r for r in blk["rows"] if LETTERS.search(clean_name(r["cells"].get("name", "")))]
        if not named:
            provenance.skip_row(blk, 'skip: not named')
            continue
        if b is None:
            why.append(f"block {bi} (page {blk['rows'][0]['page']}): body not named")
            continue
        for r in named:
            c = r["cells"]
            name_t = c.get("name", "")
            name = clean_name(name_t)
            m = re.match(r"^\s*([0-9०-९]{1,3})\s*[.)]", gj.norm(name_t))
            serial = mh.num(c.get("serial", "")) or (mh.num(m.group(1)) if m else "")
            confs = [w["conf"] for w in r["words"] if w["conf"] >= 0]
            nconf = [w["conf"] for w in r["words"] if w["conf"] >= 0 and w["text"] in name_t]
            latin = bool(re.search(r"[A-Za-z]{2}", name)) and not re.search(r"[ऀ-ॿ]", name)
            resv_t = gj.norm(c.get("reservation", ""))
            party_t = gj.norm(c.get("party", "") or c.get("group", ""))
            d = {"type": "councillor", "state": "MH", "body": (b.get("en") or [""])[0] + " Nagar Panchayat",
                 "body_local": b.get("local", ""), "body_en": b.get("name") or ((b.get("en") or [""])[0] + " Nagar Panchayat"),
                 "body_type": "Nagar Panchayat", "district": b.get("district", ""), "lgd_code": b["lgd_code"],
                 "ward_no": r["ward"] or "", "name": name, "name_text": gj.norm(name_t),
                 "reservation": (mh_np.reservation(resv_t) if latin else mh.reservation(resv_t)), "reservation_text": resv_t,
                 "address": gj.norm(c.get("address", "")), "father_or_husband": gj.norm(c.get("father", "")),
                 "party": (mh_np.party_of(party_t) or mh.party_of(party_t) or party_t), "party_text": party_t,
                 "group": gj.norm(c.get("group", "")), "group_leader": gj.norm(c.get("group_leader", "")),
                 "serial": serial, "election": ELECTION, "url": p.get("url", ""), "gazette": p.get("match", ""),
                 "gazette_date": p.get("gazette_date", ""), "page": r["page"], "lang": "en" if latin else "mr",
                 "read": "ocr (scan or legacy-font notice)", "method": METHOD, "body_from": how,
                 "src_pos": {"page": r["page"], "row": r["row"], "line": r["line"] + 1, "line_text": " / ".join(r["lines"]),
                             "conf": round(sum(confs) / len(confs), 1) if confs else None,
                             "name_conf": round(sum(nconf) / len(nconf), 1) if nconf else None, "block": bi,
                             "box_px": [min(w["x0"] for w in r["words"]), min(w["y0"] for w in r["words"]),
                                        max(w["x1"] for w in r["words"]), max(w["y1"] for w in r["words"])], "dpi": DPI}}
            if blk["has_ward"] and r["ward"]:
                key = f"councillor:MH:{b['lgd_code']}:{r['ward']}"
                by_ward.setdefault(key, []).append(d)
            elif not blk["has_ward"]:
                d["list"] = "group register (no ward)"
                out.append((f"councillor:MH:{b['lgd_code']}:grp-{p.get('notice', 'x')}-{blk['notice']}-{serial or r['row']}",
                            {k: v for k, v in d.items() if v not in ("", None)}))
    for key, ds in by_ward.items():
        en = [d for d in ds if d["lang"] == "en"]
        mr = [d for d in ds if d["lang"] == "mr"]
        d = dict(en[0] if en else ds[0])
        if en and mr:
            d["name_local"] = mr[0]["name"]
            d["src_pos_local"] = mr[0]["src_pos"]
            d.setdefault("reservation_local", mr[0]["reservation_text"])
        out.append((key, {k: v for k, v in d.items() if v not in ("", None)}))
    want = {b["lgd_code"] for b in bodies}
    for code in sorted(want):
        n = len({k for k, _ in out if k.startswith(f"councillor:MH:{code}:") and ":grp-" not in k})
        g = len([k for k, _ in out if k.startswith(f"councillor:MH:{code}:grp-")])
        if not n and not g:
            why.append(f"{code}: nothing read")
        elif n and n < int(p.get("seats", 17)):
            why.append(f"{code}: {n} of {p.get('seats', 17)} wards read")
    return out, "; ".join(why)


# ---------------------------------------------------------------- OCR and fetch

# ---------------------------------------------------------------- fallback: member lines anchored on the reservation word

# Some notices defeat the column reader: tight tables whose column-number row is misread ("g २ ३ %", Sindhudurg Ex-12), Latur's
# tables with a seven-line head and no number row, Beed's. Tesseract with psm 4 (one column of lines) reads their rows well:
#   "<serial> [ward] <name> [ward] <reservation> [address] [party]"   e.g. "१ १ जळवी ज्योती जयेंद्र सर्वसाधारण महिला"
# A member line is a line with a reservation word; the name is the letters before it (figures, look-alikes and stray marks of
# the serial and ward cells dropped). The lines between two notice starts or body titles form one body's list; the body is the
# one that the text above the list names. The ward is the place in the list, so a list is kept only when it has exactly the
# body's seats (17), or when every row's own ward figure agrees with its place. ocr-gap round 2026-11-15.
ANCHOR = re.compile(r"सर्वसाधारण|सर्व\s*साधारण|अनु\s*स\S{0,3}त|अराखीव|अ\s*राखीव|नागरिकांचा|ना\.\s*मा\.\s*[प्रव]|इतर\s*मागास|"
                    r"मागास\s*प्रवर्ग|General|Scheduled")
JUNK = re.compile(r"^[\W_0-9०-९q&%g]+$|^[क-ह][्ुूं]?[.,)]?$|^[क-ह][क-ह]$")     # ("प." = ५., "छ." = ७. in Beed)      # a figure, a look-alike or a lone letter or two
RESVW = re.compile(r"^\(?(सर्वसाधारण|साधारण|सर्व|अनु\s*स\S{0,3}त|जाती|जमाती|महिला|स्त्री|राखीव|अराखीव|प्रवर्ग|मागास|इतर|"
                   r"नागरिकांचा|ना\.?\s*मा\.?\s*\S*)\)?[,.]?$")
HEADW = re.compile(r"असल्यास|कोणासाठी|स्त्रीयासाठी|धरून|जसे\s|अगर\s|सदस्यांच|सदस्याच|शेरा|Remarks?\b", re.I)
END = re.compile(r"ठिकाण|स्थळ|^दिनांक|^दि\.\s*[0-9०-९]|जिल्हाधिकारी|Collector|^Place")
SECTION = re.compile(r"^\W*(आदेश|अधिसूचना|Order|ORDER)\W*$|^\W*नगर\s*पंचायत\s+\S+")


def anchor_lists(pages, p):
    """pages: [(page no, tesseract TSV of psm 4)] -> {lgd_code: [(ward, name, reservation text, tail, page, line, conf)]}."""
    bodies = p.get("bodies") or []
    seats = int(p.get("seats", 17))
    out, cur, intro = {}, [], ""
    addr_x = None                                # the name column's right border, when the head has an address column

    def close():
        b = body_in(intro, bodies)
        if b is None or not cur:
            return
        rows = cur
        figs = [r[0] for r in rows]
        if len(rows) == seats or (figs and all(f == i for i, f in enumerate(figs, 1))):
            got = [(str(i),) + r[1:] for i, r in enumerate(rows, 1)]
            if len(got) > len(out.get(b["lgd_code"], [])):
                out[b["lgd_code"]] = got
    for pg, tsv in pages:
        for li, l in enumerate(lines_of(tsv_words(tsv))):
            t = l["text"]
            if SECTION.search(t) and not ANCHOR.search(t):
                close()
                cur, intro = [], t
                continue
            m = ANCHOR.search(t)
            hw = [w for w in l["words"] if re.match(r"पत्ता|पत्त", w["text"])]
            nw = [w for w in l["words"] if re.search(r"नांव|नाव", w["text"])]
            if hw and nw and nw[-1]["x1"] < hw[0]["x0"]:
                # "... उमेदवाराचे नांव | पत्ता" (Beed Ex-2): the name head spans its column, the address head is centred
                addr_x = min(nw[-1]["x1"] + 60, (nw[-1]["x1"] + hw[0]["x0"]) / 2)
            if m and HEADW.search(t):
                continue                         # the table head ("जागा राखीव असल्यास कोणासाठी जसे अनुसूचित जाती ...")
            if cur and END.search(t):
                close()                          # the signature under the list ("ठिकाण - बीड"): the list ends here
                cur, intro = [], ""
                continue
            if not m or STOP.search(t):
                if not cur:
                    intro += " " + t
                continue
            pre = t[:m.start()].split()
            fig = None
            lead = 0
            while pre and (JUNK.match(pre[0]) or re.fullmatch(r"[\W_]+", pre[0])) and lead < 3:
                n = _num(pre[0])
                if n is not None and fig is None and re.search(r"[0-9०-९]", pre[0]):
                    fig = n
                if not re.fullmatch(r"[\W_]+", pre[0]):
                    lead += 1
                pre = pre[1:]
            name = []
            for tok in pre:
                if re.fullmatch(r"[|।\W_0-9०-९]+", tok):
                    break                        # the ward cell after the name ("मठपती सुषमा बस्वराज ७ सर्वसाधारण")
                name.append(tok)
            if not name:
                # the reservation before the name ("१. १ अनुसुचित जाती अडागळे किशोर परमेश्वर मु.पो. माऊली नगर", Beed): the
                # words after the reservation words, up to the address column (or a word with a dot, comma or figure; 4 words)
                ws = [w for w in l["words"] if w["x0"] >= min((x["x0"] for x in l["words"] if ANCHOR.search(x["text"])), default=0)]
                while ws and (RESVW.match(ws[0]["text"]) or ANCHOR.search(ws[0]["text"])):
                    ws = ws[1:]
                for w in ws:
                    if re.fullmatch(r"[\W_]+", w["text"]):
                        continue
                    if (addr_x and w["x0"] > addr_x) or re.search(r"[.,/0-9०-९:]", w["text"]) or len(name) >= (5 if addr_x else 3):
                        break
                    name.append(w["text"])
            while name and JUNK.match(name[-1]):
                name.pop()                       # the ward figure misread as a letter after the name ("एकनाथ न" = ६)
            name = clean_name(" ".join(name).strip(" |।.,"))
            if len(re.sub(r"[^क-हA-Za-z]", "", name)) < 3 or ANCHOR.search(name) or RESVW.match(name.split()[0]):
                continue                         # a head line ("(अनुसुचित जाती")
            conf = [w["conf"] for w in l["words"] if w["conf"] >= 0]
            cur.append((fig, name, gj.norm(t[m.start():]), t, pg, li, round(sum(conf) / len(conf), 1) if conf else None))
    close()
    return out


DARKRUN = re.compile(rb"[\x00-\x9f]{120,}")      # a ruled column line at 300 dpi: 120 dark pixels (1 cm) down
HRUN = re.compile(rb"[\x00-\x9f]{500,}")         # a ruled row line: 500 pixels (4 cm) across (a word's head line is shorter)


def unline(path):
    """Whiten the ruled lines of a grey PGM (runs of 500+ dark pixels across, 120+ down, and one pixel round them) in place:
    Tesseract then reads the cells of ruled tables it skipped (Latur Ex-1). Pure Python: rows and columns as byte slices."""
    with open(path, "rb") as f:
        img = f.read()
    m = re.match(rb"P5\s+(\d+)\s+(\d+)\s+255\s", img)
    if not m:
        return path
    w, h, off = int(m.group(1)), int(m.group(2)), m.end()
    pix = bytearray(img[off:])
    src = bytes(pix)
    for y in range(h):
        for r in HRUN.finditer(src, y * w, (y + 1) * w):
            a, b = max(0, r.start() - y * w - 1), min(w, r.end() - y * w + 1)
            for yy in (y - 1, y, y + 1):
                if 0 <= yy < h:
                    pix[yy * w + a:yy * w + b] = b"\xff" * (b - a)
    for x in range(w):
        col = src[x::w]
        for r in DARKRUN.finditer(col):
            for xx in (x - 1, x, x + 1):
                if 0 <= xx < w:
                    a, b = max(0, r.start() - 1), min(h, r.end() + 1)
                    pix[a * w + xx:b * w + xx:w] = b"\xff" * (b - a)
    with open(path, "wb") as f:
        f.write(img[:off] + bytes(pix))
    return path


def ocr_lines(pdf, page, tmp, p, clean=True):
    """The psm 4 reading of one page for anchor_lists(). clean: ruled lines whitened, Marathi only (mar+eng put Latin words
    into Marathi names: "fears साईप्रसाद"); else the page as it is, mar+eng (Vaibhavwadi, Sindhudurg Ex-12, reads better so)."""
    base = os.path.join(tmp, f"q{page}{'c' if clean else 'p'}")
    subprocess.run(["pdftoppm", "-r", str(DPI), "-gray", "-f", str(page), "-l", str(page), "-singlefile", pdf, base],
                   capture_output=True)
    img = mh_scan.upright(base + ".pgm", rotation(p, page))
    if clean:
        img = unline(img)
    r = subprocess.run(["tesseract", img, "-", "-l", "mar" if clean else "mar+eng", "--psm", "4", "tsv"], capture_output=True,
                       text=True)
    return r.stdout


def short_bodies(recs, p):
    """LGD codes of the payload bodies with fewer ward records than seats."""
    seats = int(p.get("seats", 17))
    out = []
    for b in p.get("bodies") or []:
        n = len({k for k, _ in recs if k.startswith(f"councillor:MH:{b['lgd_code']}:") and ":grp-" not in k})
        if n < seats:
            out.append(b["lgd_code"])
    return out


def merge_fallback(recs, why, lists, p):
    """The anchored lists replace the column reader's records of a body when they hold more wards."""
    short = set(short_bodies(recs, p))
    new = anchor_records({c: rows for c, rows in lists.items() if c in short}, p)
    done = set()
    for code in short:
        mine = [(k, d) for k, d in new if k.startswith(f"councillor:MH:{code}:")]
        old = [k for k, _ in recs if k.startswith(f"councillor:MH:{code}:") and ":grp-" not in k]
        if len(mine) > len(old):
            recs = [(k, d) for k, d in recs if not (k.startswith(f"councillor:MH:{code}:") and ":grp-" not in k)] + mine
            done.add(code)
    if done:
        why = "; ".join(x for x in (why or "").split("; ") if x and x.split(":")[0] not in done)
        why = (why + "; " if why else "") + "anchored lines: " + ", ".join(sorted(done))
    return recs, why


def anchor_records(lists, p):
    bodies = {b["lgd_code"]: b for b in p.get("bodies") or []}
    out = []
    for code, rows in lists.items():
        b = bodies[code]
        for ward, name, resv_t, line, pg, li, conf in rows:
            party = mh.party_of(resv_t) or mh_np.party_of(resv_t)
            d = {"type": "councillor", "state": "MH", "body": (b.get("en") or [""])[0] + " Nagar Panchayat",
                 "body_local": b.get("local", ""), "body_en": b.get("name") or ((b.get("en") or [""])[0] + " Nagar Panchayat"),
                 "body_type": "Nagar Panchayat", "district": b.get("district", ""), "lgd_code": code, "ward_no": ward,
                 "name": name, "reservation": mh.reservation(resv_t), "reservation_text": resv_t, "party": party,
                 "election": ELECTION, "url": p.get("url", ""), "gazette": p.get("match", ""),
                 "gazette_date": p.get("gazette_date", ""), "page": pg, "lang": "mr", "read": "ocr (scan or legacy-font notice)",
                 "method": METHOD + "; fallback: psm 4 lines anchored on the reservation word, ward = place in the list",
                 "body_from": "notice text", "ward_from": "place in the list",
                 "src_pos": {"page": pg, "line": li + 1, "line_text": line, "conf": conf, "dpi": DPI, "psm": 4}}
            out.append((f"councillor:MH:{code}:{ward}", {k: v for k, v in d.items() if v not in ("", None)}))
    return out


def rotation(p, page):
    deg = int(p.get("rotate", 0) or 0)
    rng = p.get("rotate_pages")
    if deg and rng and not (int(rng[0]) <= page <= int(rng[1])):
        return 0
    return deg


def ocr(pdf, page, tmp, p):
    base = os.path.join(tmp, f"p{page}")
    subprocess.run(["pdftoppm", "-r", str(DPI), "-gray", "-f", str(page), "-l", str(page), "-singlefile", pdf, base],
                   capture_output=True)
    img = mh_scan.upright(base + ".pgm", rotation(p, page))
    r = subprocess.run(["tesseract", img, "-", "-l", p.get("lang", "mar+eng"), "--psm", str(p.get("psm", 6)), "tsv"],
                       capture_output=True, text=True)
    return r.stdout


def parse_tsv(pages, p):
    """pages: [(page no, tesseract TSV)] in order -> (records, why). Pure: the tests run it on saved TSV."""
    state = {"notice": 0, "intro": "", "roles": None}
    segs = []
    for pg, tsv in pages:
        segs += page_tables(pg, lines_of(tsv_words(tsv)), state)
    return records(segs, p)


def fetch(p, get):
    from cforms.tn import mark_stored, stored
    if not tools():
        return [], [], "tesseract not available"
    content = stored(p, get)
    if content is None:
        return [], [], "stored copy not readable: " + str(p.get("stored"))
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", info)
        n = int(m.group(1)) if m else int(p.get("last", 1))
        pages = list(range(int(p.get("first", 1)), min(int(p.get("last", n) or n), n) + 1))
        with concurrent.futures.ThreadPoolExecutor(max(1, min(len(pages), os.cpu_count() or 1))) as ex:
            tsvs = list(ex.map(lambda pg: ocr(pdf, pg, tmp, p), pages))
        recs, why = parse_tsv(list(zip(pages, tsvs)), p)
        if short_bodies(recs, p):
            # a body with fewer wards than seats: the anchored-line reading of the cleaned pages (ocr-gap round 2026-11-15)
            for cl in (True, False):
                if not short_bodies(recs, p):
                    break
                with concurrent.futures.ThreadPoolExecutor(max(1, min(len(pages), os.cpu_count() or 1))) as ex:
                    lt = list(ex.map(lambda pg: ocr_lines(pdf, pg, tmp, p, cl), pages))
                recs, why = merge_fallback(recs, why, anchor_lists(list(zip(pages, lt)), p), p)
    mark_stored(recs, p, content, p.get("url"))
    if not recs:
        chars = sum(len(t) for t in tsvs)
        why = (why + "; " if why else "") + f"no members read (ocr tsv {chars} chars)"
    return recs, [], why
