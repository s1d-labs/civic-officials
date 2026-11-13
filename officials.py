"""Pure parsing for officials pages (no network): find the pages to read, and turn tables and S3WaaS AJAX answers into rows.

Most district sites run on S3WaaS (WordPress, NIC's "dbim" theme). Their Who's Who page shows each category as a table with two rows
and pages the rest through the site's own admin-ajax.php call `ww_pages`; `whoswho_blocks()` reads what that call needs from the page.
"""
import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

import provenance

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
    # "NAME (SRIYUTHS)", "ಹೆಸರು (ಶ್ರೀಯುತರು)": a bracket after the word is allowed
    "name": re.compile(r"^(name|officer|officer'?s? name|name of (the )?officers?|नाम|नाव|अधिकाऱ्याचे नाव|अधिकारी का नाम|ಹೆಸರು|பெயர்|ନାମ)"
                       r"(\s*\([^)]*\))?$", re.I),
    "designation": re.compile(r"(designation|post|पद|ಹುದ್ದೆ|பதவி|ପଦବୀ)", re.I),
    "email": re.compile(r"(e-?mail|ई-?मेल|ಇಮೇಲ್|ଇମେଲ)", re.I),
    "phone": re.compile(r"(phone|mobile|\bmob\b|\bmo\.?\s*no|contact|tel|फ़ोन|फोन|मोबाइल|दूरध्वनी|भ्रमणध्वनी|ದೂರವಾಣಿ|தொலைபேசி|ଦୂରଭାଷ|ଦୁରଭାଷ|ମୋବାଇଲ)", re.I),
    "address": re.compile(r"(address|पता|ವಿಳಾಸ|முகவரி|ଠିକଣା)", re.I),
    # the office or department a row is about (lists without a post column: "Name of Office", "Department Name", "विभाग नाम")
    "department": re.compile(r"(department|^office$|name of (the )?office$|office name|विभाग|ବିଭାଗ|କାର୍ଯ୍ୟାଳୟ)", re.I),
}


TITLED = re.compile(r"^(shri|smt|sri|sh|dr|kum|km|ms|mrs|mr|श्री|श्रीमती|ಶ್ರೀ|ಶ್ರೀಮತಿ|திரு|திருமதி)\b\.?\s*\S", re.I)
PHONE_CELL = re.compile(r"^(?:\+?91[\s-]*)?(?:0\d{2,4}[\s-]?\d{6,8}|[6-9]\d{4}[\s-]?\d{5})(?:\s*[,/]\s*.*)?$")


def normalise(cells):
    """Map a row's {header: value} to the common fields name/designation/email/phone/address (keeps the raw cells too).
    Several phone columns ("OFFICE PHONE NUMBER", "DEPT ISSUED MOB NO.") are joined. A row whose headers name no person or
    phone (a data row taken as the header row, "col0" ...) gets them from the cells: a titled cell ("Shri. Rajkumar Lehre") is the
    name, a phone-shaped cell the phone (2026-11-13, found by the reader audit)."""
    out = {}
    for h, v in cells.items():
        v = " ".join(str(v or "").split())
        for f, rx in FIELD.items():
            if rx.search(h or ""):
                if f == "phone" and out.get("phone") is not None and v and v not in out["phone"]:
                    out["phone"] = f"{out['phone']}, {v}" if out["phone"] else v
                elif f not in out:
                    out[f] = deobfuscate(v) if f == "email" else v
                else:
                    continue
                break
    vals = [" ".join(str(v or "").split()) for v in cells.values()]
    if not out.get("name"):
        n = next((v for v in vals if TITLED.match(v) and len(v) <= 80 and not re.search(r"\d{5}", v)), "")
        if n:
            out["name"] = n
    if not out.get("phone"):
        ph = next((v for v in vals if PHONE_CELL.match(v)), "")
        if ph:
            out["phone"] = ph
    return out


def tables(html):
    """Every table with a header row: [{"caption", "headers", "rows": [{header: cell}], "pos": [{"table": n, "row": m}, ...]}].
    "pos" (source trail) runs parallel to "rows": "table" = the table's place among the page's <table> elements (1-based, document
    order, nested tables counted); "row" = the row's <tr> number inside that table (1-based, header row counted)."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for ti, t in enumerate(soup.find_all("table"), 1):
        cap = t.find("caption")
        trs = t.find_all("tr")
        if not trs:
            continue
        first = 1
        head = [" ".join(c.get_text(" ", strip=True).split()) for c in trs[0].find_all(["th", "td"])]
        title = ""
        # a title row above the header row (one cell, often with colspan: "District Administration" | Sl no. | Name | ...):
        # the title becomes the caption and the next row is the header (Bihar contact directories, found by the review agents)
        if len(trs) > 2 and sum(1 for h in head if h) == 1:
            nxt = [" ".join(c.get_text(" ", strip=True).split()) for c in trs[1].find_all(["th", "td"])]
            if sum(1 for h in nxt if h) >= 2 and any(rx.search(h) for h in nxt for rx in FIELD.values()):
                title, head, trs, first = next(h for h in head if h), nxt, trs[1:], 2
        if len(head) >= 2 and not any(rx.search(h) for h in head for rx in FIELD.values()) and \
                any(TITLED.match(h) for h in head) and any(PHONE_CELL.match(h) for h in head):
            # the first row is a data row ("01 | Shri. Rajkumar Lehre | Inspector, SHO, Basantpur | 94791-93816"): no header
            rows = [{f"col{i}": v for i, v in enumerate(head)}]
            nos = [{"table": ti, "row": 1}]
            for n, tr in enumerate(trs[1:], 2):
                cells = [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append({f"col{i}": v for i, v in enumerate(cells)})
                    nos.append({"table": ti, "row": n})
                else:
                    provenance.skipped("empty")
            provenance.given(len(rows))
            out.append({"caption": " ".join(cap.get_text(" ", strip=True).split()) if cap else title, "headers": [], "rows": rows,
                        "pos": nos})
            continue
        if not any(head) or len(head) < 2:
            # no header row: a layout table, or data the readers do not see; rows with 2+ filled cells are counted as left out
            n_data = sum(1 for tr in trs[1:] if sum(1 for c in tr.find_all(["td", "th"]) if c.get_text(strip=True)) >= 2)
            if n_data >= 2:
                provenance.skipped("table without header row", n_data)
            continue
        provenance.skipped("header", first)        # the header row (and the title row above it)
        rows, nos = [], []
        for n, tr in enumerate(trs[1:], first + 1):
            cells = [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append({(head[i] if i < len(head) and head[i] else f"col{i}"): v for i, v in enumerate(cells)})
                nos.append({"table": ti, "row": n})
            else:
                provenance.skipped("empty")
        provenance.given(len(rows))
        if rows:
            out.append({"caption": " ".join(cap.get_text(" ", strip=True).split()) if cap else title, "headers": head, "rows": rows,
                        "pos": nos})
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
    rows, pos = [], []
    for k, ul in enumerate(soup.select("ul.pubutility-list"), 1):
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
        if any(v for h, v in cells.items() if h != "Office"):
            rows.append(cells)
            pos.append({"selector": "ul.pubutility-list", "card": k})
    title = soup.find("h1")
    return [{"caption": " ".join(title.get_text(" ", strip=True).split()) if title else "public utility", "rows": rows,
             "pos": pos}] if rows else []


PHONE = re.compile(r"^(?:\+?91[\s-]*)?(?:0\d{2,4}[\s-]?\d{6,8}|[6-9]\d{9})(?:\s*[,/]\s*(?:\+?91[\s-]*)?\d{10})*$")
ROLE = re.compile(r"chair|commissioner|councillor|counsellor|member|officer|engineer|inspector|secretary|accountant|assistant|clerk|"
                  r"mayor|president|executive|director|superintendent|manager|head|chief|deputy|vice|ward|"
                  r"अध्यक्ष|पार्षद|सदस्य|अधिकारी|ಸದಸ್ಯ|ಅಧ್ಯಕ್ಷ", re.I)
PEOPLE_PATH = re.compile(r"/(members?|office-staffs?|key-persons?|officials?|staffs?|councill?ors?|elected[\w-]*|team)/?$", re.I)


def text_people(html):
    """People shown as cards rather than a table (e.g. assamurban.in /members, /office-staff): in the page text, a phone line whose
    line above is a role and the line above that a name. Returns [{"caption", "rows"}] or []."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    lines = [" ".join(x.split()) for x in soup.get_text("\n").split("\n")]
    lines = [x for x in lines if x]
    rows, pos = [], []
    for i, ln in enumerate(lines):
        if i >= 2 and PHONE.match(ln) and ROLE.search(lines[i - 1]) and not ROLE.search(lines[i - 2]) and len(lines[i - 2]) <= 60:
            cell = {"Name": lines[i - 2], "Designation": lines[i - 1], "Phone": ln}
            if i + 1 < len(lines) and re.match(r"^(ward\s*no\.?\s*)?\d{1,3}$", lines[i + 1], re.I):
                cell["Ward"] = re.sub(r"\D", "", lines[i + 1])
            rows.append(cell)
            pos.append({"text_line": i - 1, "line_text": lines[i - 2]})     # 1-based among the page's non-empty text lines
    return [{"caption": "people", "rows": rows, "pos": pos}] if len(rows) >= 2 else []
