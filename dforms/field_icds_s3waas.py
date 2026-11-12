"""All states except Kerala (Kerala anganwadi workers: dforms/civic_anganwadi_kl.py): ICDS project officers (CDPO / Project
Officer), sector supervisors and district programme officers, from the "ICDS" / "Women and Child Development" pages of the
district portals (S3WaaS) and of city corporations (Surat). Typical tables: "Name of the ICDS Project | Name of the CDPO |
Contact No." (Cooch Behar, 21 projects), "Name of Office | Name of Officer | Designation" (Dhar), "Project | CDPO | Mobile"
(Bhojpur, Reasi, Datia).
Read by dforms/_field.py (layer "icds", level per row: facility = anganwadi centre, section = supervisor sector, block = ICDS
project, district). Seed: seeds/dept_field_icds_s3waas.json (pages saved in archive.s1d.me, 3+ rows on 2026-11-11).
Records: dept women_child, layer field, field_layer icds. Ids dept:field_icds_s3waas:<host>:<page>:<serial or row>.
"""
from dforms import _field

METHOD = "html table, or pdf text (pdftotext -layout, else pypdf layout) with columns from the header positions"     # source trail (provenance.py): how this reader reads its sources

MODULE = "field_icds_s3waas"
items, fetch = _field.reader(MODULE, "icds")
