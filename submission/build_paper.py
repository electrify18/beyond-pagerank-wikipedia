"""Builds submission/BDA_Paper_Kshant_10232.docx in IEEE conference format (US Letter, two columns)
and, if MS Word is available, the PDF next to it.
Every number is read from results/ (metrics.json, rankings.csv, convergence.json, robustness.json).
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
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
SUB = ROOT / "submission"
FIG = SUB / "figures"
OUT = SUB / "BDA_Paper_Kshant_10232.docx"

AUTHOR_EMAIL = "kshant.carvalho@gmail.com"

M = json.loads((ROOT / "results/metrics.json").read_text())
CONV = json.loads((ROOT / "results/convergence.json").read_text())
ROB = json.loads((ROOT / "results/robustness.json").read_text())
DF = pd.read_csv(ROOT / "results/rankings.csv", index_col="title")
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
D_NDCG = WPR["ndcg10_navigation"] - PR["ndcg10_navigation"]
RPR = ROB["spearman_navigation"]["PageRank"]


def mname(m):
    return pd.Timestamp(m + "-01").strftime("%B %Y")


def mshort(m):
    return pd.Timestamp(m + "-01").strftime("%B")


def top(col, k):
    return [DF.at[t, "label"] for t in DF[col].nlargest(k).index]


def f3(x):
    return f"{x:.3f}"


def n(x):
    return f"{x:,}"


# ------------------------------------------------------------------ page setup (US Letter, IEEE margins)
doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.element.rPr.rFonts.set(qn("w:cs"), "Times New Roman")
st.font.size = Pt(10)
st.paragraph_format.space_before = Pt(0)
st.paragraph_format.space_after = Pt(0)
st.paragraph_format.line_spacing = 1.0

sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.top_margin, sec.bottom_margin = Inches(0.75), Inches(1.0)
sec.left_margin = sec.right_margin = Inches(0.75)      # as measured in the reference paper
COL_W, COL_GAP = 3.375, 0.25
BODY_AFTER = 4          # pt between body paragraphs (the reference shows a small gap)


def add(p, text, size=10, bold=False, italic=False, smallcaps=False):
    """Add text; segments wrapped in *...* are set in italic (math variables)."""
    for i, t in enumerate(text.split("*")):
        if not t:
            continue
        r = p.add_run(t)
        r.font.size = Pt(size)
        r.font.name = "Times New Roman"
        r.bold = bold
        r.italic = italic or (i % 2 == 1)
        r.font.small_caps = smallcaps
    return p


def para(text="", size=10, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True,
         before=0, after=BODY_AFTER, keep=False):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.first_line_indent = Inches(0.2) if indent else Inches(0)
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.keep_with_next = keep
    pf.widow_control = True
    if text:
        add(p, text, size=size, bold=bold, italic=italic)
    return p


ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
_h, _s = [0], [0]


def heading(title):
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, before=10, after=4, keep=True)
    add(p, f"{ROMAN[_h[0]]}. {title.upper()}", size=10, smallcaps=True)
    _h[0] += 1
    _s[0] = 0


def subheading(title):
    p = para(align=WD_ALIGN_PARAGRAPH.LEFT, indent=False, before=4, after=2, keep=True)
    add(p, f"{chr(65 + _s[0])}. {title}", size=10, italic=True)
    _s[0] += 1


def numbered(items, size=10):
    for i, t in enumerate(items, 1):
        p = para(indent=False, after=3)
        pf = p.paragraph_format
        pf.left_indent = Inches(0.25)
        pf.first_line_indent = Inches(-0.25)
        pf.tab_stops.add_tab_stop(Inches(0.25))
        add(p, f"{i})\t{t}", size=size)
    p.paragraph_format.space_after = Pt(BODY_AFTER)


_eq = [0]


def equation(*segments):
    """Centred equation, number flush right. segments: str or (text, kinds) with kinds in i/sub/sup."""
    _eq[0] += 1
    p = para(indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, before=2, after=4)
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


def _borders(cell, color="000000", sz=6, val="single", **edges):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders")
        tcPr.append(b)
    for edge, on in edges.items():
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), val if on else "nil")
        if on:
            el.set(qn("w:sz"), str(sz))
            el.set(qn("w:color"), color)
            el.set(qn("w:space"), "0")
        b.append(el)


def _no_table_borders(t):
    tblPr = t._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{e}")
        el.set(qn("w:val"), "nil")
        b.append(el)
    tblPr.append(b)


def _cell_margins(t, top=0.04, bottom=0.04, left=0.06, right=0.06):
    tblPr = t._tbl.tblPr
    m = OxmlElement("w:tblCellMar")
    for e, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{e}")
        el.set(qn("w:w"), str(int(v * 1440)))
        el.set(qn("w:type"), "dxa")
        m.append(el)
    tblPr.append(m)


_fig = [0]


def figure(path, caption, width=COL_W - 0.16):
    """Image inside a thin dashed grey box (full column width), caption below, left-aligned, 8 pt."""
    _fig[0] += 1
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _no_table_borders(t)
    _cell_margins(t, 0.05, 0.05, 0.05, 0.05)
    c = t.cell(0, 0)
    c.width = Inches(COL_W)
    _borders(c, color="9A9A9A", sz=6, val="dashed", top=True, bottom=True, left=True, right=True)
    p = c.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width))
    cap = para(indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, before=3, after=8)
    add(cap, f"Fig. {_fig[0]}. {caption}", size=8)
    return _fig[0]


_tab = [0]


def table(title, rows, widths, align=None, size=9):
    """IEEE table: 'TABLE I' + small-caps title above, horizontal rules only (top, under header, bottom)."""
    _tab[0] += 1
    c1 = para(indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, before=4, after=0, keep=True)
    add(c1, f"TABLE {ROMAN[_tab[0] - 1]}", size=8)
    c2 = para(indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, after=3, keep=True)
    add(c2, title.upper(), size=8, smallcaps=True)
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _no_table_borders(t)
    _cell_margins(t, 0.02, 0.02, 0.05, 0.05)
    last = len(rows) - 1
    widths = [w * COL_W / sum(widths) for w in widths]
    for r, row in enumerate(rows):
        for ci, v in enumerate(row):
            cell = t.cell(r, ci)
            cell.width = Inches(widths[ci])
            cp = cell.paragraphs[0]
            a = (align or ["L"] * len(row))[ci]
            cp.alignment = {"L": WD_ALIGN_PARAGRAPH.LEFT, "C": WD_ALIGN_PARAGRAPH.CENTER,
                            "R": WD_ALIGN_PARAGRAPH.RIGHT}[a]
            cp.paragraph_format.keep_with_next = r < last
            add(cp, v, size=size, bold=(r == 0))
            _borders(cell, sz=8 if r in (0, last) else 4,
                     **({"top": True, "bottom": True} if r == 0 else {"bottom": True} if r == last else {}))
    para(after=6)
    return _tab[0]


# ------------------------------------------------------------------ title + author block (single column)
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=10)
add(p, "Beyond PageRank: Comparing Structural Importance\nwith Actual Human Navigation on Wikipedia\n"
       "(2026 FIFA World Cup)", size=20)

AUTHORS = [("Kshant Carvalho", AUTHOR_EMAIL), ("Prof. Ankita Amburle", None)]
t = doc.add_table(rows=1, cols=2)
t.alignment = WD_TABLE_ALIGNMENT.CENTER
t.autofit = False
_no_table_borders(t)
for ci, (name, email) in enumerate(AUTHORS):
    cell = t.cell(0, ci)
    cell.width = Inches(3.4)
    cp = cell.paragraphs[0]
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add(cp, name, size=11)
    for line in ("Dept. of Computer Engineering", "Fr. Conceicao Rodrigues College of Engineering",
                 "Mumbai, India"):
        q = cell.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add(q, line, size=9, italic=True)
    if email:
        q = cell.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add(q, email, size=10)
para(after=0, size=6).paragraph_format.line_spacing = Pt(8)

# ------------------------------------------------------------------ two-column body
body = doc.add_section(WD_SECTION.CONTINUOUS)
cols = body._sectPr.xpath("./w:cols")
cols = cols[0] if cols else OxmlElement("w:cols")
cols.set(qn("w:num"), "2")
cols.set(qn("w:space"), str(int(COL_GAP * 1440)))
if cols.getparent() is None:
    body._sectPr.append(cols)

p = para(indent=False, after=6)
add(p, "Abstract", size=9, bold=True, italic=True)
add(p, "—PageRank ranks pages by link structure alone and assumes a reader who follows links at random. We "
       "test whether that ranking matches where readers actually went on Wikipedia during a large live event, "
       f"the 2026 FIFA World Cup. We crawled a {n(G['nodes'])}-article, {n(G['edges'])}-link topic subgraph "
       f"through the Wikipedia API and scanned {ROWS / 1e6:.1f} million rows of the Wikimedia clickstream for "
       f"{mname(TRAIN)} and {mname(TEST)}. Both the clickstream aggregation and PageRank are written as "
       "MapReduce jobs, and the PageRank engine reproduces the course lab-manual example exactly. Four rankings "
       f"are built from {mshort(TRAIN)} data or from structure alone and scored against {mshort(TEST)} "
       f"navigation. Standard PageRank reaches a Spearman correlation of {f3(PR['spearman_navigation'])}, shares "
       f"{PR['top10_navigation']} of its top 10 articles with the readers' top 10 and has an NDCG@10 of "
       f"{f3(PR['ndcg10_navigation'])}. Weighting each link by its {mshort(TRAIN)} click count raises these to "
       f"{f3(WPR['spearman_navigation'])}, {WPR['top10_navigation']}/10 and {f3(WPR['ndcg10_navigation'])}. A "
       f"naive baseline, last month's clicks, is best ({f3(LAST['spearman_navigation'])}). We also state what the "
       "study does not do: the MapReduce jobs run in one process rather than on a cluster, and the evaluation "
       "covers one tournament and two months.", size=9, bold=True)
p = para(indent=False, after=8)
add(p, "Index Terms", size=9, bold=True, italic=True)
add(p, "—PageRank, MapReduce, Wikipedia clickstream, link analysis, big data, FIFA World Cup", size=9, bold=True)

# ================================================================== I. INTRODUCTION
heading("Introduction")
para("PageRank [1] scores a page by the rank of the pages that link to it. It is usually explained with the "
     "random surfer: a reader who clicks a random link on the current page and, with a small probability, jumps "
     "to a random page. The model needs only the link graph, which is why it scales and why it is the standard "
     "example of link analysis in big-data courses [5].")
para("Real readers do not behave like that surfer. Many arrive from a search engine, a few links on a page take "
     "most of the clicks, and during a live event interest moves with the news. Wikipedia lets us measure the "
     "gap, because Wikimedia publishes a monthly clickstream: how many times readers went from one page to "
     "another [4]. A major tournament makes the test sharper, since attention follows match results rather than "
     "the link structure.")
para("This paper asks how well PageRank predicts where readers navigate among the Wikipedia articles around the "
     "2026 FIFA World Cup, and how much it helps to weight links by real clicks. Our contributions are:")
numbered([
    f"A reproducible pipeline that crawls a {n(G['nodes'])}-article topic subgraph and filters "
    f"{ROWS / 1e6:.1f} million clickstream rows with a MapReduce job.",
    "A MapReduce PageRank engine, standard and click-weighted, checked against the lab-manual example and "
    "against NetworkX.",
    f"An out-of-sample evaluation: every model uses {mname(TRAIN)} data or structure only and is scored on "
    f"{mname(TEST)} navigation with Spearman ρ, top-10 overlap and NDCG@10.",
    "A Streamlit dashboard that shows where link structure and reader attention disagree.",
])
para("We report the gaps as plainly as the results. The MapReduce jobs run in a single Python process that "
     "imitates map, shuffle and reduce; nothing runs on Hadoop. PageRank is computed inside the subgraph only, "
     "the clickstream hides pairs with 10 or fewer transitions, and the study covers one tournament and two "
     "months. Section VII sets out what closing each gap would take.")

# ================================================================== II. RELATED WORK
heading("Related Work")
para("Page et al. [1] defined PageRank as the stationary distribution of a random surfer with a damping "
     "factor. Dean and Ghemawat [6] described MapReduce, in which a map function emits key-value pairs, the "
     "framework groups them by key, and a reduce function combines each group; combiners pre-aggregate on the "
     "map side. Leskovec, Rajaraman and Ullman [5, ch. 5] show how PageRank is computed with MapReduce and how "
     "dead ends and spider traps are handled with taxation.")
para("Dimitrov et al. [2] used the Wikipedia clickstream to study which links readers click, and found that "
     "link position and the structure around a link affect its click-through. They also showed that "
     "rankings weighted by observed navigation differ from unweighted PageRank. Devezas and Nunes [3] proposed "
     "Fatigued PageRank and evaluated ranking metrics on the Simple English Wikipedia link graph. [3] reported a "
     "Spearman correlation of 0.99 between PageRank and the number of visits (incoming transitions from the "
     "December 2018 English Wikipedia clickstream), computed over all 897,577 articles of that graph.")
para("Wulczyn and Taraborelli [4] released the clickstream dataset itself, which records (referrer, article) "
     "pairs with their monthly counts and removes pairs seen 10 times or fewer. The studies above use "
     "2016–2018 snapshots and build and evaluate on the same period. We use 2026 data on an event-driven topic, "
     "take link weights from one month and evaluate on the next, and write both the clickstream aggregation and "
     "PageRank as MapReduce jobs.")

# ================================================================== III. DATA AND EXPERIMENTAL PROTOCOL
heading("Data and Experimental Protocol")
subheading("Data")
para(f"The seed article is “{G['seed'].replace('_', ' ')}”. Hop 1 holds the {n(G['hop1'])} articles it links "
     f"to, and hop 2 holds {n(G['hop2'])} more, each linked from at least {G['hop2_min_inlinks']} hop-1 "
     f"articles. Only links with both ends in the set are kept. {len(G['excluded'])} citation and identifier "
     "pages (ISBN, Digital object identifier, Wayback Machine and others) were removed because reference "
     f"sections link them, not article text. The final graph has {n(G['nodes'])} articles and "
     f"{n(G['edges'])} directed links; the crawl took {G['minutes']} minutes with a one-second pause between "
     "API requests.")
para(f"The clickstream dumps for {mname(TRAIN)} (group stage) and {mname(TEST)} (knockout stage and final) have "
     f"{n(CT['rows_scanned'])} and {n(CV['rows_scanned'])} rows. Each row is (prev, curr, type, n): referrer, "
     "target article, referrer type (internal link, external source such as a search engine, or other) and the "
     f"monthly count [4]. The mapper kept {n(CT['rows_kept'])} and {n(CV['rows_kept'])} rows whose target is in "
     f"the subgraph; {n(CT['articles_with_clicks'])} and {n(CV['articles_with_clicks'])} articles received "
     "clicks.")
subheading("Evaluation protocol")
para(f"Every model is built from {mname(TRAIN)} data or from the link structure alone, and scored only on "
     f"{mname(TEST)}. No {mshort(TEST)} count is used to build a model, so there is no leakage between weights "
     "and ground truth. The main ground truth is navigation: the clicks an article received in "
     f"{mshort(TEST)} on links from other subgraph articles, which is exactly what a random surfer on this graph "
     f"models. A second ground truth, attention, counts all {mshort(TEST)} visits including search.")
subheading("Metrics")
para("We report Spearman's rank correlation over all articles, the overlap between the model's top 10 and the "
     "readers' top 10, and NDCG@10, which rewards putting heavily visited articles near the top. The formulas "
     "are given in Section V-E.")

# ================================================================== IV. SYSTEM ARCHITECTURE
heading("System Architecture")
f_arch = _fig[0] + 1
para(f"Fig. {f_arch} shows the pipeline. A crawler builds the link subgraph from the Wikipedia API while the "
     "clickstream dumps download in parallel. A MapReduce job reduces each dump to per-article and per-link "
     "counts. A second MapReduce engine computes PageRank, the evaluation stage scores each ranking against "
     "July, and a Streamlit dashboard presents the results. Each stage writes plain files, so any stage can be "
     "re-run on its own.")
figure(FIG / "fig_architecture.png", "System architecture of the pipeline.")
t_impl = _tab[0] + 1
para(f"Table {ROMAN[t_impl - 1]} lists which parts are implemented and which are simulated or absent. We include "
     "it because the distinction matters when reading the results.")
table("Implementation status of main components", [
    ("Component", "Status", "Notes"),
    ("Wikipedia API crawler", "Implemented", "Cached, rate-limited, resumable"),
    ("Clickstream download", "Implemented", "Monthly dumps, resumable"),
    ("Clickstream MapReduce", "Local", "In-process map/combine/reduce"),
    ("PageRank MapReduce", "Local", "In-process; two jobs per iteration"),
    ("Hadoop / HDFS cluster", "Not present", "Same functions could run on one"),
    ("Click-weighted PageRank", "Implemented", "Weights from June only"),
    ("Evaluation metrics", "Implemented", "SciPy Spearman, NDCG@10"),
    ("Correctness checks", "Implemented", "toy_check.py: lab manual, NetworkX"),
    ("Automated test suite / CI", "Not present", "Only toy_check.py"),
    ("Streamlit dashboard", "Implemented", "Reads results/ only"),
    ("Deterministic crawl", "Partial", "Ties at hop-2 cut-off not ordered"),
], widths=[1.35, 0.78, 1.37], size=8.5)

# ================================================================== V. METHODOLOGY
heading("Methodology")
subheading("Subgraph construction")
para("The crawler asks the MediaWiki API for the outgoing article links of up to 50 titles per call, follows "
     "continuation tokens, resolves redirects and caches every response on disk, so an interrupted crawl "
     "resumes where it stopped. Hop-2 candidates are counted by how many hop-1 pages link to them.")
subheading("MapReduce PageRank")
para("Let *N* be the number of pages, β the damping factor, *w*(*u*,*v*) the weight of link *u*→*v*, *W*(*u*) "
     "the total out-weight of *u*, and *D* the rank held by pages with no out-links. Starting from "
     "*r*⁰(*v*) = 1/*N*, one iteration computes", after=0)
equation(("r", "i"), ("t+1", "sup"), "(", ("v", "i"), ") = ", "(1−β)/", ("N", "i"), " + β[Σ", ("u→v", "isub"),
         " ", ("r", "i"), ("t", "sup"), "(", ("u", "i"), ")", ("w", "i"), "(", ("u", "i"), ",", ("v", "i"), ")/",
         ("W", "i"), "(", ("u", "i"), ") + ", ("D", "i"), ("t", "sup"), "/", ("N", "i"), "]")
para("Each iteration is two jobs [5], [6]. In job 1 the mapper reads a record (*u*, rank, out-links), "
     "re-emits the link list so the graph survives the iteration, and sends *r*(*u*)*w*(*u*,*v*)/*W*(*u*) to "
     "every out-neighbour *v*; a page with no out-links sends its whole rank to a special dead-end key. The "
     "shuffle groups values by key and the reducer sums the shares for each page. Job 2 is map-only: it adds "
     "the teleport term and spreads the dead-end mass evenly. Iteration stops when the L1 change between rank "
     "vectors falls below 10⁻⁹.")
t_lab = _tab[0] + 1
para(f"With β = 1 and exact fractions on the four-page lab-manual graph (A→B,C,D; B→A,D; C→A; D→B,C), the "
     f"engine gives V1 = 9/24, 5/24, 5/24, 5/24 and V2 = 15/48, 11/48, 11/48, 11/48, matching the manual exactly "
     f"(Table {ROMAN[t_lab - 1]}). It also matches NetworkX with β = 0.85 on that graph and on a 500-node random "
     "graph with dead ends, for both unweighted and weighted links.")
table("Lab-manual check (β = 1, exact fractions)", [
    ("Page", "V0", "V1", "V2"),
    ("A", "1/4", "9/24", "15/48"), ("B", "1/4", "5/24", "11/48"),
    ("C", "1/4", "5/24", "11/48"), ("D", "1/4", "5/24", "11/48"),
], widths=[0.8, 0.9, 0.9, 0.9], align=["L", "C", "C", "C"])
subheading("Click-weighted PageRank")
para(f"The same engine is run with link weights taken from the {mshort(TRAIN)} clickstream,", after=0)
equation(("w", "i"), "(", ("u", "i"), ",", ("v", "i"), ") = ", ("c", "i"), ("Jun", "sub"), "(", ("u", "i"), ",",
         ("v", "i"), ") + 1")
para(f"where *c*(*u*,*v*) is the number of {mshort(TRAIN)} clicks on that link. The +1 keeps links whose counts were "
     f"hidden by the privacy threshold. Of the {n(G['edges'])} links, {n(M['edges_with_train_clicks'])} had a "
     f"{mshort(TRAIN)} click count.")
subheading("Clickstream aggregation")
para("The mapper streams each compressed dump line by line and drops rows whose target is outside the subgraph. "
     "For a kept row it emits per-article counters (total visits, link arrivals, link arrivals from inside the "
     "subgraph, search, external, other) and, for internal links, a per-link counter keyed by (prev, curr). An "
     "in-mapper combiner sums the values in a hash map as the file streams past, so a month never sits in "
     "memory, and the reducer sums the partial counts per key.")
subheading("Metrics")
para("Spearman's ρ compares two full rankings; without ties it is", after=0)
equation("ρ = 1 − 6Σ", ("i", "isub"), ("d", "i"), ("i", "isub"), ("2", "sup"), " / [", ("n", "i"), "(",
         ("n", "i"), ("2", "sup"), " − 1)]")
para("where *d*ᵢ is the rank difference of article *i*; SciPy's tie-corrected version is used. With *y* the "
     "ground-truth clicks and π the order given by the model, NDCG@10 is", after=0)
equation(("DCG", "i"), ("@k", "sub"), " = Σ", ("i=1..k", "isub"), " ", ("y", "i"), ("π(i)", "isub"),
         " / log", ("2", "sub"), "(", ("i", "i"), " + 1)")
equation(("NDCG", "i"), ("@k", "sub"), " = ", ("DCG", "i"), ("@k", "sub"), " / ", ("IDCG", "i"), ("@k", "sub"))
para("with *k* = 10, raw click counts as gains, and IDCG the DCG of the ideal order. Top-10 overlap is the size "
     "of the intersection of the two top-10 sets.")

# ================================================================== VI. RESULTS
heading("Results")
subheading("Structure against navigation")
t_mod = _tab[0] + 1
para(f"Table {ROMAN[t_mod - 1]} gives the main result. Standard PageRank has a weak positive correlation with "
     f"{mshort(TEST)} navigation (ρ = {f3(PR['spearman_navigation'])}), none of its top 10 appear in the readers' "
     f"top 10, and its NDCG@10 is {f3(PR['ndcg10_navigation'])}. In-degree does better on every navigation "
     f"metric (ρ = {f3(IND['spearman_navigation'])}). Click-weighted PageRank, built from {mshort(TRAIN)} clicks "
     f"only, reaches ρ = {f3(WPR['spearman_navigation'])} (Δρ = {D_RHO:+.3f}, ΔNDCG@10 = {D_NDCG:+.3f}). "
     f"Click-weighted PageRank did not beat the naive baseline: last month's clicks is the strongest model "
     f"(ρ = {f3(LAST['spearman_navigation'])}, {LAST['top10_navigation']}/10, NDCG@10 = "
     f"{f3(LAST['ndcg10_navigation'])}).")
table(f"Models scored against {mname(TEST)}", [
    ("Model", "ρ nav.", "Top-10", "NDCG@10", "ρ all"),
    ("PageRank (β = 0.85)", f3(PR["spearman_navigation"]), f"{PR['top10_navigation']}/10",
     f3(PR["ndcg10_navigation"]), f3(PR["spearman_attention"])),
    ("Click-weighted PR", f3(WPR["spearman_navigation"]), f"{WPR['top10_navigation']}/10",
     f3(WPR["ndcg10_navigation"]), f3(WPR["spearman_attention"])),
    ("In-degree", f3(IND["spearman_navigation"]), f"{IND['top10_navigation']}/10",
     f3(IND["ndcg10_navigation"]), f3(IND["spearman_attention"])),
    ("Last month's clicks", f3(LAST["spearman_navigation"]), f"{LAST['top10_navigation']}/10",
     f3(LAST["ndcg10_navigation"]), f3(LAST["spearman_attention"])),
], widths=[1.1, 0.48, 0.52, 0.76, 0.45], align=["L", "C", "C", "C", "C"], size=8.5)
para("“ρ nav.”, “Top-10” and “NDCG@10” use the navigation ground truth; “ρ all” uses all "
     f"{mshort(TEST)} traffic.")

subheading("Leaderboards")
f_lead = _fig[0] + 1
para(f"Fig. {f_lead} shows why the correlation is weak. PageRank's top five are "
     f"{', '.join(top('pagerank', 5))}: countries, newspapers and the sport itself, which almost every article "
     "links to from infoboxes, navigation boxes or references. The readers' top five are "
     f"{', '.join(top('test_link_in_sub', 5))}. Click-weighting moves {top('weighted_pagerank', 1)[0]} to first "
     f"place, but general pages such as {', '.join(top('weighted_pagerank', 5)[1:4])} stay in its top five.")
figure(FIG / "01_leaderboards_crop.png",
       f"Top 10 by PageRank (left) and by {mname(TEST)} navigation (right); no article is in both lists.")

subheading("Damping factor")
f_sc = _fig[0] + 1
para(f"Fig. {f_sc} plots PageRank against navigation clicks on log scales. News outlets such as USA Today and "
     "Bloomberg News sit far right but low, while individual players sit high on the left. Changing the "
     "damping factor does not fix this: ρ against navigation is " +
     ", ".join(f"{v:.3f} at β = {b}" for b, v in BS.items()) +
     ". Less link-following gives a slightly better fit.")
figure(FIG / "02_structure_vs_attention_crop.png",
       f"PageRank against {mname(TEST)} navigation clicks per article, with the β sweep.")

subheading("Overrated and underrated articles")
f_ou = _fig[0] + 1
para(f"Fig. {f_ou} ranks articles by the gap between their click percentile and their PageRank percentile. The "
     "underrated side is players whose pages drew attention during the tournament; the overrated side is "
     f"almost entirely news organisations and reference works. Arrival sources point the same way: "
     f"{SEARCH * 100:.1f}% of {mshort(TEST)} visits to the subgraph came from search engines, "
     f"{LINK_ALL * 100:.1f}% from Wikipedia links of any origin, and {NAV * 100:.1f}% from links inside the "
     "World Cup graph.")
figure(FIG / "03_overrated_underrated_crop.png",
       "Largest gaps between click percentile and PageRank percentile.")

subheading("Robustness check")
_cite = sum(t in ROB["removed_pages"] for t in ROB["pagerank_top10"]["with_citation_pages"])
para(f"Before cleanup, {_cite} of PageRank's top 10 were citation and identifier pages. Removing the "
     f"{ROB['nodes_removed']} such pages and their {n(ROB['edges_removed'])} links changed PageRank's ρ only from "
     f"{f3(RPR['with_citation_pages'])} to {f3(RPR['without_citation_pages'])}, so the weak fit is not caused by "
     "reference-section boilerplate.")

subheading("System behaviour")
t_sum = _tab[0] + 1
para(f"PageRank (β = 0.85) converged in {ITER} iterations, each producing {n(PAIRS)} intermediate key-value "
     f"pairs and taking {SEC_IT:.2f} s on average. The two clickstream jobs took {CT['seconds']} s and "
     f"{CV['seconds']} s, and the analysis stage (four β values, the weighted run and all metrics) took "
     f"{M['analysis_seconds']} s on a laptop. These are timings from one development machine, not load tests. "
     f"Table {ROMAN[t_sum - 1]} collects the reported outputs.")
table("Summary of reported outputs", [
    ("Item", "Output"),
    ("Subgraph", f"{n(G['nodes'])} articles, {n(G['edges'])} links; hop 1: {n(G['hop1'])}, "
                 f"hop 2: {n(G['hop2'])}"),
    ("Clickstream rows", f"{mshort(TRAIN)}: {n(CT['rows_scanned'])}; {mshort(TEST)}: {n(CV['rows_scanned'])}"),
    ("Rows kept by mapper", f"{n(CT['rows_kept'])}; {n(CV['rows_kept'])}"),
    ("PageRank (nav.)", f"ρ = {f3(PR['spearman_navigation'])}; top-10 {PR['top10_navigation']}/10; "
                        f"NDCG@10 = {f3(PR['ndcg10_navigation'])}"),
    ("Click-weighted PR", f"ρ = {f3(WPR['spearman_navigation'])}; Δρ = {D_RHO:+.3f}"),
    ("Last month's clicks", f"ρ = {f3(LAST['spearman_navigation'])} (best)"),
    ("β sweep (ρ nav.)", "; ".join(f"{b}: {v:.3f}" for b, v in BS.items())),
    ("Robustness", f"ρ {f3(RPR['with_citation_pages'])} → {f3(RPR['without_citation_pages'])} "
                   f"({ROB['nodes_removed']} pages removed)"),
    (f"{mshort(TEST)} arrivals", f"search {SEARCH * 100:.1f}%; links {LINK_ALL * 100:.1f}%; "
                                  f"in-graph {NAV * 100:.1f}%"),
    ("Convergence", f"{ITER} iterations; {n(PAIRS)} pairs per iteration"),
    ("Run times", f"crawl {G['minutes']} min; clickstream {CT['seconds']} s + {CV['seconds']} s; "
                  f"analysis {M['analysis_seconds']} s"),
], widths=[1.15, 2.35], size=8.5)

# ================================================================== VII. LIMITATIONS AND FUTURE WORK
heading("Limitations and Future Work")
numbered([
    "The MapReduce jobs run in a single Python process that imitates map, shuffle and reduce. Nothing has been "
    "run on Hadoop or Spark, so we report no cluster timings or scaling results.",
    "PageRank is computed inside the subgraph. Rank that would flow to pages outside the set is cut, and link "
    "targets that are redirects to outside pages are dropped.",
    "The clickstream hides pairs with 10 or fewer transitions, so weak links look like zero. The +1 smoothing "
    "keeps them in the graph but does not recover their counts.",
    "The study covers one tournament and two months. Pages tied at the hop-2 cut-off are chosen arbitrarily, "
    "so a fresh crawl gives a slightly different graph.",
    "There is no automated test suite or CI. Correctness rests on toy_check.py (lab manual and NetworkX).",
])
para("Future work includes using the share of search arrivals as a personalised teleport vector, so the model "
     "can represent readers who do not arrive by links; running the same mappers and reducers on Hadoop or "
     "Spark over the full English Wikipedia; sorting hop-2 ties so the crawl is deterministic; and repeating the "
     "test on other events and more months.")

# ================================================================== VIII. CONCLUSION
heading("Conclusion")
para(f"On {n(G['nodes'])} World Cup articles and {ROWS / 1e6:.1f} million clickstream rows, structural PageRank "
     f"predicted {mname(TEST)} navigation poorly (ρ = {f3(PR['spearman_navigation'])}, "
     f"{PR['top10_navigation']}/10 top-10 overlap). It ranks the pages that are referenced most, not the pages "
     f"people read. Weighting links with the previous month's clicks raised ρ to "
     f"{f3(WPR['spearman_navigation'])}, and the previous month's clicks alone did best "
     f"(ρ = {f3(LAST['spearman_navigation'])}). The contribution at this stage is a reproducible MapReduce "
     "pipeline and an honest out-of-sample comparison; the most important next step is running it on a real "
     "cluster at full-Wikipedia scale.")

# ================================================================== REFERENCES
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, before=10, after=6, keep=True)
add(p, "REFERENCES", size=10, smallcaps=True)
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
    p = para(indent=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=2)
    pf = p.paragraph_format
    pf.left_indent = Inches(0.3)
    pf.first_line_indent = Inches(-0.3)
    pf.tab_stops.add_tab_stop(Inches(0.3))
    add(p, f"[{i}]\t{r}", size=8)

doc.save(OUT)
print("saved", OUT)

try:
    from docx2pdf import convert
    convert(str(OUT), str(OUT.with_suffix(".pdf")))
    print("saved", OUT.with_suffix(".pdf"))
except Exception as e:                       # Word not installed, etc.
    print("PDF skipped:", e)
