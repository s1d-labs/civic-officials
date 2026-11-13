"""seeds/councillors_cp_tn.json: one item per town site on www.tnurbantree.tn.gov.in (cforms/cp_tn.py).
The site list is platform_sites.csv (155 tnurbantree sites; "wpfc-minified" is a cache folder, not a body). Each site is tied
to its 2022 SEC body in DB civic (civic.councillor, state TN, group mun-* / corp-*: Tamil name, LGD code, district group) by
the English LGD name: same letters first, else the closest name (ratio >= 0.8, one best), else SITE_LGD below.
Items already in the file are kept as they are (with their members_held / body_alt); new sites are added.
2026-11-14: 89 items -> 153 (64 sites were not seeded; Thoothukudi had the LGD code of Tittakudi, 252789, now 252970).
Run on dev-vps-3: .venv/bin/python seeds/build_cp_tn.py"""
import csv
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cforms import cp_tn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "seeds" / "councillors_cp_tn.json"
NOT_BODY = {"wpfc-minified"}
# sites whose name alone does not give one body (checked on the sites' own pages in the archive, 2026-11-14)
SITE_LGD = {"gudalur-cbe": "252920",        # Gudalur, Coimbatore district
            "gudalur-theni": "252596",      # Gudalur, Theni district
            "gudalur-tiruppur": "252639",   # Gudalur, The Nilgiris (Tiruppur region): "NILGIRIS" on its pages
            "guduvancheri": "252329",       # Nandivaram - Guduvancheri
            "pernampattu": "252350",        # Pernambut
            "thittagudi": "252789",         # Tittakudi
            "thoothukudi": "252970"}        # corporation (the old seed had 252789, Tittakudi)

SQL = ("select distinct split_part(c.record_id,':',4), c.body, c.local_body_code, u.local_body_name "
       "from civic.councillor c join lgd.urban_local_bodies u on u.local_body_code = c.local_body_code "
       "where c.state = 'TN' and split_part(c.record_id,':',3) = 'tx' and split_part(c.record_id,':',4) ~ '^(mun|corp)-'")


def key(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def bodies():
    out = subprocess.run(["sudo", "-n", "runuser", "-u", "postgres", "--", "psql", "-d", "civic", "-AtF", "|", "-c", SQL],
                         capture_output=True, text=True, check=True).stdout
    return {r[2]: r for r in (ln.split("|") for ln in out.splitlines() if ln)}


def match(site, by_code):
    if site in SITE_LGD:
        return by_code[SITE_LGD[site]]
    k = key(site.split("-")[0])
    same = [r for r in by_code.values() if key(r[3]) == k]
    if len(same) == 1:
        return same[0]
    sc = sorted(((difflib.SequenceMatcher(None, k, key(r[3])).ratio(), r[2]) for r in by_code.values()), reverse=True)
    if sc and sc[0][0] >= 0.8 and (len(sc) < 2 or sc[1][0] < sc[0][0]):
        return by_code[sc[0][1]]
    return None


def item(site, r):
    grp, body, code, name = r
    return {"key": f"cp-tn-{site}", "payload": {"kind": "form-cp_tn", "state": "TN", "url": cp_tn.search_url(site), "site": site,
                                               "body": body, "lgd_code": code, "record_prefix": f"councillor:TN:{grp}:{body}",
                                               "name_en": name}}


def main():
    by_code = bodies()
    old = {i["payload"]["site"]: i for i in json.loads(OUT.read_text())}
    sites = [r["name"] for r in csv.DictReader(open(ROOT / "platform_sites.csv", encoding="utf-8"))
             if r["domain"].startswith("tnurbantree.tn.gov.in/") and r["name"] not in NOT_BODY]
    out, miss = [], []
    for s in sites:
        r = match(s, by_code)
        if s in old:
            it = old[s]
            if r and it["payload"]["lgd_code"] != r[2] and s in SITE_LGD:
                it["payload"]["lgd_code"] = r[2]
            out.append(it)
        elif r:
            out.append(item(s, r))
        else:
            miss.append(s)
    codes = [i["payload"]["lgd_code"] for i in out]
    assert len(codes) == len(set(codes)), "two sites on one body"
    out.sort(key=lambda i: i["key"])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(len(out), "items;", len(sites), "sites; not tied:", miss)


if __name__ == "__main__":
    main()
