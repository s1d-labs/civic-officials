"""Build dforms/pri_wb_tree.json for dforms/pri_wb.py: the West Bengal Panchayat General Election 2023 tree (Zilla Parishad ->
Panchayat Samiti (block) -> Gram Panchayat) that the WBSEC result portal portal.wbsec.org carries inside its own script
(ControllerScript/app.Portal.index.js, variable PopulateConstituencyJson; 22 ZP, 346 PS, 3,321 GP on 2026-11-13), with the LGD
local body code of each body matched by name inside its parent (DB civic, lgd.pri_local_bodies, state West Bengal).

Match: names folded (lower case, letters and digits only, roman I/II/III -> 1/2/3, common spelling pairs); exact folded name inside
the LGD parent first; else the best difflib ratio >= 0.82 inside the parent when it is unique (next best at least 0.05 lower) and the numbers in both names are the same.
"lgd_match": "name" (exact fold) or "fuzzy" (ratio, kept in "lgd_ratio"). Bodies without a match keep no code.
Run: python seeds/build_pri_wb.py <saved app.Portal.index.js>  (needs psql -d civic)."""
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROMAN = [("iii", "3"), ("ii", "2"), ("iv", "4"), ("i", "1")]
ZP_ALIAS = {"coochbehar": "coochbehar", "24parganasnorth": "north24parganas", "24parganassouth": "south24parganas",
            "bardhamanpurba": "purbabardhaman", "purbabardhaman": "purbabardhaman", "paschimbardhaman": "paschimbardhaman",
            "medinipurpaschim": "paschimmedinipur", "medinipurpurba": "purbamedinipur", "dinajpurdakshin": "dakshindinajpur",
            "dinajpuruttar": "uttardinajpur", "darjeelingsiliguri": "darjeeling", "siliguri": "darjeeling", "maldah": "malda"}


def fold(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = []
    for t in s.split():
        for r, d in ROMAN:
            if t == r:
                t = d
                break
        toks.append(t)
    s = "".join(toks)
    for a, b in (("ph", "f"), ("oo", "u"), ("ee", "i"), ("w", "o"), ("y", "i"), ("aa", "a"), ("bh", "b"), ("dh", "d"),
                 ("th", "t"), ("kh", "k"), ("gh", "g"), ("sh", "s"), ("ch", "c")):
        s = s.replace(a, b)
    return s


def lgd_rows():
    sql = ("select local_body_code, local_body_name, local_body_type_name, coalesce(parent_local_body_code,'') "
           "from lgd.pri_local_bodies where state_name='West Bengal'")
    out = subprocess.run(["psql", "-d", "civic", "-At", "-F", "\t", "-c", sql], capture_output=True, text=True, check=True).stdout
    return [line.split("\t") for line in out.splitlines() if line]


def match(name, cands, alias=None):
    """cands: [(code, name)] -> (code, how, ratio) or (None, None, None)."""
    f = fold(name)
    if alias:
        f = alias.get(f, f)
    exact = [c for c, n in cands if fold(n) == f]
    if len(exact) == 1:
        return exact[0], "name", 1.0
    num = re.findall(r"\d+", f)
    scored = sorted(((difflib.SequenceMatcher(None, f, fold(n)).ratio(), c) for c, n in cands
                     if re.findall(r"\d+", fold(n)) == num), reverse=True)        # never -I for -II
    if scored and scored[0][0] >= 0.82 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.05):
        return scored[0][1], "fuzzy", round(scored[0][0], 3)
    return None, None, None


def main(js_path):
    t = Path(js_path).read_text(encoding="utf-8")
    key = "var PopulateConstituencyJson = "
    tree, _ = json.JSONDecoder().raw_decode(t[t.index(key) + len(key):])
    rows = lgd_rows()
    kids = {}
    for code, name, typ, parent in rows:
        kids.setdefault(parent if typ != "Zilla Panchayat" else "", []).append((code, name))
    out, n = [], {"zp": [0, 0], "ps": [0, 0], "gp": [0, 0]}
    for d in tree:
        zc, zh, zr = match(d["Name"], kids.get("", []), ZP_ALIAS)
        n["zp"][0] += 1
        n["zp"][1] += bool(zc)
        zp = {"id": d["ID"], "name": d["Name"], "lgd": zc, "lgd_match": zh, "lgd_ratio": zr, "ps": []}
        for sd in d["SubDivisions"]:
            for b in sd["Municipalities"]:
                pc, ph, pr = match(b["Name"], kids.get(zc, []) if zc else [])
                n["ps"][0] += 1
                n["ps"][1] += bool(pc)
                ps = {"id": b["ID"], "name": b["Name"], "subdivision": sd["Name"], "lgd": pc, "lgd_match": ph, "lgd_ratio": pr, "gp": []}
                for g in b["GramPanchayat"]:
                    gc, gh, gr = match(g["Name"], kids.get(pc, []) if pc else [])
                    n["gp"][0] += 1
                    n["gp"][1] += bool(gc)
                    ps["gp"].append({k: v for k, v in {"id": g["ID"], "name": g["Name"], "lgd": gc, "lgd_match": gh,
                                                         "lgd_ratio": gr}.items() if v is not None})
                zp["ps"].append({k: v for k, v in ps.items() if v is not None})
        out.append({k: v for k, v in zp.items() if v is not None})
    (ROOT / "dforms" / "pri_wb_tree.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    print({k: f"{v[1]}/{v[0]}" for k, v in n.items()})


if __name__ == "__main__":
    main(sys.argv[1])
