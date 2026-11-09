"""Pure parsing for officials pages (no network): find the pages to read, and turn tables and S3WaaS AJAX answers into rows.

Most district sites run on S3WaaS (WordPress, NIC's "dbim" theme). Their Who's Who page shows each category as a table with two rows
and pages the rest through the site's own admin-ajax.php call `ww_pages`; `whoswho_blocks()` reads what that call needs from the page.
"""
import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

# Link text or address of a page that lists officials or their contacts (English, Hindi, Kannada, Tamil, Bengali, Marathi words).
LINK_WORDS = re.compile(
    r"who'?\s*'?s[\s_-]*who|who[\s_-]*is[\s_-]*who|whoswho|whos-who|directory|telephone|contact|officer|official|key[\s_-]*person|"
    r"staff|booth[\s_-]*level|\bblo\b|\bpio\b|\bapio\b|organi[sz]ation[\s_-]*chart|council|councillor|corporator|elected|"
    r"representative|member|mayor|president|chairman|commissioner|"
    r"adhikari|अधिकारी|संपर्क|सम्पर्क|निर्देशिका|पार्षद|ಅಧಿಕಾರಿ|ಸಂಪರ್ಕ|ಸಿಬ್ಬಂದಿ|ಸದಸ್ಯ|ಚುನಾಯಿತ|அலுவலர்|தொடர்பு|உறுப்பினர்|যোগাযোগ|আধিকারিক|अधिकाऱ्यां",
    re.I)
# Addresses that most S3WaaS sites have even when the home page does not link them.
COMMON_PATHS = ["whos-who/", "about-district/whos-who/", "en/whos-who/", "en/about-district/whos-who/", "directory/", "contact-us/",
                "public-utility-category/municipality/"]
SKIP = re.compile(r"\.(pdf|jpe?g|png|gif|zip|docx?|xlsx?|pptx?|mp4|mp3)$|^(mailto|tel|javascript):|/(feed|wp-json|tag|category)/", re.I)
PAGE_OF = re.compile(r"Page\s*-?\s*(\d+)\s*of\s*(\d+)", re.I)


def same_site(host, site):
    host, site = (host or "").lower().removeprefix("www."), site.lower().removeprefix("www.")
    return host == site or host.endswith("." + site)


def candidate_links(html, base, site, limit=15):
    """Addresses on `base` that probably list officials: links whose text or address matches LINK_WORDS, on the same site."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or SKIP.search(href):
            continue
        u = urljoin(base, href).split("#")[0]
        if not same_site(urlsplit(u).hostname, site):
            continue
        text = " ".join(a.get_text(" ", strip=True).split())[:120]
        if LINK_WORDS.search(text) or LINK_WORDS.search(urlsplit(u).path):
            if u not in out:
                out.append(u)
        if len(out) >= limit:
            break
    return out


def common_links(base):
    root = f"{urlsplit(base).scheme}://{urlsplit(base).netloc}/"
    return [root + p for p in COMMON_PATHS]


def deobfuscate(s):
    """dcurban[at]nic[dot]in -> dcurban@nic.in (NIC sites write emails this way)."""
    s = re.sub(r"\s*\[\s*at\s*\]\s*|\s*\(\s*at\s*\)\s*", "@", s or "", flags=re.I)
    s = re.sub(r"\s*\[\s*hyphen\s*\]\s*", "-", s, flags=re.I)
    s = re.sub(r"\s*\[\s*underscore\s*\]\s*", "_", s, flags=re.I)
    return re.sub(r"\s*\[\s*dot\s*\]\s*|\s*\(\s*dot\s*\)\s*", ".", s, flags=re.I).strip()


FIELD = {
    "name": re.compile(r"^(name|officer|officer'?s? name|name of (the )?officer|नाम|अधिकारी का नाम|ಹೆಸರು|பெயர்)$", re.I),
    "designation": re.compile(r"(designation|post|पद|ಹುದ್ದೆ|பதவி)", re.I),
    "email": re.compile(r"(e-?mail|ई-?मेल|ಇಮೇಲ್)", re.I),
    "phone": re.compile(r"(phone|mobile|contact|tel|फ़ोन|फोन|मोबाइल|ದೂರವಾಣಿ|தொலைபேசி)", re.I),
    "address": re.compile(r"(address|पता|ವಿಳಾಸ|முகவரி)", re.I),
}


def normalise(cells):
    """Map a row's {header: value} to the common fields name/designation/email/phone/address (keeps the raw cells too)."""
    out = {}
    for h, v in cells.items():
        v = " ".join(str(v or "").split())
        for f, rx in FIELD.items():
            if f not in out and rx.search(h or ""):
                out[f] = deobfuscate(v) if f == "email" else v
                break
    return out


def tables(html):
    """Every table with a header row: [{"caption", "headers", "rows": [{header: cell}]}]."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for t in soup.find_all("table"):
        cap = t.find("caption")
        trs = t.find_all("tr")
        if not trs:
            continue
        head = [" ".join(c.get_text(" ", strip=True).split()) for c in trs[0].find_all(["th", "td"])]
        if not any(head) or len(head) < 2:
            continue
        rows = []
        for tr in trs[1:]:
            cells = [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append({(head[i] if i < len(head) and head[i] else f"col{i}"): v for i, v in enumerate(cells)})
        if rows:
            out.append({"caption": " ".join(cap.get_text(" ", strip=True).split()) if cap else "", "headers": head, "rows": rows})
    return out


def pager_blocks(html, kind="ww"):
    """S3WaaS paged lists: Who's Who (kind "ww": div.whoswho, call `ww_pages`) and directory (kind "dir": div.directory, call
    `dir_pages`). Returns what the page's own pager sends: {"ajaxurl", "action", "nonce", "profile", "filter",
    "blocks": [{"slug", "name", "pages"}]}, or None when the page has no such pager."""
    soup = BeautifulSoup(html, "lxml")
    m = re.search(r'var\s+ajaxurl\s*=\s*"([^"]+)"', html)
    box = soup.select_one(".ww_html" if kind == "ww" else ".dir_html")
    nonce_box = soup.select_one(".ww_html") or box
    if not m or not box or not soup.select_one(".ww_nxt" if kind == "ww" else ".dir_nxt"):
        return None
    blocks = []
    for b in soup.select(("div.whoswho" if kind == "ww" else "div.directory") + "[data]"):
        pm = PAGE_OF.search(b.get_text(" ", strip=True))
        blocks.append({"slug": b.get("data"), "name": b.get("data-name", "") or " ".join((b.find("caption").get_text(" ", strip=True) if b.find("caption") else "").split()),
                       "pages": int(pm.group(2)) if pm else 1})
    return {"ajaxurl": m.group(1), "action": "ww_pages" if kind == "ww" else "dir_pages", "nonce": (nonce_box or {}).get("data-nonce", ""),
            "profile": box.get("data-profile", ""), "filter": box.get("data-filter", ""), "blocks": blocks}


def whoswho_blocks(html):
    return pager_blocks(html, "ww")


def ajax_rows(text):
    """Rows from one `ww_pages` / `dir_pages` answer. With the page's filter the rows are flat ({"Designation": ..., "Email": ...});
    without it they are {title: {meta: [value]}}, where title is the person's name (may be empty)."""
    try:
        obj = json.loads(text)
    except ValueError:
        return []
    rows = []
    for entry in obj.get("html") or []:
        if not isinstance(entry, dict):
            continue
        if entry and all(not isinstance(v, (dict, list)) for v in entry.values()):    # with the page's filter: flat {column: value}
            rows.append({k: "" if v is None else str(v) for k, v in entry.items()})
            continue
        for title, meta in entry.items():
            if not isinstance(meta, dict):
                continue
            cells = {k: (v[0] if isinstance(v, list) and v else v) for k, v in meta.items() if not k.startswith("_")
                     and k not in ("seo_title", "seo_description", "seo_keywords", "kv_view_count", "push_notification_link")}
            if title:
                cells = {"name": title, **cells}
            rows.append(cells)
    return rows


def row_id(site, page, caption, cells):
    h = hashlib.sha1(json.dumps([site, page, caption, cells], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
    return f"{site}:{h}"


def page_title(html):
    soup = BeautifulSoup(html, "lxml")
    return " ".join((soup.title.get_text(" ", strip=True) if soup.title else "").split())[:300]


def pubutility(html):
    """S3WaaS "public utility" cards (e.g. /public-utility-category/municipality/ on district sites): one card per office, with
    the office's name as heading and lines "Phone : ...", "Email : ...", "Website : ..." and an address. Returns [{"caption", "rows"}]."""
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for ul in soup.select("ul.pubutility-list"):
        box = ul.find_parent(["div", "li", "article"])
        head = box.find(["h2", "h3", "h4", "h5", "strong"]) if box else None
        cells = {"Office": " ".join(head.get_text(" ", strip=True).split()) if head else ""}
        for li in ul.find_all("li"):
            t = " ".join(li.get_text(" ", strip=True).split())
            m = re.match(r"(Phone|Mobile|Email|E-mail|Website|Fax|Pincode)\s*:?\s*(.*)", t, re.I)
            if m:
                cells[m.group(1).title()] = deobfuscate(m.group(2)) if m.group(1).lower().startswith("e") else m.group(2)
            elif t:
                cells.setdefault("Address", t)
        if any(v for k, v in cells.items() if k != "Office"):
            rows.append(cells)
    title = soup.find("h1")
    return [{"caption": " ".join(title.get_text(" ", strip=True).split()) if title else "public utility", "rows": rows}] if rows else []
