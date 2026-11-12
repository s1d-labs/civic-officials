"""Uttar Pradesh district portals (<district>.nic.in, prayagrajdivision.nic.in): S3WaaS police-station tables (CUG 94544xxxxx tied to the post, no SHO names; Gautam Buddh Nagar 85959xxxxx, Ghaziabad 96433xxxxx).
One queue item = one district page (its /page/N/ pages included); parsing in police_s3waas.
Record id dept:police_up:<district>:<station>."""
from dforms import police_s3waas

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_up"


def fetch(p, get):
    return police_s3waas.fetch({"state": "UP", **p}, get, M)
