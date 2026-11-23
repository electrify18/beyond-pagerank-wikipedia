"""Cross-checks every number in the deck (incl. speaker notes) and the paper against the result files.
Prints numbers that are NOT derivable from results/ or data/*meta*.json so they can be reviewed by hand.
Run from the project root:  python submission/check_numbers.py
"""
import json
import re
from pathlib import Path

import pandas as pd
from docx import Document
from pptx import Presentation

ROOT = Path(__file__).resolve().parent.parent
M = json.loads((ROOT / "results/metrics.json").read_text())
CONV = json.loads((ROOT / "results/convergence.json").read_text())
DF = pd.read_csv(ROOT / "results/rankings.csv", index_col="title")


def walk(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield o


ROB = json.loads((ROOT / "results/robustness.json").read_text())
src = list(walk(M)) + list(walk(ROB)) +[len(CONV), CONV[0]["intermediate_pairs"], sum(c["seconds"] for c in CONV) / len(CONV)]
cs = M["clickstream"]
src += [sum(v["rows_scanned"] for v in cs.values()) / 1e6]
tot = DF["test_total"].sum()
src += [DF[c].sum() / tot * 100 for c in ("test_search", "test_link_in_all", "test_link_in_sub")]
pr, wpr = M["models"]["PageRank"], M["models"]["Click-weighted PageRank"]
src += [wpr["spearman_navigation"] - pr["spearman_navigation"], wpr["ndcg10_navigation"] - pr["ndcg10_navigation"]]

allowed = set()
for x in src:
    for d in range(0, 5):
        allowed.add(f"{round(x, d):.{d}f}")
    if float(x).is_integer():
        allowed.add(str(int(x)))
allowed |= {a.lstrip("0") for a in allowed if a.startswith("0.")}

NUM = re.compile(r"(?<![\w.])[+−-]?\d[\d,]*(?:\.\d+)?")


def numbers(text):
    for m in NUM.finditer(text):
        yield m.group().replace(",", "").lstrip("+−-")


def report(name, texts):
    unknown = {}
    for where, t in texts:
        for n in numbers(t):
            if n not in allowed:
                unknown.setdefault(n, where)
    print(f"\n{name}: numbers not taken from the result files (review by hand)")
    for n, where in sorted(unknown.items(), key=lambda kv: float(kv[0])):
        print(f"  {n:>12}   e.g. {where}")


prs = Presentation(ROOT / "submission/BDA_MiniProject_Kshant_10232.pptx")
texts = []
for i, s in enumerate(prs.slides, 1):
    for sh in s.shapes:
        if sh.has_text_frame:
            texts.append((f"slide {i}", sh.text_frame.text))
        if sh.has_table:
            texts += [(f"slide {i} table", c.text) for r in sh.table.rows for c in r.cells]
    texts.append((f"slide {i} notes", s.notes_slide.notes_text_frame.text))
report("DECK", texts)

doc = Document(ROOT / "submission/BDA_Paper_Kshant_10232.docx")
texts = [("paper", p.text) for p in doc.paragraphs]
texts += [("paper table", c.text) for t in doc.tables for r in t.rows for c in r.cells]
report("PAPER", texts)
