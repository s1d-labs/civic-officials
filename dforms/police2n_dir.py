"""District portal police pages and contact directories (S3WaaS <district>.nic.in / .gov.in: /police/, /police-stations/,
/directory/, /contact-directory/, /telephone-directory/, /helpline/) for North and East India, read with the S3WaaS table and
card parser (police_s3waas.records) and then cleaned for officer rows:
- a directory page (url without "police") keeps only police rows (police_only);
- the level comes from the post: SDPO / S.D.P.O. / SDOP / Sub-Divisional Police Officer -> subdivision; Circle Inspector / CI /
  C.O. / Circle Officer / ACP -> circle; IC / OC / I/C / SHO / S.O. / Thana / PS / police post -> police_station; SP, SSP,
  Addl. SP, ASP, DCP, CP -> district. Other district units (control room, lines, DIB, court, traffic, cyber cell, RI, LIU ...)
  are left out;
- the name is kept only when it is a person's name: "Incharge", "S.O.", "SHO Jaurkian", "Superintendent Of Police" (the post
  written in the name column) are dropped; the area of a circle or subdivision is taken from the post when the post names the
  place ("S.D.P.O. Raghunathpur" -> Raghunathpur, "CI Sadar, Purulia" -> Sadar);
- West Bengal pages write the station head as "IC <station> PS" / "OC <station> PS" (inspector / officer in charge): the post
  is IC or OC.
fetch(p, get, module) is shared by the state modules police2n_<xx>.py (one queue item = one district page and its /page/N/
pages). Payload: url, state, district, optional std / std_prefix / police_only / max_pages as in police_s3waas.
Record id dept:<module>:<district>:<station or office>."""
import re

from dforms import police_s3waas as s3
from dforms._police import clean, gz, rec, slug, uniq

M = "police2n_dir"

SUBDIV = re.compile(r"\bS\.?\s?D\.?\s?P\.?\s?O\b|\bSDOP\b|Sub[- ]?Divisional Police Officer|Sub[- ]?Division(?:al)? Police", re.I)
CIRCLE = re.compile(r"Circle Inspector|Circle Officer|\bC\.?\s?I\.?(?=\s|,|$)|\bC\.\s?O\.?(?=\s|$)|^CO\s|\bACP\b|"
                    r"Assistant Commissioner of Police|Inspector Circle", re.I)
STATION = re.compile(r"\b(?:I/?C|O/?C|IIC|SHO|S\.\s?H\.\s?O\.?|S\.?\s?O\.?|Station House Officer|Thana|Thanadhyaksh|Police Station|"
                     r"P\.?\s?S\.?|Out ?Post|Police Post|Chowki|Chauki|O\.?P\.?|Officer[- ]in[- ]Charge|Incharge|In-charge)\b", re.I)
HEAD = re.compile(r"^(?:S\.?\s?P\.?|SSP|S\.S\.P\.?|Sr\.?\s*S\.?P\.?|Superintendent of Police|Senior Superintendent of Police|"
                  r"Addl\.?\s*S\.?\s?P\.?|Additional (?:Superintendent of Police|S\.?P\.?)|A\.?S\.?P\.?|D\.?C\.?P\.?|"
                  r"Deputy Commissioner of Police|Commissioner of Police|C\.?P\.?)(?:\W|$)", re.I)
UNIT = re.compile(r"control room|police lines?|reserve|\bR\.?I\.?\b|\bRO\b|\bMTO\b|\bM\.T\.|D\.?I\.?B|D\.?S\.?B|\bS\.?B\b|L\.?I\.?U|court|"
                  r"traffic|cyber cell|home guard|wireless|D\.?C\.?R\.?B|helpline|help line|\bCIA\b|\bHQ\b|hqrs|headquarter|"
                  r"special branch|\bDEB\b|\bDIO\b|fire|crime branch|vigilance|\bS\.?O\.?G\b|\bPCR\b|dial ?112|\b112\b|"
                  r"anti[- ]|women cell|mahila cell|account|establishment|computer|\bIT\b|cctns|operations|security", re.I)
WORDS = re.compile(r"\b(?:police|station|thana|officer|office|incharge|in-?charge|superintendent|inspector|sub[- ]?inspector|"
                   r"constable|SHO|SDPO|DSP|DySP|S\.?\s?P|SSP|ASP|ACP|DCP|S\.?O\.?|C\.?O\.?|I/?C|O/?C|IIC|circle|control|room|"
                   r"cell|helpline|line|lines|branch|court|traffic|district|sadar|kotwali|pratisar|nirikshak|prabhari|"
                   r"thanadhyaksh|deputy|addl|additional|commissioner|vacant|director|section|PS|P\.S|CIA|LIU|RI|DIB|HQ|"
                   r"cyber|crime|women|mahila|post|chowki|chauki)\b", re.I)
TITLE = re.compile(r"^(?:(?:Shri|Sri|Smt|Smti|Kum|Ms|Mrs|Mr|Dr|Er)\.?\s+)+", re.I)
RANK = re.compile(r"^(?:(?:W/|L|Lady\s+|Women\s+)?(?:Insp(?:r|ector)?|S\.?\s?I|A\.?S\.?I|P\.?S\.?I|Sub[- ]Inspector|"
                  r"Inspector of Police|Dy\.?\s?S\.?P|DSP|H\.?C)\.?)\s+", re.I)
SERVICE = re.compile(r"[\s,]*(?:\(\s*(?:IPS|WBPS|BPS|MPS|PPS|HPS|RPS|JPS|OPS|APS|I\.P\.S\.?|In-?Charge|I/C|Addl\.? Charge)\s*\)|"
                     r",?\s*(?:IPS|WBPS|BPS|MPS|PPS|HPS|RPS|JPS|OPS|APS|I\.P\.S\.?))\.?\s*$", re.I)


def person(name, *labels):
    """The name when it is a person's name, else None."""
    n = clean(name) or ""
    if not n or re.search(r"\d", n):
        return None
    for lab in labels:
        if lab and slug(lab) == slug(n):
            return None
    core = SERVICE.sub("", RANK.sub("", TITLE.sub("", n))).strip(" ,.-")
    core = re.sub(r"\([^)]*\)", "", core).strip(" ,.-")
    if len(re.sub(r"[^A-Za-zऀ-෿]", "", core)) < 3 or WORDS.search(core):
        return None
    if re.fullmatch(r"(?:vacant|na|n/a|nil|-+|not available|will be updated soon)", core, re.I):
        return None
    return n


def place(post, kind):
    """'S.D.P.O. Raghunathpur' -> 'Raghunathpur'; 'CI Sadar, Purulia' -> 'Sadar'; 'SDPO (Sadar)' -> 'Sadar'."""
    p = clean(post) or ""
    pat = SUBDIV if kind == "subdivision" else CIRCLE
    m = pat.search(p)
    if not m:
        return None
    rest = p[m.end():].strip(" ,.:-–")
    rest = re.sub(r"^(?:of|,)\s*", "", rest, flags=re.I)
    rest = re.sub(r"^\((.+)\)$", r"\1", rest).strip()
    rest = re.split(r"\s*,\s*|\s+-\s+", rest)[0].strip(" ()")
    if not rest or WORDS.search(rest) and not re.search(r"sadar|city|town|kotwali", rest, re.I):
        return None
    return rest


def head_post(post):
    p = clean(post) or ""
    m = re.match(r"^\s*(I\.?\s?I\.?\s?C|I/?C|O/?C|IC|OC)\b\.?", p, re.I)
    return m.group(1).upper().replace(".", "").replace(" ", "") if m else None


def clean_records(module, recs):
    out = []
    for rid, r in recs:
        post, area, rank = r.get("post") or "", r.get("area") or "", r.get("rank") or ""
        text = f"{post} {rank} {area}"
        level = r["level"]
        if SUBDIV.search(post) or SUBDIV.search(rank) or (level == "subdivision" and not UNIT.search(text)):
            level = "subdivision"
        elif CIRCLE.search(post) or CIRCLE.search(rank) or level == "circle":
            level = "circle"
        elif HEAD.match(post) or HEAD.match(area) or HEAD.match(rank):
            level = "district"
        elif level == "police_station" or STATION.search(text):
            level = "police_station"
        else:
            continue
        if level != "police_station" and UNIT.search(f"{post} {rank}"):
            continue
        if level == "police_station" and UNIT.search(area) and not re.search(r"police station|\bP\.?S\b|thana", area, re.I):
            continue
        d = dict(r)
        d["level"] = level
        name = person(d.get("name"), post, area, rank)
        if name:
            d["name"] = name
        else:
            d.pop("name", None)
        if level in ("subdivision", "circle"):
            pl = place(post, level) or place(rank, level)
            if pl:
                d["area"] = pl
            d["post"] = "SDPO" if level == "subdivision" else ("ACP" if re.search(r"\bACP\b|Assistant Commissioner", text, re.I)
                                                                else "CO" if re.search(r"C\.\s?O\.?|Circle Officer|^CO\s", text)
                                                                else "Circle Inspector")
            d["office_type"] = level
            if post and post != d["post"]:
                d["designation"] = post
        elif level == "police_station":
            hp = head_post(rank) or head_post(post)
            if hp:
                d["post"] = hp
                if d.get("rank") and head_post(d["rank"]):
                    d.pop("rank")
            if d.get("office_type") not in ("police station", "police post"):
                d["office_type"] = "police station"
        else:
            d["office_type"] = "office"
        key = rid.split(":", 2)[2] if rid.count(":") >= 2 else rid
        if level in ("subdivision", "circle"):
            dist, _, _ = key.partition(":")
            key = f"{dist}:{'sdpo' if level == 'subdivision' else 'circle'}-{slug(d['area'])}"
        out.append((f"dept:{module}:{key}", d))
    return uniq(out)


def fetch(p, get, module=M):
    p = dict(p)
    if "police_only" not in p:
        p["police_only"] = not re.search(r"police", p["url"].split("://", 1)[-1].split("/", 1)[-1], re.I)
    recs, files, why = s3.fetch(p, get, module)
    if not recs:
        return recs, files, why
    recs = clean_records(module, recs)
    return recs, files, "" if recs else "no officer rows"
