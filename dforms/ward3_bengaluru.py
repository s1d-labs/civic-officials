"""The five Bengaluru city corporations of the Greater Bengaluru Authority (GBA, since 2 Sep 2025): West, North, South, East,
Central (bengaluru<city>.karnataka.gov.in). Each site is a single-page app (React): its "<City> City Corporation Officers" block and
the "Zone Offices" footer are in the app's script bundle (/static/js/main.<hash>.js, named in /home):
  - one officer object per site, {TOP: [...], ZONE_01: [...], ZONE_02: [...]} (North: NORTH_TOP, South: SOUTH_TOP), each entry
    {name: <locale key>, designation: <locale key>, image, email}: TOP = Commissioner and Additional Commissioners (development,
    revenue), ZONE_0n = the Joint Commissioner and the Deputy Commissioner of zone n;
  - two locale objects (English, Kannada) with the same keys: the officer's name and post under its keys, and zone<n>_title /
    zone<n>_address for the zone offices.
Live samples from Mumbai (dev-vps-3) 2026-11-13; not in archive.s1d.me; the sites show no date. bbmp.gov.in and site.bbmp.gov.in
did not answer (time-out / refused) on 2026-11-13. The pages do not say which wards each zone holds: zone records have no "wards".
A name key with no English text in the locale (some entries are placeholders) gives a record with post and email but no name.
Emails are kept as written (one ends ".comm" on the site).
Records: zone officers and zone offices at level "zone" (area "Zone-1" / "Zone-2"), the Commissioner and Additional
Commissioners at level "body". Two requests per item: /home, then the bundle. Record ids:
dept:ward3_bengaluru:<city>:<zone-n | top>:<post slug>[:<n>].
"""
import json
import re

from dforms import _esw, _ward

METHOD = "js bundle (officer object and locale objects read by regex)"     # source trail (provenance.py)

MODULE = "ward3_bengaluru"
STATE, DISTRICT = "KA", "Bengaluru Urban"
# city key -> (host, body, LGD code)
BODIES = {
    "west": ("bengaluruwest.karnataka.gov.in", "Bengaluru West City Corporation", "305854"),
    "north": ("bengalurunorth.karnataka.gov.in", "Bengaluru North City Corporation", "305853"),
    "south": ("bengalurusouth.karnataka.gov.in", "Bengaluru South City Corporation", "305852"),
    "central": ("bengalurucentral.karnataka.gov.in", "Bengaluru Central City Corporation", "305851"),
    "east": ("bengalurueast.karnataka.gov.in", "Bengaluru East City Corporation", "305850"),
}
OFFICERS = re.compile(r"=\{((?:[A-Z]+_)?TOP:\[.*?\])\};", re.S)
GROUP = re.compile(r"((?:[A-Z]+_)?TOP|ZONE_\d+):\[(.*?)\]", re.S)
ENTRY = re.compile(r"\{([^{}]*)\}")
FIELD = re.compile(r'(\w+):"((?:[^"\\]|\\.)*)"')
PAIR = re.compile(r'"([^"\\]{1,80})":"((?:[^"\\]|\\.)*)"')
KANNADA = re.compile(r"[ಀ-೿]")
POSTS = {"commissioner": "Commissioner", "add_comm_dev": "Additional Commissioner (Development)",
         "add_comm_rev": "Additional Commissioner (Revenue)", "add_comm_rev_ic": "Additional Commissioner (Revenue) (In charge)",
         "joint_commissioner": "Joint Commissioner", "deputy_commissioner": "Deputy Commissioner",
         "deputy_commissioner_ic": "Deputy Commissioner (In charge)"}


def items(get=None):
    return [{"key": f"{MODULE}-{c}", "payload": {"reader": MODULE, "url": f"https://{h}/home", "state": STATE, "city": c}}
            for c, (h, _, _) in BODIES.items()]


def bundle_url(html, base):
    m = re.search(r'src="(/static/js/main\.[0-9a-f]+\.js)"', html)
    return re.match(r"https?://[^/]+", base).group(0) + m.group(1) if m else None


def _text(v):
    try:
        v = json.loads('"' + v + '"')
    except ValueError:
        pass
    return v.replace("\\n", " ")


def locales(js):
    """(English {key: text}, Kannada {key: text}): every "key":"text" pair of the bundle, sorted by script (first one wins)."""
    en, kn = {}, {}
    for m in PAIR.finditer(js):
        v = _text(m.group(2))
        (kn if KANNADA.search(v) else en).setdefault(m.group(1), v)
    return en, kn


def officers(js):
    """[(group, index in group, {name, designation, email}, offset)] of the officer object."""
    m = OFFICERS.search(js)
    if not m:
        return []
    out = []
    for g in GROUP.finditer(m.group(1)):
        for i, e in enumerate(ENTRY.finditer(g.group(2)), 1):
            f = {k: _text(v) for k, v in FIELD.findall(e.group(1))}
            out.append((g.group(1), i, f, m.start(1) + g.start(2) + e.start()))
    return out


def _name(s):
    s = _esw.clean(s)
    return "" if re.fullmatch(r"[-–.\s]*", s) else s


def parse(js, p, source=None):
    city = p["city"]
    host, body, lgd = BODIES[city]
    en, kn = locales(js)
    seen, recs = set(), []
    kw = dict(body=body, lgd=lgd, state=STATE, district=DISTRICT, source=source or p["url"], page=p["url"])
    for group, i, f, off in officers(js):
        zone = re.match(r"ZONE_0*(\d+)", group)
        z = f"Zone-{zone.group(1)}" if zone else None
        dkey = f.get("designation", "")
        post = POSTS.get(re.sub(r"_zone_\d+$", "", dkey)) or _esw.clean(en.get(dkey, dkey)).title()
        nkey = f.get("name", "")
        name = _name(en.get(nkey, ""))
        email = re.sub(r"\s+", "", f.get("email", ""))
        if not (name or email):
            continue
        area = z or body
        recs.append(_ward.record(MODULE, f"{city}:{_esw.slug(z) if z else 'top'}:{_esw.slug(post)}", seen,
                                 level="zone" if z else "body", area=area, zone=z, post=post,
                                 post_regional=_name(kn.get(dkey, "")) or None, name=name,
                                 name_regional=_name(kn.get(nkey, "")) or None, email=email,
                                 role="head" if z and dkey.startswith("joint") else None, wing="administration",
                                 vacant=None, **kw,
                                 src_pos={"object": group, "index": i, "offset": off, "name_key": nkey}))
    for n in sorted({int(x) for x in re.findall(r"zone(\d+)_address", " ".join(en))}):
        addr = en.get(f"zone{n}_address")
        if not addr:
            continue
        z = f"Zone-{n}"
        recs.append(_ward.record(MODULE, f"{city}:{_esw.slug(z)}:zone-office", seen, level="zone", area=z, zone=z,
                                 post="Zone Office", address=addr.replace("\n", " "),
                                 address_regional=_name(kn.get(f"zone{n}_address", "")) or None, wing="administration",
                                 role="staff", **kw, src_pos={"object": "locale", "key": f"zone{n}_address"}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (home page)"
    js_url = bundle_url(r.text, p["url"])
    if not js_url:
        return [], [_esw.keep(MODULE, f"{p['city']}-home", r.content)], "no script bundle in the home page"
    j = get(js_url)
    if j is None:
        return [], [], "no answer (script bundle)"
    recs = _ward.tag(parse(j.text, p, source=js_url), j, js_url)
    return recs, [_esw.keep(MODULE, f"{p['city']}-bundle", j.content, "js")], "" if recs else "no officer object in the bundle"
