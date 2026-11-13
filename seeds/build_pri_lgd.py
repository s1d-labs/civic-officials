"""Write cforms/pri_lgd/<st>.json.gz from DB civic (lgd.pri_local_bodies): rows [code, level, name, local name, parent code].
Run on the box: .venv/bin/python seeds/build_pri_lgd.py KL TN ... (reads with psql -d civic)."""
import gzip
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cforms._pri import HERE, level_of  # noqa: E402

NAMES = {"KL": "Kerala", "TN": "Tamil Nadu", "KA": "Karnataka", "AP": "Andhra Pradesh", "TG": "Telangana", "MH": "Maharashtra",
         "GJ": "Gujarat", "GA": "Goa", "PY": "Puducherry"}


def main(states):
    HERE.mkdir(exist_ok=True)
    for st in states:
        sql = ("copy (select local_body_code, local_body_type_name, local_body_name, coalesce(local_body_name_local,''), "
               f"coalesce(parent_local_body_code,'') from lgd.pri_local_bodies where state_name = '{NAMES[st]}' "
               "order by local_body_code) to stdout with (format csv)")
        import csv
        import io
        out = subprocess.run(["psql", "-d", "civic", "-Atc", sql], capture_output=True, text=True, check=True).stdout
        rows = [[c, level_of(t), n, ln, p] for c, t, n, ln, p in csv.reader(io.StringIO(out))]
        rows = [r for r in rows if r[1]]
        (HERE / f"{st.lower()}.json.gz").write_bytes(gzip.compress(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode(), 9))
        print(st, len(rows))


if __name__ == "__main__":
    main(sys.argv[1:] or list(NAMES))
