"""cforms/ka.py member rows: the ward named in the post wins over a ward in the address; nominee rows get no ward."""
import importlib

from esw_common import DATA

ka = importlib.import_module("cforms.ka")


def test_ward_in_post_and_nominees():
    rows, admins, term, blank = ka.members((DATA / "ka" / "council_ward_in_post.html").read_text())
    by = {r["name"]: r for r in rows}
    assert ka._ward(by["Sri. Ramachandra S"]["ward_no"]) == "13"       # address says "Ward No.10": the member's house, not the seat
    assert ka._ward(by["Smt. Annapurna S"]["ward_no"]) == "15"
    assert ka._ward(by["Sri. Ananda Reddy"]["ward_no"]) == "10"
    assert ka._ward(by["Sri. Somebody"]["ward_no"]) == "11"             # "President": no number in the post, the address gives it
    assert by["ತೀರ್ಥ ಕುಮಾರ್"]["nominated"] and by["Shri. B. Maulali"]["nominated"]
    assert not by["Sri. Ananda Reddy"]["nominated"] and not admins
