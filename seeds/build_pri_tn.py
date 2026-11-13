"""seeds/pri_tn.json: Tamil Nadu rural local body results files (cforms/pri_tn.py).
Static items: the district-wide files (dpwm, puwm, vpp) of the 27 districts of 2019 and the 9 districts of the October 2021
ordinary election (file names follow one pattern; checked for ari 2019, kki and slm 2021 on 2026-11-13), the 6 Ariyalur 2019
union files seen on the district page, and one seed item that lists every PDF of every district page of both years
(per-union vpwm files and the 2021 casual elections), for civic-india/hub_register.sh to queue.
Run: .venv/bin/python seeds/build_pri_tn.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cforms import pri_tn  # noqa: E402

D2019 = [c for c in pri_tn.DISTRICTS if c not in pri_tn.NEW_2021 and c != "myl"]
ARI_UNIONS = ["ariyal", "andima", "sendur", "jayamk", "tpalur", "thirum"]


def main():
    out = [{"key": "pri_tn:seed", "payload": {"kind": "seed", "module": "pri_tn", "state": "TN", "route": "proxy",
                                              "url": pri_tn.BASE.format(year="2019") + "rlbe2019.php"}}]
    for year, codes in (("2019", D2019), ("2021", sorted(pri_tn.NEW_2021))):
        for code in codes:
            for kind in ("dpwm", "puwm", "vpp"):
                out.append(pri_tn.item(year, code, f"{kind}_{code}.pdf"))
    out += [pri_tn.item("2019", "ari", f"vpwm_ari_{u}.pdf") for u in ARI_UNIONS]
    miss = sorted({i["payload"]["district"] for i in out[1:] if not i["payload"]["zp_lgd"]})
    Path(__file__).with_name("pri_tn.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(len(out), "items; districts without LGD code:", miss)


if __name__ == "__main__":
    main()
