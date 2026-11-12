"""Dadra-Nagar Haveli and Daman-Diu: Diu Municipal Council's office (diu.gov.in/diu-municipal-council/, S3WaaS page of the Diu
district: name, phone, address, email; "Last Updated: 18.10.2022"; archive.s1d.me copy of 2026-11-10). Parser: dforms/ulb2_mh.py
parse_office_page() (kind "office_page"). One "Office" record (role staff), no person named.

Silvassa Municipal Council: dnh.gov.in/silvassa-municipal-council/ is prose only and links the council's own site; dnh.gov.in's
who's who and ddd.gov.in/directory/ name no Silvassa officer (ddd.gov.in names the Chief Officer of Daman, which is not a gap).
dnh.gov.in's public-utility municipality card is left to the S3WaaS reader (ulb2_s3waas).
"""
from dforms import ulb2_mh

METHOD = "pdf text (pypdf) + json api + html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_dd"


def items(get=None):
    return [{"key": f"{MODULE}-diu", "payload": {"reader": MODULE, "kind": "office_page", "url": "https://diu.gov.in/diu-municipal-council/",
                                                "state": "DD", "district": "Diu", "india_only": False}}]


def with_lgd(recs):
    for _, d in recs:
        if d["area"].lower() == "diu":
            d["lgd_code"] = "251271"
    return recs


def parse(html, url):
    return with_lgd(ulb2_mh.parse_office_page(html, "Diu", url, "DD", MODULE))


def fetch(p, get):
    recs, files, why = ulb2_mh.fetch(p, get, MODULE)
    return with_lgd(recs), files, why
