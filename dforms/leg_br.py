"""Bihar: MLAs of the 18th Bihar Vidhan Sabha (2025-) from the assembly's "Know your MLA" page
(vidhansabha.bihar.gov.in/Knowyourmla.html). Answers only from India (Germany gets no connection).

One HTML table, one row per seat (243): AC number, photo, constituency, name, gender, party, mobile. The page also has an
"Email ID" column that is commented out in the HTML (<!--<td>mla-vnagar-bih@nic.in</td>-->): the official NIC address of the
seat, served publicly in the page source. This reader keeps it as email (extra "email_note" says so).
No address, no residence, no constituency office. One queue item = the whole page.
"""
import re

from dforms import _leg

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_br"
URL = "https://vidhansabha.bihar.gov.in/Knowyourmla.html"
EMAIL_NOTE = "from a hidden (commented-out) column of the page"


def items(get=None):
    return [{"key": "leg_br-list", "payload": {"reader": MODULE, "url": URL, "state": "BR", "india_only": True}}]


def parse(html, url=URL):
    from bs4 import BeautifulSoup
    html = html.replace("\u200d", "").replace("\u200c", "")   # _esw.clean turns ZWJ/ZWNJ into spaces inside Devanagari words
    html = re.sub(r"<!--\s*<td>([^<]*)</td>\s*-->", r"<td class='hidden-email'>\1</td>", html)   # keep the hidden email cell
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for tr in soup.select("tbody tr"):
        tds = tr.find_all("td", recursive=False)
        cells = [_leg.clean(td.get_text(" ")) for td in tds]
        if len(cells) < 7 or not cells[0].strip().isdigit():
            continue
        no, cons, name, gender, party, mobile = cells[0], cells[2], cells[3], cells[4], cells[5], cells[6]
        email = cells[7] if len(cells) > 7 else ""
        seat, note = _leg.ac_seat("BR", no, cons)
        recs.append(_leg.member(MODULE, "BR", "AC", seat, name, constituency=cons, party=party, source=url, mobile=mobile,
                                email=email, seat_no=int(no), gender=gender.strip("_ "), note=note,
                                email_note=EMAIL_NOTE if _leg.emails(email) else ""))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "list", r.content, "html")]
    recs = parse(r.content.decode("utf-8", "replace"), p["url"])
    return recs, files, "" if recs else "no members"
