"""Shared helpers for the ward / zone officer readers of the Madhya Pradesh, Chhattisgarh and Rajasthan corporations that had no
ward-level officers in DB civic before 2026-11-13 (dforms/ward3_<city>.py, branch ward-staff-central).

- post_en(): English post for the Hindi posts these sites write (MP / CG words: यंत्री for engineer, दरोगा for the ward sanitation
  supervisor), else dforms/_ward.hi_post().
- zones_of(): zone numbers in a post text ("जोनल अधिकारी जोन क्र.02 एवं 05" -> ["2", "5"]).
- strip_title(): a name without श्री / श्रीमती / सुश्री / कु. / डॉ. (kept in name_regional as written).
- elementor_rows(): the rows of an Elementor page that draws a table as one top-level section per row and one column per cell.
"""
import re

from dforms import _esw, _ward

MP_POSTS = (
    (r"अधीक्षण\s*यंत्री", "Superintending Engineer"), (r"कार्यपालन\s*यंत्री", "Executive Engineer"),
    (r"सहायक\s*यंत्री", "Assistant Engineer"), (r"उप\s*यंत्री", "Sub Engineer"),
    (r"जोनल\s*अधिकारी|ज़ोनल\s*अधिकारी", "Zonal Officer"), (r"जोन\s*आयुक्त|जोन\s*कमिश्नर", "Zone Commissioner"),
    (r"सहा\.?\s*स्वच्छता\s*अधिकारी|सहायक\s*स्वच्छता\s*अधिकारी", "Assistant Sanitation Officer"),
    (r"स्वच्छता\s*अधिकारी", "Sanitation Officer"), (r"स्वास्थ्य\s*निरीक्षक", "Health Inspector"),
    (r"स्वास्थ्य\s*अधिकारी", "Health Officer"), (r"दरोगा", "Ward Daroga (sanitation supervisor)"),
    (r"उपायुक्त", "Deputy Commissioner"), (r"आयुक्त", "Commissioner"), (r"विधि\s*अधिकारी", "Law Officer"),
    (r"राजस्व\s*निरीक्षक", "Revenue Inspector"), (r"राजस्व\s*अधिकारी", "Revenue Officer"),
)


def post_en(post):
    """English post of a Hindi post; "प्र." (प्रभारी, in charge) at the start adds " (in charge)"."""
    p = _ward.hi_norm(post)
    en = None
    for rx, e in MP_POSTS:
        if re.search(rx, p):
            en = e
            break
    en = en or _ward.hi_post(post)
    if re.match(r"\s*प्र\s*\.", p) and en != _esw.clean(post):
        en += " (in charge)"
    return en


def zones_of(text):
    """Zone numbers a post text names, as strings without leading zeros: "जोन क्र.02 एवं 05" -> ["2", "5"],
    "जोन क्रमांक 1, 3 एवं 4" -> ["1", "3", "4"]. [] when the text names no zone."""
    t = _ward.hi_norm(text)
    m = re.search(r"(?:जोन|zone)\s*(?:क्र(?:मांक)?\.?|no\.?|number)?\s*([\d\s,.]+(?:(?:एवं|व|और|and|&)\s*[\d\s,.]+)*)", t, re.I)
    if not m:
        return []
    out = []
    for n in re.findall(r"\d{1,2}", m.group(1)):
        if str(int(n)) not in out:
            out.append(str(int(n)))
    return out


TITLE = re.compile(r"^(?:श्रीमती\s|श्री\s|सुश्री\s|कु\.|डॉ\.|डाॅ\.|डा\.|Shri\s|Smt\.?\s|Dr\.|Mr\.?\s|Mrs\.?\s|Ms\.?\s)\s*", re.I)


def strip_title(name):
    n = _esw.clean(name)
    while True:
        m = TITLE.match(n)
        if not m or not m.group(0):
            return n
        n = n[m.end():].strip()


def elementor_rows(html):
    """[(cells, src_pos)] of an Elementor page: one entry per top-level section (section.elementor-top-section) with the text of
    each of its columns (the widgets of a column joined by " / "). src_pos = {"selector": "section.elementor-top-section",
    "index": n} (1-based, document order)."""
    s = _esw.soup(html)
    out = []
    for i, sec in enumerate(s.select("section.elementor-top-section"), 1):
        cols = sec.select(":scope > .elementor-container > .elementor-column")
        cells = [" / ".join(w.get_text("\n", strip=True) for w in c.select(".elementor-widget")) for c in cols]
        if any(c.strip() for c in cells):
            out.append((cells, {"selector": "section.elementor-top-section", "index": i}))
    return out


def phones_in(text):
    """Every 10-digit mobile in a text, joined with ", "."""
    return ", ".join(dict.fromkeys(re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", text or "")))


HI_WINGS = (("electrical", r"विद्युत|प्रकाश"), ("water", r"पेयजल|जल\s*कार्य|जलप्रदाय|जल\s*प्रदाय"), ("sewerage", r"सीवे[जर]|ड्रेनेज"),
            ("sanitation", r"स्वच्छता|सफाई|दरोगा"), ("health", r"स्वास्थ्य"), ("revenue", r"राजस्व|कर\s"),
            ("planning", r"भवन\s*अधिकारी|नगर\s*नियोजन|योजना"), ("horticulture", r"उद्यान"))


def wing(post_hi, post_en):
    """Wing of a post: from the Hindi words when they name one ("उपयंत्री (विद्युत)" -> electrical), else _ward.wing_of(English)."""
    p = _ward.hi_norm(post_hi)
    for w, rx in HI_WINGS:
        if re.search(rx, p):
            return w
    return _ward.wing_of(post_en)
