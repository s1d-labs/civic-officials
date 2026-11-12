"""Maharashtra, Palghar district: the Gram Panchayat Adhikari (gram sevak / secretary of a gram panchayat) of each gram panchayat
of the 8 panchayat samitis, from the "Grampanchayat" office cards of the panchayat samiti websites ps<samiti>.zppalghar.gov.in
(WordPress theme of Zilla Parishad Palghar, office-center cards).

Structure (archive.s1d.me copies of 2026-11-11): /en/center-type/grampanchayat/ and /en/center-type/grampanchayat/page/<n>/
(Vikramgad: 4 pages; about 25-30 cards per page). Each card (div.card) has the gram panchayat (h4), and in div.hover-details
<p> lines: "👤 <name>", "🏢 Grampanchayat", "💼 <designation>" ("Grampanchayat Adhikari"), "📞 <tel link>", "✉️ <mailto>", and a
Google Maps link with the office point (destination=lat,lon).

Records (dept rural_development, level gram_panchayat): area = the gram panchayat, block = the panchayat samiti, district Palghar,
post "Gram Panchayat Adhikari (Panchayat Secretary)" when the designation says Grampanchayat Adhikari / Gramsevak (designation kept
as written), name, phone, email, lat / lon. src_pos = {"page": page number, "card": card number on the page}.
One queue item per panchayat samiti (8): 1 GET per page, pages followed while the page links the next one (at most 12).
Record ids: dept:gp_mh_palghar:<samiti>:<slug of gram panchayat>[:n].
"""
import re

from dforms import _esw

METHOD = "html cards (office-center theme: div.card, one card per gram panchayat)"     # source trail (provenance.py)

MODULE = "gp_mh_palghar"
SAMITIS = {"dahanu": "Dahanu", "jawhar": "Jawhar", "mokhada": "Mokhada", "palghar": "Palghar", "talasari": "Talasari",
           "vasai": "Vasai", "vikramgad": "Vikramgad", "wada": "Wada"}
POST = re.compile(r"(?i)gram\s*panchayat\s*adhikari|grampanchayat\s*adhikari|gram\s*sevak|gramsevak|ग्रामसेवक|ग्रामपंचायत\s*अधिकारी|ग्राम\s*पंचायत\s*अधिकारी|secretary")


def cards(html, url, p, page):
    soup = _esw.soup(html)
    out = []
    for n, c in enumerate(soup.select("div.card"), 1):
        hd = c.select_one("div.hover-details") or c
        gp = _esw.clean((hd.find("h4") or c.find("h3") or hd).get_text(" ")) if (hd.find("h4") or c.find("h3")) else ""
        f = {}
        for para in hd.find_all("p"):
            t = _esw.clean(para.get_text(" "))
            for mark, k in (("👤", "name"), ("🏢", "office_type"), ("💼", "designation"), ("📞", "phone"), ("✉", "email")):
                if t.startswith(mark):
                    f[k] = _esw.clean(t[len(mark):].lstrip("️"))
        tel = [a["href"][4:] for a in hd.find_all("a", href=True) if a["href"].startswith("tel:")]
        mail = [a["href"][7:] for a in hd.find_all("a", href=True) if a["href"].startswith("mailto:")]
        geo = next((m for a in hd.find_all("a", href=True) for m in [re.search(r"destination=(-?\d+\.\d+),(-?\d+\.\d+)", a["href"])] if m),
                   None)
        if not gp or not (f.get("name") or tel or f.get("phone")):
            continue
        out.append((n, gp, f, tel, mail, geo))
    return out


def records(html, url, p, page, seen):
    recs = []
    for n, gp, f, tel, mail, geo in cards(html, url, p, page):
        desig = f.get("designation")
        post = "Gram Panchayat Adhikari (Panchayat Secretary)" if not desig or POST.search(desig) else desig
        base = f"{p['samiti']}:{_esw.slug(gp) or n}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="rural_development", level="gram_panchayat", area=gp, block=p["block"],
                                district="Palghar", state="MH", post=post, designation=desig, name=f.get("name"),
                                phone=_esw.phones(*(tel or [f.get("phone", "")])), email=_esw.emails(" ".join(mail) or f.get("email", "")),
                                office_type=f.get("office_type"), lat=float(geo.group(1)) if geo else None,
                                lon=float(geo.group(2)) if geo else None, kind="panchayat_secretary", source=url, page=url,
                                src_url=url, portal=p["host"], src_pos={"page": page, "card": n}))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}:{s}", "payload": {"reader": MODULE, "host": f"ps{s}.zppalghar.gov.in", "samiti": s, "block": b,
                                                "url": f"https://ps{s}.zppalghar.gov.in/en/center-type/grampanchayat/",
                                                "district": "Palghar", "state": "MH", "india_only": False, "route": "abroad"}}
            for s, b in sorted(SAMITIS.items())]


def fetch(p, get):
    recs, files, seen = [], [], set()
    for page in range(1, 13):
        url = p["url"] if page == 1 else f"{p['url']}page/{page}/"
        r = get(url)
        if r is None:
            if page == 1:
                return [], [], "no answer"
            break
        html = r.content.decode("utf-8", "replace")
        got = records(html, url, p, page, seen)
        recs.extend(got)
        if got:
            files.append(_esw.keep(MODULE, f"{p['samiti']}/page-{page}", r.content, "html"))
        if not got or f"/page/{page + 1}/" not in html:
            break
    return recs, files, "" if recs else "no cards"
