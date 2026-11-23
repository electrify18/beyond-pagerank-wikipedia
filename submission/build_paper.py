"""Builds submission/BDA_Paper_Kshant_10232.docx (IEEE conference style, two columns)
and, if MS Word is available, the PDF next to it.
Every number is read from results/ (metrics.json, rankings.csv, convergence.json).
Run from the project root:  python submission/build_paper.py
"""
import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
SUB = ROOT / "submission"
FIG = SUB / "figures"
OUT = SUB / "BDA_Paper_Kshant_10232.docx"

M = json.loads((ROOT / "results/metrics.json").read_text())
CONV = json.loads((ROOT / "results/convergence.json").read_text())
DF = pd.read_csv(ROOT / "results/rankings.csv", index_col="title")
ROB = json.loads((ROOT / "results/robustness.json").read_text())
G, CS, MOD = M["graph"], M["clickstream"], M["models"]
TRAIN, TEST = M["train_month"], M["test_month"]
CT, CV = CS[TRAIN], CS[TEST]
ROWS = CT["rows_scanned"] + CV["rows_scanned"]
PR, WPR, IND, LAST = (MOD[k] for k in ("PageRank", "Click-weighted PageRank", "In-degree", "Last month's clicks"))
BS = M["beta_sweep_spearman_navigation"]
TOT = DF["test_total"].sum()
SEARCH = DF["test_search"].sum() / TOT
LINK_ALL = DF["test_link_in_all"].sum() / TOT
NAV = DF["test_link_in_sub"].sum() / TOT
ITER = len(CONV)
PAIRS = CONV[0]["intermediate_pairs"]
SEC_IT = sum(c["seconds"] for c in CONV) / ITER
D_RHO = WPR["spearman_navigation"] - PR["spearman_navigation"]


def mname(m):
    return pd.Timestamp(m + "-01").strftime("%B %Y")


def lab(t):
    return DF.at[t, "label"]


def top(col, k):
    return [lab(t) for t in DF[col].nlargest(k).index]


def f3(x):
    return f"{x:.3f}"


def n(x):
    return f"{x:,}"


# ------------------------------------------------------------------ document setup
doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.font.size = Pt(10)
pf = st.paragraph_format
pf.space_before = Pt(0)
pf.space_after = Pt(0)
pf.line_spacing = 1.0

sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)        # A4
sec.top_margin, sec.bottom_margin = Inches(0.75), Inches(1.0)
sec.left_margin = sec.right_margin = Inches(0.62)
COL_W = (8.27 - 2 * 0.62 - 0.17) / 2                                  # one column, inches


def para(text="", size=10, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         indent=True, after=0, before=0, keep=False):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.first_line_indent = Inches(0.14) if indent else Inches(0)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    if keep:
        p.paragraph_format.keep_with_next = True
    if text:
        add(p, text, size=size, bold=bold, italic=italic)
    return p


def add(p, text, size=10, bold=False, italic=False, sup=False, sub=False, smallcaps=False):
    """Add text; segments wrapped in *...* are italic (math variables)."""
    parts = text.split("*")
    for i, t in enumerate(parts):
        if not t:
            continue
        r = p.add_run(t)
        r.font.size = Pt(size)
        r.font.name = "Times New Roman"
        r.bold = bold
        r.italic = italic or (i % 2 == 1)
        r.font.superscript = sup
        r.font.subscript = sub
        r.font.small_caps = smallcaps
    return p


ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
_h = [0]
_sub = [0]


def heading(title):
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, before=8, after=4, keep=True)
    add(p, f"{ROMAN[_h[0]]}. ", size=10)
    add(p, title, size=10, smallcaps=True)
    _h[0] += 1
    _sub[0] = 0


def subheading(title):
    p = para(align=WD_ALIGN_PARAGRAPH.LEFT, indent=False, before=4, after=2, keep=True)
    add(p, f"{chr(65 + _sub[0])}. {title}", size=10, italic=True)
    _sub[0] += 1


_eq = [0]


def equation(*segments):
    """Centered equation with a right-aligned number. segments: (text, kind) kind in '', 'i', 'sub', 'sup'."""
    _eq[0] += 1
    p = para(indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, before=3, after=3)
    ts = p.paragraph_format.tab_stops
    ts.add_tab_stop(Inches(COL_W / 2), WD_TAB_ALIGNMENT.CENTER)
    ts.add_tab_stop(Inches(COL_W), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run("\t")
    for seg in segments:
        t, kind = seg if isinstance(seg, tuple) else (seg, "")
        r = p.add_run(t)
        r.font.size = Pt(10)
        r.italic = "i" in kind
        r.font.subscript = "sub" in kind
        r.font.superscript = "sup" in kind
    p.add_run(f"\t({_eq[0]})")
    return _eq[0]


_fig = [0]


def figure(path, caption, width=COL_W):
    _fig[0] += 1
    p = para(indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, keep=True)
    p.add_run().add_picture(str(path), width=Inches(width))
    c = para(indent=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=3, after=6)
    add(c, f"Fig. {_fig[0]}.  ", size=8)
    add(c, caption, size=8)
    return _fig[0]


def listing(lines):
    for i, ln in enumerate(lines):
        p = para(indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, before=4 if i == 0 else 0,
                 after=4 if i == len(lines) - 1 else 0, keep=i < len(lines) - 1)
        p.paragraph_format.left_indent = Inches(0.1)
        r = p.add_run(ln)
        r.font.name = "Courier New"
        r.font.size = Pt(7.5)


def set_cols(section, num):
    el = section._sectPr.xpath("./w:cols")
    el = el[0] if el else OxmlElement("w:cols")
    el.set(qn("w:num"), str(num))
    el.set(qn("w:space"), str(int(0.17 * 1440)))
    if el.getparent() is None:
        section._sectPr.append(el)


def _frame(p, width_in, yalign="top"):
    fp = OxmlElement("w:framePr")
    for k, v in (("w", str(int(width_in * 1440))), ("hSpace", "0"), ("vSpace", str(int(0.12 * 1440))),
                 ("wrap", "around"), ("vAnchor", "margin"), ("hAnchor", "margin"),
                 ("xAlign", "center"), ("yAlign", yalign)):
        fp.set(qn(f"w:{k}"), v)
    pPr = p._p.get_or_add_pPr()
    pPr.insert(0, fp)


def figure_wide(path, caption, width=7.0, yalign="top", num=None):
    """Figure spanning both columns, floated to the top of the page in a Word frame (IEEE style)."""
    if num is None:
        _fig[0] += 1
        num = _fig[0]
    p = para(indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    p.add_run().add_picture(str(path), width=Inches(width))
    c = para(indent=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=3, after=4)
    add(c, f"Fig. {num}.  ", size=8)
    add(c, caption, size=8)
    _frame(p, width, yalign)
    _frame(c, width, yalign)
    return num


_tab = [0]


def set_cell_border(cell, **edges):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for edge, val in edges.items():
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), val)
        el.set(qn("w:sz"), "6")
        el.set(qn("w:color"), "000000")
        b.append(el)
    tcPr.append(b)


def table(caption, rows, widths, bold_rows=(0,)):
    _tab[0] += 1
    c = para(indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=1, keep=True)
    add(c, f"TABLE {ROMAN[_tab[0] - 1]}", size=8)
    c = para(indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, after=3, keep=True)
    add(c, caption, size=8, smallcaps=True)
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for r, row in enumerate(rows):
        for ci, v in enumerate(row):
            cell = t.cell(r, ci)
            cell.width = Inches(widths[ci])
            cp = cell.paragraphs[0]
            cp.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 else WD_ALIGN_PARAGRAPH.CENTER
            cp.paragraph_format.first_line_indent = Inches(0)
            cp.paragraph_format.keep_with_next = r < len(rows) - 1      # keep the table in one piece
            add(cp, v, size=8, bold=r in bold_rows)
            edges = {}
            if r == 0:
                edges.update(top="single", bottom="single")
            if r == len(rows) - 1:
                edges["bottom"] = "single"
            if edges:
                set_cell_border(cell, **edges)
    para(after=4)
    return _tab[0]


# ------------------------------------------------------------------ title block (one column)
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=10)
add(p, "Beyond PageRank: Comparing Structural Importance with Actual Human Navigation "
       "on Wikipedia (2026 FIFA World Cup)", size=22)
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
add(p, "Kshant Carvalho", size=11)
for line in ("Roll No. 10232, Group 2, BE Computer Engineering, Sem VII (AY 2026-27)",
             "Fr. Conceicao Rodrigues College of Engineering (FRCRCE), Bandra, Mumbai, India",
             "Big Data Analytics Mini Project  ·  Guide: [GUIDE NAME]"):
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add(p, line, size=10, italic=line.startswith("Fr."))
para(after=8)

# ------------------------------------------------------------------ two-column body
body = doc.add_section(WD_SECTION.CONTINUOUS)
cols = body._sectPr.xpath("./w:cols")
cols = cols[0] if cols else OxmlElement("w:cols")
cols.set(qn("w:num"), "2")
cols.set(qn("w:space"), str(int(0.17 * 1440)))
if cols.getparent() is None:
    body._sectPr.append(cols)

p = para(indent=True, after=4)
add(p, "Abstract", size=9, bold=True, italic=True)
add(p, "—PageRank ranks web pages by link structure alone, assuming a reader who follows links at random. "
       "We test whether that structural ranking matches where people actually go on Wikipedia during a large "
       f"event, the 2026 FIFA World Cup. We crawled a topic subgraph of {n(G['nodes'])} articles and "
       f"{n(G['edges'])} links through the Wikipedia API and processed {ROWS / 1e6:.1f} million rows of the "
       f"public Wikimedia clickstream for {mname(TRAIN)} and {mname(TEST)}. Both PageRank and the clickstream "
       "aggregation are written as MapReduce jobs; the PageRank engine reproduces the course lab-manual example "
       "exactly. Four rankings are built from June data or from structure only and scored against July navigation. "
       f"Standard PageRank reaches a Spearman correlation of {f3(PR['spearman_navigation'])}, shares "
       f"{PR['top10_navigation']} of its top-10 articles with the readers' top 10, and has an NDCG@10 of "
       f"{f3(PR['ndcg10_navigation'])}. Weighting each link by its June click count raises these to "
       f"{f3(WPR['spearman_navigation'])}, {WPR['top10_navigation']}/10 and {f3(WPR['ndcg10_navigation'])}. "
       f"A naive baseline, last month's clicks, is best overall ({f3(LAST['spearman_navigation'])}). "
       "Link structure mostly measures how often a page is referenced, not how often it is read.", size=9, bold=True)

p = para(indent=True, after=6)
add(p, "Index Terms", size=9, bold=True, italic=True)
add(p, "—PageRank, MapReduce, link analysis, Wikipedia clickstream, web usage mining, rank correlation.",
    size=9, bold=True)

# ------------------------------------------------------------------ I. Introduction
heading("Introduction")
para("PageRank [1] scores a page by the rank of the pages that link to it. It is usually explained with the "
     "random surfer: a reader who clicks a random link on the current page and, with a small probability, jumps "
     "to a random page instead. The model needs only the link graph, which is why it scales and why it became the "
     "standard example of link analysis in big-data courses [5].")
para("Real readers do not behave like that surfer. Many arrive from a search engine, some links are clicked far "
     "more often than others, and interest during a live event changes week by week. Wikipedia is a good place to "
     "measure the difference, because Wikimedia publishes a monthly clickstream: counts of how many times readers "
     "went from one page to another [4]. A major tournament makes the test sharper, since attention moves with "
     "match results rather than with the link structure.")
para("This paper asks a direct question: on the Wikipedia articles around the 2026 FIFA World Cup, how well does "
     "PageRank predict where readers actually navigate, and how much does it help to weight links by real clicks? "
     "The contributions are:")
for b in (f"a reproducible pipeline that builds a {n(G['nodes'])}-article topic subgraph and filters "
          f"{ROWS / 1e6:.1f} million clickstream rows with MapReduce;",
          "a MapReduce PageRank (standard and click-weighted) checked against the lab-manual example and NetworkX;",
          f"an out-of-sample evaluation: every model uses {mname(TRAIN)} data or structure only and is scored on "
          f"{mname(TEST)};",
          "an interactive dashboard that shows where structure and attention disagree."):
    p = para(indent=False)
    p.paragraph_format.left_indent = Inches(0.15)
    p.paragraph_format.first_line_indent = Inches(-0.12)
    add(p, "•  " + b)

# ------------------------------------------------------------------ II. Related work
heading("Related Work")
para("Page et al. [1] introduced PageRank as the stationary distribution of a random surfer with a damping "
     "factor. Leskovec, Rajaraman and Ullman [5, ch. 5] describe the practical issues used here: dead ends, spider "
     "traps, taxation with teleport probability 1−β, and computing PageRank with MapReduce. Dean and Ghemawat [6] "
     "describe the MapReduce model of map, shuffle by key and reduce, including combiners that pre-aggregate "
     "values on the mapper side.")
para("Wulczyn and Taraborelli [4] released the Wikipedia clickstream, which records (referrer, article) pairs "
     "and their monthly counts, with pairs seen 10 times or fewer removed for privacy. Dimitrov et al. [2] used "
     "this data to study which links readers click. They found that link position and the structure around a link "
     "affect its click-through, and that rankings weighted by observed navigation differ from unweighted "
     "PageRank. Devezas and Nunes [3] proposed Fatigued PageRank and evaluated PageRank-style rankings against "
     "clickstream transitions on the Simple English Wikipedia link graph. [3] reported a Spearman correlation of "
     "0.99 between PageRank and the number of visits (incoming transitions from the December 2018 English "
     "Wikipedia clickstream), computed over all 897,577 articles of that graph.")
para("These studies use clickstream snapshots from 2016-2018 and, in general, build and evaluate on the same "
     "period. This project uses 2026 data, focuses on an event-driven topic, takes link weights from one month and "
     "evaluates on the next, and implements both the clickstream aggregation and PageRank as MapReduce jobs.")

# ------------------------------------------------------------------ III. Dataset
heading("Dataset")
subheading("Link Graph")
para(f"The seed article is “{G['seed'].replace('_', ' ')}”. Hop 1 contains the {n(G['hop1'])} articles the seed "
     f"links to. Hop 2 contains {n(G['hop2'])} further articles, each linked from at least "
     f"{G['hop2_min_inlinks']} hop-1 articles. Only links with both ends inside the set are kept (an induced "
     f"subgraph). {len(G['excluded'])} citation and identifier pages, such as ISBN, Digital object identifier and "
     f"Wayback Machine, were removed because they are linked from reference sections rather than article text. "
     f"The final graph has {n(G['nodes'])} articles and {n(G['edges'])} directed links. The crawl used the MediaWiki "
     f"API and took {G['minutes']} minutes with a one-second pause between requests.")
subheading("Clickstream")
para("Each clickstream row is (prev, curr, type, n): the referrer, the target article, the kind of referrer "
     "(an internal link, an external source such as a search engine, or other) and the number of transitions in "
     f"the month [4]. We use English Wikipedia dumps for {mname(TRAIN)} (group stage) and {mname(TEST)} "
     "(knockout stage and final). Table I summarises both months.")
table("Clickstream processing per month", [
    ("", mname(TRAIN), mname(TEST)),
    ("Rows scanned", n(CT["rows_scanned"]), n(CV["rows_scanned"])),
    ("Rows kept by mapper", n(CT["rows_kept"]), n(CV["rows_kept"])),
    ("Articles with clicks", n(CT["articles_with_clicks"]), n(CV["articles_with_clicks"])),
    ("Links with clicks", n(CT["edges_with_clicks"]), n(CV["edges_with_clicks"])),
    ("Total visits to subgraph", n(CT["total_clicks_in_subgraph"]), n(CV["total_clicks_in_subgraph"])),
    ("Job time (s)", str(CT["seconds"]), str(CV["seconds"])),
], widths=[1.45, 0.95, 0.95])

# ------------------------------------------------------------------ IV. Methodology
heading("Methodology")
f_arch = figure_wide(FIG / "architecture.png",
                "System pipeline. The crawl and the clickstream download run in parallel; every later stage "
                "reads only the files written by the stage before it.")
para(f"Fig. {f_arch} shows the pipeline. Each stage writes plain files (node list, edge list, per-month click "
     "counts, rankings and metrics), so any stage can be re-run on its own.")
subheading("Subgraph Construction")
para("The crawler requests the outgoing article links of up to 50 titles per API call, follows continuation "
     "tokens, resolves redirects, and caches every response on disk so an interrupted crawl can resume. Hop-2 "
     "candidates are counted by how many hop-1 pages link to them and kept if they reach the threshold.")
subheading("MapReduce PageRank")
para("Let *N* be the number of pages, β the damping factor, *w*(*u*,*v*) the weight of link *u*→*v*, "
     "*W*(*u*) the total out-weight of *u*, and *D* the rank held by dead-end pages. One iteration computes")
equation(("r", "i"), ("t+1", "sup"), "(", ("v", "i"), ") = (1−β)/", ("N", "i"), " + β [ Σ", ("u→v", "isub"), " ",
         ("r", "i"), ("t", "sup"), "(", ("u", "i"), ")·", ("w", "i"), "(", ("u", "i"), ",", ("v", "i"), ")/",
         ("W", "i"), "(", ("u", "i"), ") + ", ("D", "i"), ("t", "sup"), "/", ("N", "i"), " ]")
para("with *r*⁰(*v*) = 1/*N*. Each iteration runs as two jobs, following [5], [6]. In job 1 the mapper reads a "
     "record (*u*, rank, out-links), re-emits the out-link list so the graph survives the iteration, and emits "
     "the share *r*(*u*)·*w*(*u*,*v*)/*W*(*u*) to every out-neighbour *v*. A page with no out-links emits its "
     "whole rank to a special dead-end key. The shuffle groups values by key, and the reducer sums the incoming "
     "shares for each page. Job 2 is map-only: it adds the teleport term and spreads the dead-end mass evenly. "
     "Iteration stops when the L1 change between rank vectors falls below 10⁻⁹. The job-1 functions are:")
listing(["map(u, (r, out)):",
         "  emit(u, ('G', out))           # keep the graph",
         "  W = sum(w for (v, w) in out)",
         "  if W == 0: emit('#DANGLING', ('R', r))",
         "  else: for (v, w) in out:",
         "          emit(v, ('R', r * w / W))",
         "reduce(v, values):",
         "  s = sum(x for (t, x) in values if t == 'R')",
         "  out = the 'G' payload, or [] if none",
         "  emit(v, (s, out))"])
para("The engine was checked in two ways. With β = 1 and exact fractions on the four-page example of the course "
     "lab manual (A→B,C,D; B→A,D; C→A; D→B,C), it gives V1 = (9/24, 5/24, 5/24, 5/24) and "
     "V2 = (15/48, 11/48, 11/48, 11/48), matching the manual exactly. It also matches NetworkX on that graph "
     "with β = 0.85 and on a 500-node random graph with dead ends, for both unweighted and weighted links. "
     f"Table {_tab[0] + 1} shows the first two iterations.")
table("Lab-manual example, β = 1 (exact fractions)", [
    ("Page", "V0", "V1", "V2"),
    ("A", "1/4", "9/24", "15/48"), ("B", "1/4", "5/24", "11/48"),
    ("C", "1/4", "5/24", "11/48"), ("D", "1/4", "5/24", "11/48"),
], widths=[0.6, 0.6, 0.6, 0.6])
subheading("Click-Weighted PageRank")
para(f"The same engine is run with *w*(*u*,*v*) = *c*(*u*,*v*) + 1, where *c* is the number of {mname(TRAIN)} "
     "clicks on that link. The +1 keeps links whose counts were hidden by the ≤10 privacy threshold in the graph. "
     f"Of the {n(G['edges'])} links, {n(M['edges_with_train_clicks'])} had a June click count.")
subheading("Clickstream MapReduce")
para("The mapper streams the compressed dump line by line and drops any row whose target is outside the subgraph. "
     "For a kept row it emits per-article counters (total visits, link arrivals, link arrivals from inside the "
     "subgraph, search, external, other) and, for internal links, a per-link counter keyed by (prev, curr). An "
     "in-mapper combiner sums values in a hash map as the file streams, so the full month never sits in memory, "
     "and the reducer sums the partial counts per key.")
subheading("Baselines")
para(f"In-degree counts incoming links inside the subgraph. Last month's clicks ranks articles by their "
     f"{mname(TRAIN)} link arrivals from other subgraph articles. It is a naive persistence forecast.")
subheading("Evaluation Metrics")
para(f"The main ground truth *y*(*v*) is navigation: {mname(TEST)} clicks into *v* on links from other subgraph "
     "articles, which is what a random surfer on this graph models. A second ground truth, attention, counts all "
     f"{mname(TEST)} visits including search. No {mname(TEST)} data is used to build any model. Spearman's "
     "rank correlation compares the full rankings; without ties it is")
equation("ρ = 1 − 6 Σ", ("i", "isub"), " ", ("d", "i"), ("i", "isub"), ("2", "sup"), " / [ ", ("n", "i"), "(",
         ("n", "i"), ("2", "sup"), " − 1) ]")
para("where *d*ᵢ is the rank difference of article *i* (SciPy's tie-corrected version is used). Top-10 overlap is "
     "|*T*₁₀(model) ∩ *T*₁₀(truth)|. NDCG@10 rewards placing heavily visited articles near the top:")
equation(("DCG", "i"), ("@k", "isub"), " = Σ", ("i=1..k", "isub"), " ", ("y", "i"), ("π(i)", "isub"),
         " / log", ("2", "sub"), "(", ("i", "i"), " + 1)")
equation(("NDCG", "i"), ("@k", "isub"), " = ", ("DCG", "i"), ("@k", "isub"), " / ", ("IDCG", "i"), ("@k", "isub"))
para("where π orders articles by model score and IDCG is the DCG of the ideal order, with *k* = 10 and raw click "
     "counts as gains.")

# ------------------------------------------------------------------ V. Implementation
heading("Implementation")
para("The project is written in Python with requests (API and downloads), pandas and SciPy (analysis), and "
     "Plotly with Streamlit (dashboard). The MapReduce runtime is a small in-process implementation: a map phase "
     "over records, a shuffle that groups emitted pairs by key, and a reduce phase. The mapper and reducer "
     "functions are written exactly as they would be for Hadoop, so the same logic could run on a cluster. "
     f"On the World Cup graph PageRank (β = 0.85) converged in {ITER} iterations, each producing {n(PAIRS)} "
     f"intermediate key-value pairs and taking {SEC_IT:.2f} s on average. The two clickstream jobs took "
     f"{CT['seconds']} s and {CV['seconds']} s, and the full analysis stage (four β values, the weighted run and "
     f"all metrics) took {M['analysis_seconds']} s on a laptop. Fig. {_fig[0] + 1} shows the convergence; the "
     "L1 change falls at a steady geometric rate, as expected for damping β = 0.85.")
figure(FIG / "convergence.png", f"Convergence of MapReduce PageRank on the World Cup graph (L1 change per "
       f"iteration, log scale): {ITER} iterations, {n(PAIRS)} intermediate pairs per iteration.")
para("The dashboard has six tabs: leaderboards, a structure-versus-attention scatter plot with a β slider, "
     "overrated and underrated articles, the model scoreboard, June-to-July movers with arrival sources, and an "
     "‘under the hood’ tab with the lab-manual check and convergence plot. It reads only the result files, so it "
     "can be hosted without the raw data.")

# ------------------------------------------------------------------ VI. Results
heading("Results")
f_lead = figure_wide(FIG / "01_leaderboards_crop.png",
       f"Top 10 by PageRank (left) and by {mname(TEST)} navigation (right). No article appears in both lists.")
t_main = table(f"Models scored against {mname(TEST)}", [
    ("Model", "ρ nav.", "Top-10", "NDCG@10", "ρ all"),
    ("PageRank (β = 0.85)", f3(PR["spearman_navigation"]), f"{PR['top10_navigation']}/10",
     f3(PR["ndcg10_navigation"]), f3(PR["spearman_attention"])),
    ("Click-weighted PageRank", f3(WPR["spearman_navigation"]), f"{WPR['top10_navigation']}/10",
     f3(WPR["ndcg10_navigation"]), f3(WPR["spearman_attention"])),
    ("In-degree", f3(IND["spearman_navigation"]), f"{IND['top10_navigation']}/10",
     f3(IND["ndcg10_navigation"]), f3(IND["spearman_attention"])),
    ("Last month's clicks", f3(LAST["spearman_navigation"]), f"{LAST['top10_navigation']}/10",
     f3(LAST["ndcg10_navigation"]), f3(LAST["spearman_attention"])),
], widths=[1.3, 0.45, 0.5, 0.6, 0.45])
para(f"Table {ROMAN[t_main - 1]} gives the main result. ‘ρ nav.’, ‘Top-10’ and ‘NDCG@10’ use the navigation ground truth; "
     f"‘ρ all’ uses all {mname(TEST)} traffic. Standard PageRank has a weak positive correlation with navigation "
     f"(ρ = {f3(PR['spearman_navigation'])}), none of its top 10 appear in the readers' top 10, and its NDCG@10 is "
     f"{f3(PR['ndcg10_navigation'])}. In-degree does better on every navigation metric "
     f"(ρ = {f3(IND['spearman_navigation'])}). Click-weighted PageRank, built from {mname(TRAIN)} clicks only, "
     f"reaches ρ = {f3(WPR['spearman_navigation'])}, an improvement of Δρ = {D_RHO:+.3f} over PageRank. The "
     f"last-month baseline is the strongest model (ρ = {f3(LAST['spearman_navigation'])}, "
     f"{LAST['top10_navigation']}/10, NDCG@10 = {f3(LAST['ndcg10_navigation'])}).")
f_sc = _fig[0] + 2                      # numbered after Fig. (scoreboard), anchored early
figure_wide(FIG / "02_structure_vs_attention_crop.png", num=f_sc, caption=
       f"PageRank against {mname(TEST)} navigation clicks for each article (log scales), with the β sweep on the "
       "right. Articles with zero clicks are not drawn.")
para(f"Fig. {f_lead} shows why. PageRank's top five are {', '.join(top('pagerank', 5))}: countries, newspapers and "
     f"the sport itself, which almost every article links to from infoboxes, navigation boxes or references. The "
     f"readers' top five are {', '.join(top('test_link_in_sub', 5))}. Click-weighting moves "
     f"{', '.join(top('weighted_pagerank', 1))} to first place, but general pages such as "
     f"{', '.join(top('weighted_pagerank', 5)[1:4])} stay in its top five. Table {_tab[0] + 1} lists the "
     "full top 10 of each ranking.")
rows = [("#", "PageRank", "Click-weighted PR", f"{mname(TEST).split()[0]} navigation")]
for i, (a, b, c) in enumerate(zip(top("pagerank", 10), top("weighted_pagerank", 10), top("test_link_in_sub", 10)), 1):
    rows.append((str(i), a, b, c))
table("Top 10 articles under each ranking", rows, widths=[0.3, 0.95, 1.1, 1.05])
para(f"Fig. {_fig[0] + 1} plots the Spearman and NDCG@10 columns of Table {ROMAN[t_main - 1]} side by side. "
     f"Click-weighting raises both metrics by a similar amount (ρ by {D_RHO:+.3f}, NDCG@10 by "
     f"{WPR['ndcg10_navigation'] - PR['ndcg10_navigation']:+.3f}), so the gain is not limited to the top of the "
     "ranking.")
figure(FIG / "scoreboard_chart.png", f"Spearman ρ (solid) and NDCG@10 (faded) for each model against "
       f"{mname(TEST)} navigation.")
_fig[0] += 1                             # consume the scatter figure number
para(f"Fig. {f_sc} plots PageRank against navigation clicks. The cloud is wide: news outlets such as USA Today and "
     "Bloomberg News sit far right but low, while individual players sit high on the left. Changing the damping "
     "factor does not fix this. Spearman ρ against navigation is " +
     ", ".join(f"{v:.3f} at β = {b}" for b, v in BS.items()) +
     ", so less link-following gives a slightly better fit.")
f_ou = _fig[0] = _fig[0] + 1            # number reserved; figure is placed at the Discussion
para(f"Fig. {f_ou} lists the largest disagreements. The ‘underrated’ side is players whose pages drew attention "
     f"during the tournament. The ‘overrated’ side is almost entirely news organisations and reference works. "
     f"Arrival sources point the same way: across the {n(G['nodes'])} articles, {SEARCH * 100:.1f}% of "
     f"{mname(TEST)} visits came from search engines, {LINK_ALL * 100:.1f}% from Wikipedia links of any origin, "
     f"and {NAV * 100:.1f}% from links inside the World Cup graph. Fig. {_fig[0] + 1} breaks this down for "
     "the ten most-visited articles.")
figure(FIG / "arrivals.png", f"How readers arrived at the ten most-visited articles in {mname(TEST)}: search "
       "engines, Wikipedia links, other sites and apps, and other.")

# ------------------------------------------------------------------ VII. Discussion
heading("Discussion")
figure_wide(FIG / "03_overrated_underrated_crop.png", num=f_ou, caption=
       "Articles with the largest gap between click percentile and PageRank percentile. Left: more clicks than "
       "structure predicts. Right: structurally central but rarely clicked.")
para("The results separate two meanings of ‘important’. PageRank rewards being referenced: a country or a "
     "newspaper is linked from hundreds of player and match articles, and those links pass rank to each other. "
     "Readers, however, mostly move between tournament pages and the players and teams in the news. The links "
     "that carry rank and the links that carry readers are different links.")
para("Weighting links by observed clicks is a simple fix and it works out of sample: the weights come from June "
     f"and the score from July, yet ρ rises from {f3(PR['spearman_navigation'])} to "
     f"{f3(WPR['spearman_navigation'])}. This agrees with the direction reported by Dimitrov et al. [2]. "
     "Click-weighted PageRank still does not beat the naive baseline. Attention persists from month to month, so "
     "last month's clicks is a strong forecast, and PageRank was never designed to forecast. Its value here is "
     "as a measure of how much the link structure alone explains, and the answer is: not much.")
_rpr = ROB["spearman_navigation"]["PageRank"]
para(f"The weak fit is not caused by reference-section boilerplate: removing the {ROB['nodes_removed']} "
     f"citation and identifier pages ({n(ROB['edges_removed'])} links) changed PageRank's ρ only from "
     f"{f3(_rpr['with_citation_pages'])} to {f3(_rpr['without_citation_pages'])}.")
para("In-degree beating PageRank is also worth noting. On this graph, the recursive part of PageRank mostly "
     "moves rank among general hub pages, which pushes them further up, while a plain in-link count keeps "
     "football pages higher. The β sweep supports this: the less weight given to link-following, the closer the "
     "ranking gets to navigation.")

# ------------------------------------------------------------------ VIII. Limitations
heading("Limitations and Future Work")
para("The study has several limitations. PageRank is computed inside the subgraph, so rank that would flow to "
     "outside pages is cut. The clickstream hides pairs with 10 or fewer transitions, so weak links look like "
     "zero. Link targets that are redirects to pages outside the set are dropped. The study covers one tournament "
     "and two months. Pages tied at the hop-2 threshold are chosen arbitrarily, so a fresh crawl gives a slightly "
     "different graph. The MapReduce jobs run in a single process rather than on a Hadoop cluster.")
para("Future work: use the share of search arrivals as a personalised teleport vector so the model can "
     "represent readers who do not arrive by links; run the same mappers and reducers on Hadoop or Spark over the "
     "full English Wikipedia; and repeat the test on other events and more months to see whether the gap is "
     "specific to sport.")

# ------------------------------------------------------------------ IX. Conclusion
heading("Conclusion")
para(f"On {n(G['nodes'])} World Cup articles and {ROWS / 1e6:.1f} million clickstream rows, structural PageRank "
     f"predicted July 2026 navigation poorly (ρ = {f3(PR['spearman_navigation'])}, {PR['top10_navigation']}/10 "
     f"top-10 overlap). It ranks the pages that are referenced most, not the pages people read. Weighting links "
     f"with the previous month's clicks raised ρ to {f3(WPR['spearman_navigation'])}, and the previous month's "
     f"clicks alone did best (ρ = {f3(LAST['spearman_navigation'])}). The MapReduce pipeline, the lab-manual "
     "check and the dashboard make the comparison reproducible.")

p = para(align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, before=8, after=4, keep=True)
add(p, "Acknowledgment", size=10, smallcaps=True)
para("The author thanks [GUIDE NAME] for guidance, and the Wikimedia Foundation for publishing the clickstream "
     "and link data under open licences.")

p = para(align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, before=8, after=4, keep=True)
add(p, "References", size=10, smallcaps=True)
REFS = [
    "L. Page, S. Brin, R. Motwani, and T. Winograd, “The PageRank citation ranking: Bringing order to the web,” "
    "Stanford InfoLab, Tech. Rep., 1999.",
    "D. Dimitrov, P. Singer, F. Lemmerich, and M. Strohmaier, “What makes a link successful on Wikipedia?,” in "
    "Proc. 26th Int. Conf. World Wide Web (WWW), 2017. arXiv:1611.02508.",
    "J. Devezas and S. Nunes, “Fatigued PageRank,” arXiv:2104.05369, 2021.",
    "E. Wulczyn and D. Taraborelli, “Wikipedia clickstream,” figshare / Wikimedia Research, 2015.",
    "J. Leskovec, A. Rajaraman, and J. D. Ullman, Mining of Massive Datasets, 3rd ed. Cambridge, U.K.: "
    "Cambridge Univ. Press, 2020, ch. 5.",
    "J. Dean and S. Ghemawat, “MapReduce: Simplified data processing on large clusters,” in Proc. 6th USENIX "
    "Symp. Operating Systems Design and Implementation (OSDI), 2004.",
]
for i, r in enumerate(REFS, 1):
    p = para(indent=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=1)
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    add(p, f"[{i}]  {r}", size=8)

doc.save(OUT)
print("saved", OUT)

try:
    from docx2pdf import convert
    convert(str(OUT), str(OUT.with_suffix(".pdf")))
    print("saved", OUT.with_suffix(".pdf"))
except Exception as e:                       # Word not installed, etc.
    print("PDF skipped:", e)
