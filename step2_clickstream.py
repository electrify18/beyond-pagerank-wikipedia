"""
STEP 2 - Download the monthly clickstream dumps and aggregate them with MapReduce.

Clickstream row:  prev <TAB> curr <TAB> type <TAB> n
   type = link     (prev is an article that links to curr)
          external (prev is other-search / other-external / other-empty ...)
          other

Mapper   : keeps rows whose destination article is in our subgraph and emits
           (key, n) pairs - per-article totals and per-edge click counts.
Combiner : sums values per key in memory as the file streams by (in-mapper
           combining - the standard trick so ~30M rows never sit in RAM).
Reducer  : sums the values per key.

Outputs (per month)
  data/attention_<month>.tsv   title, total, link_in_all, link_in_sub, search, external, other
  data/edge_clicks_<month>.tsv src, dst, n   (links inside the subgraph only)
  data/clickstream_meta_<month>.json
"""
import argparse
import gzip
import json
import time
from collections import defaultdict

import requests
from tqdm import tqdm

import config

ATTENTION_FIELDS = ["total", "link_in_all", "link_in_sub", "search", "external", "other"]


class MonthNotAvailable(Exception):
    pass


def raw_path(month):
    return config.RAW_DIR / f"clickstream-enwiki-{month}.tsv.gz"


def download(month):
    dest = raw_path(month)
    if dest.exists():
        print(f"[{month}] already downloaded ({dest.stat().st_size / 1e6:.0f} MB)")
        return dest
    url = config.CLICKSTREAM_URL.format(m=month)
    r = requests.get(url, stream=True, timeout=60, headers={"User-Agent": config.USER_AGENT})
    if r.status_code == 404:
        raise MonthNotAvailable(f"{month} clickstream not published yet: {url}")
    r.raise_for_status()
    tmp = dest.with_suffix(".part")
    total = int(r.headers.get("content-length", 0))
    with open(tmp, "wb") as f, tqdm(total=total, unit="B", unit_scale=True,
                                    desc=f"download {month}") as bar:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
            bar.update(len(chunk))
    tmp.replace(dest)
    return dest


# ---------------------------------------------------------------- MapReduce
def clickstream_mapper(line, nodes):
    parts = line.rstrip("\n").split("\t")
    if len(parts) != 4:
        return
    prev, curr, typ, n = parts
    if curr not in nodes:
        return
    n = int(n)
    yield ("A", curr, "total"), n
    if typ == "link":
        yield ("A", curr, "link_in_all"), n
        if prev in nodes:
            yield ("A", curr, "link_in_sub"), n
            yield ("E", prev, curr), n
    elif prev == "other-search":
        yield ("A", curr, "search"), n
    elif typ == "external":
        yield ("A", curr, "external"), n
    else:
        yield ("A", curr, "other"), n


def sum_reducer(key, values):
    yield key, sum(values)


def run_job(month, nodes):
    t0 = time.time()
    combined = defaultdict(int)            # in-mapper combiner = partial reduce
    rows = kept = 0
    with gzip.open(raw_path(month), "rt", encoding="utf-8", errors="replace") as f:
        for line in tqdm(f, desc=f"map {month}", unit=" rows", unit_scale=True, mininterval=1):
            rows += 1
            emitted = False
            for key, value in clickstream_mapper(line, nodes):
                combined[key] += value
                emitted = True
            kept += emitted

    attention = defaultdict(lambda: dict.fromkeys(ATTENTION_FIELDS, 0))
    edge_clicks = {}
    for key, value in combined.items():    # reduce phase
        for (kind, a, b), total in sum_reducer(key, [value]):
            if kind == "A":
                attention[a][b] = total
            else:
                edge_clicks[(a, b)] = total

    with open(config.DATA_DIR / f"attention_{month}.tsv", "w", encoding="utf-8") as f:
        f.write("title\t" + "\t".join(ATTENTION_FIELDS) + "\n")
        for title in sorted(attention):
            f.write(title + "\t" + "\t".join(str(attention[title][k]) for k in ATTENTION_FIELDS) + "\n")
    with open(config.DATA_DIR / f"edge_clicks_{month}.tsv", "w", encoding="utf-8") as f:
        for (s, d), n in sorted(edge_clicks.items()):
            f.write(f"{s}\t{d}\t{n}\n")

    meta = {"month": month, "rows_scanned": rows, "rows_kept": kept,
            "articles_with_clicks": len(attention), "edges_with_clicks": len(edge_clicks),
            "total_clicks_in_subgraph": sum(a["total"] for a in attention.values()),
            "seconds": round(time.time() - t0, 1)}
    (config.DATA_DIR / f"clickstream_meta_{month}.json").write_text(json.dumps(meta, indent=2))
    print(f"[{month}] scanned {rows:,} rows, kept {kept:,}; "
          f"{len(attention):,} articles and {len(edge_clicks):,} links got clicks "
          f"({meta['seconds']}s)")
    return meta


def load_nodes():
    path = config.DATA_DIR / "nodes.txt"
    if not path.exists():
        raise SystemExit("Run step1_subgraph.py first (data/nodes.txt missing).")
    return set(path.read_text(encoding="utf-8").split())


def main(months=None, skip_download=False):
    months = months or [config.TRAIN_MONTH, config.TEST_MONTH]
    nodes = load_nodes()
    for m in months:
        if not skip_download:
            download(m)
        run_job(m, nodes)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", nargs="*")
    ap.add_argument("--skip-download", action="store_true")
    a = ap.parse_args()
    main(a.months, a.skip_download)
