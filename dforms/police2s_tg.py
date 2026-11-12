"""Telangana district portals (<district>.telangana.gov.in, S3WaaS) with police pages that police_tg does not list: Kamareddy
(public-utility cards: SP, SDPOs, circle inspectors, stations), Nirmal (police contact directory: SP, Addl. SP, DSPs) and Rajanna
Sircilla (SP office, SDPO). CUG mobiles and station / office emails; no officer names on any of them (checked on the archive copies of
2026-11-05). Parsing is police_s3waas. Works from outside India. One queue item = one district page (its /page/N/ pages included).
Record id dept:police2s_tg:<district>:<station or office>."""
from dforms import police_s3waas

METHOD = "html table + html cards (S3WaaS public utility), paged /page/N/"     # source trail (provenance.py): how this reader reads its sources

M = "police2s_tg"


def fetch(p, get):
    return police_s3waas.fetch({"state": "TG", **p}, get, M)
