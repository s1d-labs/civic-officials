"""Kerala Fire and Rescue Services (fire.kerala.gov.in, WordPress). Three kinds of queue item, payload "kind":
- "table": the officer tables in Malayalam, "District Fire Offices" (/district-fire-offices/, 14 District Fire Officers + the
  academy, civil defence academy and water rescue institute) and "Regional Fire Offices" (/റീജിയണൽ-ഫയർ-ഓഫീസ്സ്/, Regional Fire
  Officers). Columns: officer | district | address | phone & email. Names are in Malayalam only: name = name_regional = the
  name as written; district names are mapped to English.
- "team": the headquarters page (/ഹെഡ്-ക്വാർട്ടേഴ്സ്/): one card per officer (h3.team-title = name, .team-designation = post) and
  a text block "ഫോൺ / ഫാക്സ് / ഇമെയിൽ" after it.
- "posts": the public WordPress REST list /wp-json/wp/v2/posts?per_page=100&page=N (329 posts on 2026-11-11, 4 pages). Station
  and district posts carry a "Contact Information" block: heading = station, address lines, "Ph: ...". Other posts (tenders,
  notices) are skipped. The /en/<station>/ pages answered 404 from Germany on 2026-11-11 (archive.s1d.me has only the
  Thiruvananthapuram district page), so the reader reads the posts through the API. Station posts name no officer.
All three pages saved on archive.s1d.me 2026-11-05/06. The footer "Last Updated on" shows the time of the visit, not a
content date, so last_updated is left out (posts: the post's "modified" date).
Record ids: dept:emerg_fire_kl:dfo-<district>, rfo-<district>, hq-<post>, st-<post id>.
"""
import json
import re

from dforms import _emerg, _esw
import provenance

METHOD = "html table / html cards / json api (WordPress posts), by payload kind"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_fire_kl"
HOST = "https://fire.kerala.gov.in"
DISTRICTS = (  # Malayalam spelling (start) -> English
    ("തിരുവനന്തപുരം", "Thiruvananthapuram"), ("കൊല്ലം", "Kollam"), ("ആലപ്പുഴ", "Alappuzha"), ("പത്തനംതിട്ട", "Pathanamthitta"),
    ("കോട്ടയം", "Kottayam"), ("ഇടുക്കി", "Idukki"), ("എറണാകുളം", "Ernakulam"), ("തൃശൂർ", "Thrissur"), ("തൃശ്ശൂർ", "Thrissur"),
    ("പാലക്കാട്", "Palakkad"), ("മലപ്പുറം", "Malappuram"), ("കോഴിക്കോട്", "Kozhikode"), ("വയനാട്", "Wayanad"),
    ("കണ്ണൂർ", "Kannur"), ("കാസർകോട്", "Kasaragod"), ("കാസർഗോഡ്", "Kasaragod"),
)
POSTS = {"district": "District Fire Officer", "regional": "Regional Fire Officer"}


def items(get=None):
    return _emerg.seed(MODULE)


def district_of(text):
    t = _emerg.clean(text)
    for ml, en in DISTRICTS:
        if t.startswith(ml):
            return en
    found = None
    for ml, en in DISTRICTS:                 # "അക്കാദമി, വിയ്യൂർ, തൃശൂർ": a district named inside the cell
        if ml in t:
            found = en
    return found


def table_records(html, p):
    s = _esw.soup(html)
    which = p.get("table", "district")
    recs, seen = [], set()
    for t in s.select(".entry-content table") or s.find_all("table"):
        gp = []
        g = _esw.grid(t, pos=gp)
        for row, rp in zip(g[1:], gp[1:]):
            if len(row) < 4:
                provenance.skip_row(row, 'skip: len(row) < 4')
                continue
            names, place, adr, contact = row[0], row[1], row[2], row[3]
            dist = district_of(place)
            area = _emerg.clean(place.replace(" | ", " ")).strip(" ,")
            special = bool(re.search(r"അക്കാദമി|ഇൻസ്റ്റിറ്റ്യൂട്ട്|സിവിൽ\s*ഡിഫൻസ്|ആസ്ഥാന", area))
            office_post = "Head of Office" if special else POSTS[which]
            people = [_emerg.clean(x) for x in re.split(r"\s*\|\s*|(?<=\S)\s+(?=ശ്രീ\.)", names) if _emerg.clean(x)] or [""]
            is_district = bool(dist) and not special
            mail = _emerg.emails(contact)
            base = _emerg.slug(dist) if is_district else (mail.split("@")[0].replace(".", "-") if mail else "office")
            for name in people:
                key = _emerg.unique(f"{'dfo' if which == 'district' else 'rfo'}-{base}", seen)
                recs.append(_emerg.record(
                    MODULE, key, "fire", dept="fire", level="district" if is_district else "state",
                    area=dist if is_district else area, area_regional=area, post=office_post, name=name or None, name_regional=name or None,
                    phone=_emerg.phones(re.sub(r"[\w.+-]+@[\w.-]+", " ", contact)), email=mail,
                    address=adr.replace(" | ", ", "), district=dist, state="KL", office_id=key, source=p["url"],
                    src_pos=rp, method="html table"))
    return recs


def team_records(html, p):
    s = _esw.soup(html)
    recs, seen = [], set()
    for ti, title in enumerate(s.select("h3.team-title"), 1):
        cell = title.find_parent(class_="panel-grid-cell")
        if cell is None:
            continue
        post_el = cell.select_one(".team-designation")
        post = _emerg.clean(post_el.get_text(" ")) if post_el else ""
        text = _esw.cell_text(cell)
        phone_part = re.split(r"ഫാക്സ്|Fax", text)[0]
        fax = re.search(r"(?:ഫാക്സ്|Fax)\s*:?\s*([\d -]+)", text)
        name = _emerg.clean(title.get_text(" "))
        mail = _emerg.emails(text)
        key = _emerg.unique(f"hq-{mail.split('@')[0].replace('.', '-') if mail else len(recs) + 1}", seen)
        recs.append(_emerg.record(
            MODULE, key, "fire", dept="fire", level="state", area="Kerala Fire and Rescue Services Headquarters",
            post=post, post_regional=post, name=name, name_regional=name, phone=_emerg.phones(phone_part),
            fax=_emerg.clean(fax.group(1)) if fax else None, email=mail,
            address="Fire Force Junction, Pulimoodu P.O, Thiruvananthapuram 695001", district="Thiruvananthapuram",
            state="KL", office_id=key, source=p["url"], src_pos={"selector": "h3.team-title", "card": ti},
            method="html cards (team panel)"))
    return recs


def contact_block(html):
    """(heading, address, phone) of a station or district post's "Contact Information" block, or None."""
    i = (html or "").find("Contact Information")
    if i < 0:
        return None
    s = _esw.soup(html[i:])
    box = s.find(class_="textwidget") or s
    head = box.find(["h4", "h3", "h5"])
    lines = [x for x in (_emerg.clean(t) for t in _esw.cell_text(box.find("p") or box).split("|")) if x]
    phone = next((x for x in lines if re.match(r"(?i)(ph|phone|tel|mob)", x)), "")
    adr = [x for x in lines if x != phone]
    return (_emerg.clean(head.get_text(" ")) if head else "", ", ".join(adr), _emerg.phones(re.sub(r"(?i)^(ph|phone|tel)\w*\s*:?", "", phone)))


def post_records(posts, p):
    recs = []
    for pi, post in enumerate(posts):
        html = (post.get("content") or {}).get("rendered") or ""
        cb = contact_block(html)
        if not cb:
            continue
        title = _emerg.clean(re.sub(r"<[^>]+>", " ", (post.get("title") or {}).get("rendered") or ""))
        head, adr, phone = cb
        link = post.get("link") or ""
        url = link if link.startswith("http") else HOST + link
        district = district_of(adr) or next((en for _, en in DISTRICTS if en.lower() in (adr + " " + title).lower()), None)
        key = f"st-{post.get('id')}"
        recs.append(_emerg.record(
            MODULE, key, "fire", dept="fire", level="facility", area=title or head, area_heading=head,
            post="Station Officer", phone=phone, address=adr, district=district, state="KL", office_id=key,
            source=url, last_updated=(post.get("modified") or "")[:10] or None, src_url=p["url"],
            src_pos={"index": pi, "id": post.get("id"), "field": "content.rendered: Contact Information block"},
            method="json api (WordPress posts) + html block"))
    return recs


def fetch(p, get):
    kind = p.get("kind", "table")
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    name = {"table": f"table-{p.get('table', 'district')}", "team": "headquarters"}.get(kind, f"posts-{p.get('page', 1)}")
    files = [_emerg.keep(MODULE, name, r.content, "json" if kind == "posts" else "html")]
    if kind == "posts":
        try:
            posts = json.loads(r.content)
        except ValueError:
            return [], files, "not json"
        recs = post_records(posts if isinstance(posts, list) else [], p)
        return recs, files, "" if recs else ("no station posts on this page" if posts else "empty page")
    recs = (team_records if kind == "team" else table_records)(r.text, p)
    return recs, files, "" if recs else "no rows"
