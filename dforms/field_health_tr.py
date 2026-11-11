"""Tripura: Health & Family Welfare Department "Who is Who" (health.tripura.gov.in/who_is_who): state officers, the Chief
Medical Officers of the 8 districts and the medical superintendents of district and sub-divisional hospitals, with phone and
mobile. 33 rows with a name or phone in the archive copy of 2026-11-11. One queue item (one GET).
Read by dforms/_field.py (layer "health"). Records: dept health, layer field, field_layer health, state TR.
"""
from dforms import _field

MODULE = "field_health_tr"
items, fetch = _field.reader(MODULE, "health", state="TR")
