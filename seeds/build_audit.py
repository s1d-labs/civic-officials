"""Queue items of the `audit` task (audit.py): one item = a batch of saved sources, each with the records made from it.

Runs on dev-vps-3 (needs psql on scrape_hub and civic). Reads:
  1. the source index records "src:<sha256>" of the civic-officials-* projects in scrape_hub (records_pkey: project = X and
     record_id LIKE 'src:%', one project at a time): the bucket file, url and content type of each saved source;
  2. the data records with a src from civic.official_raw, the full copy of the family's records that civic-india/officials_pull.sh
     makes (not the live hub table): name, phones, e-mail and the trail of each record;
  3. the reader of each trail (trail records in the same copy).
A source is queued when it has a saved copy and at least one record. Records that name a bucket copy themselves (src.file,
provenance.file_src) use that copy. Small sources go together: at most 50 sources and 2000 records per item.

  python seeds/build_audit.py                  counts only
  python seeds/build_audit.py --out FILE       also write the items (seeds/audit_items.json is not committed: it is large)
  python seeds/build_audit.py --sample 20 --out FILE    20 sources, one per reader, of different kinds (for a local try)
  python seeds/build_audit.py --insert         also put the items in the hub queue of civic-officials-audit (INSERT ... ON
                                               CONFLICT DO NOTHING, like civic-officials-whoswho-direct); the project must exist
                                               (Setup workflow) and the owner must agree first
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zlib
from collections import Counter, defaultdict

PROJECT = "civic-officials-audit"
MAX_SOURCES, MAX_RECORDS, MAX_BYTES = 50, 2000, 400_000
NAME = "coalesce(nullif(data->>'name',''), nullif(data->>'name_en',''), nullif(data->>'officer_name',''), nullif(data->>'name_regional',''))"
PHONES = ("concat_ws(',', data->>'phone', data->>'mobile', data->>'office_phone', data->>'residence_phone', data->>'landline', "
          "data->>'phone_office', data->>'cug', data->>'contact')")


def psql(db, sql):
    """Rows of a one-column query that returns json; streamed (FETCH_COUNT), nothing kept by psql."""
    p = subprocess.Popen(["psql", "-d", db, "-XAt", "-v", "ON_ERROR_STOP=1", "-v", "FETCH_COUNT=20000", "-c",
                          "set statement_timeout = '15min'", "-c", sql], stdout=subprocess.PIPE, text=True)
    for ln in p.stdout:
        if ln.startswith("{") or ln.startswith("["):
            yield json.loads(ln)
    if p.wait():
        raise SystemExit(f"psql on {db} failed")


def projects():
    return [r[0] for r in psql("scrape_hub", "select json_build_array(name) from projects where name like 'civic-officials-%' "
                                             "and name <> 'civic-officials-audit' order by name")]


def src_index(projs):
    out = {}
    for p in projs:
        q = (f"select json_build_array(record_id, data->>'file', data->>'url', data->>'content_type', data->>'bytes') from records "
             f"where project = '{p}' and record_id like 'src:%'")
        for rid, file, url, ctype, size in psql("scrape_hub", q):
            sha = rid[4:]
            if file and sha not in out:
                out[sha] = {"sha256": sha, "project": p, "file": file, "url": url or "", "content_type": ctype or "",
                            "bytes": int(size or 0)}
    return out


def records(shas=None):
    cond = ""
    if shas:
        cond = " and data->'src'->>'sha256' in (" + ",".join(f"'{s}'" for s in shas) + ")"
    q = (f"select json_build_array(data->'src'->>'sha256', project, record_id, data->>'trail', {NAME}, {PHONES}, data->>'email', "
         f"data->'src'->>'file', data->'src'->>'url') from civic.official_raw where data ? 'src' and record_id not like 'src:%' "
         f"and record_id not like 'trail:%' and coalesce(data->>'type', '') not in ('source_copy', 'trail', 'audit_source'){cond}")
    return psql("civic", q)


def readers():
    return {r[0]: r[1] for r in psql("civic", "select json_build_array(record_id, data->>'reader') from civic.official_raw "
                                              "where record_id like 'trail:%'")}


def common_prefix(ids):
    if not ids:
        return ""
    a, b = min(ids), max(ids)
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return a[:i]


def build(sample=0, projs=None):
    projs = projs or projects()
    index = src_index(projs)
    trail_reader = readers()
    by_sha = defaultdict(list)
    meta = {}
    no_copy = Counter()
    for sha, proj, rid, trail, name, phones, email, file, url in records():
        if not sha:
            continue
        by_sha[sha].append((rid, name or "", phones or "", email or ""))
        m = meta.setdefault(sha, {"trails": Counter(), "project": proj, "file": file, "url": url})
        m["trails"][trail_reader.get(trail or "", "")] += 1
    sources = []
    for sha, recs in by_sha.items():
        m = meta[sha]
        s = index.get(sha)
        if s is None and m["file"]:          # the reader read a bucket copy itself: src.file = "<project>/<path>"
            proj, _, path = m["file"].partition("/")
            s = {"sha256": sha, "project": proj, "file": path, "url": m["url"] or "", "content_type": "", "bytes": 0}
        if s is None:
            no_copy[m["project"]] += 1
            continue
        reader = m["trails"].most_common(1)[0][0]
        ids = [r[0] for r in recs]
        pre = common_prefix(ids)
        sources.append({**s, "reader": reader, "records": len(recs), "id_prefix": pre,
                        "recs": [[r[0][len(pre):], r[1], r[2], r[3]] for r in recs]})
    if sample:
        sources = pick(sources, sample)
    return sources, {"projects": len(projs), "src_index": len(index), "sources_with_records": len(by_sha),
                     "records": sum(len(v) for v in by_sha.values()), "sources_without_copy": sum(no_copy.values()),
                     "without_copy_by_project": dict(no_copy.most_common(10))}


def pick(sources, n):
    """n sources with >= 3 records: one per reader, kinds (content types) spread, larger sources first."""
    def kind(s):
        c, f = (s["content_type"] or "").lower(), s["file"].lower()
        return "pdf" if "pdf" in c or ".pdf" in f else "json" if "json" in c or ".json" in f else "html" if "html" in c or ".html" in f else "other"
    best = {}
    for s in sorted(sources, key=lambda s: (-s["records"], s["sha256"])):
        if s["records"] >= 3 and s["records"] <= 5000:
            best.setdefault(s["reader"], s)
    by_kind = defaultdict(list)
    for s in sorted(best.values(), key=lambda s: hashlib.sha256(s["reader"].encode()).hexdigest()):
        by_kind[kind(s)].append(s)
    out = []
    while len(out) < n and any(by_kind.values()):
        for k in ("html", "pdf", "json", "other"):
            if by_kind[k] and len(out) < n:
                out.append(by_kind[k].pop(0))
    return out


def items(sources):
    out, cur, n_rec, n_bytes = [], [], 0, 0

    def flush():
        nonlocal cur, n_rec, n_bytes
        if cur:
            key = "audit:" + (cur[0]["sha256"] if len(cur) == 1 else
                              hashlib.sha256("".join(s["sha256"] for s in cur).encode()).hexdigest()[:24] + f":{len(cur)}")
            out.append({"key": key, "payload": {"sources": cur, "expected": len(cur)}})
        cur, n_rec, n_bytes = [], 0, 0
    for s in sorted(sources, key=lambda s: (s["project"], s["records"] > MAX_RECORDS, s["sha256"])):
        size = len(json.dumps(s, ensure_ascii=False).encode())
        if cur and (len(cur) >= MAX_SOURCES or n_rec + s["records"] > MAX_RECORDS or n_bytes + size > MAX_BYTES):
            flush()
        cur.append(s)
        n_rec += s["records"]
        n_bytes += size
    flush()
    return out


def insert(its):
    """Queue the items in the hub (owner's OK first). Same partition rule as the hub's seed endpoint."""
    rows = [json.dumps([it["key"], zlib.crc32(it["key"].encode()) % 1_000_000, json.dumps(it["payload"], ensure_ascii=False)],
                       ensure_ascii=False) for it in its]
    sql = ("create temp table t (j jsonb); copy t from stdin; insert into queue (project, key, partition_id, payload) "
           f"select '{PROJECT}', j->>0, (j->>1)::int, (j->>2)::jsonb from t on conflict (project, key) do nothing;")
    data = "\n".join(r.replace("\\", "\\\\") for r in rows) + "\n"
    r = subprocess.run(["psql", "-d", "scrape_hub", "-X", "-v", "ON_ERROR_STOP=1", "-c", sql], input=data, text=True,
                       capture_output=True)
    print(r.stdout.strip() or r.stderr.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--projects", help="comma-separated project names (default: every civic-officials-* project)")
    ap.add_argument("--insert", action="store_true")
    a = ap.parse_args()
    sources, counts = build(a.sample, a.projects.split(",") if a.projects else None)
    its = items(sources)
    sizes = sorted(len(json.dumps(i, ensure_ascii=False).encode()) for i in its)
    counts.update({"sources_queued": len(sources), "records_queued": sum(s["records"] for s in sources), "items": len(its),
                   "item_bytes_max": sizes[-1] if sizes else 0, "item_bytes_total": sum(sizes),
                   "by_project": dict(Counter(s["project"] for s in sources).most_common()),
                   "readers": len({s["reader"] for s in sources})})
    print(json.dumps(counts, indent=1))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(its, f, ensure_ascii=False)
        print("wrote", a.out, os.path.getsize(a.out), "bytes")
    if a.insert:
        insert(its)


if __name__ == "__main__":
    sys.exit(main())
