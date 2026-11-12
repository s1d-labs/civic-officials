"""Goa: Chief Officers of municipal councils from the charge orders of the Department of Personnel, Government of Goa
(www.goa.gov.in/wp-content/uploads/2026/11/, archive.s1d.me copies of 2026-11-10). Parser: dforms/ulb2_mh.py parse_order()
(kind "charge_order"). Two orders read: Valpoi (dated 21.10.2026) and Pernem (dated 04.02.2026). Each gives one "Chief Officer"
record (role head) with the officer's own post in own_post and charge "additional charge".

Not read: the table orders ("Posting order of JSO dated 30-06-2026" names Chief Officers of Bicholim, Sankhali, Mapusa, Quepem,
Curchorem, Cuncolim and Canacona), because their text comes out with the columns mixed, so the name and the new post cannot be paired
safely. Goa has no statewide list: dma.goa.gov.in has no DNS record; goaulbservice.gov.in shows staff only in a session (see ulb_ga).
www.goa.gov.in answers 403 from Germany (2026-11-11): india_only.
"""
from dforms import ulb2_mh

METHOD = "pdf text (pypdf plain mode)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_ga"
GOA = "https://www.goa.gov.in/wp-content/uploads/2026/11/"
ORDERS = (("valpoi", "transfer%20order%20of%20Chief%20Officer%20Valpoi%20Municipal%20Council.pdf"),
          ("pernem", "transfer%20order%20BDO.pdf"))
LGD = {"valpoi": "252079", "pernem": "252057", "bicholim": "252075", "sankhali": "252077", "mapusa": "252061", "ponda": "252082"}


def with_lgd(recs):
    for _, d in recs:
        d.setdefault("lgd_code", LGD.get(d["area"].lower()))
        if not d["lgd_code"]:
            del d["lgd_code"]
    return recs


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "kind": "charge_order", "url": GOA + f, "state": "GA",
                                                "district": "North Goa", "india_only": True}} for k, f in ORDERS]


def parse(text, url, district="North Goa"):
    return with_lgd(ulb2_mh.parse_order(text, district, url, "GA", MODULE))


def fetch(p, get):
    recs, files, why = ulb2_mh.fetch(p, get, MODULE)
    return with_lgd(recs), files, why
