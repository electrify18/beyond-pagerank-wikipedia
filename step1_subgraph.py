"""
STEP 1 - Build the World Cup link subgraph from the Wikipedia API.

  seed article  ->  hop 1: every article the seed links to
                ->  hop 2: articles linked from at least HOP2_MIN_INLINKS hop-1 pages
  keep only links where BOTH ends are inside the set (induced subgraph)

Outputs
  data/nodes.txt          one article title per line (underscores, like the clickstream)
  data/edges.tsv          src <TAB> dst
  data/subgraph_meta.json sizes of each hop

Every API response is cached in data/api_cache, so a re-run is instant.
"""
import hashlib
import json
import time
from collections import Counter

import requests
from tqdm import tqdm

import config

API = "https://en.wikipedia.org/w/api.php"
session = requests.Session()
session.headers["User-Agent"] = config.USER_AGENT


def norm(title):
    return title.replace(" ", "_")


def is_excluded(title):
    return title in config.EXCLUDE_TITLES or title.endswith(config.EXCLUDE_SUFFIX)


def api_get(params):
    key = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    cached = config.CACHE_DIR / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))

    for attempt in range(10):
        retry_after = 0
        try:
            r = session.get(API, params=params, timeout=30)
            if r.status_code == 429 and r.headers.get("Retry-After", "").isdigit():
                retry_after = int(r.headers["Retry-After"])
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            data = r.json()
            if data.get("error", {}).get("code") == "maxlag":
                raise requests.HTTPError("server lagged")
            break
        except (requests.RequestException, ValueError) as e:
            wait = max(2 ** attempt, retry_after)
            tqdm.write(f"  retry in {wait}s ({e})")
            time.sleep(wait)
    else:
        raise RuntimeError("Wikipedia API kept failing - check your internet and re-run "
                           "(finished batches are cached).")

    cached.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(1)
    return data


def fetch_links(titles, label):
    """Return ({canonical_title: set(link targets)}, {redirect_title: target_title})."""
    links, redirects = {}, {}
    batches = range(0, len(titles), 50)
    for i in tqdm(batches, desc=label, unit="batch"):
        params = {
            "action": "query", "format": "json", "formatversion": "2",
            "prop": "links", "plnamespace": "0", "pllimit": "max",
            "redirects": "1", "maxlag": "5",
            "titles": "|".join(t.replace("_", " ") for t in titles[i:i + 50]),
        }
        cont = {}
        while True:
            data = api_get({**params, **cont})
            q = data.get("query", {})
            for r in q.get("redirects", []):
                redirects[norm(r["from"])] = norm(r["to"])
            for page in q.get("pages", []):
                if page.get("missing") or page.get("invalid") or page.get("ns", 0) != 0:
                    continue
                targets = links.setdefault(norm(page["title"]), set())
                targets.update(norm(link["title"]) for link in page.get("links", []))
            if "continue" not in data:
                break
            cont = data["continue"]
    return links, redirects


def main():
    t0 = time.time()
    print(f"Seed article: {config.SEED}")

    seed_links, redirects = fetch_links([config.SEED], "seed  ")
    if not seed_links:
        raise SystemExit(f"Seed article '{config.SEED}' not found on Wikipedia.")
    seed = next(iter(seed_links))

    hop1_titles = sorted(t for t in seed_links[seed] if not is_excluded(redirects.get(t, t)))
    hop1_links, r = fetch_links(hop1_titles, "hop 1 ")
    redirects.update(r)
    nodes = {seed} | {t for t in hop1_links if not is_excluded(t)}

    candidates = Counter()
    for targets in hop1_links.values():
        for t in targets:
            t = redirects.get(t, t)
            if t not in nodes and not is_excluded(t):
                candidates[t] += 1
    hop2_titles = [t for t, c in candidates.most_common()
                   if c >= config.HOP2_MIN_INLINKS][:config.HOP2_MAX]
    hop2_links, r = fetch_links(hop2_titles, "hop 2 ")
    redirects.update(r)
    nodes |= {t for t in hop2_links if not is_excluded(t)}

    all_links = {**seed_links, **hop1_links, **hop2_links}
    edges = set()
    for src in nodes:
        for t in all_links.get(src, ()):
            t = redirects.get(t, t)
            if t in nodes and t != src:
                edges.add((src, t))

    (config.DATA_DIR / "nodes.txt").write_text("\n".join(sorted(nodes)) + "\n", encoding="utf-8")
    with open(config.DATA_DIR / "edges.tsv", "w", encoding="utf-8") as f:
        for s, d in sorted(edges):
            f.write(f"{s}\t{d}\n")

    meta = {"seed": seed, "hop1": len(hop1_links), "hop2": len(hop2_links),
            "nodes": len(nodes), "edges": len(edges),
            "hop2_min_inlinks": config.HOP2_MIN_INLINKS,
            "built": time.strftime("%Y-%m-%d %H:%M"), "mock": False,
            "minutes": round((time.time() - t0) / 60, 1)}
    (config.DATA_DIR / "subgraph_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nSubgraph: {meta['nodes']:,} articles, {meta['edges']:,} links "
          f"(hop1 {meta['hop1']:,}, hop2 {meta['hop2']:,}) in {meta['minutes']} min")


if __name__ == "__main__":
    main()
