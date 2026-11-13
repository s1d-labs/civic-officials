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


def test_administrator_only_gives_body_status(monkeypatch):
    from esw_common import Answer
    monkeypatch.setattr(ka, "_base", lambda p: "http://" + p["host"])
    p = {"host": "www.x.mrc.gov.in", "url": "http://www.x.mrc.gov.in/en/council-members", "slug": "x-city-corporation",
         "body": "X City Corporation", "body_type": "City Corporation", "district": "Mysuru", "lgd_code": "252045"}
    page = (DATA / "ka" / "council_admin_only.html").read_bytes()
    recs, files, why = ka.fetch(p, lambda url, **kw: Answer(page, url))
    assert why == "" and len(recs) == 1
    rid, d = recs[0]
    assert rid == "body_status:KA:x-city-corporation" and d["type"] == "body_status" and d["status"] == "administrator"
    assert d["lgd_code"] == "252045" and "Administrator" in d["administrator"] and d["url"].endswith("/en/council-members")
    assert d["src_pos"] == {"table": 1, "row": 2}


def test_empty_ward_table_gives_no_members_status(monkeypatch):
    import requests as rq
    from cforms import ka
    r = rq.Response()
    r.status_code, r._content, r.url = 200, b"<html><table><tr><td>1</td><td></td></tr></table></html>", "http://x.mrc.gov.in/en/council-members"
    monkeypatch.setattr(ka, "members", lambda html: ([], [], None, 3))
    monkeypatch.setattr(ka, "_base", lambda p: "http://x.mrc.gov.in")
    recs, files, why = ka.fetch({"slug": "x-tmc", "body": "X", "lgd_code": "123", "base": "https://x.mrc.gov.in", "url": "https://x.mrc.gov.in"},
                                lambda url, *a, **k: r)
    assert why == "" and len(recs) == 1
    rid, d = recs[0]
    assert rid == "body_status:KA:x-tmc" and d["status"] == "no members listed" and "empty names" in d["note"] and d["lgd_code"] == "123"


def test_https_refused_goes_to_http():
    import requests as rq
    import councillors
    assert councillors.https_refused("https://a.mrc.gov.in/", rq.exceptions.ConnectionError("Connection refused"))
    assert not councillors.https_refused("https://a.mrc.gov.in/", rq.exceptions.ConnectTimeout("timed out"))
    assert not councillors.https_refused("http://a.mrc.gov.in/", rq.exceptions.ConnectionError("Connection refused"))


def test_message_page_names_administrator(monkeypatch):
    """Shivamogga (saved 2026-11-13): the council page lists no member; the home page's "Mayor's Message" link
    (/en/administrator-message) names the Administrator -> body_status administrator with the message page as source."""
    from esw_common import Answer
    monkeypatch.setattr(ka, "_base", lambda p: "http://www.shivamoggacity.mrc.gov.in")
    pages = {"http://www.shivamoggacity.mrc.gov.in/en": (DATA / "ka" / "shivamogga_home.html").read_bytes(),
             "http://www.shivamoggacity.mrc.gov.in/en/administrator-message": (DATA / "ka" / "shivamogga_admin_message.html").read_bytes()}
    empty = b"<html><article><p>Council Members</p></article></html>"
    p = {"host": "www.shivamoggacity.mrc.gov.in", "url": "http://www.shivamoggacity.mrc.gov.in/en/council-members",
         "slug": "shivamogga-city-corporation", "body": "Shivamogga City Corporation", "lgd_code": "251951"}
    seen = []

    def get(url, **kw):
        seen.append(url)
        return Answer(pages.get(url, empty), url)
    assert ka.message_links(pages["http://www.shivamoggacity.mrc.gov.in/en"].decode(), "http://www.shivamoggacity.mrc.gov.in") == \
        ["http://www.shivamoggacity.mrc.gov.in/en/administrator-message"]
    recs, files, why = ka.fetch(p, get)
    assert why == "" and len(recs) == 1 and seen[-1].endswith("/en/administrator-message")
    rid, d = recs[0]
    assert rid == "body_status:KA:shivamogga-city-corporation" and d["status"] == "administrator"
    assert "Administrator , Shivamogga City Corporation" in d["administrator"] and d["url"].endswith("/administrator-message")
    assert d["src_url"].endswith("/administrator-message") and len(files) == 3
    assert ka.admin_message("<article>Message of the President, Smt. X</article>") is None


# ---- 2026-11-14: ward numbers from the full saved council pages (bucket copies, civic-officials-india-direct sources/)
def _town(name):
    import gzip
    return gzip.decompress((DATA / "ka" / f"town_{name}.html.gz").read_bytes()).decode("utf-8")


def _wards(rows):
    return [(r["name"], r["nominated"], None if r["nominated"] else ka._ward(r.get("ward_no")), r.get("ward_name")) for r in rows]


def test_saligrama_ward_at_end_of_address(monkeypatch):
    """Saligrama (kn page, sha256 811f2314...): "Address & Ward Number" cells end with "<ward no>-<ward name>"."""
    from esw_common import Answer
    page = _town("saligramatown")
    rows, admins, term, blank = ka.members(page)
    w = _wards(rows)
    assert len(w) == 16 and sum(1 for x in w if x[2]) == 16 and not any(x[1] for x in w)
    assert w[0] == ("ಸುಕನ್ಯ ಜೆ ಶೆಟ್ಟಿ", False, "6", "ಮಾರಿ ಗುಡಿ") and w[1][2:] == ("10", "ತೆಂಕುಹೋಳಿ")
    assert w[5][2:] == ("4", "ತೋಡುಕಟ್ಟು") and w[15][2:] == ("16", "ಯಕ್ಷಿಮಠ")
    assert [x[2] for x in w].count("15") == 2           # two rows write ward 15 (as the page writes it)
    monkeypatch.setattr(ka, "_base", lambda p: "http://" + p["host"])
    p = {"host": "www.saligramatown.mrc.gov.in", "url": "http://www.saligramatown.mrc.gov.in/en/council-members",
         "slug": "saligram-town-panchayat", "body": "Saligram Town Panchayat", "lgd_code": "251954"}
    recs, files, why = ka.fetch(p, lambda url, **kw: Answer(page.encode(), url) if "/kn/" in url else None)
    d = dict(recs)
    assert why == "" and len(d) == 16 and all(v["ward_no"] for v in d.values())
    assert d["councillor:KA:saligram-town-panchayat:6"]["ward_name"] == "ಮಾರಿ ಗುಡಿ"
    assert "councillor:KA:saligram-town-panchayat:15-2" in d


def test_kadaba_house_number_is_no_ward():
    """Kadaba: "1-175 Hoigekere House ..." is a house number; the ward is the "Ward Name" column (no number on the page)."""
    w = _wards(ka.members(_town("kadabatown"))[0])
    assert len(w) == 13 and sum(1 for x in w if x[2]) == 0 and sum(1 for x in w if x[3]) == 13
    assert ("K M Hanief", False, None, "Maleshwara") in w


def test_nominated_block_inside_the_table():
    """A title row inside the member table starts the nominated block: Kembhavi "NOMINATTED MEMBERS DETAILS" (+ the header row
    again), Srinivasapura "ನಾಮನಿರ್ದೇಶಿತ ಸದಸ್ಯರು", Kakkera "Nominated Member" (a title row, not a person)."""
    k = _wards(ka.members(_town("kembhavitown"))[0])
    assert len(k) == 28 and sum(x[1] for x in k) == 5 and sum(1 for x in k if x[2]) == 23 and "Name" not in [x[0] for x in k]
    s = _wards(ka.members(_town("srinivasapuratown"))[0])
    assert len(s) == 28 and sum(x[1] for x in s) == 5 and sum(1 for x in s if x[2]) == 23
    kk = _wards(ka.members(_town("kakkeratown"))[0])
    assert len(kk) == 28 and sum(x[1] for x in kk) == 5 and "Nominated Member" not in [x[0] for x in kk]


def test_ward_in_address():
    assert ka._ward_in_address("ವಾರ್ಡ್ ನಂ 01 ಗೂರಮಾರನಹಳ್ಳಿ ಬಡಾವಣೆ") == ("1", None)
    assert ka._ward_in_address("12 - Gandhi Nagar") == ("12", "Gandhi Nagar") and ka._ward_in_address("23") == ("23", None)
    assert ka._ward_in_address("1-175 Hoigekere House Near Govt PU college,kadaba") == (None, None)
    assert ka._ward_in_address("Pulikukku 2-164 , Kodimbala") == (None, None)
    assert ka._ward_in_address("Ainapur") == (None, None)
