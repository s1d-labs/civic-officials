"""District portals (S3WaaS): pages that list village front-line workers by name: ASHA and ANM per sub-centre and village,
anganwadi workers per centre, police patil / gram rakshak / chowkidar per village.

Sources found 2026-11-13 (archive.s1d.me copies, measured):
- Siaha, Mizoram, "Health Department" (https://siaha.nic.in/health-dept/): one table "Name of the CHC or PHC | Name & Mobile No.
  of MO | Sl. No. | Name of the Sub Center | Name of the ANM | Mobile No. | Village Name | Name of the ASHA | Mobile No.":
  34 ANMs and 75 ASHAs with mobiles (the MO column is not a village post; it stays in table_row).
- Siaha, "List of Anganwadi Workers & Centres" (https://siaha.nic.in/list-of-anganwadi-workers-centres/): two tables (Siaha
  and Tuipang ICDS projects), "S.No | Name of Anganwadi Centre | Name of Anganwadi Worker": 115 named workers, no phones.
  The page says "Last Updated: 23.10.2019".
Read by dforms/_vilwork.py (header words -> columns; each person column gives its own record). Payload "post" sets the post
for a plain "Name" column. Seed: seeds/dept_vil_s3waas_workers.json.
Records: dept health / women_child / police, level village, layer village_worker. Ids
dept:vil_s3waas_workers:<host>:<page slug>:t<table>-r<row>:<post slug>.
"""
from urllib.parse import urlparse

from dforms import _esw, _field, _vilwork

METHOD = "html table (header words -> person, phone and area columns)"     # source trail (provenance.py)

MODULE = "vil_s3waas_workers"


def parse(html, url, p):
    tag = p.get("tag") or _esw.slug(urlparse(url).path)[-50:] or "page"
    recs = _vilwork.html_records(MODULE, html, url, p, tag)
    lu = _field.last_updated(html)
    if lu:
        for _, d in recs:
            d["last_updated"] = lu
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    host = urlparse(p["url"]).netloc
    tag = p.get("tag") or _esw.slug(urlparse(p["url"]).path)[-50:] or "page"
    files = [_esw.keep(MODULE, f"{host}-{tag}", r.content)]
    recs = parse(r.text, p["url"], p)
    return recs, files, "" if recs else "no worker table"
