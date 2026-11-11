"""Delhi: drugs inspectors and food safety officers, two sources (one queue item each):

1. Drugs Control Department "Who's Who" (drugs.delhi.gov.in/drugs/whos-who): five tables, each row "S. No. | Name of
   Licensing Authority | Name of Drugs Inspector | Allotted Pincode" (sale licences: each inspector has a list of PIN codes) or
   "... | District" (manufacturing, blood banks, vigilance). The licensing authority cell holds the officer's name, rank (DDC /
   ADC) and an obfuscated e-mail (dirdcd[at]nic[dot]in). The table titles above the tables give the function.
   38 inspector rows in the archive copy of 2026-11-05. Records: one per inspector and table row; area = PIN codes or district;
   pincodes = list; licensing_authority, licensing_authority_email; function = table title.
2. Department of Food Safety "Know your field officials" (foodsafety.delhi.gov.in/.../know_your_officials.pdf): names by
   group: Designated Officers (Group B gazetted) for all districts, overseers, Food Safety Officers "for districts as per
   Inspection Order", field assistants. No phone and no area per person: the FSO-to-area allocation is a separate scanned
   order (work-allocation-fsos, order_1.pdf: no text layer, needs OCR). The note "last updated on 29.07.2026" gives the date.
Records: dept health, layer field, field_layer food, state DL. Ids dept:field_food_dl:<source>:<n>.
"""
import re

from dforms import _esw, _field

MODULE = "field_food_dl"
DRUGS = "https://drugs.delhi.gov.in/drugs/whos-who"
FOOD = "https://foodsafety.delhi.gov.in/sites/default/files/Foodsafety/circulars-orders/know_your_officials.pdf"
GROUPS = [  # (heading words, post, level)
    (r"designated officer", "Designated Officer (Food Safety)", "district"),
    (r"overseer|gazetted officers", "Food Safety Officer (Overseer)", "district"),
    (r"food safety officers", "Food Safety Officer", "circle"),
    (r"field assistant|process server", "Field Assistant / Process Server", "circle"),
]


def items(get=None):
    """seeds/dept_field_food_dl.json: the two sources."""
    return _field.seed(MODULE)


def la_split(cell):
    """'Sh. Rohit Bajpai (DDC) dirdcd[at]nic[dot]in' -> ('Sh. Rohit Bajpai', 'DDC', 'dirdcd@nic.in')."""
    em = _esw.emails(cell)
    t = re.sub(r"\S+\[at\]\S+|\S+@\S+", "", cell)
    m = re.match(r"^(.*?)\s*\(([^)]+)\)", t)
    return (_esw.clean(m.group(1)), _esw.clean(m.group(2)), em) if m else (_esw.clean(t), "", em)


def parse_drugs(html, url):
    soup = _esw.soup(html)
    recs, n = [], 0
    for table in soup.find_all("table"):
        g = _esw.grid(table)
        if len(g) < 2:
            continue
        head = [h.lower() for h in g[0]]
        h = table.find_previous(["h2", "h3", "h4", "strong", "p"])
        func = _esw.clean(h.get_text(" ")) if h else ""
        la_i = next((i for i, c in enumerate(head) if "licensing authority" in c or "approving authority" in c), None)
        area_i = next((i for i, c in enumerate(head) if "pincode" in c or "pin code" in c or c.strip() == "district"), None)
        di = [i for i, c in enumerate(head) if "drugs inspector" in c or "name of di" in c or "(name of di)" in c]
        if la_i is None or not di:
            continue
        for row in g[1:]:
            la, rank, em = la_split(row[la_i]) if la_i < len(row) else ("", "", "")
            area = _esw.clean(row[area_i]) if area_i is not None and area_i < len(row) else ""
            for i in di:
                name = _esw.clean(row[i]) if i < len(row) else ""
                if not name or re.search(r"(?i)concerned|^-+$", name):
                    continue
                n += 1
                cell_head = _esw.clean(g[0][i])
                pins = re.findall(r"\b11\d{4}\b", area)
                recs.append(_esw.record(
                    MODULE, f"drugs:{n}", dept="health", level="circle" if pins else "district", layer="field",
                    field_layer="food", area=area or "Delhi (all districts)", post="Drugs Inspector", name=name, state="DL",
                    pincodes=pins or None, function=(_esw.clean(cell_head.split("|")[0]) if "cell" in cell_head.lower() else func) or None,
                    licensing_authority=la, licensing_authority_rank=rank, licensing_authority_email=em,
                    office_id=f"drugs:{n}", source=url, last_updated=_field.last_updated(html)))
    return recs


def parse_food(text, url):
    m = re.search(r"last updated on (\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    lu = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None
    recs, grp, n = [], None, 0
    for ln in text.split("\n"):
        t = _esw.clean(ln)
        if not t or re.search(r"(?i)implementation of|corresponding with|know your field|^\(\*\)|note:", t):
            continue
        g = next((x for x in GROUPS if re.search(x[0], t, re.I)), None)
        if g and len(re.split(r"\s{2,}", ln.strip())) == 1:
            grp = g
            continue
        if grp is None or re.search(r"(?i)^for (all )?districts", t):
            continue
        for name in re.split(r"\s{2,}", ln.strip()):
            name = _esw.clean(name)
            if len(name) < 3 or not re.match(r"^[A-Za-z. ]+$", name):
                continue
            n += 1
            recs.append(_esw.record(MODULE, f"food:{n}", dept="health", level=grp[2], layer="field", field_layer="food",
                                    area="Delhi (all districts)", post=grp[1], name=name, state="DL", office_id=f"food:{n}",
                                    source=url, last_updated=lu,
                                    notes="area per FSO: the work allocation order (scanned PDF) assigns districts"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if p.get("source") == "food" or r.content[:5] == b"%PDF-":
        files = [_esw.keep(MODULE, "know_your_officials", r.content, "pdf")]
        recs = parse_food(_field.pdf_text(r.content), p["url"])
    else:
        files = [_esw.keep(MODULE, "drugs-whos-who", r.content)]
        recs = parse_drugs(r.text, p["url"])
    return recs, files, "" if recs else "no officials found"
