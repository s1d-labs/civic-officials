"""Telangana district portals (<district>.telangana.gov.in): S3WaaS police tables (Gadwal, Medak, Siddipet, Nizamabad) and public-utility cards paged with /page/N/ (Hyderabad City, Jangaon). Station emails sho-<ps>@tspolice.gov.in, CUG 87126xxxxx / 94906xxxxx, no names.
One queue item = one district page (its /page/N/ pages included); parsing in police_s3waas.
Record id dept:police_tg:<district>:<station>."""
from dforms import police_s3waas

METHOD = "html table + html cards (S3WaaS public utility), paged /page/N/"     # source trail (provenance.py): how this reader reads its sources

M = "police_tg"


def fetch(p, get):
    return police_s3waas.fetch({"state": "TG", **p}, get, M)
