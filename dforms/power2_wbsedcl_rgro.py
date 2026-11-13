"""West Bengal: WBSEDCL officers by name, and the customer care centres; www.wbsedcl.in (times out from Germany: India only).
power2_wbsedcl reads Imp_Phone_Number.html (office phones). This module reads two other pages, one queue item each:
- "rgro": /irj/go/km/docs/internet/new_website/Grievance_Redressal_for_consumers.html, "Contact Information of Regional Grievance
  Redressal Officers": one table Sl No. | Name of the Region | Name of RGRO | Designation | Address | Telephone | Mobile Number
  (Official) | E-mail. 23 regions (the regional offices sit between zone and division: level circle). The RGRO is a named
  engineer (S.E. / D.E.) of the regional office, with landline, official mobile and e-mail.
- "ccc": /irj/go/km/docs/internet/new_website/Contact_Customer_Care.html, "Customer Care Centres": one table DIVISION | CUSTOMER
  CARE CENTRE | TELEPHONE. 165 CCCs (the section-level supply offices) of the southern divisions (Bidhannagar .. Singur-Haripal);
  phones only, no names. Level section, parent division.
No page date. Records "dept:power2_wbsedcl_rgro:rgro:<region>" and "dept:power2_wbsedcl_rgro:ccc:<division>:<ccc>".
"""
import re

from bs4 import BeautifulSoup

from dforms import _power, _util2_east
from dforms._power import tr_pos
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "power2_wbsedcl_rgro"
BASE = "https://www.wbsedcl.in/irj/go/km/docs/internet/new_website/"
PAGES = {"rgro": "Grievance_Redressal_for_consumers.html", "ccc": "Contact_Customer_Care.html"}
HEADS = {"region": r"region", "name": r"name of rgro|^name", "post": r"designation", "address": r"address", "tel": r"telephone",
         "mobile": r"mobile", "email": r"e-?mail"}


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "page": k, "url": BASE + v, "state": "WB", "india_only": True}}
            for k, v in PAGES.items()]


def _phones(s):
    """The number(s) as the page writes them ('2359-9215/2337-0887', '(03218)203131/132'); a note like '(No Landline)' is dropped.
    Kolkata numbers have 8 digits without the 033 code, so the shared phone() rule (5+ digits in a run) is not used."""
    s = _power.clean(re.sub(r"\((?=[A-Za-z])[^)]*\)", " ", s or ""))
    return s if s and len(re.sub(r"\D", "", s)) >= 7 else None


def _title(s):
    """'BIDHANNAGAR - II' -> 'Bidhannagar - II' (roman numerals stay upper case)."""
    return " ".join(w if re.fullmatch(r"[IVX]+", w) else w.capitalize() for w in re.split(r" ", s)) if s else s


def parse(html, page, url):
    soup = BeautifulSoup(html, "lxml")
    out = _power.Out(MODULE, "WB", url, discom="WBSEDCL")
    for tb in soup.find_all("table"):
        head = None
        for tr in tb.find_all("tr"):
            out.src = {"src_pos": tr_pos(tr)}
            c = _power.cells(tr)
            if head is None:
                if page == "rgro" and any(re.search(r"RGRO", x) for x in c):
                    head = _util2_east.head_map(c, HEADS)
                elif page == "ccc" and any(re.search(r"CUSTOMER CARE", x, re.I) for x in c):
                    head = {"division": 0, "ccc": 1, "tel": 2}
                continue
            g = {k: c[i] if i < len(c) else "" for k, i in head.items()}
            if page == "rgro":
                region = _power.clean(re.sub(r"\s*Regional\s+office$|\s*Region$", "", g.get("region", ""), flags=re.I))
                if not region:
                    provenance.skip_row(tr, 'skip: not region')
                    continue
                out.add(f"rgro:{region}", "circle", region, post=f"Regional Grievance Redressal Officer ({_power.clean(g.get('post'))})",
                        name=_util2_east.person(g.get("name")),
                        phone_=", ".join(x for x in (_phones(g.get("tel")), _power.phone(g.get("mobile"))) if x) or None,
                        email_=_power.email(g.get("email")), address=g.get("address"))
            else:
                div, ccc = _power.clean(g.get("division")), _power.clean(g.get("ccc"))
                if not ccc:
                    provenance.skip_row(tr, 'skip: not ccc')
                    continue
                out.add(f"ccc:{div}:{ccc}", "section", _title(ccc), post="Customer Care Centre (Station Manager)",
                        phone_=_phones(g.get("tel")), parents={"division": "-".join(_title(x) for x in div.split("-"))} if div else None)
    out.src = {}
    return out.recs


def fetch(p, get):
    page = p.get("page", "rgro")
    url = p.get("url") or BASE + PAGES[page]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, page, url)
    return recs, [_power.raw(MODULE, page, r.content, "html")], "" if recs else "no rows"
