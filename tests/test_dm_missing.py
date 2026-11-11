"""Fixes for the district officers gap (2026-11-11): title rows above the header row, office / department columns, Odia headers,
and web server placeholder pages that ended as "done"."""
from pathlib import Path

import whoswho
from officials import normalise, tables

DATA = Path(__file__).parent / "data"


def read(name):
    return (DATA / name).read_text(encoding="utf-8")


def test_title_row_khagaria():
    ts = tables(read("dm_title_row_khagaria.html"))
    assert ts[0]["caption"] == "District Administration" and ts[1]["caption"] == "Police Officers"
    row = normalise(ts[0]["rows"][0])
    assert row["name"] == "Vikram Virkar, IAS" and row["designation"] == "District Magistrate"
    assert row["phone"] == "9473191420" and row["email"] == "dm-khagaria.bih@nic.in"


def test_title_row_sheohar():
    # one-cell title row (colspan 6): the old reader skipped these tables
    ts = tables(read("dm_title_row_sheohar.html"))
    assert [t["caption"] for t in ts] == ["District Administration", "Block/Circle/Revenue Level Officer"]
    assert normalise(ts[0]["rows"][0])["designation"] == "District Magistrate"


def test_department_and_odia_headers():
    assert normalise({"Name of the Office": "SDPO, Khordha", "Contact No": "06755-223426"}) == {"department": "SDPO, Khordha", "phone": "06755-223426"}
    assert normalise({"Department Name": "NABARD, Gadag", "Contact No": "231629"})["department"] == "NABARD, Gadag"
    assert normalise({"विभाग नाम": "चिकित्सा", "अधिकारी का नाम": "DR Danveer Singh"}) == {"department": "चिकित्सा", "name": "DR Danveer Singh"}
    assert normalise({"Office Telephone No": "227077", "Office Address": "Collectorate"}) == {"phone": "227077", "address": "Collectorate"}
    row = normalise({"ନାମ": "ଜିଲ୍ଲା ପରିସଂଖ୍ୟାନ କାର୍ଯ୍ୟାଳୟ", "ପଦବୀ": "ଜିଲ୍ଲା ପରିସଂଖ୍ୟାନ ଅଧିକାରୀ", "ଦୁରଭାଷ ନମ୍ବର": "06766-255420"})
    assert row["designation"] == "ଜିଲ୍ଲା ପରିସଂଖ୍ୟାନ ଅଧିକାରୀ" and row["phone"] == "06766-255420"


class _Resp:
    def __init__(self, url, text):
        self.url, self.text, self.status_code, self.encoding, self.headers = url, text, 200, "utf-8", {"content-type": "text/html"}


class _Session:
    def request(self, method, url, **kw):
        return _Resp(url, "<html><head><title>Welcome to nginx!</title></head><body><h1>Welcome to nginx!</h1></body></html>")

    def mount(self, *a):
        pass


def test_server_default_page_is_a_failure():
    site = whoswho.Site(None, _Session(), {"key": "x", "payload": {"url": "https://jaipur.rajasthan.gov.in"}}, 0)
    ok, why = site.run()
    assert not ok and why.startswith("server default page")
