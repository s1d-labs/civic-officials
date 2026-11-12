"""Tamil Nadu: ward councillors' mobiles, addresses and e-mails from the municipalities' and corporations' own sites on the
state platform www.tnurbantree.tn.gov.in/<site>/ (WordPress multisite, ~150 bodies). Each body has one "Councillors" page,
but its address differs per body (councilars, councilors, municipal-councillors, corporation-councillor, ta/municipal-councillor
...), so the reader asks the site's own page search: <site>/wp-json/wp/v2/pages?search=counc (the public WordPress API, one
request, page content included) and takes the page whose table has the most councillor rows. Tables differ per body: ward
no, name, father's/husband's name, address, mobile or "Contact No./ Landline No.", e-mail, party, photo; in English.
Councillors of the 2022 term (the same as the SEC results that cforms/tn.py reads); our records have the Tamil names of
those results, so sql/72 must join TN on body + ward (the names are in two scripts).
Some bodies publish only a PDF of the list: the PDF goes to the bucket and the item gives "list is a PDF (stored)".
One queue item = one body: payload {"kind": "form-cp_tn", "state": "TN", "url" (the search url), "site", "body" (Tamil name as
in civic.councillor), "lgd_code", "record_prefix" (councillor:TN:<group>:<body> of cforms/tn.py), "name_en"}.
A payload url that is not a wp-json url is read as one HTML page. Record id cp:TN:<site>:<ward>."""
import gzip
import json
import re

from cforms.cp_common import column, emails, keyed, phones, record, table_rows, useful, ward_no

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://www.tnurbantree.tn.gov.in/"
TITLE = re.compile(r"^(thiru|tmt|selvi|thirumathi|mr|mrs|ms|dr|adv)\b\.?\s*", re.I)


def search_url(site):
    return f"{BASE}{site}/wp-json/wp/v2/pages?search=counc&_fields=link,title,content&per_page=50"


def name_of(s):
    s = re.sub(r"\((?:chair(?:man|person)|vice[- ]?chair(?:man|person)|mayor|deputy mayor)[^)]*\)", " ", s or "", flags=re.I)
    s = re.sub(r"\s+[SDWC]/[Oo]\b.*$", "", s)                 # "A.K.Ramesh S/o Kupusamy": the father's name is not part of it
    s = TITLE.sub("", s.strip())
    return " ".join(s.split()) or None


def parse(html, p, url):
    recs = []
    for head, cells in table_rows(html):
        if not head:
            continue
        ni = column(head, r"name of (the )?(elected )?(councill?or|candidate|member)", r"councill?or name", r"^name")
        wi = column(head, r"^ward", r"ward\s*(no|number)")
        pi = column(head, r"mobile", r"contact", r"phone", r"cell")
        ei = column(head, r"e-?\s*mail")
        ai = column(head, r"address")
        if ni is None or (pi is None and ei is None and ai is None) or len(cells) <= ni:
            continue
        at = lambda i: cells[i] if i is not None and i < len(cells) else ""
        name = name_of(at(ni))
        if not name or re.fullmatch(r"[\d\W]+", name):
            continue
        w = ward_no(at(wi)) if wi is not None else None
        tel = phones(at(pi))
        recs.append(record("TN", p["body"], w, name, url, phone=tel, email=emails(at(ei)) or emails(at(pi)), address=at(ai),
                           ward_label=at(wi), lgd_code=p.get("lgd_code"),
                           record_for=f"{p['record_prefix']}:{w}" if w and p.get("record_prefix") else None,
                           extra={"name_en": p.get("name_en")}))
    return useful(recs)


def best_page(pages, p):
    """(url, records) of the search hit with the most councillor rows; ([], pdf links) when only PDFs are linked."""
    best, pdfs = (None, []), []
    for pg in pages if isinstance(pages, list) else []:
        html = (pg.get("content") or {}).get("rendered") or ""
        link = pg.get("link") or ""
        recs = parse(html, p, link)
        if len(recs) > len(best[1]):
            best = (link, recs)
        title = ((pg.get("title") or {}).get("rendered") or "").lower()
        if re.search(r"councill?or|councilar|members", title + link):
            pdfs += [u for u in re.findall(r'href="([^"]+\.pdf)"', html, re.I) if u not in pdfs]
    return best, pdfs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/TN/cp-{p['site']}.json.gz" if "wp-json" in p["url"] else f"councillors/TN/cp-{p['site']}.html.gz",
              gzip.compress(r.content), "application/gzip")]
    if "wp-json" in p["url"]:
        try:
            pages = json.loads(r.text)
        except ValueError:
            return [], files, "search answer is not JSON"
        (link, recs), pdfs = best_page(pages, p)
        if not recs and pdfs:
            f = get(pdfs[0])
            if f is not None and f.content[:5] == b"%PDF-":
                files.append((f"councillors/TN/cp-{p['site']}.pdf", f.content, "application/pdf"))
                return [], files, "list is a PDF (stored)"
    else:
        recs = parse(r.text, p, p["url"])
    return keyed("TN", p["site"], recs), files, "" if recs else "no councillor table with contacts"
