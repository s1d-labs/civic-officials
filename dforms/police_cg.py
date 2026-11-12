"""Chhattisgarh district portals (<district>.gov.in, gaurela-pendra-marwahi.cg.gov.in): S3WaaS police tables and public-utility cards. CUG series 94791-9xxxx (post-based, no names), except Balrampur's directory (names). Durg answers only from India; the rest were saved from India by archive.s1d.me.
One queue item = one district page (its /page/N/ pages included); parsing in police_s3waas.
Record id dept:police_cg:<district>:<station>."""
from dforms import police_s3waas

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_cg"


def fetch(p, get):
    return police_s3waas.fetch({"state": "CG", **p}, get, M)
