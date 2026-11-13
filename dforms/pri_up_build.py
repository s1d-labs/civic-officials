"""Builds dforms/pri_up_lgd.json.gz for dforms/pri_up.py: the SEC Uttar Pradesh district ids (WinnerListPRI2021.aspx, the same
ids as NewWinnerList2023.aspx: cforms/cr_up_lgd.json) with their LGD district and Zilla Panchayat code, and the LGD Kshetra
Panchayats (blocks) and Gram Panchayats of each Zilla Panchayat (DB civic, lgd.pri_local_bodies, Uttar Pradesh).
Run on a box with DB civic: `python -m dforms.pri_up_build` (reads psql -d civic). Not used by the hub tasks."""
import gzip
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
ALIAS = {"Kushinagar": "Kushi Nagar", "Lakhimpur Kheri": "Kheri", "Sant Kabir Nagar": "Sant Kabeer Nagar", "Bara Banki": "Barabanki",
         "Mahrajganj": "Maharajganj", "Shrawasti": "Shravasti", "Siddharthnagar": "Siddharth Nagar",
         "Bhadohi": "Sant Ravidas Nagar", "Kushi Nagar": "Kushi Nagar"}


def q(sql):
    out = subprocess.run(["psql", "-d", "civic", "-At", "-F", "\t", "-c", sql], capture_output=True, text=True, check=True).stdout
    return [line.split("\t") for line in out.splitlines() if line]


def main():
    zps = {n: c for c, n in q("select local_body_code, local_body_name from lgd.pri_local_bodies "
                              "where state_name='Uttar Pradesh' and local_body_type_name='Zilla Panchayat'")}
    sec = json.loads((HERE.parent / "cforms" / "cr_up_lgd.json").read_text(encoding="utf-8"))["districts"]
    districts = {}
    for sid, (hi, en) in sec.items():
        zn = ALIAS.get(en, en)
        assert zn in zps, (sid, hi, en)
        districts[sid] = [hi, en, zps[zn]]
    blocks, gps = {}, {}
    for c, n, p in q("select local_body_code, local_body_name, parent_local_body_code from lgd.pri_local_bodies "
                     "where state_name='Uttar Pradesh' and local_body_type_name='Kshetra Panchayat' order by 1"):
        blocks.setdefault(p, []).append([c, n])
    for c, n, p in q("select local_body_code, local_body_name, parent_local_body_code from lgd.pri_local_bodies "
                     "where state_name='Uttar Pradesh' and local_body_type_name='Gram Panchayat' order by 1"):
        gps.setdefault(p, []).append([c, n])
    out = {"note": "SEC UP district id -> [Hindi, LGD district, LGD Zilla Panchayat code]; LGD blocks per ZP and GPs per block "
                   "(lgd.pri_local_bodies, DB civic, built by dforms/pri_up_build.py)",
           "districts": districts, "blocks": blocks, "gps": gps}
    (HERE / "pri_up_lgd.json.gz").write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode(), 9, mtime=0))
    print(len(districts), sum(map(len, blocks.values())), sum(map(len, gps.values())))


if __name__ == "__main__":
    main()
