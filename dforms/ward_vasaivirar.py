"""Vasai-Virar City Municipal Corporation (vvcmc.in): the Assistant Commissioners of its 9 ward committees (prabhag samiti A-I)
and the Deputy Commissioners of its 4 circles (parimandal) with the ward committees each circle holds. One page, /contacts/
(WordPress; answers from Germany; live sample 2026-11-11, not in archive.s1d.me), in Marathi: one table per rank (heading before
it: अतिरिक्त महापालिका आयुक्त, महापालिका उपायुक्त, सहायक आयुक्त), rows "<no> | Photo | key | value" with keys नाव (name), पदनाम (post),
संपर्क क्र. / Contact No. (phone), ई-मेल आयडी (email), कार्यक्षेत्र (jurisdiction), कर्तव्य (duties).
Records: the Assistant Commissioners (level "zone", area = "Prabhag Samiti <letter>" from the jurisdiction) and the Deputy
Commissioners whose duties name a circle (level "zone", area = "Parimandal <n>", extra key "samitis" = the committee letters).
The electoral prabhags of each committee are not on the page (no "wards" key). Names and posts are Marathi: name and
name_regional carry the same text; post is English, post_regional as written. Record ids: dept:ward_vasaivirar:<area slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_vasaivirar"
BODY, LGD, STATE, DISTRICT = "Vasai-Virar City Municipal Corporation", "251463", "MH", "Palghar"
URL = "https://vvcmc.in/contacts/"
LETTERS = {"अ": "A", "ए": "A", "बी": "B", "ब": "B", "सी": "C", "डी": "D", "ई": "E", "एफ": "F", "जी": "G", "एच": "H", "आय": "I"}
KEYS = {"नाव": "name", "पदनाम": "post", "संपर्क": "phone", "contact": "phone", "ई-मेल": "email", "कार्यक्षेत्र": "area", "कर्तव्य": "duty"}


def items(get=None):
    return [{"key": f"{MODULE}-contacts", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def samiti(text):
    """Ward committee letters named in a text: "प्रभाग समिती अ" / "प्रभाग समिती "बी"" / "प्रभाग समिती (D,G,H,I)"."""
    out = []
    for m in re.finditer(r"प्रभाग\s*समिती\s*[\"'“”(]*\s*([A-I](?:\s*,\s*[A-I])*|बी|सी|डी|एफ|जी|एच|आय|अ|ए|ई)(?![ऀ-ॿ])", text):
        for x in re.split(r"\s*,\s*", m.group(1)):
            x = LETTERS.get(x, x)
            if x not in out:
                out.append(x)
    return out


def people(html):
    soup = _esw.soup(html)
    out = []
    for t in soup.find_all("table"):
        rank = next((x.strip() for x in t.find_all_previous(string=True, limit=5) if x.strip()), "")
        cur = None
        for r in _esw.grid(t)[1:]:
            if len(r) < 4:
                continue
            key = next((v for k, v in KEYS.items() if r[2].lower().startswith(k)), None)
            if key == "name":
                cur = {"rank": rank}
                out.append(cur)
            if cur is not None and key:
                cur[key] = _esw.clean(r[3])
    return out


def parse(html, p):
    seen, recs = set(), []
    for x in people(html):
        name, post = x.get("name", ""), x.get("post", "")
        if "सहा" in x["rank"] or "सहा" in post:
            s = samiti(x.get("area", "") + " " + post)
            if not s:
                continue
            area = f"Prabhag Samiti {s[0]}"
            en = "Assistant Commissioner"
        else:
            m = re.search(r"परिमंड[ळल]\s*-?\s*(\d)", x.get("duty", ""))
            if not m:
                continue
            area = f"Parimandal {m.group(1)}"
            s = samiti(x["duty"])
            en = "Deputy Commissioner" if "उपायुक्त" in post else post
        recs.append(_ward.record(MODULE, f"{_esw.slug(area)}:{_esw.slug(x.get('email', '')) or len(recs)}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="zone", area=area, zone=area, post=en, post_regional=post,
                                 name=name, name_regional=name, phone=x.get("phone", ""), email=x.get("email", ""),
                                 samitis=s or None, jurisdiction=x.get("area") or None, wing="administration", source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "contacts", r.content)], "" if recs else "no officer tables"
