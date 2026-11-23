"""Builds submission/BDA_MiniProject_Kshant_10232.pptx.
Every number is read from results/metrics.json, results/rankings.csv, results/convergence.json
and data/*meta*.json (falls back to metrics.json, which embeds the same meta, if data/ is absent).
Run from the project root:  python submission/build_deck.py
"""
import json
from pathlib import Path

import pandas as pd
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
SUB = ROOT / "submission"
FIG = SUB / "figures"
OUT = SUB / "BDA_MiniProject_Kshant_10232.pptx"

M = json.loads((ROOT / "results/metrics.json").read_text())
CONV = json.loads((ROOT / "results/convergence.json").read_text())
DF = pd.read_csv(ROOT / "results/rankings.csv", index_col="title")
G, CS, MOD = M["graph"], M["clickstream"], M["models"]
TRAIN, TEST = M["train_month"], M["test_month"]
ROWS = sum(v["rows_scanned"] for v in CS.values())
SEARCH_SHARE = DF["test_search"].sum() / DF["test_total"].sum()
NAV_SHARE = DF["test_link_in_sub"].sum() / DF["test_total"].sum()


def mname(m):
    return pd.Timestamp(m + "-01").strftime("%B %Y")


def top(col, k=5):
    return [DF.at[t, "label"] for t in DF[col].nlargest(k).index]


# ------------------------------------------------------------------ style
NAVY = RGBColor(0x0B, 0x10, 0x20)
CARD = RGBColor(0x14, 0x1B, 0x2D)
EDGE = RGBColor(0x26, 0x30, 0x4A)
BLUE = RGBColor(0x5B, 0x8D, 0xEF)
AMBER = RGBColor(0xF5, 0xA5, 0x24)
GREEN = RGBColor(0x2B, 0xC4, 0x8A)
WHITE = RGBColor(0xE8, 0xEC, 0xF4)
MUTED = RGBColor(0x8B, 0x97, 0xAD)
FONT = "Segoe UI"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def new_slide(title=None, kicker=None):
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = NAVY
    if kicker:
        text(s, kicker, 0.6, 0.35, 12, 0.35, size=13, color=AMBER, bold=True)
    if title:
        text(s, title, 0.6, 0.65, 12.1, 0.8, size=32, bold=True)
    # thin accent bar bottom-left: blue (structure) + amber (clicks)
    for i, c in enumerate((BLUE, AMBER)):
        r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6 + i * 0.6), Inches(7.18), Inches(0.6), Inches(0.05))
        r.fill.solid(); r.fill.fore_color.rgb = c; r.line.fill.background()
    text(s, "Beyond PageRank · Kshant Carvalho · BDA Mini Project", 2.0, 7.05, 8, 0.3, size=10, color=MUTED)
    return s


def text(s, content, x, y, w, h, size=18, color=WHITE, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, font=FONT, spacing=1.0):
    """content: str or list of str / (str, dict) runs-per-paragraph."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = anchor
    paras = content if isinstance(content, list) else [content]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.line_spacing = spacing
        runs = p if isinstance(p, list) else [p]
        for r in runs:
            t, o = (r, {}) if isinstance(r, str) else r
            run = para.add_run()
            run.text = t
            f = run.font
            f.name = o.get("font", font)
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.color.rgb = o.get("color", color)
        if isinstance(p, list) or not isinstance(p, tuple):
            pass
    return tb


def box(s, x, y, w, h, fill=CARD, line=EDGE, radius=True, lw=1.0):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                             Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shp.adjustments[0] = 0.12
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line; shp.line.width = Pt(lw)
    shp.shadow.inherit = False
    return shp


def arrow(s, x1, y1, x2, y2, color=MUTED, w=2.0):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(w)
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return c


def picture(s, path, x, y, w, h, crop=None):
    """Fit image inside box (x,y,w,h) keeping aspect; optional crop (l,t,r,b) in px."""
    path = Path(path)
    if crop:
        im = Image.open(path).crop(crop)
        path = FIG / f"_{path.stem}_{crop[1]}_{crop[3]}.png"
        im.save(path)
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    pic = s.shapes.add_picture(str(path), Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2),
                               Inches(pw), Inches(ph))
    pic.line.color.rgb = EDGE
    pic.line.width = Pt(0.75)
    return pic


def stat(s, x, y, w, h, value, label, color=WHITE):
    box(s, x, y, w, h)
    text(s, value, x + 0.2, y + 0.15, w - 0.4, h * 0.55, size=30, bold=True, color=color,
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, label, x + 0.2, y + h * 0.6, w - 0.4, h * 0.38, size=13, color=MUTED)


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


pr, wpr, ind, last = (MOD[k] for k in ("PageRank", "Click-weighted PageRank", "In-degree", "Last month's clicks"))
d_rho = wpr["spearman_navigation"] - pr["spearman_navigation"]

# ================================================================== 1. Title
s = new_slide()
text(s, "BDA MINI PROJECT · BIG DATA ANALYTICS", 0.8, 1.2, 11, 0.4, size=14, color=AMBER, bold=True)
text(s, "Beyond PageRank", 0.8, 1.7, 11.5, 1.1, size=60, bold=True, color=BLUE)
text(s, "Comparing Structural Importance with Actual Human Navigation\non Wikipedia (2026 FIFA World Cup)",
     0.8, 2.85, 11.5, 1.2, size=26, color=WHITE)
box(s, 0.8, 4.45, 7.2, 1.95)
text(s, [[("Kshant Carvalho", {"bold": True, "size": 22})],
         "Roll No 10232 · Group 2",
         "BE Computer Engineering · Sem VII · AY 2026-27",
         "Guide: [GUIDE NAME]"], 1.05, 4.6, 6.8, 1.7, size=16, color=WHITE)
text(s, ["Fr. Conceicao Rodrigues College", "of Engineering (FRCRCE)", "Bandra, Mumbai"],
     8.4, 4.6, 4.6, 1.5, size=15, color=MUTED)
notes(s, "Hi, I'm Kshant Carvalho, roll number 10232. My BDA mini project asks one question: does Wikipedia's "
         "link structure, measured by PageRank, predict where readers actually click? I test it on the 2026 FIFA World Cup.")

# ================================================================== 2. Problem
s = new_slide("Does link structure predict where people go?", "PROBLEM & MOTIVATION")
for i, (col, head, body) in enumerate((
        (BLUE, "PageRank assumes", "a random surfer who follows links uniformly at random and sometimes teleports."),
        (AMBER, "Real readers", "search, follow stories and stars, and ignore most links in a page's references."),
        (GREEN, "So we measure", "how far the structural ranking is from real navigation, and whether real clicks fix it."))):
    x = 0.6 + i * 4.1
    box(s, x, 2.0, 3.85, 3.0)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(2.0), Inches(3.85), Inches(0.09))
    bar.fill.solid(); bar.fill.fore_color.rgb = col; bar.line.fill.background()
    text(s, head, x + 0.3, 2.35, 3.3, 0.6, size=22, bold=True, color=col)
    text(s, body, x + 0.3, 3.05, 3.3, 1.9, size=19, color=WHITE, spacing=1.1)
text(s, "A big sporting event is a good test: attention shifts quickly and is driven by match results, not links.",
     0.6, 5.4, 12, 0.5, size=17, color=MUTED)
notes(s, "PageRank models a random surfer clicking links uniformly. Real readers behave differently: they search, "
         "they chase stars and match results. So the problem is to measure how far the structural ranking is from "
         "real behaviour, and whether weighting links by real clicks closes the gap.")

# ================================================================== 3. Gap
s = new_slide("Research gap", "WHAT IS NEW HERE")
rows = [("Prior work", "This project"),
        ("2016-2018 clickstream snapshots", f"{mname(TRAIN)} and {mname(TEST)} clickstream"),
        ("Same month for weights and evaluation", f"Weights from {mname(TRAIN)}, tested on {mname(TEST)}"),
        ("Whole wiki or Simple English Wikipedia", "Event-driven topic subgraph (World Cup)"),
        ("Single-machine matrix methods", "PageRank and clickstream aggregation written as MapReduce")]
for r, (a, b) in enumerate(rows):
    y = 1.85 + r * 0.92
    hdr = r == 0
    box(s, 0.6, y, 5.9, 0.78, fill=CARD if not hdr else NAVY, line=EDGE if not hdr else None)
    box(s, 6.83, y, 5.9, 0.78, fill=CARD if not hdr else NAVY, line=BLUE if not hdr else None)
    text(s, a, 0.85, y, 5.5, 0.78, size=20 if hdr else 17, bold=hdr, color=MUTED if not hdr else WHITE,
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, b, 7.08, y, 5.5, 0.78, size=20 if hdr else 17, bold=hdr, color=WHITE if not hdr else AMBER,
         anchor=MSO_ANCHOR.MIDDLE)
notes(s, "Earlier studies, such as Dimitrov et al. and Fatigued PageRank, used 2016 to 2018 data and the same month "
         "for weights and evaluation. I use 2026 data, build the weights from June, test on July, and implement "
         "everything as MapReduce.")

# ================================================================== 4. Dataset
s = new_slide("Dataset", "REAL DATA, TWO SOURCES")
stat(s, 0.6, 1.9, 3.9, 1.6, f"{G['nodes']:,}", "articles in the World Cup subgraph", BLUE)
stat(s, 4.72, 1.9, 3.9, 1.6, f"{G['edges']:,}", "hyperlinks between them", BLUE)
stat(s, 8.84, 1.9, 3.9, 1.6, f"{ROWS / 1e6:.1f} M", "clickstream rows scanned", AMBER)
ct, cv = CS[TRAIN], CS[TEST]
text(s, [[("Wikipedia API link graph  ", {"bold": True, "color": BLUE})],
         f"Seed: {G['seed'].replace('_', ' ')}",
         f"Hop 1: {G['hop1']:,} pages · hop 2: {G['hop2']:,} pages (linked from ≥ {G['hop2_min_inlinks']} hop-1 pages)",
         f"{len(G['excluded'])} citation / identifier pages removed (ISBN, DOI, …)"],
     0.6, 3.85, 6.0, 2.6, size=16, spacing=1.15)
text(s, [[("Wikimedia clickstream dumps  ", {"bold": True, "color": AMBER})],
         f"{mname(TRAIN)} (group stage): {ct['rows_scanned']:,} rows",
         f"{mname(TEST)} (knockouts): {cv['rows_scanned']:,} rows",
         f"Rows kept by the mapper: {ct['rows_kept']:,} / {cv['rows_kept']:,}"],
     6.85, 3.85, 6.0, 2.6, size=16, spacing=1.15)
notes(s, f"The graph has {G['nodes']:,} articles and {G['edges']:,} links, crawled from the Wikipedia API two hops "
         f"out from the 2026 World Cup article. The clickstream is the public Wikimedia dump: about {ROWS / 1e6:.1f} "
         f"million rows across June and July 2026. June builds the weights; July is the ground truth.")

# ================================================================== 5. Architecture
s = new_slide("System architecture", "PIPELINE")
stages = [("Wikipedia API", "crawl, 2 hops,\ncached, ~1 req/s", BLUE),
          ("Subgraph", f"{G['nodes']:,} nodes\n{G['edges']:,} edges", BLUE),
          ("Clickstream\nMapReduce", "map · combine ·\nreduce", AMBER),
          ("PageRank\nMapReduce", "standard +\nclick-weighted", BLUE),
          ("Evaluation", "Spearman ρ,\ntop-10, NDCG@10", GREEN),
          ("Streamlit", "6-tab\ndashboard", AMBER)]
bw, gap, y0 = 1.75, 0.37, 2.45
for i, (head, sub, col) in enumerate(stages):
    x = 0.6 + i * (bw + gap)
    b = box(s, x, y0, bw, 2.0, line=col, lw=2)
    text(s, head, x + 0.1, y0 + 0.2, bw - 0.2, 0.85, size=17, bold=True, color=col, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, sub, x + 0.1, y0 + 1.05, bw - 0.2, 0.85, size=13, color=MUTED, align=PP_ALIGN.CENTER)
    if i < len(stages) - 1:
        arrow(s, x + bw + 0.03, y0 + 1.0, x + bw + gap - 0.03, y0 + 1.0)
# clickstream dump feeding in from below
box(s, 0.6 + 2 * (bw + gap), 5.25, bw, 0.9, line=AMBER)
text(s, "Clickstream dumps\n(.tsv.gz, ~1 GB)", 0.6 + 2 * (bw + gap) + 0.05, 5.25, bw - 0.1, 0.9, size=12,
     color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
xm = 0.6 + 2 * (bw + gap) + bw / 2
arrow(s, xm, 5.22, xm, y0 + 2.03, color=AMBER)
text(s, "Python · requests · pandas · SciPy · Plotly · Streamlit", 0.6, 6.4, 12, 0.4, size=14, color=MUTED)
notes(s, "The pipeline has six stages. A rate-limited crawler builds the subgraph. A MapReduce job filters the "
         "clickstream to that subgraph. MapReduce PageRank ranks the pages. The results are evaluated against July "
         "clicks and shown in a Streamlit dashboard.")

# ================================================================== 6. MapReduce PageRank
s = new_slide("MapReduce PageRank", "ALGORITHM")
for i, (head, body, col) in enumerate((
        ("Map", "emit link list + share\nrank·w / Σw to each out-link;\ndead ends → special key", BLUE),
        ("Shuffle", "group pairs by\ndestination page", MUTED),
        ("Reduce", "sum incoming shares;\nmap-only job adds\n(1−β)/N + dead-end mass", AMBER))):
    y = 1.75 + i * 1.45
    box(s, 0.6, y, 5.6, 1.2, line=col, lw=1.5)
    text(s, head, 0.8, y, 1.4, 1.2, size=20, bold=True, color=col, anchor=MSO_ANCHOR.MIDDLE)
    text(s, body, 2.2, y, 3.9, 1.2, size=14, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    if i < 2:
        arrow(s, 3.4, y + 1.22, 3.4, y + 1.43)
text(s, "r′(v) = (1−β)/N + β [ Σ u→v  r(u)·w(u,v)/W(u)  +  D/N ]", 0.6, 6.15, 6.2, 0.5, size=15,
     color=WHITE, font="Cambria Math")
# lab manual table
text(s, "Lab manual check (Exp 11, β = 1)", 6.9, 1.75, 5.8, 0.45, size=17, bold=True, color=AMBER)
vals = [("", "V0", "V1", "V2"), ("A", "1/4", "9/24", "15/48"), ("B", "1/4", "5/24", "11/48"),
        ("C", "1/4", "5/24", "11/48"), ("D", "1/4", "5/24", "11/48")]
tbl = s.shapes.add_table(5, 4, Inches(6.9), Inches(2.3), Inches(5.8), Inches(2.5)).table
for r, row in enumerate(vals):
    for c, v in enumerate(row):
        cell = tbl.cell(r, c)
        cell.fill.solid(); cell.fill.fore_color.rgb = CARD if r else EDGE
        cell.text = v
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        f = p.runs[0].font if p.runs else p.font
        f.size = Pt(17); f.name = FONT; f.bold = r == 0 or c == 0
        f.color.rgb = AMBER if (c == 3 and r) else WHITE
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
text(s, [f"Exact fractions match. Checked against NetworkX (toy_check.py).",
         f"World Cup graph: {len(CONV)} iterations to L1 < 10⁻⁹,",
         f"{CONV[0]['intermediate_pairs']:,} key-value pairs per iteration."],
     6.9, 5.0, 5.9, 1.4, size=14, color=MUTED, spacing=1.1)
notes(s, "Each iteration is two jobs. The mapper sends each page's rank along its out-links in proportion to the "
         "edge weight, the shuffle groups by page, and the reducer sums. A map-only job adds teleport. On the lab "
         f"manual example it gives exactly 9/24 and 15/48. On our graph it converges in {len(CONV)} iterations.")

# ================================================================== 7. Leaderboards
s = new_slide("PageRank picks hubs; fans pick the tournament", "RESULT 1 · LEADERBOARDS")
picture(s, FIG / "01_leaderboards_crop.png", 0.6, 1.65, 12.13, 5.25)
notes(s, f"Left is PageRank's top ten: {', '.join(top('pagerank', 3))}, newspapers. Right is where fans navigated in "
         f"July: the World Cup pages. Overlap is {pr['top10_navigation']} out of 10.")

# ================================================================== 8. Scatter
s = new_slide("Structure vs attention", "RESULT 2 · ONE DOT PER ARTICLE")
picture(s, FIG / "02_structure_vs_attention_crop.png", 0.6, 1.55, 8.6, 5.4)
bs = M["beta_sweep_spearman_navigation"]
text(s, [[("Spearman ρ vs navigation", {"bold": True, "color": BLUE, "size": 17})]] +
     [f"β = {b}:  ρ = {v:.3f}" for b, v in bs.items()] +
     ["", "Changing β barely helps: the structure itself is the problem."],
     9.5, 1.8, 3.4, 4.5, size=16, spacing=1.15)
notes(s, f"Each dot is an article: PageRank against July clicks, both on log scales. The cloud is wide, "
         f"ρ = {pr['spearman_navigation']:.2f}. Changing the damping factor moves ρ only between "
         f"{min(bs.values()):.2f} and {max(bs.values()):.2f}.")

# ================================================================== 9. Over/under
s = new_slide("Overrated and underrated articles", "RESULT 3 · PERCENTILE GAP")
picture(s, FIG / "03_overrated_underrated_crop.png", 0.6, 1.55, 12.13, 5.0)
text(s, "Amber: many clicks, low PageRank (players in form).   Blue: high PageRank, few clicks (news outlets, encyclopedias).",
     0.6, 6.55, 12.1, 0.4, size=14, color=MUTED)
notes(s, "This ranks articles by the gap between their click percentile and their PageRank percentile. Underrated "
         "pages are breakout players. Overrated pages are newspapers and reference sites that every article cites "
         "but few readers open.")

# ================================================================== 10. Scoreboard
s = new_slide("Model scoreboard", f"RESULT 4 · GROUND TRUTH = {mname(TEST).upper()} NAVIGATION")
hdr = ("Model", "Spearman ρ", "Top-10 overlap", "NDCG@10", "ρ (all traffic)")
names = ["PageRank", "Click-weighted PageRank", "In-degree", "Last month's clicks"]
colors = [BLUE, GREEN, RGBColor(0xA7, 0x8B, 0xFA), MUTED]
tbl = s.shapes.add_table(5, 5, Inches(0.6), Inches(1.75), Inches(12.13), Inches(3.3)).table
widths = [4.0, 2.0, 2.2, 1.9, 2.03]
for c, w in enumerate(widths):
    tbl.columns[c].width = Inches(w)
for r in range(5):
    for c in range(5):
        cell = tbl.cell(r, c)
        cell.fill.solid(); cell.fill.fore_color.rgb = EDGE if r == 0 else CARD
        if r == 0:
            v = hdr[c]
        else:
            m = MOD[names[r - 1]]
            v = [names[r - 1], f"{m['spearman_navigation']:.3f}", f"{m['top10_navigation']}/10",
                 f"{m['ndcg10_navigation']:.3f}", f"{m['spearman_attention']:.3f}"][c]
        cell.text = v
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
        f = p.runs[0].font
        f.size = Pt(19 if r else 16); f.name = FONT
        f.bold = r == 0 or c == 0 or (r == 2 and c in (1, 3))
        f.color.rgb = colors[r - 1] if (c == 0 and r) else WHITE
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
box(s, 0.6, 5.35, 12.13, 1.35, line=GREEN, lw=1.5)
text(s, [[("Click-weighted PageRank (June weights) vs PageRank:  ", {"bold": True}),
          (f"Δρ = {d_rho:+.3f}", {"bold": True, "color": GREEN})],
         "Out-of-sample: weights from June, scores against July. The naive “last month's clicks” baseline is still "
         "best, because attention persists from month to month."],
     0.85, 5.43, 11.7, 1.2, size=16, spacing=1.1)
notes(s, f"Standard PageRank gets ρ = {pr['spearman_navigation']:.2f} and zero of the top ten. Weighting links with "
         f"June clicks raises it to {wpr['spearman_navigation']:.2f}. But the simple baseline, last month's clicks, "
         f"is best at {last['spearman_navigation']:.2f}. I report that honestly: attention persists.")

# ================================================================== 11. June -> July
s = new_slide(f"{mname(TRAIN).split()[0]} → {mname(TEST).split()[0]}: attention moves, and arrives by search",
              "RESULT 5 · TEMPORAL VIEW")
picture(s, FIG / "05_june_to_july_crop.png", 0.45, 1.6, 5.6, 4.85, crop=(0, 0, 1190, 960))
picture(s, FIG / "05_june_to_july_crop.png", 6.25, 1.6, 6.65, 4.85, crop=(0, 1080, 1995, 2120))
text(s, f"{SEARCH_SHARE * 100:.1f}% of {mname(TEST)} visits to the {G['nodes']:,} graph articles came from search; "
        f"only {NAV_SHARE * 100:.1f}% were link clicks from inside the World Cup graph.",
     0.6, 6.55, 12.1, 0.45, size=15, color=WHITE)
notes(s, f"From June to July, knockout-stage players and referees rose sharply, and eliminated teams faded. On the "
         f"right, most visits arrive from search: {SEARCH_SHARE * 100:.0f} percent. A random-surfer model cannot "
         f"see search at all.")

# ================================================================== 12. Conclusion
s = new_slide("Conclusion, limitations, future work", "WRAP-UP")
cols = [("Conclusion", GREEN, [
            f"Link structure ranks reference hubs, not destinations (ρ = {pr['spearman_navigation']:.2f}).",
            f"June click weights lift PageRank to ρ = {wpr['spearman_navigation']:.2f} on July data.",
            f"Last month's clicks still wins (ρ = {last['spearman_navigation']:.2f})."]),
        ("Limitations", AMBER, [
            "Subgraph boundary cuts outgoing rank.",
            "Clickstream hides pairs with ≤ 10 clicks.",
            "One tournament, two months.",
            "Local MapReduce runtime, not a Hadoop cluster."]),
        ("Future work", BLUE, [
            "Model search arrivals as a teleport vector.",
            "Run on Hadoop / Spark for the full wiki.",
            "More events and more months."])]
for i, (head, col, items) in enumerate(cols):
    x = 0.6 + i * 4.1
    box(s, x, 1.8, 3.85, 4.2, line=col, lw=1.5)
    text(s, head, x + 0.3, 2.0, 3.3, 0.5, size=22, bold=True, color=col)
    text(s, ["• " + t for t in items], x + 0.3, 2.65, 3.35, 3.3, size=17, spacing=1.2)
notes(s, "Structure alone tells you what is referenced, not what is read. Real clicks fix much of that, but "
         "recent behaviour is the best predictor. Limitations are the subgraph boundary and hidden small counts. "
         "Next I would model search as the teleport vector and scale up on Spark.")

# ================================================================== 13. References
s = new_slide("References")
refs = [
    "[1] L. Page, S. Brin, R. Motwani, T. Winograd, “The PageRank Citation Ranking: Bringing Order to the Web,” Stanford InfoLab, Tech. Rep., 1999.",
    "[2] D. Dimitrov, P. Singer, F. Lemmerich, M. Strohmaier, “What Makes a Link Successful on Wikipedia?,” in Proc. WWW, 2017. arXiv:1611.02508.",
    "[3] J. Devezas, S. Nunes, “Fatigued PageRank,” arXiv:2104.05369, 2021.",
    "[4] E. Wulczyn, D. Taraborelli, “Wikipedia Clickstream,” figshare / Wikimedia Research, 2015.",
    "[5] J. Leskovec, A. Rajaraman, J. D. Ullman, Mining of Massive Datasets, 3rd ed., Cambridge Univ. Press, 2020, ch. 5.",
    "[6] J. Dean, S. Ghemawat, “MapReduce: Simplified Data Processing on Large Clusters,” in Proc. OSDI, 2004.",
]
text(s, refs, 0.6, 1.7, 12.1, 5.0, size=16, spacing=1.25)
notes(s, "These are the six references: the original PageRank report, two Wikipedia clickstream studies, the "
         "clickstream dataset, the MMDS textbook chapter on link analysis, and the MapReduce paper. Thank you.")

prs.save(OUT)
print("saved", OUT, len(prs.slides), "slides")
