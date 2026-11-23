"""
Beyond PageRank - dashboard.        streamlit run app.py
"""
import inspect
import json
from fractions import Fraction

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from pagerank_mr import contribution_mapper, contribution_reducer, pagerank

st.set_page_config(page_title="Beyond PageRank", page_icon="⚽", layout="wide")

STRUCT = "#5B8DEF"   # link structure / PageRank
FANS = "#F5A524"     # human clicks
WPR = "#2BC48A"
INDEG = "#A78BFA"
LAST = "#94A3B8"
MODEL_COLORS = {"PageRank": STRUCT, "Click-weighted PageRank": WPR,
                "In-degree": INDEG, "Last month's clicks": LAST}

st.markdown("""
<style>
  .block-container {padding-top: 2rem; max-width: 1350px;}
  .hero h1 {font-size: 2.6rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;
            background: linear-gradient(90deg, #5B8DEF, #F5A524);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
  .hero p {color: #A9B4C8; font-size: 1.05rem; margin: .35rem 0 0 0;}
  .chips {margin: .8rem 0 1.2rem 0;}
  .chip {display:inline-block; padding:.25rem .7rem; margin-right:.4rem; border-radius:999px;
         background:#141B2D; border:1px solid #26304A; color:#C9D2E3; font-size:.8rem;}
  .kpi {background:#141B2D; border:1px solid #26304A; border-radius:14px; padding:1rem 1.1rem; min-height:108px;}
  .kpi .v {font-size:1.7rem; font-weight:750; color:#E8ECF4; line-height:1.1;}
  .kpi .l {font-size:.78rem; color:#8B97AD; text-transform:uppercase; letter-spacing:.06em;}
  .board {background:#141B2D; border:1px solid #26304A; border-radius:14px; padding:1rem 1.2rem;}
  .board h3 {margin:0 0 .7rem 0; font-size:1.05rem;}
  .row {display:flex; align-items:center; gap:.7rem; padding:.32rem 0; border-bottom:1px solid #1E263A;}
  .rank {width:1.6rem; color:#8B97AD; font-weight:700; text-align:right;}
  .name {flex:1; font-size:.95rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
  .bar {height:6px; border-radius:3px;}
  .both {font-size:.65rem; padding:.05rem .4rem; border-radius:6px; background:#2BC48A22;
         color:#2BC48A; border:1px solid #2BC48A55;}
  .mock {background:#F5A52422; border:1px solid #F5A524; color:#F5A524; padding:.6rem 1rem;
         border-radius:10px; font-weight:600; margin-bottom:1rem;}
  .note {color:#8B97AD; font-size:.85rem;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load():
    df = pd.read_csv(config.RESULTS_DIR / "rankings.csv", index_col="title")
    metrics = json.loads((config.RESULTS_DIR / "metrics.json").read_text())
    conv = json.loads((config.RESULTS_DIR / "convergence.json").read_text())
    return df, metrics, conv


if not (config.RESULTS_DIR / "metrics.json").exists():
    st.error("No results yet. Run `python run_all.py` first, then refresh this page.")
    st.stop()

df, M, conv = load()
train, test = M["train_month"], M["test_month"]
g = M["graph"]


def month_name(m):
    return pd.Timestamp(m + "-01").strftime("%B %Y")


def fmt(n):
    n = float(n)
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return f"{n:,.0f}"


def plot_layout(fig, height=430, **kw):
    fig.update_layout(template="plotly_dark", height=height, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=40, b=10),
                      font=dict(color="#C9D2E3"), **kw)
    return fig


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### Ground truth")
    truth_choice = st.radio(
        "What counts as 'fans clicked'?",
        ["Navigation inside the World Cup graph", "All traffic to the article"],
        help="Navigation = link clicks from other World Cup articles (what PageRank's "
             "random surfer models). All traffic also includes Google searches and external sites.")
    TRUTH = "test_link_in_sub" if truth_choice.startswith("Navigation") else "test_total"
    TKEY = "navigation" if TRUTH == "test_link_in_sub" else "attention"
    st.markdown("---")
    st.markdown(f"**Seed:** {g['seed'].replace('_', ' ')}  \n"
                f"**Weights from:** {month_name(train)}  \n"
                f"**Evaluated on:** {month_name(test)}  \n"
                f"**Damping β:** {config.MAIN_BETA}")
    st.markdown("---")
    st.caption("Data: Wikimedia clickstream dumps + Wikipedia link graph (CC0 / CC BY-SA).")

# ---------------------------------------------------------------- hero
st.markdown(f"""
<div class="hero">
  <h1>Beyond PageRank</h1>
  <p>Does Wikipedia's link structure predict where football fans actually clicked during the
  2026 FIFA World Cup?</p>
</div>
<div class="chips">
  <span class="chip">⚙️ MapReduce PageRank</span>
  <span class="chip">🗺️ {g['nodes']:,} articles · {g['edges']:,} links</span>
  <span class="chip">📅 trained on {month_name(train)} → tested on {month_name(test)}</span>
</div>
""", unsafe_allow_html=True)

if g.get("mock"):
    st.markdown('<div class="mock">MOCK DATA - synthetic test dataset, not real Wikipedia '
                'numbers. Run <code>python run_all.py</code> for the real analysis.</div>',
                unsafe_allow_html=True)

cs = M["clickstream"]
rows_scanned = sum(m["rows_scanned"] for m in cs.values())
pr_rho = M["models"]["PageRank"][f"spearman_{TKEY}"]
wpr_rho = M["models"]["Click-weighted PageRank"][f"spearman_{TKEY}"]
kpis = [(fmt(g["nodes"]), "Articles in graph"), (fmt(g["edges"]), "Hyperlinks"),
        (fmt(rows_scanned), "Clickstream rows scanned"),
        (fmt(df["test_total"].sum()), f"Visits in {pd.Timestamp(test + '-01'):%b}"),
        (f"{pr_rho:+.2f}", "Spearman ρ · PageRank"),
        (f"{wpr_rho:+.2f}", "Spearman ρ · click-weighted")]
for col, (v, l) in zip(st.columns(len(kpis)), kpis):
    col.markdown(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>',
                 unsafe_allow_html=True)
st.write("")

tabs = st.tabs(["🏆 Leaderboards", "📈 Structure vs attention", "🔥 Overrated / underrated",
                "🧪 Model scoreboard", "🚀 June → July", "⚙️ Under the hood"])


# ---------------------------------------------------------------- 1. leaderboards
def board(title, series, color, overlap):
    top = series.nlargest(10)
    mx = top.max() or 1
    rows = ""
    for i, (t, v) in enumerate(top.items(), 1):
        badge = '<span class="both">in both</span>' if t in overlap else ""
        rows += (f'<div class="row"><div class="rank">{i}</div>'
                 f'<div class="name">{df.at[t, "label"]} {badge}</div>'
                 f'<div class="bar" style="width:{max(6, 110 * v / mx):.0f}px;background:{color}"></div></div>')
    return f'<div class="board"><h3>{title}</h3>{rows}</div>'


with tabs[0]:
    pr_top = set(df["pagerank"].nlargest(10).index)
    fan_top = set(df[TRUTH].nlargest(10).index)
    both = pr_top & fan_top
    c1, c2 = st.columns(2)
    c1.markdown(board("🔵 What PageRank says matters", df["pagerank"], STRUCT, both), unsafe_allow_html=True)
    c2.markdown(board("🟠 Where fans actually clicked", df[TRUTH], FANS, both), unsafe_allow_html=True)
    st.write("")
    st.markdown(f"**{len(both)} of 10** articles appear in both lists. "
                f"<span class='note'>PageRank uses only the link structure; the right list is "
                f"real reader behaviour in {month_name(test)}.</span>", unsafe_allow_html=True)

# ---------------------------------------------------------------- 2. scatter
with tabs[1]:
    c1, c2 = st.columns([3, 1])
    beta = c2.select_slider("Damping factor β", options=config.BETAS, value=config.MAIN_BETA,
                            help="Probability the random surfer follows a link instead of teleporting.")
    pr_col = f"pr_{beta:.2f}"
    sub = df[df[TRUTH] > 0].copy()
    rho = sub[[pr_col, TRUTH]].corr(method="spearman").iloc[0, 1] if len(sub) > 2 else float("nan")
    rho_all = df[[pr_col, TRUTH]].corr(method="spearman").iloc[0, 1]
    c2.metric("Spearman ρ (all articles)", f"{rho_all:+.3f}")
    c2.metric("ρ (articles with clicks)", f"{rho:+.3f}")
    sweep = {float(b): df[[f'pr_{b:.2f}', TRUTH]].corr(method='spearman').iloc[0, 1] for b in config.BETAS}
    sfig = go.Figure(go.Scatter(x=list(sweep), y=list(sweep.values()), mode="lines+markers",
                                line=dict(color=STRUCT, width=3), marker=dict(size=9)))
    sfig.add_vline(x=beta, line_dash="dot", line_color=FANS)
    c2.plotly_chart(plot_layout(sfig, 230, title="ρ vs β", xaxis_title="β",
                                yaxis_title="ρ", showlegend=False), width="stretch")

    sub["gap"] = sub[TRUTH].rank(pct=True) - sub[pr_col].rank(pct=True)
    labelled = pd.concat([sub.nlargest(3, TRUTH), sub.nlargest(3, pr_col),
                          sub.nlargest(3, "gap"), sub.nsmallest(3, "gap")])
    labelled = labelled[~labelled.index.duplicated()]
    positions = ["top center", "bottom center", "middle right", "middle left"]
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=sub[pr_col], y=sub[TRUTH], mode="markers",
                               marker=dict(size=6, color=STRUCT, opacity=.45),
                               text=sub["label"], name="article",
                               hovertemplate="<b>%{text}</b><br>PageRank %{x:.2e}<br>clicks %{y:,}<extra></extra>"))
    fig.add_trace(go.Scatter(x=labelled[pr_col], y=labelled[TRUTH], mode="markers+text",
                             text=labelled["label"],
                             textposition=[positions[i % 4] for i in range(len(labelled))],
                             textfont=dict(size=11, color="#E8ECF4"),
                             marker=dict(size=10, color=FANS, line=dict(width=1, color="#0B1020")),
                             hovertemplate="<b>%{text}</b><br>PageRank %{x:.2e}<br>clicks %{y:,}<extra></extra>",
                             name="notable"))
    plot_layout(fig, 600, title=f"Link-structure importance vs real clicks · β = {beta}",
                xaxis=dict(type="log", title="PageRank (log)"),
                yaxis=dict(type="log", title=f"Clicks in {month_name(test)} (log)"), showlegend=False)
    c1.plotly_chart(fig, width="stretch")
    c1.caption("Points above the trend get more clicks than their link structure predicts; "
               "points below are structurally central but ignored by readers. "
               "Articles with zero clicks are hidden on the log scale.")

# ---------------------------------------------------------------- 3. over / under
with tabs[2]:
    sub = df[df[TRUTH] > 0].copy()
    sub["pr_rank"] = sub["pagerank"].rank(ascending=False).astype(int)
    sub["fan_rank"] = sub[TRUTH].rank(ascending=False).astype(int)
    sub["gap"] = sub[TRUTH].rank(pct=True) - sub["pagerank"].rank(pct=True)
    under = sub.nlargest(12, "gap").sort_values("gap")
    over = sub.nsmallest(12, "gap").sort_values("gap", ascending=False)
    c1, c2 = st.columns(2)
    for col, data, color, title, desc in (
        (c1, under, FANS, "🟠 Underrated - fans love it, the link graph doesn't",
         "High clicks, low PageRank: hype, breakout stories, search-driven interest."),
        (c2, over, STRUCT, "🔵 Overrated - central in the graph, ignored by fans",
         "High PageRank, few clicks: hub and reference pages everything links to.")):
        fig = go.Figure(go.Bar(x=data["gap"].abs() * 100, y=data["label"], orientation="h",
                               marker_color=color,
                               customdata=data[["pr_rank", "fan_rank"]],
                               hovertemplate="<b>%{y}</b><br>PageRank rank #%{customdata[0]}"
                                             "<br>Fans rank #%{customdata[1]}<extra></extra>"))
        plot_layout(fig, 480, title=title, xaxis_title="percentile gap (points)")
        col.plotly_chart(fig, width="stretch")
        col.caption(desc)
    with st.expander("Show the numbers"):
        show = pd.concat([under, over])[["label", "pr_rank", "fan_rank", "in_degree", TRUTH]]
        st.dataframe(show.rename(columns={"label": "article", "pr_rank": "PageRank rank",
                                          "fan_rank": "Fans rank", "in_degree": "in-links",
                                          TRUTH: "clicks"}), hide_index=True, width="stretch")

# ---------------------------------------------------------------- 4. scoreboard
with tabs[3]:
    names = list(M["models"])
    fig = go.Figure()
    for metric, label, opacity in ((f"spearman_{TKEY}", "Spearman ρ", 1.0),
                                   (f"ndcg10_{TKEY}", "NDCG@10", .65)):
        fig.add_trace(go.Bar(name=label, x=names, y=[M["models"][n][metric] for n in names],
                             marker_color=[MODEL_COLORS[n] for n in names], opacity=opacity,
                             text=[f"{M['models'][n][metric]:.2f}" for n in names], textposition="outside"))
    plot_layout(fig, 430, barmode="group", title=f"How well each model predicts {month_name(test)} behaviour",
                yaxis=dict(range=[min(0, *[M['models'][n][f'spearman_{TKEY}'] for n in names]) - .05, 1.1]),
                legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
    st.plotly_chart(fig, width="stretch")
    st.caption("Solid bars = Spearman ρ, faded bars = NDCG@10 (each pair shares the model's colour).")

    table = pd.DataFrame({n: {"Spearman ρ": m[f"spearman_{TKEY}"], "Top-10 overlap": f"{m[f'top10_{TKEY}']}/10",
                              "NDCG@10": m[f"ndcg10_{TKEY}"]} for n, m in M["models"].items()}).T
    table = table.astype({"Spearman ρ": float, "NDCG@10": float, "Top-10 overlap": str})
    st.dataframe(table, width="stretch")
    delta = wpr_rho - pr_rho
    verdict = "improves on" if delta > 0.01 else ("is worse than" if delta < -0.01 else "roughly ties with")
    st.markdown(f"**Finding:** click-weighted PageRank (built only from {month_name(train)} clicks) "
                f"{verdict} standard PageRank at predicting {month_name(test)} behaviour "
                f"(Δρ = {delta:+.3f}). Weights and evaluation use different months, so this is a "
                f"genuine out-of-sample test.")
    st.markdown("<span class='note'>Context: the Fatigued PageRank study (arXiv 2104.05369) reports a Spearman correlation of 0.99 "
                "between PageRank and visits (incoming December 2018 clickstream transitions) over all 897,577 "
                "articles of the Simple English Wikipedia link graph - a different setting from this topic "
                "subgraph; Dimitrov et al. (2017) "
                "found navigation-weighted PageRank beats the unweighted version.</span>",
                unsafe_allow_html=True)

# ---------------------------------------------------------------- 5. movers
with tabs[4]:
    big = df[(df["test_total"] >= df["test_total"].quantile(.8)) & (df["train_total"] > 0)].copy()
    big["growth"] = (big["test_total"] + 1) / (big["train_total"] + 1)
    risers = big.nlargest(12, "growth").sort_values("growth")
    fallers = big.nsmallest(8, "growth").sort_values("growth", ascending=False)
    c1, c2 = st.columns([3, 2])
    fig = go.Figure(go.Bar(x=risers["growth"], y=risers["label"], orientation="h", marker_color=FANS,
                           text=[f"×{x:.1f}" for x in risers["growth"]], textposition="outside", cliponaxis=False,
                           hovertemplate="<b>%{y}</b><br>×%{x:.2f} visits<extra></extra>"))
    c1.plotly_chart(plot_layout(fig, 470, title=f"Biggest risers · {month_name(train)} → {month_name(test)}",
                                xaxis_title="growth in total visits (×)",
                                xaxis_range=[0, risers["growth"].max() * 1.15]), width="stretch")
    fig = go.Figure(go.Bar(x=fallers["growth"], y=fallers["label"], orientation="h", marker_color=STRUCT,
                           text=[f"×{x:.2f}" for x in fallers["growth"]], textposition="outside", cliponaxis=False))
    c2.plotly_chart(plot_layout(fig, 470, title="Faded away", xaxis_title="growth (×)",
                                xaxis_range=[0, fallers["growth"].max() * 1.25]),
                    width="stretch")
    st.caption("Among the top 20% most-visited articles in the test month.")

    st.markdown("#### How fans arrived at the top articles")
    top = df.nlargest(10, "test_total").iloc[::-1]
    fig = go.Figure()
    for col, name, color in (("test_search", "Search engines", FANS), ("test_link_in_all", "Wikipedia links", STRUCT),
                             ("test_external", "Other sites / apps", WPR), ("test_other", "Other", LAST)):
        fig.add_trace(go.Bar(name=name, y=top["label"], x=top[col] / top["test_total"].clip(lower=1) * 100,
                             orientation="h", marker_color=color,
                             hovertemplate="%{y}: %{x:.0f}%<extra>" + name + "</extra>"))
    st.plotly_chart(plot_layout(fig, 430, barmode="stack", xaxis_title="% of visits",
                                legend=dict(orientation="h", y=1.1)), width="stretch")
    st.caption("If search dominates, readers arrive from Google rather than by surfing links - "
               "something PageRank's random-surfer model cannot see.")

# ---------------------------------------------------------------- 6. under the hood
with tabs[5]:
    st.markdown("#### MapReduce PageRank - one iteration = two jobs")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**1 · Map**  \nEach page emits its link list, plus `rank × weight / total weight` "
                "to every page it links to. Dead-end pages send their rank to a special key.")
    c2.markdown("**2 · Shuffle**  \nPairs are grouped by key, so each reducer receives every "
                "contribution flowing into one page.")
    c3.markdown("**3 · Reduce + finalize**  \nReducer sums the contributions; a map-only job adds "
                "teleport `(1-β)/N` and redistributes the dead-end rank.")
    with st.expander("Mapper and reducer source code"):
        st.code(inspect.getsource(contribution_mapper) + "\n" + inspect.getsource(contribution_reducer),
                language="python")

    st.markdown("#### Lab manual check (Experiment 11)")
    toy = [("A", "B"), ("A", "C"), ("A", "D"), ("B", "A"), ("B", "D"), ("C", "A"), ("D", "B"), ("D", "C")]
    _, hist = pagerank(toy, beta=1, max_iter=2, exact=True, history=True)
    expected = [{k: Fraction(1, 4) for k in "ABCD"},
                {"A": Fraction(9, 24), "B": Fraction(5, 24), "C": Fraction(5, 24), "D": Fraction(5, 24)},
                {"A": Fraction(15, 48), "B": Fraction(11, 48), "C": Fraction(11, 48), "D": Fraction(11, 48)}]
    dens = [4, 24, 48]
    toy_df = pd.DataFrame({f"V{i}": [f"{hist[i][k] * d}/{d}" for k in "ABCD"] for i, d in enumerate(dens)},
                          index=list("ABCD"))
    c1, c2 = st.columns([2, 3])
    c1.dataframe(toy_df, width="stretch")
    ok = all(hist[i] == expected[i] for i in range(3))
    c2.markdown(("✅ **Exact match** with the lab manual: V1 = 9/24, 5/24, 5/24, 5/24 and "
                 "V2 = 15/48, 11/48, 11/48, 11/48 (β = 1, exact fractions).") if ok
                else "❌ Mismatch with lab manual")
    c2.markdown("<span class='note'>Graph from the manual's matrix M: A→B,C,D · B→A,D · C→A · D→B,C. "
                "The full engine is also checked against NetworkX to within 10⁻¹¹ (toy_check.py).</span>",
                unsafe_allow_html=True)

    st.markdown("#### Convergence on the World Cup graph")
    cdf = pd.DataFrame(conv)
    c1, c2 = st.columns([3, 1])
    fig = go.Figure(go.Scatter(x=cdf["iteration"], y=cdf["l1_change"], mode="lines+markers",
                               line=dict(color=STRUCT, width=3)))
    c1.plotly_chart(plot_layout(fig, 330, yaxis=dict(type="log", title="L1 change (log)"),
                                xaxis_title="iteration"), width="stretch")
    c2.metric("Iterations to converge", len(cdf))
    c2.metric("Key-value pairs per iteration", fmt(cdf["intermediate_pairs"].iloc[0]))
    c2.metric("Seconds per iteration", f"{cdf['seconds'].mean():.2f}")

    st.markdown("#### Pipeline numbers")
    st.dataframe(pd.DataFrame({m: {"rows scanned": f"{v['rows_scanned']:,}", "rows kept (map)": f"{v['rows_kept']:,}",
                                   "articles with clicks": f"{v['articles_with_clicks']:,}",
                                   "links with clicks": f"{v['edges_with_clicks']:,}",
                                   "seconds": f"{v['seconds']}"} for m, v in cs.items()}),
                 width="stretch")
    st.caption("Limitations: clickstream hides pairs with ≤10 clicks; PageRank is computed inside the "
               "subgraph (links leaving it are cut); link targets that are redirects not in the set are dropped.")
