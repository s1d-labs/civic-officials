"""Sri Vijaya Puram (Port Blair) MC councillors from the council's RTI 4(1)(b) disclosure (cforms/ce_an.py)."""
import json
from pathlib import Path

from cforms import ce_an

DATA = Path(__file__).parent / "data"


def test_svpmc_councillors():
    recs = dict(ce_an.parse((DATA / "ce_an_svpmc_rti.txt").read_text()))
    assert len(recs) == 24
    assert recs["councillor:AN:sri-vijaya-puram-mc:1"]["name"] == "Shri. S Shahul Hameed"
    assert recs["councillor:AN:sri-vijaya-puram-mc:13"]["position"] == "Chairperson"
    assert recs["councillor:AN:sri-vijaya-puram-mc:9"]["position"] == "Sr Vice Chairperson"
    assert recs["councillor:AN:sri-vijaya-puram-mc:20"]["position"] == "Junior Vice Chairperson"
    assert recs["councillor:AN:sri-vijaya-puram-mc:24"]["name"] == "Smti. U Kavitha"
    assert all(d["lgd_code"] == "253098" for d in recs.values())


def test_seed():
    items = json.loads((Path(__file__).parent.parent / "seeds" / "councillors_ce_an.json").read_text())
    assert items[0]["payload"]["kind"] == "form-ce_an"


def test_svpmc_full_file_officers_and_staff():
    """The whole RTI file (pdftotext -layout of the bucket copy 25e1518b678d..., 27 pages). Before 2026-11-13 the reader kept the
    24 councillors only; the audit counted 286 person rows. Now also item (ix) (28 officers with office phones), item (x)
    (155 officers and employees with code and pay level) and item (xvi) (8 RTI posts with e-mail and phone): 215 records."""
    import gzip
    text = gzip.decompress((DATA / "ce_an_svpmc_rti_full.txt.gz").read_bytes()).decode("utf-8")
    assert len(ce_an.parse(text)) == 24
    recs = dict(ce_an.staff(text))
    kinds = {}
    for rid in recs:
        k = rid.split(":")[3].split("-")[0]
        kinds[k] = kinds.get(k, 0) + 1
    assert kinds == {"dir": 28, "emp": 155, "rti": 8}
    assert all(d["type"] == "dept_office" and d["dept"] == "town_body" for d in recs.values())
    d = recs["dept:ce_an:svpmc:dir-4"]
    assert (d["name"], d["post"], d["phone"]) == ("Avinash Kumar Singh", "Superintending Engineer (i/c)", "03192-243247")
    assert recs["dept:ce_an:svpmc:dir-28"]["name"] == "Krishnendu Das Gupta"                 # wrapped onto the next line
    assert recs["dept:ce_an:svpmc:emp-R2030"]["name"] == "H Joseph" and recs["dept:ce_an:svpmc:emp-R2030"]["pay_level"] == "2"
    n = recs["dept:ce_an:svpmc:rti-nodal-1"]
    assert (n["phone"], n["email"]) == ("9679508764", "prkaruppaiah.pbmc@pbmc.gov.in")
    a = recs["dept:ce_an:svpmc:rti-apio-3"]
    assert a["email"] == "santhi.pbmc@pbmc.gov.in" and a["post"].endswith("Administrative Officer (i/c), Administrative Wing")
