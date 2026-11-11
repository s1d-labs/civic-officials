"""All states: block and cluster education officers (BEO / BEEO / Khand Shiksha Adhikari, BRC and CRC coordinators,
Sub-divisional Education Officers) and the district education officers above them, from the "Education" department pages of
the district portals (S3WaaS). Typical tables: "Officer's Name | Designation | Phone | E-mail" (Gopalganj: DEO + 13 BEOs),
"Block | Office | Phone" (Khargone, Mandya, Siddharthnagar), "BRC | Coordinator | Mobile" (Thoothukudi).
Pages that list only schools (school name + phone) are left out of the seed: they name no officer.
Read by dforms/_field.py (layer "education", level per row: section = cluster (CRC), block = BEO / BRC, district).
Seed: seeds/dept_field_education_s3waas.json (pages saved in archive.s1d.me, 3+ rows on 2026-11-11). One item = one page.
Records: dept education, layer field, field_layer education. Ids dept:field_education_s3waas:<host>:<page>:<serial or row>.
"""
from dforms import _field

MODULE = "field_education_s3waas"
items, fetch = _field.reader(MODULE, "education")
