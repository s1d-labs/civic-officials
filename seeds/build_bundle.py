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
A shard = the sources whose sha256 starts with the same SHARD_DIGITS hex digits (2: 256 shards of about 950 sources and 90 MB
of original bytes). The item carries its whole source list (compact rows, about 0.3-0.5 MB), so the task needs no other list.
Item key "bundle:<shard>:<list hash 12>": a shard whose source list did not change keeps its key, so a done item is not queued
again; the task also skips a shard whose list hash equals the one in the bucket (bundle/shards/<shard>.json).

  python seeds/build_bundle.py                 counts and payload sizes only
  python seeds/build_bundle.py --out FILE      also write the items (seeds/bundle_items.json is not committed: it is large)
  python seeds/build_bundle.py --sample 3 --out FILE    3 small shards of 5 sources each + their index item (a local try)
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


def build(digits=bundle.SHARD_DIGITS):
    shards, n_rec, n_rd, n_arch, n_multi, hosts, size = {}, 0, 0, 0, 0, set(), 0
    for sha, key, url, final, ctype, nbytes, at, projs, rd, n, ids, cap in psql("civic", QUERY):
        row = bundle.row(sha, key, url, final, ctype, nbytes, at, projs, rd, n, ids, cap)
        shards.setdefault(sha[:digits], []).append(row)
        n_rec += n > 0
        n_rd += bool(rd)
        n_arch += bool(cap)
        n_multi += ";" in projs
        hosts.add(row[2])
        size += int(nbytes or 0)
    return shards, {"sources": sum(len(v) for v in shards.values()), "bytes": size, "hosts": len(hosts), "with_records": n_rec,
                    "with_reader": n_rd, "with_archive": n_arch, "multi_project": n_multi}


def items(shards):
    out, hashes = [], {}
    for shard, rows in sorted(shards.items()):
        h = bundle.list_hash(rows)
        hashes[shard] = h
        out.append({"key": f"bundle:{shard}:{h[:12]}", "payload": {"kind": "shard", "shard": shard, "list_hash": h,
                                                                    "expected": len(rows), "bytes": sum(r[6] for r in rows),
                                                                    "cols": bundle.COLS, "rows": rows}})
    ih = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    out.append({"key": f"bundle-index:{ih[:12]}", "payload": {"kind": "index", "shards": hashes, "expected": 1}})
    return out


def sample(shards, n, per=5):
    """n small shards of `per` small sources each (a local try with few downloads)."""
    out = {}
    for shard in sorted(shards)[:n]:
        out[shard] = sorted(shards[shard], key=lambda r: r[6])[:per]
    return out


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
    ap.add_argument("--digits", type=int, default=bundle.SHARD_DIGITS, help="hex digits per shard (1 = 16 shards, 2 = 256)")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--insert", action="store_true")
    a = ap.parse_args()
    shards, counts = build(a.digits)
    if a.sample:
        shards = sample(shards, a.sample)
    its = items(shards)
    sizes = sorted(len(json.dumps(i, ensure_ascii=False).encode()) for i in its)
    raw = sorted(sum(r[6] for r in rows) for rows in shards.values())
    counts.update({"shards": len(shards), "items": len(its), "item_bytes_max": sizes[-1], "item_bytes_median": sizes[len(sizes) // 2],
                   "item_bytes_total": sum(sizes), "shard_sources_max": max(len(r) for r in shards.values()),
                   "shard_raw_bytes_max": raw[-1], "shard_raw_bytes_median": raw[len(raw) // 2],
                   "content_types": dict(Counter(r[5].split(";")[0].strip().lower() for rows in shards.values() for r in rows).most_common(8))})
    print(json.dumps(counts, indent=1))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(its, f, ensure_ascii=False)
        print("wrote", a.out, os.path.getsize(a.out), "bytes")
    if a.insert:
        insert(its)


if __name__ == "__main__":
    sys.exit(main())
