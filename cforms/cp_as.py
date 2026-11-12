"""Assam: phones of ward commissioners from each municipal board's own site on the UDD platform, <town>.assamurban.in/members
("Members: Details about the Municipal Board Elected Representative"). One card per member: name (h3), post (Chairman, Vice
Chairman, Ward Commissioner), mobile, "Ward No. Ward no.4" (the chairman's card often has no ward). Members of the 2022
term, the same people as the SEC 2022 gazette (cforms/as_.py). A card marked "(Expired)" keeps the chairman's office phone, not
the member's own: it gives no record. The page answers from outside India.
One queue item = one board: payload {"kind": "form-cp_as", "state": "AS", "url", "body", "lgd_code", "record_slug"}. The
record ids of the SEC reader are councillor:AS:<record_slug>:<ward>; ours are cp:AS:<record_slug>:<ward> (cp_common).
Seeds: seeds/councillors_cp_as.json (boards we hold, host from civic.official_site or the board name)."""
import gzip
import re

from bs4 import BeautifulSoup

from cforms.cp_common import keyed, phones, record, useful, ward_no

METHOD = "html cards (h3 + p)"     # source trail (provenance.py): how this reader reads its sources

GONE = re.compile(r"\((?:expired|late|died|deceased|resigned)\)", re.I)


def cards(html):
    """(name, [texts under the name]) per member card."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for h in soup.find_all("h3"):
        ps = [" ".join(p.get_text(" ", strip=True).split()) for p in h.find_next_siblings("p")]
        if ps:
            out.append((" ".join(h.get_text(" ", strip=True).split()), ps))
    return out


def parse(html, p):
    recs = []
    for k, (name, ps) in enumerate(cards(html), 1):
        if GONE.search(name):
            continue
        post = next((t for t in ps if re.search(r"chair|commissioner|councillor|member", t, re.I)), None)
        tel = next((phones(t) for t in ps if phones(t)), None)
        wtxt = next((t for t in ps if re.search(r"ward\s*no", t, re.I)), None)
        if wtxt is None:                      # "12" alone under the phone (Tezpur): a short number is the ward
            wtxt = next((t for t in ps if re.fullmatch(r"\d{1,3}", t)), None)
        w = ward_no(wtxt) if wtxt else None
        recs.append(record("AS", p["body"], w, name, p["url"], phone=tel, position=post, ward_label=wtxt, lgd_code=p.get("lgd_code"),
                           record_for=f"councillor:AS:{p['record_slug']}:{w}" if w and p.get("record_slug") else None,
                           pos={"selector": "h3 with p after it", "card": k}))
    return useful(recs)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    host = re.sub(r"^https?://([^/]+).*", r"\1", p["url"])
    files = [(f"councillors/AS/cp-{host}.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = parse(r.text, p)
    return keyed("AS", p["record_slug"], recs), files, "" if recs else "no member cards with a phone"
