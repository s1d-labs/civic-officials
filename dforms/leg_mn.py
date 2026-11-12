"""Manipur: members of the 12th Legislative Assembly (2022-) with party, addresses, email and phone, from the member profiles
of the assembly site (assembly.mn.gov.in/members/profile/<slug>; the list assembly.mn.gov.in/members names the 60 slugs, two of
them "...-vacant"). Answers from Germany too. The assembly is in suspended animation (President's rule since 13 February 2025);
its members keep their seats.

Profile ("bu-item" label / value pairs): Constituency ("23-Mayang Imphal"), Political Party, Date of Birth, Father's Name,
Permanent Address, Present Address, Email (written with HTML character references), Contact (phone), Position Held.
One queue item = one member profile. items(get) reads the list page for the slugs; without get it uses SLUGS (as read on
2026-11-11). Record ids: dept:leg_mn:MN-AC-<no>.
"""
import re

from dforms import _esw, _leg, _leg_se

METHOD = "html page (member profile: div.bu-item label / value)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_mn"
LIST = "https://assembly.mn.gov.in/members"
PROFILE = "https://assembly.mn.gov.in/members/profile/{}"
SLUGS = ["thokchom-lokeshwar-singh", "nongthombam-biren-singh", "leishangthem-susindro-meitei", "sheikh-noorul-hassan",
         "thongam-biswajit-singh", "lourembam-rameshwor-meetei", "thounaojam-shyamkumar", "khongbantabam-ibomcha",
         "khumukcham-joykisan-singh", "khwairakpam-raghumani-singh", "rajkumar-imo-singh", "nishikant-sapam",
         "yumnam-khemchand-singh", "thokchom-satyabrata-singh", "thangjam-arunkumar", "heikham-dingo-singh", "sorokhaibam-rajen-singh",
         "dr-sapam-ranjan-singh", "sapam-kunjakeswor-keba-singh", "karam-shyam", "sagolshem-kebi-devi", "khurajam-loken-singh",
         "kongkham-robindro-singh", "thounaojam-basanta-kumar-singh", "irengbam-nalini-devi", "konthoujam-govindas-singh",
         "thongam-shanti-singh", "tongbram-robindro-singh", "sanasam-premchandra-singh", "mohd-abdul-nasir", "okram-ibobi-singh",
         "keisham-meghachandra-singh", "thokchom-radheshyam-singh", "paonam-brojen-singh", "surjakumar-okram", "dr-ushem-deben-singh",
         "mayanglambam-rameshwar-singh", "dr-yumnam-radheshyam-singh", "kangujam-ranjit-singh", "achab-uddin", "ss-olish",
         "letpao-haokip", "leishiyo-keishing", "ram-muivah", "khashim-vashum", "kimneo-haokip-hangshing", "j-kumo-sha", "losii-dikho",
         "nemcha-kipgen", "haokholet-kipgen", "awangbow-newmai", "janghemlung-panmei", "dinganglung-gangmei", "ngursanglur-sanate",
         "letzamang-haokip", "lm-khaute", "paolienlal-haokip", "chinlunthang"]


def list_slugs(html):
    out = []
    for s in re.findall(r'/members/profile/([a-z0-9-]+)"', html):
        if s not in out and not s.endswith("-vacant"):
            out.append(s)
    return out


def items(get=None):
    slugs = SLUGS
    if get is not None:
        r = get(LIST)
        slugs = (list_slugs(r.text) if r is not None else []) or SLUGS
    return [{"key": f"{MODULE}-{s}", "payload": {"reader": MODULE, "url": PROFILE.format(s), "state": "MN", "slug": s,
                                               "india_only": False}} for s in slugs]


def parse(html, url):
    s = _esw.soup(html)
    f = {}
    for it in s.select("div.bu-item"):
        k, v = it.select_one(".bu-label"), it.select_one(".bu-value")
        if k and v:
            first = v.find("div")          # Political Party: the name, then the symbol image
            f[_esw.clean(k.get_text(" ")).lower()] = _esw.clean((first or v).get_text(" ")) if "party" in k.get_text().lower() \
                else _esw.cell_text(v).replace(" | ", ", ")
    m = re.match(r"\s*(\d+)\s*-\s*(.+)", f.get("constituency", ""))
    if not m:
        return []
    h = s.select_one("div.section-header h2") or s.find("title")
    nm = _leg_se.name(re.sub(r"\s*\|.*$", "", h.get_text(" ")) if h else "")
    no, cons = int(m.group(1)), _esw.clean(m.group(2))
    seat, note = _leg_se.seat("MN", no, cons)
    return [_leg.member(MODULE, "MN", "AC", seat, nm, constituency=cons, party=f.get("political party", ""), source=url,
                        mobile=f.get("contact", ""), email=f.get("email", ""), residence_address=f.get("present address", ""),
                        permanent_address=f.get("permanent address", ""), note=note,
                        house="Manipur Legislative Assembly (12th)", src_pos={"selector": "div.bu-item"})]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, p.get("slug", "member"), r.content)]
    recs = parse(r.text, p["url"])
    return recs, files, "" if recs else "no profile in the page"
