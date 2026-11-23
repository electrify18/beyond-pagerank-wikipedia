"""
Correctness checks for pagerank_mr.py

1. Reproduces the CRCE BDA lab manual (Exp 11) example EXACTLY:
      V1 = [9/24, 5/24, 5/24, 5/24],  V2 = [15/48, 11/48, 11/48, 11/48]
   Graph read off the transition matrix M (columns = source pages):
      A -> B, C, D     B -> A, D     C -> A     D -> B, C
2. Matches NetworkX on the toy graph with damping 0.85.
3. Matches NetworkX on a random graph with dangling nodes (standard + weighted).
"""

import random
from fractions import Fraction

import networkx as nx

from pagerank_mr import pagerank

TOY_EDGES = [("A", "B"), ("A", "C"), ("A", "D"),
             ("B", "A"), ("B", "D"),
             ("C", "A"),
             ("D", "B"), ("D", "C")]


def show(vec):
    return "  ".join(f"{k}={v}" for k, v in vec.items())


def check_lab_manual():
    print("=" * 64)
    print("CHECK 1: lab manual example (beta = 1, exact fractions)")
    print("=" * 64)
    _, hist = pagerank(TOY_EDGES, beta=1, max_iter=2, exact=True, history=True)
    for i, vec in enumerate(hist):
        print(f"V{i}: {show(vec)}")

    expected_v1 = {"A": Fraction(9, 24), "B": Fraction(5, 24),
                   "C": Fraction(5, 24), "D": Fraction(5, 24)}
    expected_v2 = {"A": Fraction(15, 48), "B": Fraction(11, 48),
                   "C": Fraction(11, 48), "D": Fraction(11, 48)}
    assert hist[1] == expected_v1, "V1 mismatch"
    assert hist[2] == expected_v2, "V2 mismatch"
    print("PASS: V1 and V2 match the lab manual exactly\n")


def max_abs_diff(a, b):
    return max(abs(a[k] - b[k]) for k in a)


def check_vs_networkx_toy():
    print("=" * 64)
    print("CHECK 2: toy graph, beta = 0.85, vs NetworkX")
    print("=" * 64)
    ours = pagerank(TOY_EDGES, beta=0.85, tol=1e-12)
    ref = nx.pagerank(nx.DiGraph(TOY_EDGES), alpha=0.85, tol=1e-12)
    for k in sorted(ours):
        print(f"{k}: ours={ours[k]:.6f}  networkx={ref[k]:.6f}")
    d = max_abs_diff(ours, ref)
    assert d < 1e-8, d
    print(f"PASS: max difference = {d:.2e}\n")


def check_vs_networkx_random():
    print("=" * 64)
    print("CHECK 3: random graph (500 nodes, dangling nodes), vs NetworkX")
    print("=" * 64)
    rng = random.Random(42)
    nodes = list(range(500))
    edges = set()
    for u in nodes[:450]:                      # last 50 nodes have no out-links
        for v in rng.sample(nodes, rng.randint(1, 8)):
            if u != v:
                edges.add((u, v))
    weighted = [(u, v, rng.randint(1, 1000)) for u, v in sorted(edges)]

    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_weighted_edges_from(weighted)

    ours = pagerank(sorted(edges), beta=0.85, tol=1e-12, nodes=nodes)
    ref = nx.pagerank(G, alpha=0.85, tol=1e-12, weight=None)
    d1 = max_abs_diff(ours, ref)
    print(f"standard PageRank: max difference = {d1:.2e}")

    ours_w = pagerank(weighted, beta=0.85, tol=1e-12, nodes=nodes)
    ref_w = nx.pagerank(G, alpha=0.85, tol=1e-12, weight="weight")
    d2 = max_abs_diff(ours_w, ref_w)
    print(f"weighted PageRank: max difference = {d2:.2e}")

    assert d1 < 1e-8 and d2 < 1e-8
    print(f"ranks sum to {sum(ours.values()):.10f}")
    print("PASS\n")


if __name__ == "__main__":
    check_lab_manual()
    check_vs_networkx_toy()
    check_vs_networkx_random()
    print("All checks passed.")
