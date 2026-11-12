"""All states: medical officers and in-charges of PHCs, UPHCs, CHCs, dispensaries and hospitals, and the district health
officers above them, from the "Health" department pages of the district portals (S3WaaS: <district>.nic.in / .gov.in, Delhi
DM sites). Typical tables: "Name of the Block | Name of Ayushman Arogya Mandir | Name of the Incharge Medical Officer/MLHP |
Contact No." (Bandipora: 104 rows), "Name of Institutions | Name of Officer | Designation | Mobile" (Buxar), "Name of the
Officers | Designation | Place of Posting | Mobile No" (Jhargram), "Dispensary | Medical Officer In-charge" (Delhi North West).
Read by dforms/_field.py (column mapping by header words, layer filter "health", level per row: facility / block / district).
Seed: seeds/dept_field_health_s3waas.json = the pages that archive.s1d.me holds and that gave 3+ health rows on 2026-11-11
(payload "expect" = rows / named / phones / levels of that copy). One queue item = one page.
Records: dept health, layer field, field_layer health; area = facility or office; post; name; phone; email; block / tehsil /
district when the table gives them. Ids dept:field_health_s3waas:<host>:<page>:<serial or row>.
"""
from dforms import _field

METHOD = "html table, or pdf text (pdftotext -layout, else pypdf layout) with columns from the header positions"     # source trail (provenance.py): how this reader reads its sources

MODULE = "field_health_s3waas"
items, fetch = _field.reader(MODULE, "health")
