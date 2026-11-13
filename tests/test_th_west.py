"""Offline tests of the town-head readers of fork WEST (dforms/th_*.py) on archive.s1d.me copies saved in tests/data/ (gzip)."""
import gzip

from esw_common import *  # noqa: F401,F403

FILES = {"mp-damoh": "th_mp_damoh", "mp-datia": "th_mp_datia", "mp-jhabua": "th_mp_jhabua", "mp-khargone": "th_mp_khargone",
         "mp-sheopur": "th_mp_sheopur", "mp-sidhi": "th_mp_sidhi", "mp-umaria": "th_mp_umaria", "mh-ahilyanagar": "th_mh_ahilyanagar",
         "mh-dharashiv": "th_mh_dharashiv", "mh-palghar": "th_mh_palghar"}


def run(key):
    m = mod("th_dist")
    p = next(i["payload"] for i in m.items() if i["key"] == f"th_dist-{key}")

    def get(url, method="GET", data=None, headers=None):
        assert url == p["url"]
        return Answer(gzip.decompress((DATA / f"{FILES[key]}.html.gz").read_bytes()), url)
    recs, files, why = m.fetch(p, get)
    assert why == "" and files[0][0].startswith("depts/th_dist/")
    check_records(recs, "th_dist", "town_body")
    for _, d in recs:
        assert d["src_pos"]["table"] >= 1 and d["src_pos"]["row"] >= 1 and d["page"] == p["url"] and d["role"] == "head"
    return {d["area"]: d for _, d in recs}


def test_th_dist_items_match_seed():
    seed = json.loads((ROOT / "seeds" / "dept_th_dist.json").read_text())
    assert mod("th_dist").items() == seed and len(seed) == len(FILES)
    assert sorted(i["key"] for i in seed if i["payload"]["india_only"]) == ["th_dist-mh-ahilyanagar", "th_dist-mh-dharashiv"]
    assert hasattr(mod("th_dist"), "METHOD")


BADWAH = "\u092c\u095c\u0935\u093e\u0939"        # the page writes the one-character ड़ (U+095C)


def test_th_dist_mp_row_layouts():
    d = run("mp-datia")                                   # name cell + post cell with the town
    assert d["इन्दरगढ"]["name"] == "श्री एम.एस.यादव" and d["इन्दरगढ"]["lgd_code"] == "250702" and d["इन्दरगढ"]["phone"] == "9754838521"
    assert d["इन्दरगढ"]["email"] == "cmoindargarh@mpurban.gov.in" and d["इन्दरगढ"]["post"] == "Chief Municipal Officer"
    assert d["दतिया"].get("name") is None and d["दतिया"]["lgd_code"] == "250703"   # "CMO Datia, PO DUDA", name "——-"
    d = run("mp-sheopur")                                 # name, post and town in one cell
    assert d["श्योपुर"]["name"] == "श्री नरेंद्र जाटव" and d["श्योपुर"]["lgd_code"] == "250673"
    assert d["बड़ौदा"]["lgd_code"] == "250674" and d["विजयपुर"]["phone"] == "62604-14410, 95169-26870"
    d = run("mp-khargone")                                # town from the address cell; प्रभारी = additional charge
    assert d[BADWAH]["name"] == "श्री कुलदीप किंशुक" and d[BADWAH]["lgd_code"] == "250907"
    assert d["भीकनगाँव"]["charge"] == "additional charge" and "lgd_code" not in d["बिस्टान"]
    d = run("mp-jhabua")                                  # a misspelt mail domain still ties by the mailbox name
    assert d["Ranapur"]["lgd_code"] == "250883" and d["झाबुआ"]["lgd_code"] == "250879"
    d = run("mp-sidhi")
    assert d["Sidhi"]["name"] == "Shri Mahmood Hasan" and d["Rampur Naikin"]["charge"] == "additional charge"
    d = run("mp-damoh")
    assert d["Hatta"]["lgd_code"] == "250771" and d["Tendukheda"]["lgd_code"] == "290462" and d["Damoh"]["last_updated"] == "2026-08-20"
    d = run("mp-umaria")
    assert d["नौरोजाबाद"]["lgd_code"] == "250803" and d["नौरोजाबाद"]["name"] == "श्रीमती ज्योति सिंह"


def test_th_dist_mh_head_layout():
    d = run("mh-ahilyanagar")
    assert len(d) == 16 and all(v.get("lgd_code") for v in d.values())
    assert d["अहिल्यानगर"]["post"] == "Commissioner" and d["अहिल्यानगर"]["lgd_code"] == "251548" and d["अहिल्यानगर"]["name"] == "श्री. यशवंत डांगे"
    assert d["अकोले"]["post"] == "Chief Officer" and d["अकोले"]["email"] == "coakole1@gmail.com"   # Devanagari digit in the mailbox
    assert d["कर्जत"]["lgd_code"] == "275729" and d["कर्जत"]["last_updated"] == "2025-03-18"
    d = run("mh-dharashiv")
    assert d["धाराशिव"]["lgd_code"] == "251569" and d["तुळजापूर"]["phone"] == "02471-244511"
    d = run("mh-palghar")
    assert d["तलासरी"]["lgd_code"] == "276315" and d["तलासरी"]["phone"] == "02521-299620"


def test_th_dist_lgd_match():
    m = mod("th_dist")
    assert m.lgd_of("MP", "Damoh", "Hatta") == "250771"
    assert m.lgd_of("MP", "Sheopur", "Sheopur") == "250673"
    assert m.lgd_of("MP", "Damoh", "Nowhere") is None
    assert m.body_of("नगर पालिका परिषद " + BADWAH + ",जिला खरगोन म.प्र.") == BADWAH
    assert m.body_of("मुख्य नगरपालिका कार्यालय झाबुआ") == "झाबुआ"
