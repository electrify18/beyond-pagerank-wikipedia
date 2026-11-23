"""
PageRank with MapReduce (explicit mapper / shuffle / reducer stages).

Supports:
  - standard PageRank      (every out-link weight = 1)
  - weighted PageRank      (out-link weight = observed click count, Dimitrov et al. 2017 idea)
  - dangling nodes         (their rank mass is collected under a special key and
                            redistributed uniformly, the way a Hadoop driver would
                            use a job counter)
  - teleport / damping     (beta; beta = 1 reproduces the textbook / lab-manual example)

Each iteration = two MapReduce jobs, like a real Hadoop pipeline:
  Job 1 (contribution): mapper sends rank shares along out-links, reducer sums them.
  Job 2 (finalize, map-only): applies damping + redistributes dangling mass.

Graph record format (one per node):  node -> (rank, [(target, weight), ...])
"""

import time
from collections import defaultdict
from fractions import Fraction

DANGLING_KEY = "#DANGLING"
GRAPH_TAG = "G"
RANK_TAG = "R"


# ---------------------------------------------------------------- Job 1: contributions
def contribution_mapper(node, record):
    """Emit the node's structure (so the graph survives the iteration)
    and send rank shares to every out-neighbour, proportional to edge weight."""
    rank, outlinks = record
    yield node, (GRAPH_TAG, outlinks)

    total_w = sum(w for _, w in outlinks)
    if total_w == 0:                         # dangling node: no out-links
        yield DANGLING_KEY, (RANK_TAG, rank)
        return
    for target, w in outlinks:
        yield target, (RANK_TAG, rank * w / total_w)


def contribution_reducer(node, values):
    """Sum incoming rank shares and re-attach the node's out-links."""
    incoming = 0
    outlinks = []
    for tag, payload in values:
        if tag == GRAPH_TAG:
            outlinks = payload
        else:
            incoming += payload
    yield node, (incoming, outlinks)


# ---------------------------------------------------------------- Job 2: finalize (map-only)
def make_finalize_mapper(beta, n_nodes, dangling_mass):
    teleport = (1 - beta) / n_nodes
    dangling_share = dangling_mass / n_nodes

    def finalize_mapper(node, record):
        incoming, outlinks = record
        yield node, (teleport + beta * (incoming + dangling_share), outlinks)

    return finalize_mapper


# ---------------------------------------------------------------- tiny local MapReduce runtime
def run_map_reduce(records, mapper, reducer=None):
    """map -> shuffle (group by key) -> reduce. Returns dict of results and the
    size of the intermediate data (useful to show in the demo)."""
    shuffled = defaultdict(list)
    n_intermediate = 0
    for key, value in records.items():
        for out_key, out_value in mapper(key, value):
            shuffled[out_key].append(out_value)
            n_intermediate += 1

    if reducer is None:                       # map-only job
        return {k: v[0] for k, v in shuffled.items()}, n_intermediate

    output = {}
    for key, values in shuffled.items():
        for out_key, out_value in reducer(key, values):
            output[out_key] = out_value
    return output, n_intermediate


# ---------------------------------------------------------------- driver
def pagerank(edges, beta=0.85, max_iter=100, tol=1e-10, exact=False,
             history=False, verbose=False, nodes=None, stats=None):
    """
    edges : iterable of (src, dst) or (src, dst, weight)
    nodes : optional full node list (includes isolated pages with no links at all)
    exact : use Fractions (for checking the lab-manual answers exactly)
    stats : optional list; one dict per iteration is appended (L1 change,
            intermediate key-value pairs, seconds) for the dashboard
    Returns {node: rank} (and the per-iteration history if history=True).
    """
    adj = defaultdict(list)
    nodes = set(nodes or ())
    for e in edges:
        src, dst = e[0], e[1]
        w = e[2] if len(e) > 2 else 1
        adj[src].append((dst, w))
        nodes.update((src, dst))

    n = len(nodes)
    one = Fraction(1) if exact else 1.0
    beta = Fraction(beta) if exact else float(beta)
    graph = {v: (one / n, adj.get(v, [])) for v in sorted(nodes)}

    hist = [{v: r for v, (r, _) in graph.items()}]
    for it in range(1, max_iter + 1):
        t0 = time.perf_counter()
        # Job 1
        reduced, n_inter = run_map_reduce(graph, contribution_mapper, contribution_reducer)
        zero = one * 0                        # keeps exact (Fraction) mode exact
        dangling_mass = reduced.pop(DANGLING_KEY, (zero, []))[0]
        for v in nodes:                       # nodes with no in-links got no reducer call
            reduced.setdefault(v, (zero, graph[v][1]))
        # Job 2
        new_graph, _ = run_map_reduce(reduced, make_finalize_mapper(beta, n, dangling_mass))

        delta = sum(abs(new_graph[v][0] - graph[v][0]) for v in nodes)
        graph = new_graph
        if history:
            hist.append({v: r for v, (r, _) in graph.items()})
        if stats is not None:
            stats.append({"iteration": it, "l1_change": float(delta),
                          "intermediate_pairs": n_inter,
                          "seconds": time.perf_counter() - t0})
        if verbose:
            print(f"iter {it:3d}  L1 change = {float(delta):.3e}  "
                  f"intermediate pairs = {n_inter}")
        if not exact and delta < tol:
            break

    ranks = {v: r for v, (r, _) in graph.items()}
    return (ranks, hist) if history else ranks
