"""Queue items of the `bundle` task (bundle.py): one item per shard of the saved source copies, plus one `index` item.

Owner, 2026-11-14: "The actual source files we should keep an updated zip in the bucket, which we can serve anytime via a signed
link." Runs on dev-vps-3 (needs psql on DB civic). Reads DB civic with ONE query (QUERY; about 2 s; no
scrape_hub query, no write anywhere unless --insert):
  - civic.source_copy: every saved copy (sha256, project, bucket key, url, final url, content type, bytes, fetch time); one
    row per sha256 (the same bytes saved by two projects: the oldest copy, all project names kept);
  - civic.raw_src: the records made from each source (count and up to 3 record ids);
  - civic.source_trail_src + civic.source_trail: the readers that read each source, and archive.s1d.me captures of the same
    url (archive-first hits), if any.
Nothing here runs after a refresh: the owner (or a weekly timer, if the owner wants one) runs it and queues the items.
Shards are append-only (owner, 2026-11-14). The builder reads, with the read-only bucket key (as audit.py --local does),
the last bundle/assignment.csv.gz (sha256 -> shard; written by the index item) and bundle/index.json (list hash per shard):
  - every sha256 in the assignment keeps its shard (a source that left the database stays there, from the assignment's row);
  - new sha256 values fill new shards s<NNNNN> (after the highest id so far), in fetched_at order, then sha256; a shard closes
    at SHARD_MAX_FILES sources, SHARD_MAX_BYTES original bytes or SHARD_MAX_PAYLOAD bytes of payload rows;
  - an item is made only for a shard whose list hash is not the one in index.json (new shards; an old shard only when the
    bucket lost its state), plus the index item. A first run (no assignment, no index) needs --first.
The item carries its whole source list (compact rows, < 0.4 MB), so the task needs no other list. Item key
"bundle:<shard>:<list hash 12>": a shard whose list did not change keeps its key; the task also skips a shard whose list hash
equals the one in bundle/shards/<shard>.json.

  python seeds/build_bundle.py                 counts and payload sizes only
  python seeds/build_bundle.py --out FILE      also write the items (seeds/bundle_items.json is not committed: it is large)
  python seeds/build_bundle.py --sample 3 --out FILE    3 small shards of 5 sources each + their index item (a local try)
  --first                                      allow a first run (no assignment.csv.gz and no index.json in the bucket)
  --keys FILE                                  read-only bucket key (default /etc/scrape-hub/member-keys/sarthak.env)
  python seeds/build_bundle.py --insert        also put the items in the hub queue of civic-officials-bundle (INSERT ... ON
                                               CONFLICT DO NOTHING) and remove its PENDING items of older lists; the project
                                               must exist (Setup workflow) and the owner must agree first
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zlib
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bundle  # noqa: E402

PROJECT = "civic-officials-bundle"


def psql(db, sql):
    """Rows of a one-column query that returns json; streamed (FETCH_COUNT), nothing kept by psql."""
    p = subprocess.Popen(["psql", "-d", db, "-XAt", "-v", "ON_ERROR_STOP=1", "-v", "FETCH_COUNT=20000", "-c",
                          "set statement_timeout = '15min'", "-c", sql], stdout=subprocess.PIPE, text=True)
    for ln in p.stdout:
        if ln.startswith("{") or ln.startswith("["):
            yield json.loads(ln)
    if p.wait():
        raise SystemExit(f"psql on {db} failed")


# One statement on DB civic (2026-11-14: 0.5 s for the aggregates, about 2 s in all): no scrape_hub query, no other table.
QUERY = """
with c as (select distinct on (sha256) sha256, bucket_key, url, final_url, content_type, bytes, fetched_at from civic.source_copy
           where bucket_key is not null order by sha256, fetched_at nulls last, project),
     p as (select sha256, string_agg(project, ';' order by project) projects from civic.source_copy group by sha256),
     r as (select src_sha256 sha256, count(*) n, (array_agg(record_id order by record_id))[1:3] ids from civic.raw_src
           where src_sha256 is not null group by src_sha256),
     t as (select s.sha256, string_agg(distinct t.reader, ';') readers from civic.source_trail_src s
           join civic.source_trail t using (trail_id) where s.sha256 is not null and coalesce(t.reader, '') <> '' group by s.sha256),
     a as (select url, trim(max(archive_url) || ' ' || coalesce(max(archive_captured), '')) cap from civic.source_trail_src
           where archive_url is not null group by url)
select json_build_array(c.sha256, c.bucket_key, coalesce(c.url, ''), coalesce(c.final_url, ''), coalesce(c.content_type, ''),
       coalesce(c.bytes, 0), coalesce(to_char(c.fetched_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), ''), p.projects,
       coalesce(t.readers, ''), coalesce(r.n, 0), coalesce(r.ids, '{}'), coalesce(a1.cap, a2.cap, ''))
from c join p using (sha256) left join r using (sha256) left join t using (sha256)
left join a a1 on a1.url = c.url left join a a2 on a2.url = c.final_url
order by c.sha256"""


def db_rows():
    """{sha256: payload row} of every saved copy (one query on DB civic)."""
    out = {}
    for sha, key, url, final, ctype, nbytes, at, projs, rd, n, ids, cap in psql("civic", QUERY):
        out[sha] = bundle.row(sha, key, url, final, ctype, nbytes, at, projs, rd, n, ids, cap)
    return out


def assignment_row(a):
    """A payload row for a source that left the database, from its assignment.csv.gz row."""
    return bundle.row(a["sha256"], a.get("bucket_copy", ""), a.get("url", ""), a.get("final_url", ""), a.get("content_type", ""),
                      a.get("bytes") or 0, a.get("fetched_at", ""), "", "", 0, [], "")


def row_size(r):
    return len(json.dumps(r, ensure_ascii=False).encode()) + 1


def plan(rows, assignment, index_hashes, max_files=bundle.SHARD_MAX_FILES, max_bytes=bundle.SHARD_MAX_BYTES,
         max_payload=bundle.SHARD_MAX_PAYLOAD):
    """(shards {id: rows}, hashes {id: list hash}, changed [ids]) from the database rows {sha: row}, the last assignment
    {sha: {"shard", ...}} and the last index's list hashes {id: hash}. Pure: tested without the bucket."""
    shards = {}
    for sha, a in assignment.items():
        shards.setdefault(a["shard"], []).append(rows.get(sha) or assignment_row(a))
    new = sorted((r for sha, r in rows.items() if sha not in assignment), key=lambda r: (r[8] or "9999", r[0]))
    n = max([int(i[1:]) for i in shards if bundle.SHARD_ID.match(i)] or [0])
    cur, cur_bytes, cur_payload = None, 0, 0
    for r in new:
        size = row_size(r)
        if cur is None or len(shards[cur]) >= max_files or cur_bytes + r[6] > max_bytes or cur_payload + size > max_payload:
            n += 1
            cur, cur_bytes, cur_payload = f"s{n:05d}", 0, 0
            shards[cur] = []
        shards[cur].append(r)
        cur_bytes += r[6]
        cur_payload += size
    hashes = {i: bundle.list_hash(v) for i, v in shards.items()}
    changed = sorted(i for i, h in hashes.items() if index_hashes.get(i) != h)
    return shards, hashes, changed


def read_bucket(keys, first):
    """(assignment {sha: row}, index list hashes {id: hash}) of the last build, read with the read-only key."""
    import csv
    import gzip
    import io
    import requests
    import audit
    env, sess = audit.read_env(keys), requests.Session()
    base = f"{PROJECT}/{bundle.PREFIX}/"
    raw_a, raw_i = audit.s3_get(env, base + "assignment.csv.gz", sess), audit.s3_get(env, base + "index.json", sess)
    if raw_a is None and raw_i is None:
        if not first:
            raise SystemExit("no assignment.csv.gz and no index.json in the bucket: a first run? (then add --first)")
        return {}, {}
    if raw_a is None or raw_i is None:
        raise SystemExit("the bucket has only one of assignment.csv.gz and index.json: the last index item did not finish?")
    assignment = {a["sha256"]: a for a in csv.DictReader(io.StringIO(gzip.decompress(raw_a).decode("utf-8")))}
    index = {s["shard"]: s["list_hash"] for s in json.loads(raw_i).get("shards", [])}
    return assignment, index


def items(shards, hashes, changed):
    out = []
    for shard in changed:
        rows, h = shards[shard], hashes[shard]
        out.append({"key": f"bundle:{shard}:{h[:12]}", "payload": {"kind": "shard", "shard": shard, "list_hash": h,
                                                                    "expected": len(rows), "bytes": sum(r[6] for r in rows),
                                                                    "cols": bundle.COLS, "rows": rows}})
    ih = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    out.append({"key": f"bundle-index:{ih[:12]}", "payload": {"kind": "index", "shards": hashes, "expected": 1}})
    return out


def sample(rows, n, per=5):
    """n small shards of `per` small sources each (a local try with few downloads; first-run ids)."""
    small = sorted(rows.values(), key=lambda r: (r[6], r[0]))[:n * per]
    shards = {f"s{i + 1:05d}": small[i * per:(i + 1) * per] for i in range(n)}
    return shards, {i: bundle.list_hash(v) for i, v in shards.items()}, sorted(shards)


def insert(its):
    """Queue the items (owner's OK first) and drop PENDING items of older lists. Same partition rule as the hub's seed endpoint."""
    rows = [json.dumps([it["key"], zlib.crc32(it["key"].encode()) % 1_000_000, json.dumps(it["payload"], ensure_ascii=False)],
                       ensure_ascii=False) for it in its]
    keys = "array[" + ",".join("'" + it["key"].replace("'", "''") + "'" for it in its) + "]"
    ins = ("insert into queue (project, key, partition_id, payload) "
           f"select '{PROJECT}', j->>0, (j->>1)::int, (j->>2)::jsonb from t on conflict (project, key) do nothing")
    drop = f"delete from queue where project = '{PROJECT}' and status = 'pending' and not (key = any({keys}))"
    data = "\n".join(r.replace("\\", "\\\\") for r in rows) + "\n"
    psql_cmd = ["psql"] if os.environ.get("USER") == "postgres" else ["sudo", "-n", "runuser", "-u", "postgres", "--", "psql"]
    r = subprocess.run(psql_cmd + ["-d", "scrape_hub", "-X", "-v", "ON_ERROR_STOP=1", "-c", "create temp table t (j jsonb)",
                                   "-c", "copy t from stdin", "-c", ins, "-c", drop], input=data, text=True, capture_output=True)
    print(r.stdout.strip() or r.stderr.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--first", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="counts as on a first run, without reading the bucket (no --insert)")
    ap.add_argument("--keys", default="/etc/scrape-hub/member-keys/sarthak.env")
    ap.add_argument("--insert", action="store_true")
    a = ap.parse_args()
    if a.fresh and a.insert:
        raise SystemExit("--fresh is for counts only")
    rows = db_rows()
    assignment = {}
    if a.sample:
        shards, hashes, changed = sample(rows, a.sample)
    else:
        assignment, index = ({}, {}) if a.fresh else read_bucket(a.keys, a.first)
        shards, hashes, changed = plan(rows, assignment, index)
    its = items(shards, hashes, changed)
    sizes = sorted(len(json.dumps(i, ensure_ascii=False).encode()) for i in its)
    old_ids = {x["shard"] for x in assignment.values()}
    ch = [shards[i] for i in changed] or [[]]
    raw = sorted(sum(r[6] for r in v) for v in ch)
    counts = {"db_sources": len(rows), "assigned_before": len(assignment),
              "left_db": sum(1 for sha in assignment if sha not in rows),
              "new_sources": sum(1 for sha in rows if sha not in assignment), "shards": len(shards),
              "shards_queued": len(changed), "shards_new": sum(1 for i in changed if i not in old_ids),
              "items": len(its), "item_bytes_max": sizes[-1], "item_bytes_median": sizes[len(sizes) // 2],
              "item_bytes_total": sum(sizes), "queued_sources": sum(len(v) for v in ch), "queued_raw_bytes": sum(raw),
              "shard_raw_bytes_max": raw[-1], "shard_raw_bytes_median": raw[len(raw) // 2],
              "shard_files_min": min(len(v) for v in ch), "shard_files_median": sorted(len(v) for v in ch)[len(ch) // 2],
              "shard_files_max": max(len(v) for v in ch),
              "content_types": dict(Counter(r[5].split(";")[0].strip().lower() for v in ch for r in v).most_common(6))}
    print(json.dumps(counts, indent=1))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(its, f, ensure_ascii=False)
        print("wrote", a.out, os.path.getsize(a.out), "bytes")
    if a.insert:
        insert(its)


if __name__ == "__main__":
    sys.exit(main())
