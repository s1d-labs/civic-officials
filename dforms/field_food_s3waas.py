"""All states: food safety officers, designated officers (FSSA) and drugs inspectors that district portals list on their
"Food Safety" / "Drugs Control" pages (S3WaaS). On 2026-11-11 only Kodagu (Karnataka) has such a table in the archive copy:
"Designated Officer | Senior Food Safety Officer | Food Safety Officer" with taluk and mobile. Most district food safety pages
only link PDFs (Tiruvallur: legacy Tamil font, not readable as text; Malda: scheme leaflets).
Read by dforms/_field.py (layer "food", level per row: circle = FSO / DI area, district = designated officer).
Seed: seeds/dept_field_food_s3waas.json. Records: dept health, layer field, field_layer food.
"""
from dforms import _field

MODULE = "field_food_s3waas"
items, fetch = _field.reader(MODULE, "food")
