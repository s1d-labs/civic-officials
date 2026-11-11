"""Delhi: Delhi Jal Board Summer Action Plan 2026, one PDF per assembly constituency (delhijalboard.delhi.gov.in/sites/default/files/
inline-files/ac_<no>_<name>[_n].pdf, linked from /jalboard/summer-action-plan-2026; 68 files, ACs 38 and 40 have none). Answers from
Germany and India. Page 2 or 3 of each file holds the officer table: five columns "Name of CE", "Name of SE (C)", "Name of EE (C)",
"Name of AE (C)", "Name of JE (C)", each cell with name lines, a post line ("CE(Maintenance)-II", "SE (C)-11", "EE (C)-33") and a
mobile; a cell can hold two or more officers, and some files add rows under a heading (e.g. "PPP Area"). The rest of the file is
the colony-wise supply hours and the tanker list (kept in the bucket file, not parsed here). One queue item = one file.
Record ids: dept:water_dl:DL-AC-<no>:<ce|se|ee|ae|je>:<slug of the post or n>[:<slug of heading>]. Extra key "ac" = "DL-AC-<no>".
"""
import re

from dforms import _esw

MODULE = "water_dl"
INDEX = "https://delhijalboard.delhi.gov.in/jalboard/summer-action-plan-2026"
BASE = "https://delhijalboard.delhi.gov.in/sites/default/files/inline-files/"
FILES = ["ac_1_narela_0", "ac_2_burari_0", "ac_3_timarpur_1", "ac_4_adarsh_nagar_1", "ac_5_badli_1", "ac_6_rithala_1",
         "ac_7_bawana_1", "ac_8_mundka_1", "ac_9_kirari_0", "ac_10_sultan_majra", "ac_11_nangloi_jat_0", "ac_12_mangop_puri",
         "ac_13_rohini_0", "ac_14_shalimar_bagh_0", "ac_15_shakur_basti_0", "ac_16_tri_nagar_0", "ac_17_wazirpur_2",
         "ac_18_model_town_0", "ac_19_sadar_bazar_0", "ac_20_chandni_chowk_0", "ac_21_matia_mahal_0", "ac_22_balli_maran",
         "ac_23_karol_bagh_0", "ac_24_patel_nagar_0", "ac_25_moti_nagar_0", "ac_26_madipur_2", "ac_27_rajouri_garden_2",
         "ac_28_hari_nagar_2", "ac_29_tilak_nagar_2", "ac_30_janakpuri_2", "ac_31_vikas_puri", "ac_32_uttam_nagar_0",
         "ac_33_dwarka_0", "ac_34_matiala_0", "ac_35_najafgarh_0", "ac_36_bijwasan", "ac_37_palam_1", "ac_39_rajinder_nagar_1",
         "ac_41_jangpura_1", "ac_42_kasturba_nagar_1", "ac_43_malviya_nagar_1", "ac_44_r_k_puram_2", "ac_45_mehrauli_0",
         "ac_46_chhatarpur_1", "ac_47_deoli_1", "ac_48_ambedkar_nagar_1", "ac_49_sangam_vihar_0", "ac_50_greater_kailash_0",
         "ac_51_kalka", "ac_52_tughlakabad", "ac_53_badarpur_0", "ac_54_okhla_0", "ac_55_trilokpuri_0", "ac_56_kondli_0",
         "ac_57_patparganj_0", "ac_58_laxmi_nagar_0", "ac_59_vishwas_nagar_0", "ac_60_krishna_nagar_0", "ac_61_gandhi_nagar_0",
         "ac_62_shahdara_0", "ac_63_seemapuri_0", "ac_64_rohtas_nagar_0", "ac_65_seelampur_0", "ac_66_ghonda_0", "ac_67_babarpur_0",
         "ac_68_gokulpur", "ac_69_mustafabad_0", "ac_70_karawal_nagar_0"]
ROLES = ("ce", "se", "ee", "ae", "je")
LEVEL = {"ce": "zone", "se": "circle", "ee": "division", "ae": "subdivision", "je": "section"}
POSTNAME = {"ce": "Chief Engineer", "se": "Superintending Engineer", "ee": "Executive Engineer", "ae": "Assistant Engineer",
            "je": "Junior Engineer"}
PHONE = re.compile(r"^[\d\s/,-]{10,}$")
POST = re.compile(r"^(CE|SE|EE|AE|JE|ACE)\s*[\(\-]|^(CE|SE|EE|AE|JE)\b(?!\w)", re.I)
END = re.compile(r"Water Supply Hours|Fixed Supply Points|Name of Colony|Tanker", re.I)
ORG = "Delhi Jal Board"


def items(get=None):
    out = []
    for f in FILES:
        no = int(f.split("_")[1])
        out.append({"key": f"{MODULE}-ac{no}", "payload": {"reader": MODULE, "url": BASE + f + ".pdf", "state": "DL", "ac": no}})
    return out


def _runs(line):
    """(start column, text) of each run of text separated by 2+ spaces."""
    return [(m.start(), m.group(0).strip()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def _people(lines):
    """One cell's lines -> [{"name", "posts", "phones"}]: a name line after a phone starts the next officer."""
    out, cur = [], None
    for t in lines:
        t = _esw.clean(t)
        if not t or t.upper() in ("NA", "N/A", "-"):
            continue
        if PHONE.match(t):
            if cur is None:
                cur = {"name": [], "posts": [], "phones": []}
                out.append(cur)
            cur["phones"].append(t)
        elif POST.match(t) and cur is not None and not cur["phones"]:
            cur["posts"].append(t)
        elif POST.match(t) and cur is None:
            cur = {"name": [], "posts": [t], "phones": []}
            out.append(cur)
        else:
            if cur is None or cur["phones"] or cur["posts"]:
                cur = {"name": [], "posts": [], "phones": []}
                out.append(cur)
            cur["name"].append(t)
    return [p for p in out if p["name"] or p["phones"]]


def table(pages):
    """The officer table of one file: (AC heading, [(section heading or "", role, person)])."""
    for text in pages:
        lines = text.splitlines()
        hi = next((i for i, ln in enumerate(lines) if re.search(r"Name of\s+CE", ln) and re.search(r"Name of\s+JE", ln)), None)
        if hi is None:
            continue
        heading = next((_esw.clean(ln) for ln in lines[:hi][::-1] if "Assembly Constituency" in ln), "")
        starts = [m.start() for m in re.finditer(r"Name of", lines[hi])][:5]
        bounds = [(starts[i] + starts[i + 1]) / 2 for i in range(len(starts) - 1)]
        sections, sec = {"": [[] for _ in ROLES]}, ""
        for ln in lines[hi + 1:]:
            if END.search(ln):
                break
            runs = _runs(ln)
            if not runs:
                continue
            if len(runs) == 1 and not PHONE.match(runs[0][1]) and not POST.match(runs[0][1]) \
                    and min(abs(runs[0][0] - s) for s in starts) > 8:
                sec = runs[0][1]
                sections.setdefault(sec, [[] for _ in ROLES])
                continue
            for x, t in runs:
                col = sum(1 for b in bounds if x >= b)
                sections[sec][col].append(t)
        out = []
        for s, cols in sections.items():
            for role, cell in zip(ROLES, cols):
                for person in _people(_join(cell)):
                    out.append((s, role, person))
        return heading, out
    return "", []


def _join(cell):
    """Runs split inside one line ("Sh." + "SK Dahiya") are already in order; a lone title ("Sh.", "Smt.") joins the next run."""
    out = []
    for t in cell:
        if out and re.fullmatch(r"(Sh|Smt|Ms|Mr|Dr|Er)\.?", out[-1], re.I):
            out[-1] = f"{out[-1]} {t}"
        else:
            out.append(t)
    return out


def parse(pages, p):
    no = int(p.get("ac") or re.search(r"ac_(\d+)_", p["url"]).group(1))
    heading, rows = table(pages)
    m = re.search(r"No\.?\s*\d+\s*[–—-]\s*(.+)$", heading)
    ac_name = _esw.clean(m.group(1)).title() if m else ""
    ac = f"DL-AC-{no}"
    recs, n = [], {}
    for sec, role, person in rows:
        post = " ".join(person["posts"])
        name = " ".join(person["name"]).strip(" ,")
        base = f"{ac}:{role}"
        n[(sec, role)] = n.get((sec, role), 0) + 1
        office = _esw.slug(post) if post else str(n[(sec, role)])
        key = f"{base}:{office}" + (f":{_esw.slug(sec)}" if sec else "")
        k, i = key, 2
        while any(k == r[len(f"dept:{MODULE}:"):] for r, _ in recs):
            k, i = f"{key}:{i}", i + 1
        area = post if role in ("ce", "se", "ee") and post else (f"{no} - {ac_name}" if ac_name else ac)
        recs.append(_esw.record(MODULE, k, dept="water", level=LEVEL[role], area=area, post=post or POSTNAME[role],
                                name=name, phone=_esw.phones(*person["phones"]), state="DL", ac=ac,
                                office_id=f"DL-DJB-{_esw.slug(post)}" if post else f"DL-DJB-{k.replace(':', '-')}", org=ORG,
                                section=sec, plan="Summer Action Plan 2026", source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    no = p.get("ac") or re.search(r"ac_(\d+)_", p["url"]).group(1)
    files = [_esw.keep(MODULE, f"sap2026-ac{no}", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, p)
    return recs, files, "" if recs else "no officer table"
