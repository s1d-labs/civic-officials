"""Municipal Corporation Sonipat (mcsonipat.in): its officers and engineers, with the wards of the ward-level posts, from the page
"Officers Directory" (/officers-directory; Drupal site of the HKCL template for Haryana corporations; in archive.s1d.me, saved
2026-11-11; the page shows no date). One table: Sr. No. | Name of Employee | Designation | Mobile No. | Branch | Ward
("7-11" = wards 7 to 11; empty for head-office posts). Records: rows with wards: level "ward" (wards = the list); the other rows:
level "body". parse() also reads the same table without the Branch / Ward columns, with "Mob. No." / "Contact No." and
"Email ID" / "Mail Id" columns (Karnal, Panchkula, Rohtak, Ambala, Manesar: dforms/ward2n_<city>.py).
Record ids: dept:<module>:<wards | hq>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_sonipat"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Sonipat", "248529", "HR", "Sonipat"
URL = "https://mcsonipat.in/officers-directory"
BRANCH_WING = (("sewer", "sewerage"), ("water", "water"), ("sanitation", "sanitation"), ("horticulture", "horticulture"),
               ("electric", "electrical"), ("property tax", "revenue"), ("building", "planning"), ("engineering", "engineering"))


def items(get=None):
    return [{"key": f"{MODULE}-officers-directory", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def cf_emails(html):
    """Cloudflare writes emails as <span class="__cf_email__" data-cfemail="<hex>">[email protected]</span> (or an <a>): the first
    byte is the key, each next byte XOR the key is one letter. Put the plain address back."""
    def dec_(h):
        k = int(h[:2], 16)
        return "".join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))
    return re.sub(r'<(a|span)[^>]*data-cfemail="([0-9a-fA-F]+)"[^>]*>.*?</\1>', lambda m: dec_(m.group(2)), html, flags=re.S)


def parse(html, p, module=MODULE, body=BODY, lgd=LGD, district=DISTRICT):
    html = cf_emails(html)
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "name", "designation"):
        for r in rows:
            name = _ward.col(r, "name of employee", "name")
            post = _ward.col(r, "designation").strip(" -")
            if not post or not name or name == post or re.fullmatch(r"(?i)name.*", name):
                continue
            phone = _ward.col(r, "mobile", "mob", "contact", "phone")
            email = _ward.col(r, "email", "mail")
            branch = _ward.col(r, "branch").strip(" -")
            ws = _ward.wards_of(_ward.col(r, "ward")) if any("ward" in h.lower() for h in head) else []
            low = (branch + " " + post).lower()
            wing = "sanitation" if re.fullmatch(r"(?i)c?\.?s\.?i\.?|a\.?s\.?i\.?", post) else _ward.wing_of(post)
            if wing in ("other", "engineering", "administration"):
                wing = next((w for k, w in BRANCH_WING if k in branch.lower()), wing)
            key = ("ward-" + "-".join(ws)) if ws else "hq"
            recs.append(_ward.record(module, f"{key}:{_esw.slug(post)}:{_esw.slug(name)}", seen, body=body, lgd=lgd, state=p["state"],
                                     district=district, level="ward" if ws else "body", area=("Ward " + ", ".join(ws)) if ws else body,
                                     post=post, name=name, phone=phone if len(re.sub(r"\D", "", phone)) >= 6 else "", email=email, wards=ws or None,
                                     ward_text=_ward.col(r, "ward") if ws else None, section=branch or None, wing=wing if low else None, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "officers-directory", r.content)], "" if recs else "no directory table"
