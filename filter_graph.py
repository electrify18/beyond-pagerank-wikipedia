"""
Remove citation/identifier boilerplate pages from the existing subgraph, with no re-crawl.

Rewrites data/nodes.txt, data/edges.tsv and data/subgraph_meta.json in place.
Hop-2 slots are not refilled, so the graph differs from the original only by these pages.
Then re-run the clickstream and analysis stages (see step2_clickstream.py, step3_analysis.py).
"""
import json

import config


def is_excluded(title):
    return title in config.EXCLUDE_TITLES or title.endswith(config.EXCLUDE_SUFFIX)


def main():
    nodes_path = config.DATA_DIR / "nodes.txt"
    edges_path = config.DATA_DIR / "edges.tsv"
    meta_path = config.DATA_DIR / "subgraph_meta.json"

    nodes = nodes_path.read_text(encoding="utf-8").splitlines()
    edges = [l for l in edges_path.read_text(encoding="utf-8").splitlines() if l]

    removed = sorted(t for t in nodes if is_excluded(t))
    kept_nodes = [t for t in nodes if not is_excluded(t)]
    kept_edges = [l for l in edges
                  if not any(is_excluded(end) for end in l.split("\t"))]

    nodes_path.write_text("\n".join(kept_nodes) + "\n", encoding="utf-8")
    edges_path.write_text("\n".join(kept_edges) + "\n", encoding="utf-8")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(nodes=len(kept_nodes), edges=len(kept_edges), excluded=removed)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Removed {len(removed)} nodes: {len(nodes):,} -> {len(kept_nodes):,}")
    print(f"Removed {len(edges) - len(kept_edges):,} edges: {len(edges):,} -> {len(kept_edges):,}")
    print("Titles removed:", ", ".join(removed))


if __name__ == "__main__":
    main()
