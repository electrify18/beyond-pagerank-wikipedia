"""
Citation-page robustness check -> results/robustness.json

Compares the final run (results/, citation/identifier pages removed) with the earlier run on the raw crawl
(results_with_citation_pages/). Both metric files come from step3_analysis.py on the same clickstream months.
"""
import json

import config

BEFORE = config.ROOT / "results_with_citation_pages" / "metrics.json"
AFTER = config.RESULTS_DIR / "metrics.json"


def main():
    b = json.loads(BEFORE.read_text())
    a = json.loads(AFTER.read_text())
    out = {
        "description": "Spearman rho vs test-month navigation, with and without citation/identifier pages",
        "train_month": a["train_month"], "test_month": a["test_month"],
        "removed_pages": a["graph"].get("excluded", []),
        "with_citation_pages": {"nodes": b["graph"]["nodes"], "edges": b["graph"]["edges"]},
        "without_citation_pages": {"nodes": a["graph"]["nodes"], "edges": a["graph"]["edges"]},
        "nodes_removed": b["graph"]["nodes"] - a["graph"]["nodes"],
        "edges_removed": b["graph"]["edges"] - a["graph"]["edges"],
        "spearman_navigation": {
            m: {"with_citation_pages": b["models"][m]["spearman_navigation"],
                "without_citation_pages": a["models"][m]["spearman_navigation"]}
            for m in a["models"]},
        "beta_sweep_spearman_navigation": {
            "with_citation_pages": b["beta_sweep_spearman_navigation"],
            "without_citation_pages": a["beta_sweep_spearman_navigation"]},
    }
    path = config.RESULTS_DIR / "robustness.json"
    path.write_text(json.dumps(out, indent=2))
    pr = out["spearman_navigation"]["PageRank"]
    print(f"PageRank rho: {pr['with_citation_pages']} with citation pages -> "
          f"{pr['without_citation_pages']} without ({out['nodes_removed']} pages, "
          f"{out['edges_removed']:,} links removed). Written to {path}")


if __name__ == "__main__":
    main()
