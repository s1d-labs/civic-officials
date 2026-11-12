"""Source trail positions for readers that walk HTML themselves (not through _esw.grid or officials.tables).

tr_pos(tr) -> {"table": n, "row": m}: n = the table's place among the page's <table> elements (1-based, document order, nested
tables counted: the same number as _esw.table_no and officials.tables give), m = the row's <tr> number inside its own table
(1-based, header row counted). A <tr> outside any table gives {"tr": k} (its place among the page's <tr> elements).
"""
from dforms import _esw


def tr_pos(tr):
    t = tr.find_parent("table")
    if t is None:
        return {"tr": len(tr.find_all_previous("tr")) + 1}
    nos = t.__dict__.get("_trail_rows")
    if nos is None:
        nos = {id(x): i for i, x in enumerate((x for x in t.find_all("tr") if x.find_parent("table") is t), 1)}
        t.__dict__["_trail_rows"] = nos
        t.__dict__["_trail_no"] = _esw.table_no(t)
    return {"table": t.__dict__["_trail_no"], "row": nos.get(id(tr))}
