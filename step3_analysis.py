"""
STEP 3 - Rank the articles four ways and compare them with what readers actually did.

Models (all built from TRAIN month or from structure only):
  PageRank                 standard MapReduce PageRank (beta = 0.85), structure only
  Click-weighted PageRank  edges weighted by TRAIN-month link clicks (+1 smoothing)
  In-degree                number of incoming links inside the subgraph
  Last month's clicks      TRAIN-month link clicks received (naive baseline)

Ground truth (TEST month, never used to build any model):
  navigation  = link clicks received from other World Cup articles (what PageRank models)
  attention   = all traffic to the article (search, links, external)

Metrics: Spearman rank correlation, top-10 overlap, NDCG@10.
Writes results/rankings.csv, results/metrics.json, results/convergence.json
"""
import argparse
import json
import math
import time

import pandas as pd
from scipy.stats import spearmanr

import config
from pagerank_mr import pagerank

MODELS = {
    "PageRank": "pagerank",
    "Click-weighted PageRank": "weighted_pagerank",
    "In-degree": "in_degree",
    "Last month's clicks": "train_link_in_sub",
}
TRUTHS = {"navigation": "test_link_in_sub", "attention": "test_total"}


def load_attention(month):
    path = config.DATA_DIR / f"attention_{month}.tsv"
    if not path.exists():
        raise SystemExit(f"{path.name} missing - run step2_clickstream.py first.")
    return pd.read_csv(path, sep="\t", keep_default_na=False, dtype={"title": str}).set_index("title")


def load_edge_clicks(month):
    clicks = {}
    with open(config.DATA_DIR / f"edge_clicks_{month}.tsv", encoding="utf-8") as f:
        for line in f:
            s, d, n = line.rstrip("\n").split("\t")
            clicks[(s, d)] = int(n)
    return clicks


def top_k_overlap(df, a, b, k=10):
    return len(set(df.nlargest(k, a).index) & set(df.nlargest(k, b).index))


def ndcg_at_k(df, model_col, truth_col, k=10):
    def dcg(values):
        return sum(v / math.log2(i + 2) for i, v in enumerate(values))
    predicted = df.sort_values(model_col, ascending=False)[truth_col].head(k).tolist()
    ideal = df[truth_col].sort_values(ascending=False).head(k).tolist()
    return dcg(predicted) / dcg(ideal) if dcg(ideal) else 0.0


def evaluate(df, col):
    out = {}
    for name, truth in TRUTHS.items():
        rho = spearmanr(df[col], df[truth]).statistic
        out[f"spearman_{name}"] = round(float(rho), 4)
        out[f"top10_{name}"] = top_k_overlap(df, col, truth)
        out[f"ndcg10_{name}"] = round(ndcg_at_k(df, col, truth), 4)
    return out


def main(train=config.TRAIN_MONTH, test=config.TEST_MONTH):
    t0 = time.time()
    nodes = (config.DATA_DIR / "nodes.txt").read_text(encoding="utf-8").split()
    edges = [tuple(l.split("\t")) for l in
             (config.DATA_DIR / "edges.tsv").read_text(encoding="utf-8").splitlines() if l]
    print(f"Graph: {len(nodes):,} articles, {len(edges):,} links")

    df = pd.DataFrame(index=pd.Index(nodes, name="title"))
    df["label"] = [t.replace("_", " ") for t in nodes]
    df["in_degree"] = pd.Series([d for _, d in edges]).value_counts().reindex(df.index, fill_value=0)
    df["out_degree"] = pd.Series([s for s, _ in edges]).value_counts().reindex(df.index, fill_value=0)

    for prefix, month in (("train", train), ("test", test)):
        att = load_attention(month).reindex(df.index, fill_value=0)
        for c in att.columns:
            df[f"{prefix}_{c}"] = att[c].astype(int)

    # ---- standard PageRank for several damping factors (MapReduce engine)
    convergence = []
    for beta in config.BETAS:
        stats = [] if beta == config.MAIN_BETA else None
        ranks = pagerank(edges, beta=beta, nodes=nodes, tol=1e-9, stats=stats)
        df[f"pr_{beta:.2f}"] = df.index.map(ranks)
        if stats is not None:
            convergence = stats
        print(f"  PageRank beta={beta:.2f} done")
    df["pagerank"] = df[f"pr_{config.MAIN_BETA:.2f}"]

    # ---- click-weighted PageRank (weights from TRAIN month only)
    train_clicks = load_edge_clicks(train)
    weighted_edges = [(s, d, train_clicks.get((s, d), 0) + config.CLICK_SMOOTHING) for s, d in edges]
    wr = pagerank(weighted_edges, beta=config.MAIN_BETA, nodes=nodes, tol=1e-9)
    df["weighted_pagerank"] = df.index.map(wr)
    print("  click-weighted PageRank done")

    # ---- evaluation on TEST month
    metrics = {name: evaluate(df, col) for name, col in MODELS.items()}
    beta_sweep = {f"{b:.2f}": round(float(spearmanr(df[f'pr_{b:.2f}'], df['test_link_in_sub']).statistic), 4)
                  for b in config.BETAS}

    graph_meta = json.loads((config.DATA_DIR / "subgraph_meta.json").read_text())
    cs_meta = {m: json.loads((config.DATA_DIR / f"clickstream_meta_{m}.json").read_text())
               for m in (train, test)}

    df.sort_values("pagerank", ascending=False).to_csv(config.RESULTS_DIR / "rankings.csv")
    (config.RESULTS_DIR / "convergence.json").write_text(json.dumps(convergence, indent=2))
    (config.RESULTS_DIR / "metrics.json").write_text(json.dumps({
        "train_month": train, "test_month": test, "models": metrics,
        "beta_sweep_spearman_navigation": beta_sweep,
        "graph": graph_meta, "clickstream": cs_meta,
        "edges_with_train_clicks": sum(1 for e in edges if e in train_clicks),
        "analysis_seconds": round(time.time() - t0, 1),
    }, indent=2))

    print("\nSpearman vs real navigation in", test)
    for name, m in metrics.items():
        print(f"  {name:<25} rho={m['spearman_navigation']:+.3f}  "
              f"top10={m['top10_navigation']}/10  NDCG@10={m['ndcg10_navigation']:.3f}")
    print(f"\nResults written to {config.RESULTS_DIR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=config.TRAIN_MONTH)
    ap.add_argument("--test", default=config.TEST_MONTH)
    a = ap.parse_args()
    main(a.train, a.test)
