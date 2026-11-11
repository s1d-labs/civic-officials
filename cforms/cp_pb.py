"""Punjab: phones and addresses of ward members from the municipal corporations' own sites. Bathinda: www.mcbathinda.com/
Councillors.aspx, one table "WARD NO. | NAME OF MC | DESIGNATION | ADDRESS | MOBILE NO" (the 2021 council, the same members as
cforms/pb.py). Amritsar and Jalandhar already give phones through cforms/cn_pb.py. The other corporations (Mohali, Hoshiarpur,
Moga, Abohar, Batala, Pathankot, Kapurthala, Barnala) have no saved councillor page in archive.s1d.me (checked 2026-11-11).
One queue item = one body: payload {"kind": "form-cp_pb", "state": "PB", "url", "body" (the name cforms/pb.py gives), "lgd_code",
"slug" (cforms/pb.py's body slug, for record_for)}. Seeds: seeds/councillors_cp_pb.json."""
import gzip
from urllib.parse import urlsplit

from cforms import cp_common as cp


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/PB/cp/{urlsplit(p['url']).hostname}-{cp.slug(p['body'])}.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = cp.table_members(r.text, "PB", p["body"], p["url"], lgd_code=p.get("lgd_code"), record_prefix=f"councillor:PB:{p['slug']}")
    good = cp.useful(recs)
    return cp.keyed("PB", p["slug"], good), files, "" if good else ("no member table" if not recs else "no contacts listed")
