"""Sikkim: Power Department (Energy and Power, Government of Sikkim), power.sikkim.gov.in. Two kinds of pages, one queue item each:
- "officers": /visitor/listofofficers: one table SL No | Name | Designation | Place of Posting | Contact No.: the department's senior
  officers (PCE cum Secretary, CE, ACE, SE), about 35 rows, all posted at "Gangtok Power, HQ.". Level state.
- "cell": /visitor/divisioncell/<id> (2, 4-13: EHV, Accounts, SLDC, SDA, Mechanical, Maintenance HQ-I/II, Civil, Revenue-I..IV, Admin,
  IT, SREDA): one table DEPARTMENT | NAME OF OFFICER | DESIGNATION | CONTACT NO.; each row is one division / cell; its cells hold one
  <p> per officer, and the <p> of the same position in the next cell belong to the same officer (the page was typed in Word with one
  paragraph per line, empty paragraphs keep the lines level). Level from the post: SE -> circle, Divisional Engineer -> division,
  Assistant Engineer -> subdivision, Junior Engineer -> section; else division.
- "staff": /visitor/stafflists (2.4 MB): the full staff list, one table per circle (GANGTOK-HQ-I, -III, -IV, CIRCLE-EAST-I, -II,
  TEMI, LLHP, GYLASHING (WEST-I), SORENG (WEST-I)); Sr. No. | Name | Designation | Sub division | [E Mail ID] | Contact no. About 1,400
  people from SE down to JE, lineman, meter reader and office staff. The circle title is the table's first one-cell row, or the text
  just above the table. Level: SE / ACE -> circle, DE / EE -> division, AE / SDO -> subdivision, JE -> section (area = its
  sub-division), other staff -> the sub-division office when the row names one, else the circle office. No page date. Answers from abroad too (archive copy 2026-11-05).
Records "dept:power2_sikkim:<page>:<area>:<post>:<name>".
"""
import re

from bs4 import BeautifulSoup

from dforms import _power, _util2
from dforms._power import tr_pos
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "power2_sikkim"
BASE = "https://power.sikkim.gov.in/visitor/"
CELLS = (2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)


def items(get=None):
    out = [{"key": f"{MODULE}:officers", "payload": {"reader": MODULE, "page": "officers", "url": BASE + "listofofficers", "state": "SK",
                                                     "india_only": False}}]
    out.append({"key": f"{MODULE}:staff", "payload": {"reader": MODULE, "page": "staff", "url": BASE + "stafflists", "state": "SK",
                                                      "india_only": False}})
    out += [{"key": f"{MODULE}:cell-{c}", "payload": {"reader": MODULE, "page": "cell", "url": f"{BASE}divisioncell/{c}", "state": "SK",
                                                       "india_only": False}} for c in CELLS]
    return out


def paras(td):
    ps = td.find_all("p")
    if not ps:
        return [" ".join(td.get_text(" ", strip=True).split())]
    return [" ".join(p.get_text(" ", strip=True).split()) for p in ps]


def level(post):
    p = (post or "").upper()
    if re.search(r"JUNIOR\s+ENG|\bJ\.?E\b", p):
        return "section"
    if re.search(r"ASSISTANT\s+ENG|\bA\.?E\b|\bSDO\b", p):
        return "subdivision"
    if re.search(r"SUPERINTENDING|\bS\.?E\b", p):
        return "circle"
    if re.search(r"CHIEF|\bC\.?E\b|\bACE\b|\bPCE\b|SECRETARY|DIRECTOR", p):
        return "state"
    return "division"


def staff_level(post, subdiv):
    p = " " + re.sub(r"[^A-Z]+", " ", (post or "").upper()) + " "
    if re.search(r" (S E|SE|SUPERINTEND\w*|ACE|ADDL CHIEF|CHIEF ENGINEER|CE) ", p):
        return "circle"
    if re.search(r" (D E|DE|EE|EXECUTIVE ENGINEER|DIVISIONAL ENGINEER) ", p):
        return "division"
    if re.search(r" (A E|AE|ASSISTANT ENGINEER|SDO) ", p):
        return "subdivision"
    if re.search(r" (J E|JE|JUNIOR ENGINEER) ", p):
        return "section"
    return "subdivision" if subdiv else "circle"


def staff(soup, out):
    for tb in soup.find_all("table"):
        title, head = None, None
        for tr in tb.find_all("tr"):
            out.src = {"src_pos": tr_pos(tr)}
            c = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all(["td", "th"])]
            filled = [x for x in c if x]
            if len(filled) == 1 and not head and not re.fullmatch(r"[\d\s]+", filled[0]):
                title = filled[0]
                continue
            if any(re.search(r"designation", x, re.I) for x in c):
                head = [x.lower() for x in c]
                continue
            if not head or len(c) < len(head) - 1:
                provenance.skip_row(tr, 'skip: not head or len(c) < len(head) - 1')
                continue
            if title is None:
                prev = tb.find_previous(string=lambda t: t and re.search(r"[A-Z]{3}", t) and not re.search(r"\d{6}", t))
                title = " ".join((prev or "Power Department").split())
            d = dict(zip(head, c))
            name = _util2.person(d.get("name"))
            post = _power.clean(d.get("designation"))
            if not (name or post):
                provenance.skip_row(tr, 'skip: not (name or post)')
                continue
            sub = _power.clean(d.get("sub division"))
            lvl = staff_level(post, sub)
            area = sub if (sub and lvl in ("section", "subdivision")) else title
            par = {"circle": title} if area != title else None
            if par and lvl == "section" and sub:
                par["subdivision"] = sub
            out.add(f"staff:{title}:{sub}:{post}:{name}", lvl, area, post=post, name=name,
                    phone_=_util2.tel(d.get("contact no.") or ""), email_=_power.email(d.get("e mail id")), parents=par)


def parse(html, page, url):
    soup = BeautifulSoup(html, "lxml")
    if page == "staff":
        out = _power.Out(MODULE, "SK", url, discom="Power Department, Sikkim")
        staff(soup, out)
        out.src = {}
        return out.recs
    out = _power.Out(MODULE, "SK", url, discom="Power Department, Sikkim")
    heads = [h.get_text(" ", strip=True) for h in soup.find_all(["h3", "h4"])]
    title = next((h for h in heads if h and h != "Division / Cells"), None)
    for tb in soup.find_all("table"):
        head = None
        for tr in tb.find_all("tr"):
            out.src = {"src_pos": tr_pos(tr)}
            tds = tr.find_all(["td", "th"])
            c = [" ".join(td.get_text(" ", strip=True).split()) for td in tds]
            if not head:
                if any(re.search(r"designation", x, re.I) for x in c):
                    head = [x.lower() for x in c]
                continue
            if page == "officers":
                if len(c) < 4 or not c[1]:
                    provenance.skip_row(tr, 'skip: len(c) < 4 or not c[1]')
                    continue
                d = dict(zip(head, c))
                post = d.get("designation") or None
                out.add(f"officers:{c[1]}:{post}", "state", _power.clean(d.get("place of posting")) or "Gangtok Power HQ",
                        post=post, name=_util2.person(c[1]), phone_=_power.phone(*re.split(r"\s*/\s*", d.get("contact no.", ""))),
                        district="Gangtok")
            else:
                if len(tds) < 3:
                    provenance.skip_row(tr, 'skip: len(tds) < 3')
                    continue
                cols = [paras(td) for td in tds]
                area = " ".join(cols[0]).strip() or title
                names, posts = cols[1], cols[2]
                phones = cols[3] if len(cols) > 3 else []
                for i, nm in enumerate(names):
                    nm = _util2.person(nm)
                    post = _power.clean(posts[i]) if i < len(posts) else None
                    if not nm and not post:
                        continue
                    ph = _power.phone(phones[i]) if i < len(phones) else None
                    out.add(f"cell:{area}:{post}:{nm}", level(post), area, post=post, name=nm, phone_=ph,
                            parents={"division": title} if title and title != area else None, district="Gangtok")
    out.src = {}
    return out.recs


def fetch(p, get):
    page = p.get("page", "officers")
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    name = page if page in ("officers", "staff") else "cell-" + url.rstrip("/").rsplit("/", 1)[-1]
    recs = parse(r.text, page, url)
    return recs, [_power.raw(MODULE, name, r.content, "html")], "" if recs else "no rows"
