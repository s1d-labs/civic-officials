"""Ward map file reader (dforms/wm_geopdf.py) on a saved 2 KB GeoPDF (tests/data/wm_tiny_ward7.pdf, made with GDAL's PDF
driver): no network. The reader stores the file once and records what it is; polygons are made later by civic-india/wm_geopdf.py."""
import hashlib
import json

from test_dept_police import DATA, FakeGet

from dforms import wm_geopdf

PDF = (DATA / "wm_tiny_ward7.pdf").read_bytes()
SHA = hashlib.sha256(PDF).hexdigest()
POINTER = f"version https://git-lfs.github.com/spec/v1\noid sha256:{SHA}\nsize {len(PDF)}\n"


def payload(**kw):
    p = {"reader": "wm_geopdf", "url": "https://media.githubusercontent.com/media/o/r/main/Akola/WARD_07.pdf", "state": "MH",
         "body": "251312", "body_name": "Akola", "ward": "7", "stage": "final", "source": "okeskar", "path": "Akola/WARD_07.pdf"}
    p.update(kw)
    return p


def test_stores_geopdf_once():
    recs, files, why = wm_geopdf.fetch(payload(sha256=SHA, size=len(PDF)), FakeGet({"https://media.githubusercontent.com/": PDF}))
    assert why == "" and len(recs) == 1 and len(files) == 1
    rid, d = recs[0]
    assert rid == f"wm_file:{SHA[:16]}" and d["type"] == "wm_file"
    assert d["file"] == f"wardmaps/MH/251312/{SHA[:16]}.pdf" == files[0][0]
    assert d["geo"] is True and d["pages"] == 1 and d["bytes"] == len(PDF) and d["ward"] == "7"
    assert files[0][1] == PDF and files[0][2] == "application/pdf"


def test_lfs_pointer_falls_back_to_batch_api():
    def batch(url, method, data):
        assert method == "POST" and json.loads(data)["objects"][0]["oid"] == SHA
        return json.dumps({"objects": [{"oid": SHA, "actions": {"download": {"href": "https://lfs.example/obj"}}}]})
    get = FakeGet({"https://media.githubusercontent.com/": POINTER, "https://github.com/o/r.git/info/lfs/objects/batch": batch,
                   "https://lfs.example/obj": PDF})
    recs, files, why = wm_geopdf.fetch(payload(sha256=SHA, size=len(PDF), lfs_repo="o/r"), get)
    assert why == "" and recs[0][1]["sha256"] == SHA and files


def test_truncated_answer_is_refused():
    recs, files, why = wm_geopdf.fetch(payload(sha256=SHA, size=len(PDF)), FakeGet({"https://media.githubusercontent.com/": PDF[:900]}))
    assert recs == [] and files == [] and "short" in why


def test_plain_pdf_is_not_geo():
    plain = PDF.replace(b"/LGIDict", b"/XXXXXXX").replace(b"/GPTS", b"/XXXX").replace(b"/Measure", b"/XXXXXXX")
    recs, files, why = wm_geopdf.fetch(payload(), FakeGet({"https://media.githubusercontent.com/": plain}))
    assert why == "" and recs[0][1]["geo"] is False
