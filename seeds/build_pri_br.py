"""Build dforms/pri_br_lgd.json (Bihar SEC names -> LGD panchayat codes) and seeds/dept_pri_br*.json.
Run from the family root: python seeds/build_pri_br.py (reads DB civic lgd.pri_local_bodies with psql)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dforms import pri_br  # noqa: E402

# SEC district value -> LGD Zilla Parishad code (by name; checked by hand 2026-11-13)
SEC_ZP = {"1": "202", "2": "204", "3": "211", "4": "212", "5": "197", "6": "214", "7": "179", "8": "194", "9": "205", "10": "192",
          "11": "196", "12": "207", "13": "186", "14": "199", "15": "188", "16": "213", "17": "209", "18": "215", "19": "208",
          "20": "182", "21": "193", "22": "183", "23": "181", "24": "198", "25": "195", "26": "210", "27": "200", "28": "203",
          "29": "184", "30": "185", "31": "191", "32": "206", "33": "561", "34": "190", "35": "180", "36": "187", "37": "201",
          "38": "189"}


def rows(sql):
    out = subprocess.run(["psql", "-d", "civic", "-At", "-F", "\t", "-c", sql], capture_output=True, text=True, check=True).stdout
    return [r.split("\t") for r in out.splitlines() if r]


def build_lgd():
    m = {"sec_district": SEC_ZP, "zp_by_name": {}, "zp": {}}
    for code, name, local in rows("select local_body_code, local_body_name, local_body_name_local from lgd.pri_local_bodies "
                                  "where state_name='Bihar' and local_body_type_name='Zilla Parishad'"):
        m["zp"][code] = {"name": name, "name_local": local, "blocks": {}}
        m["zp_by_name"][pri_br.norm(local)] = code
    blk = {}
    for code, name, local, parent in rows("select local_body_code, local_body_name, local_body_name_local, parent_local_body_code "
                                          "from lgd.pri_local_bodies where state_name='Bihar' and local_body_type_name='Panchayat Samiti'"):
        if parent in m["zp"]:
            e = {"code": code, "name": name, "name_local": local, "gps": {}}
            m["zp"][parent]["blocks"][pri_br.norm(local) or pri_br.norm(name)] = e
            blk[code] = e
    for code, local, parent in rows("select local_body_code, local_body_name_local, parent_local_body_code from lgd.pri_local_bodies "
                                    "where state_name='Bihar' and local_body_type_name='Gram Panchayat'"):
        if parent in blk:
            blk[parent]["gps"][pri_br.norm(local)] = code
    for z in m["zp"].values():          # GP names only (the reader needs the code); keep the file small
        for b in z["blocks"].values():
            b.pop("name_local", None)
    (ROOT / "dforms" / "pri_br_lgd.json").write_text(json.dumps(m, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def build_seeds():
    (ROOT / "seeds" / "dept_pri_br.json").write_text(json.dumps(pri_br.items(), ensure_ascii=False, indent=1) + "\n")
    (ROOT / "seeds" / "dept_pri_br_members.json").write_text(json.dumps(pri_br.member_items(), ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    build_lgd()
    build_seeds()
