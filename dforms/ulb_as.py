"""Assam: the state's shared urban body platform (UDD / Directorate of Municipal Administration, built by Sumato), one site per body
at https://<subdomain>.assamurban.in. 103 bodies (municipal boards, town committees and Silchar Municipal Corporation; the list at
https://assamurban.in/ulb, saved in seeds/raw/assam-assamurban-ulb.html on 2026-11-09). Guwahati Municipal Corporation is not on it.

Each body site has two server-rendered pages (Laravel, the same template everywhere), read in one queue item per body:
- /office-staff: cards (h3 name, then <p> lines: post category, mobile, "Ward No. ...", section). The Executive Officer is the card
  with the post "Executive Officer"; staff cards carry the category "Office Staff" and the real post in the last line
  ("JUNIOR ENGINEER, M.P.I. SECTION"). One record per card. Silchar: about 70 cards.
- /members: the elected board, the same cards (name, post, mobile, "Ward No. n"). Only the Chairman / Chairperson and the Vice
  Chairman are kept: the other members are "Ward Commissioner" (ward councillors; role_of() would read "commissioner" as the head).
  Many bodies show "No members found." (Silchar on 2026-11-11).
- The footer gives the body's office address, phone and email: they go on the Executive Officer's record (address, office_phone,
  office_email) and, when the page has no Executive Officer card, on an "Office" record.
/key-persons loads its list through a Livewire call (a signed component snapshot): not used.
Pages show no date. They answer from outside India (checked from Germany 2026-11-11). Area = the body name as the platform's list
writes it, with the type word split off into body_type ("Barpeta Rd.MB" -> area "Barpeta Rd.", body_type "MB"; "Lakhipur MB(Cachar)"
-> "Lakhipur (Cachar)"; the list's own text is kept in list_name): sql/86 compares civic.skel() of the area, and a trailing "MB"
made 10 bodies fail. District = the platform's district (older names: Karimganj, Morigaon).
Card names often carry the post or the service after a comma ("Dayaram Nath , Peon", "KAKOLI DAS, AUAS"): split_name() keeps the
name and gives the rest as the post (cards whose post is only "Office Staff"), "designation" (when the card has its own post),
"service" (AUAS, AUFS, AUES, ...) or "note" (a remark in brackets). Placeholders ("N/A", "A/A"), fake numbers (9999999999,
1234567890) and the PIN code in the footer phone ("Barpeta-781301") are left out; a footer with a template e-mail (@example.net)
also has a template address and number ("1057 Brekke Well", Hamren), so none of it is used.
"""
import re

from dforms import _esw, _ulb
import provenance

METHOD = "html cards (h3.font-semibold + p lines; office from the page footer)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_as"
STATE = "AS"
INDEX = "https://assamurban.in/ulb"
# district -> "subdomain=name; ..." as the platform's list writes them (seeds/raw/assam-assamurban-ulb.html, the TEST MB row left out)
BODIES = {
    "Baksa": "goreswar=Goreswar MB",
    "Barpeta": "barpeta=Barpeta MB; howly=Howly MB; sarthebari=Sarthebari MB; barpetaroad=Barpeta Rd.MB; sorbhog=Sorbhog MB; "
               "pathsala=Pathsala MB; patacharkuchi=Patacharkuchi MB",
    "Biswanath": "gohpur=Gohpur MB; biswanathchariali=B. Chariali MB; sootea=Sootea MB",
    "Bongaigaon": "bongaigaon=Bongaigaon MB; abhayapuri=Abhayapuri MB",
    "Cachar": "silchar=Silchar Municipal Corporation; lakhipurcachar=Lakhipur MB(Cachar); sonai=Sonai MB",
    "Charaideo": "sonari=Sonari MB; moran=Moran MB",
    "Chirang": "bijni=Bijni MB; basugaon=Basugaon MB; kajalgaon=Kajalgaon MB",
    "Darrang": "mangaldoi=Mangaldoi MB; kharupetia=Kharupetia MB; sipajhar=Sipajhar MB",
    "Dhemaji": "dhemaji=Dhemaji MB; silapathar=Silapathar MB",
    "Dhubri": "dhubri=Dhubri MB; gauripur=Gauripur MB; bilasipara=Bilasipara MB; chapar=Chapar MB; sapatgram=Sapatgram MB; "
              "golukganj=Golukganj MB",
    "Dibrugarh": "dibrugarh=Dibrugarh MB; naharkatia=Naharkatia MB; chabua=Chabua MB; namrup=Namrup MB",
    "Dima Hasao": "haflong=Haflong MB; mahur=Mahur MB; maibong=Maibong MB; umrangshu=Umrangshu MB",
    "Goalpara": "goalpara=Goalpara MB; lakhipur=Lakhipur MB(Goalpara)",
    "Golaghat": "golaghat=Golaghat MB; dergaon=Dergaon MB; bokakhat=Bokakhat MB; sarupathar=Sarupathar MB; barpathar=Barpathar MB",
    "Hailakandi": "hailakandi=Hailakandi MB; lala=Lala MB",
    "Hojai": "lanka=Lanka MB; hojai=Hojai MB; doboka=Doboka MB; lumding=Lumding MB",
    "Jorhat": "jorhat=Jorhat MB; moriani=Moriani MB; titabar=Titabar MB; teok=Teok MB",
    "Kamrup": "palasbari=Palasbari MB; northguwahati=N.Guwahati MB; rangia=Rangia MB",
    "Karbi-Anglong": "diphu=Diphu MB; dokmoka=Dokmoka MB; howaraghat=Howaraghat MB; bokajan=Bokajan MB; bokolia=Bokolia MB; "
                     "langhin=Langhin MB",
    "Karimganj": "karimganj=Karimganj MB; badarpur=Badarpur MB; ramkrishnanagar=Ramkrishnanagar MB",
    "Kokrajhar": "kokrajhar=Kokrajhar MB; gossaigaon=Gossaigaon MB; fakiragram=Fakiragram MB",
    "Lakhimpur": "nlakhimpur=N.Lakhimpur MB; bihpuria=Bihpuria MB; dhakuakhana=Dhakuakhana MB; narayanpur=Narayanpur MB",
    "Morigaon": "morigaon=Morigaon MB",
    "Nagaon": "nagaon=Nagaon MB; kampur=Kampur MB; raha=Raha MB; dhing=Dhing MB",
    "Nalbari": "nalbari=Nalbari MB; tihu=Tihu MB",
    "Sivasagar": "sibsagar=Sibsagar MB; nazira=Nazira MB; amguri=Amguri MB; simaluguri=Simaluguri MB; demow=Demow MB",
    "Sonitpur": "tezpur=Tezpur MB; dhekiajuli=Dhekiajuli MB; rangapara=Rangapara MB; jamugurihat=Jamugurihat MB",
    "Tinsukia": "tinsukia=Tinsukia MB; doomdooma=Doom Dooma MB; makum=Makum MB; digboi=Digboi MB; margherita=Margherita MB; "
                "chapakhowa=Chapakhowa MB",
    "Udalguri": "udalguri=Udalguri MB; tangla=Tangla MB",
    "West Karbi-Anglong": "hamren=Hamren MB; donkamokam=Donkamokam MB; baithalangso=Baithalangso MB",
}
KEEP_MEMBER = re.compile(r"(?i)\b(chair|vice|president)")       # chairman / chairperson / vice chairman; not ward commissioners
TYPE = re.compile(r"(?i)^(.*?)\s*\b(MB|Municipal Corporation)\b\s*(\(.*\))?$")
STAFF = re.compile(r"(?i)^(office\s*staff|staff|employee|others?)$")


PLACEHOLDER = re.compile(r"(?i)^(n\s*/?\s*a|a\s*/\s*a|nil|none|null|not available|-+|\.+)$")
SERVICE = re.compile(r"^\(?\s*(A\.?U\.?A\.?S|A\.?U\.?F\.?S|A\.?U\.?E\.?S|A\.?U\.?S|A\.?C\.?S|A\.?F\.?S)\.?\s*\)?\.?$", re.I)
TEMPLATE_MAIL = re.compile(r"(?i)@example\.(com|net|org)\b")


def real(s):
    """'' for page placeholders ('N/A', 'A/A', '-')."""
    s = _esw.clean(s)
    return "" if PLACEHOLDER.match(s) else s


def fake_number(n):
    d = re.sub(r"\D", "", n)
    return len(set(d)) == 1 or d in ("1234567890", "0123456789", "9876543210")


def good_phones(s, pins=()):
    """_esw.phones() without fake numbers and PIN codes."""
    out = [x for x in (_esw.phones(s) or "").split(", ") if x and not fake_number(x)
           and not (re.fullmatch(r"\d{6}", x) and (x in pins or x.startswith("78")))]
    return ", ".join(out)


def split_name(name):
    """'Dayaram Nath , Peon' -> ('Dayaram Nath', {'designation': 'Peon'}); 'KAKOLI DAS, AUAS' -> ('KAKOLI DAS', {'service': 'AUAS'});
    'Parag Dutta, (Already Retired ...)' -> ('Parag Dutta', {'note': 'Already Retired ...'})."""
    name = real(name)
    if "," not in name:
        return name, {}
    head, tail = (_esw.clean(x).strip(" ,.") for x in name.split(",", 1))
    if not head or not tail:
        return head or tail, {}
    if SERVICE.match(tail):
        return head, {"service": re.sub(r"[().\s]", "", tail).upper()}
    if tail.startswith("(") and tail.endswith(")"):
        return head, {"note": _esw.clean(tail[1:-1]).strip(" ,")}
    return head, {"designation": tail}


def items(get=None):
    out = []
    for district, s in BODIES.items():
        for part in s.split("; "):
            sub, name = part.split("=", 1)
            out.append({"key": f"{MODULE}-{sub}", "payload": {"reader": MODULE, "url": f"https://{sub}.assamurban.in/office-staff",
                                                             "members": f"https://{sub}.assamurban.in/members", "body": name,
                                                             "district": district, "state": STATE, "india_only": False}})
    return out


def split_type(name):
    """'Lakhipur MB(Cachar)' -> ('Lakhipur (Cachar)', 'MB'); 'Silchar Municipal Corporation' -> ('Silchar', 'Municipal Corporation')."""
    m = TYPE.match(_esw.clean(name))
    if not m or not m.group(1):
        return _esw.clean(name), None
    return _esw.clean(f"{m.group(1)} {m.group(3) or ''}"), m.group(2)


def blank(s):
    s = _esw.clean(s)
    return "" if re.fullmatch(r"[.\-–\s*]*", s) else s


def cards(html, where=None):
    """[(name, [p lines])] of the person cards in the page body (the footer's h3 headings are left out). where: a list; when
    given, it gets {"selector": "h3.font-semibold", "card": n} per card (n counts the page's h3.font-semibold)."""
    soup = _esw.soup(html)
    out = []
    for n, h in enumerate(soup.find_all("h3", class_="font-semibold"), 1):
        if h.find_parent("footer"):
            continue
        if where is not None:
            where.append({"selector": "h3.font-semibold", "card": n})
        lines = [blank(p.get_text(" ")) for p in h.find_next_siblings("p")]
        out.append((blank(h.get_text(" ")), [x for x in lines if x]))
    return out


def footer(html):
    """(address, phone, email) of the body office from the page footer."""
    soup = _esw.soup(html)
    f = soup.find("footer")
    if not f:
        return "", "", ""
    addr = f.find("div", class_="mb-2")
    text = f.get_text(" | ")
    top = text.split("Quick")[0]
    address = _esw.clean(addr.get_text(" ")) if addr else ""
    if TEMPLATE_MAIL.search(top):                    # the template's sample footer (fake address, number and e-mail)
        return "", "", ""
    pins = set(re.findall(r"(?<!\d)(\d{6})(?!\d)", address))
    top = re.sub(r"(?i)pin\s*:?-?\s*\d{6}|(?<=[A-Za-z])\s*-\s*\d{6}(?!\d)", " ", top)
    return address, good_phones(top, pins), _esw.emails(top)


def split(lines):
    """card lines -> (category, phone, ward, detail)"""
    cat, phone, ward, rest = "", "", "", []
    for i, x in enumerate(lines):
        if i == 0:
            cat = x
        elif not phone and re.fullmatch(r"[\d\s+,/-]{6,}", x):
            phone = good_phones(x)
        elif re.match(r"(?i)^ward\s*no", x):
            ward = _esw.clean(re.sub(r"(?i)^ward\s*no\.?\s*(ward\s*no\.?)?", "", x))
        else:
            rest.append(x)
    return real(cat), phone, ward, real(", ".join(rest))


def parse(staff_html, members_html=None, body="", district=None, url="", members_url=""):
    recs, seen = [], set()
    head = None
    list_name, (body, btype) = body, split_type(body)
    common = {"district": district, "body_type": btype, "list_name": list_name}
    where = []
    for (name, lines), pos in zip(cards(staff_html, where), where):
        cat, phone, ward, detail = split(lines)
        name, more = split_name(name)
        post, section = (detail, None) if STAFF.match(cat) and detail else (cat or detail, detail if cat else None)
        des = more.pop("designation", None)
        if des and (not post or STAFF.match(post)):
            post = des                                   # "Dayaram Nath , Peon" on an "Office Staff" card: the post is Peon
        elif des and _esw.slug(des) != _esw.slug(post or ""):
            more["designation"] = des
        if not post or not (name or phone):
            provenance.skipped('skip: not post or not (name or phone)')
            continue
        recs.append(_ulb.record(MODULE, STATE, body, post, seen, name=name, phone=phone, source=url, **common,
                                section=section, ward=ward or None, src_url=url, src_pos=pos, **more))
        if head is None and recs[-1][1]["role"] == "head":
            head = len(recs) - 1
    where = []
    for (name, lines), pos in zip(cards(members_html or "", where), where):
        cat, phone, ward, detail = split(lines)
        name, more = split_name(name)
        more.pop("designation", None)
        if not KEEP_MEMBER.search(cat) or not (name or phone):
            provenance.skipped('skip: not KEEP_MEMBER.search(cat) or not (name or phone)')
            continue
        recs.append(_ulb.record(MODULE, STATE, body, cat, seen, name=name, phone=phone, source=members_url, **common,
                                ward=ward or None, src_url=members_url, src_pos=pos, **more))
    addr, ophone, oemail = footer(staff_html)
    if head is not None:
        rid, d = recs[head]
        d.update({k: v for k, v in (("address", addr), ("office_phone", ophone), ("office_email", oemail)) if v})
        if addr or ophone or oemail:
            d["src_pos"] = {**d.get("src_pos", {}), "office_from": "footer"}
    elif ophone or oemail:
        recs.append(_ulb.record(MODULE, STATE, body, "Office", seen, phone=ophone, email=oemail, source=url, **common,
                                address=addr or None, src_url=url, src_pos={"selector": "footer"}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"{_esw.slug(p['body'])}-office-staff", r.content)]
    m = get(p["members"]) if p.get("members") else None
    if m is not None:
        files.append(_esw.keep(MODULE, f"{_esw.slug(p['body'])}-members", m.content))
    recs = parse(r.text, m.text if m is not None else None, p["body"], p.get("district"), p["url"], p.get("members", ""))
    return recs, files, "" if recs else "no rows"
