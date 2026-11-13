"""Build seeds/dept_vil_kl_asha.json: one item per Kerala grama panchayat (LGD, 941) plus the urban bodies that
seeds/dept_civic_anganwadi_kl.json already names (their hosts are known). Run on the server (reads DB civic, schema lgd):
    python seeds/build_vil_kl_asha.py
GP host rule: <LGD name, letters only, lower case>panchayat.lsgkerala.gov.in (12 of the 15 GP hosts in archive.s1d.me follow
it); hosts known from the anganwadi seeds win. The item url is the body's home page (/en); dforms/vil_kl_asha.py follows its
ASHA menu link."""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SQL = """select g.local_body_code, g.local_body_name, coalesce(d.local_body_name, '') from lgd.pri_local_bodies g
left join lgd.pri_local_bodies b on b.local_body_code = g.parent_local_body_code
left join lgd.pri_local_bodies d on d.local_body_code = b.parent_local_body_code
where g.state_code = '32' and g.local_body_type_name = 'GRAMA PANCHAYAT' order by 1"""


def main():
    known = {}
    for i in json.loads((HERE / "dept_civic_anganwadi_kl.json").read_text()):
        p = i["payload"]
        known[p.get("local_body_code") or p["url"]] = p
    out = subprocess.run(["psql", "-d", "civic", "-At", "-F", "\t", "-c", SQL], capture_output=True, text=True, check=True).stdout
    items, seen = [], set()
    for line in out.splitlines():
        code, name, dist = line.split("\t")
        kp = known.get(code)
        host = (re.sub(r"^https?://", "", kp["url"]).split("/")[0] if kp else
                re.sub(r"[^a-z]", "", name.lower()) + "panchayat.lsgkerala.gov.in")
        if host in seen:
            continue
        seen.add(host)
        items.append({"key": f"vil_kl_asha:{host.split('.')[0]}", "payload": {
            "reader": "vil_kl_asha", "url": f"https://{host}/en", "state": "KL", "local_body_code": code, "body": name,
            "body_type": "rural", "district": dist.title() or None, "host_guess": not kp, "route": "abroad"}})
    for kp in known.values():
        if kp.get("body_type") != "urban":
            continue
        host = re.sub(r"^https?://", "", kp["url"]).split("/")[0]
        if host in seen:
            continue
        seen.add(host)
        items.append({"key": f"vil_kl_asha:{host.split('.')[0]}", "payload": {
            "reader": "vil_kl_asha", "url": f"https://{host}/en", "state": "KL", "local_body_code": kp.get("local_body_code"),
            "body": kp.get("body"), "body_type": "urban", "district": kp.get("district"), "host_guess": False, "route": "abroad"}})
    (HERE / "dept_vil_kl_asha.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n")
    print(len(items), "items")


if __name__ == "__main__":
    main()
