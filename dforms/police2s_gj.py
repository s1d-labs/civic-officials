"""Gujarat Police unit sites that seeds/dept_police_gj.json does not list yet: the same CMS (https://<unit>.gujarat.gov.in/<unit>/
CMS.aspx?orgchart=true, org chart + one 'office contact' page per designation, names and mobiles of PI / PSI station posts, circle
inspectors, DySP divisions). Parsing is police_gj.fetch; this module only renames the records and files to police2s_gj, so the
two seed lists never clash. Units: 14 SP districts whose host names resolve in DNS (2026-11-11) and the railway SP unit.
Still missing: Devbhumi Dwarka, Gir Somnath, Kutch East (Gandhidham) and Western Railway Vadodara: no sp<name>.gujarat.gov.in
host was found. India only (the *.gujarat.gov.in police hosts time out from Germany). One queue item = one unit
(~100-160 requests). Record id dept:police2s_gj:<unit>:<designation id>."""
from dforms import police_gj

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

M = "police2s_gj"


def fetch(p, get):
    recs, files, why = police_gj.fetch(p, get)
    old = f"dept:{police_gj.M}:"
    recs = [(f"dept:{M}:" + rid[len(old):] if rid.startswith(old) else rid, d) for rid, d in recs]
    files = [(name.replace(f"/{police_gj.M}/", f"/{M}/", 1), body, ctype) for name, body, ctype in files]
    return recs, files, why
