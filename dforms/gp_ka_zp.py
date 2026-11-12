"""Karnataka: the Panchayat Development Officer (PDO, the secretary of a gram panchayat) of each gram panchayat, with the CUG
mobile, from the "Gram Panchayat" pages of the Zilla Panchayat websites zp<district>.karnataka.gov.in (one state template:
/<page id>/<page name>/en; the page id differs per district).

Structure (archive.s1d.me copy of 2026-11-06 and live pages, measured 2026-11-12): Tumakuru /46/gram-panchayat/en has one table
Block | Panchayath | Designation ("PDO/Secretary") | Contact Number (330 rows, CUG numbers 94808772xx); Kalaburagi
/17/gram-panchayats/en lists only gram panchayat names per taluk (no officer: no records); Mandya /119/gram-panchayat-officers/en
(content not in the archive copy: unverified). Several ZP hosts fail the TLS check from Mumbai (certificate chain): the task's get()
retries without the check and marks the records tls_unverified.
The reader reads the ZP home, follows up to 4 menu links of the same host whose address or text names gram panchayats / PDOs
(not taluk / zilla panchayat pages), and the pages named in the payload ("pages", known ids). Tables: the header row (first 3 rows)
must name the panchayat (panchayat / gp / grama) and a phone column (contact / mobile / phone / cug); other columns: block / taluk,
designation, name, email. A linked PDF is saved to the bucket and noted as a source_file record.

Records (dept rural_development, level gram_panchayat): area = the gram panchayat as written, block = the taluk, district = LGD
name, post "Panchayat Development Officer (PDO)" (designation kept as written in "designation"), name when the page gives one,
phone, email, cells (header -> text). Record ids: dept:gp_ka_zp:<district slug>:<page id>:<table>-<row>.
One queue item per ZP (28): 1 GET of the home + 1-5 GETs.
"""
import hashlib
import re
from urllib.parse import urljoin, urlparse

from dforms import _esw

METHOD = "html table (Zilla Panchayat gram panchayat pages, header words -> columns)"     # source trail (provenance.py)

MODULE = "gp_ka_zp"
# ZP host label -> LGD district (names as dforms/sub2_ka.py); hosts checked by DNS on 2026-11-12 (Bidar, Bengaluru Rural and
# Bengaluru South / Ramanagara have no zp<name> host)
HOSTS = {
    "zpbagalkote": "Bagalkote", "zpbellary": "Ballari", "zpbelagavi": "Belagavi", "zpbengaluruurban": "Bengaluru Urban",
    "zpchamarajanagar": "Chamarajanagar", "zpchikkaballapur": "Chikkaballapura", "zpchikkamagaluru": "Chikkamagaluru",
    "zpchitradurga": "Chitradurga", "zpdk": "Dakshina Kannada", "zpdavanagere": "Davanagere", "zpdharwad": "Dharwad",
    "zpgadag": "Gadag", "zphassan": "Hassan", "zphaveri": "Haveri", "zpkalaburagi": "Kalaburagi", "zpkodagu": "Kodagu",
    "zpkolar": "Kolar", "zpkoppal": "Koppal", "zpmandya": "Mandya", "zpmysuru": "Mysuru", "zpraichur": "Raichur",
    "zpshivamogga": "Shivamogga", "zptumakuru": "Tumakuru", "zpudupi": "Udupi", "zpuk": "Uttara Kannada",
    "zpvijayapura": "Vijayapura", "zpvijayanagara": "Vijayanagara", "zpyadgiri": "Yadgir",
}
PAGES = {  # known gram panchayat pages (archive.s1d.me): read even when the home menu does not link them
    "zptumakuru": ["/46/gram-panchayat/en"], "zpmandya": ["/119/gram-panchayat-officers/en"],
    "zpkalaburagi": ["/17/gram-panchayats/en"],
}
LINK = re.compile(r"(?i)gram[\s-]*panchay|grama[\s-]*panchay|\bpdo|panchayat[\s-]*development[\s-]*officer|ಗ್ರಾಮ\s*ಪಂಚಾಯ|ಪಿಡಿಒ")
NOT_LINK = re.compile(r"(?i)taluk|zilla|members|/kn$|scheme|grant|election|\.zip$")
GP_H = re.compile(r"(?i)panchay|^gp\b|gp\s*name|grama|ಪಂಚಾಯ")
PHONE_H = re.compile(r"(?i)contact|mobile|phone|cug|ದೂರವಾಣಿ|ಮೊಬೈಲ್")
BLOCK_H = re.compile(r"(?i)block|taluk|ತಾಲ್ಲೂಕ")
DESIG_H = re.compile(r"(?i)designation|ಹುದ್ದೆ|post")
NAME_H = re.compile(r"(?i)name|ಹೆಸರು")
EMAIL_H = re.compile(r"(?i)e-?mail")
SNO_H = re.compile(r"(?i)^(sl\.?\s*no\.?|s\.?\s*no\.?|no\.?|ಕ್ರ)")


def roles(header):
    out = {}
    for i, h in enumerate(header):
        if not h:
            continue
        if EMAIL_H.search(h):
            out[i] = "email"
        elif PHONE_H.search(h):
            out[i] = "phone"
        elif SNO_H.match(h):
            out[i] = "sno"
        elif DESIG_H.search(h):
            out[i] = "designation"
        elif BLOCK_H.search(h):
            out[i] = "block"
        elif GP_H.search(h):
            out[i] = "gp" if "gp" not in out.values() else "name" if NAME_H.search(h) else "gp2"
        elif NAME_H.search(h):
            out[i] = "name"
    return out


def records(html, url, p, page_id):
    soup = _esw.soup(html)
    dslug = _esw.slug(p["district"])
    recs = []
    for t in soup.find_all("table"):
        pos = []
        g = _esw.grid(t, pos=pos)
        hi = next((i for i, r in enumerate(g[:3]) if any(GP_H.search(c) for c in r) and any(PHONE_H.search(c) for c in r)), None)
        if hi is None:
            continue
        header = [_esw.clean(c) for c in g[hi]]
        rl = roles(header)
        if "gp" not in rl.values() or "phone" not in rl.values():
            continue
        for r, sp in zip(g[hi + 1:], pos[hi + 1:]):
            cells = [_esw.clean(c) for c in r]
            if cells[:len(header)] == header:
                continue
            v = {}
            for i, c in enumerate(cells):
                if rl.get(i) and c and c not in v.get(rl[i], []):
                    v.setdefault(rl[i], []).append(c)
            gp = " | ".join(v.get("gp") or [])
            phone = _esw.phones(*(v.get("phone") or []))
            name = " | ".join(v.get("name") or []) or None
            if not gp or not (phone or name):
                continue
            desig = " | ".join(v.get("designation") or []) or None
            post = ("Panchayat Development Officer (PDO)" if not desig or re.search(r"(?i)\bpdo\b|development officer|secretar", desig)
                    else desig)
            recs.append(_esw.record(MODULE, f"{dslug}:{page_id}:{sp['table']}-{sp['row']}", dept="rural_development",
                                    level="gram_panchayat", area=gp, block=" | ".join(v.get("block") or []) or None,
                                    district=p["district"], state="KA", post=post, designation=desig, name=name, phone=phone,
                                    email=_esw.emails(" ".join(v.get("email") or [])), list_no=" | ".join(v.get("sno") or []) or None,
                                    kind="panchayat_secretary",
                                    cells={header[i] or f"col{i + 1}": c for i, c in enumerate(cells) if c and i < len(header)},
                                    source=url, page=url, src_url=url, portal=p["host"], src_pos=sp))
    return recs


def links(html, base, host):
    out = []
    for a in _esw.soup(html).find_all("a", href=True):
        href, label = a["href"].strip(), _esw.clean(a.get_text(" "))
        u = urljoin(base, href)
        if urlparse(u).hostname != host or not LINK.search(f"{href} {label}") or NOT_LINK.search(href):
            continue
        if u not in out:
            out.append(u)
    return out


def items(get=None):
    return [{"key": f"{MODULE}:{label}", "payload": {"reader": MODULE, "url": f"https://{label}.karnataka.gov.in/",
                                                    "host": f"{label}.karnataka.gov.in", "district": district, "state": "KA",
                                                    "pages": [f"https://{label}.karnataka.gov.in{x}" for x in PAGES.get(label, [])],
                                                    "india_only": True, "route": "direct"}}
            for label, district in sorted(HOSTS.items())]


def fetch(p, get):
    host, recs, files = p["host"], [], []
    pages = list(p.get("pages") or [])
    r = get(p["url"])
    if r is not None:
        for u in links(r.content.decode("utf-8", "replace"), getattr(r, "url", "") or p["url"], host)[:4]:
            if u not in pages:
                pages.append(u)
    elif not pages:
        return [], [], "ZP home did not answer"
    dslug = _esw.slug(p["district"])
    for u in pages:
        if u.lower().split("?")[0].endswith(".pdf"):
            f = get(u)
            ok = f is not None and f.content[:5] == b"%PDF-"
            h = hashlib.sha1(u.encode()).hexdigest()[:12]
            path = f"depts/{MODULE}/{dslug}/{h}.pdf" if ok else None
            if ok:
                files.append((path, f.content, "application/pdf"))
            recs.append((f"dept:{MODULE}:{dslug}:file:{h}",
                         {"type": "source_file", "url": u, "stored": path, "bytes": len(f.content) if ok else None, "fetched": ok,
                          "state": "KA", "district": p["district"], "portal": host, "source": p["url"],
                          **({"src_url": u, "method": "file saved to the bucket (pdf)"} if ok else {})}))
            continue
        g = get(u)
        if g is None:
            continue
        m = re.search(r"/(\d+)/", urlparse(u).path)
        got = records(g.content.decode("utf-8", "replace"), u, p, m.group(1) if m else _esw.slug(urlparse(u).path))
        recs.extend(got)
        if got:
            files.append(_esw.keep(MODULE, f"{dslug}/{_esw.slug(urlparse(u).path)}", g.content, "html"))
        else:   # a page that only links the list as a PDF
            for a in _esw.soup(g.content.decode("utf-8", "replace")).find_all("a", href=True):
                x = urljoin(u, a["href"])
                if x.lower().endswith(".pdf") and x not in pages and len(pages) < 12 and \
                        LINK.search(f"{a['href']} {_esw.clean(a.get_text(' '))}"):
                    pages.append(x)
    if not any(d.get("type") == "dept_office" for _, d in recs):
        return recs, files, "no PDO table"
    return recs, files, ""
