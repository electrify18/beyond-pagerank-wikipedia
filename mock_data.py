"""
TEST ONLY - creates a fake subgraph + fake clickstream files in the exact real formats,
so the whole pipeline and dashboard can be checked without downloading anything.
The dashboard shows a big MOCK DATA banner when this data is loaded.
"""
import gzip
import json
import random

import config


def main(train, test, n_nodes=1500, seed=7):
    rng = random.Random(seed)
    nodes = [f"Mock_Article_{i:04d}" for i in range(n_nodes)]

    # preferential attachment-ish structure: a few hubs get most links
    weights = [1 / (i + 1) ** 0.8 for i in range(n_nodes)]
    edges = set()
    for s in nodes:
        for d in rng.choices(nodes, weights=weights, k=rng.randint(3, 25)):
            if d != s:
                edges.add((s, d))

    (config.DATA_DIR / "nodes.txt").write_text("\n".join(nodes) + "\n", encoding="utf-8")
    with open(config.DATA_DIR / "edges.tsv", "w", encoding="utf-8") as f:
        for s, d in sorted(edges):
            f.write(f"{s}\t{d}\n")
    (config.DATA_DIR / "subgraph_meta.json").write_text(json.dumps({
        "seed": "Mock_Article_0000", "hop1": 400, "hop2": n_nodes - 401,
        "nodes": n_nodes, "edges": len(edges), "hop2_min_inlinks": 8,
        "built": "mock", "mock": True, "minutes": 0}, indent=2))

    # reader interest = partly structure, partly independent "hype"
    base = {v: weights[i] * 5e5 * rng.lognormvariate(0, 1.0) for i, v in enumerate(nodes)}
    for month, drift in ((train, 0.0), (test, 0.6)):
        pop = {v: base[v] * rng.lognormvariate(0, drift) for v in nodes}
        rows = []
        for s, d in edges:
            n = int(pop[d] / 400 * rng.random())
            if n > 10:                                   # real dumps hide pairs <= 10
                rows.append((s, d, "link", n))
        for v in nodes:
            for src, frac in (("other-search", 0.5), ("other-external", 0.05),
                              ("other-empty", 0.15), ("other-internal", 0.02)):
                n = int(pop[v] * frac * rng.random())
                if n > 10:
                    rows.append((src, v, "external", n))
        for i in range(60_000):                          # rows about unrelated articles
            rows.append((f"Unrelated_{i}", f"Unrelated_{i + 1}", "link", rng.randint(11, 500)))
        rng.shuffle(rows)
        with gzip.open(config.RAW_DIR / f"clickstream-enwiki-{month}.tsv.gz", "wt", encoding="utf-8") as f:
            for r in rows:
                f.write("\t".join(map(str, r)) + "\n")
    (config.RAW_DIR / "MOCK_FILES_HERE").write_text("delete me before a real run")
    print(f"Mock data: {n_nodes} articles, {len(edges)} links, clickstream for {train} and {test}")
