"""Project settings. Change SEED / months here if needed."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CACHE_DIR = DATA_DIR / "api_cache"
RESULTS_DIR = ROOT / "results"

# ---------------------------------------------------------------- subgraph
SEED = "2026_FIFA_World_Cup"
HOP2_MIN_INLINKS = 8      # a hop-2 page joins only if >= this many hop-1 pages link to it
HOP2_MAX = 1500           # cap on hop-2 pages (full crawl took ~93 min at ~1 API request/s)
# Citation/identifier/authority-control/archive pages: reference-section boilerplate, not football content.
EXCLUDE_TITLES = {
    "Digital_object_identifier", "ISBN", "ISSN", "PubMed", "PubMed_Central", "Semantic_Scholar",
    "Wayback_Machine", "Bibcode", "OCLC", "Handle_System", "JSTOR", "ArXiv", "CiteSeerX", "WorldCat",
    "Internet_Archive", "Archive.today", "Library_of_Congress_Control_Number",
    "Virtual_International_Authority_File", "International_Standard_Name_Identifier",
    "Integrated_Authority_File", "Google_Books", "Open_Library", "Wikidata",
    "Geographic_coordinate_system",
}
EXCLUDE_SUFFIX = "_(identifier)"   # also excluded: any title ending in this

# ---------------------------------------------------------------- clickstream
TRAIN_MONTH = "2026-06"   # group stage   -> builds the click weights
TEST_MONTH = "2026-07"    # knockouts     -> ground truth for evaluation
CLICKSTREAM_URL = ("https://dumps.wikimedia.org/other/clickstream/{m}/"
                   "clickstream-enwiki-{m}.tsv.gz")

# ---------------------------------------------------------------- PageRank
BETAS = [0.50, 0.70, 0.85, 0.95]
MAIN_BETA = 0.85
CLICK_SMOOTHING = 1       # weighted PR edge weight = clicks + 1 (pairs <=10 clicks are hidden)

# Wikimedia's User-Agent policy asks API clients for contact info (email or project URL);
# generic/library User-Agents get rate-limited (HTTP 429). Before a crawl, set your own contact:
#   PowerShell:  $env:WIKI_CONTACT = "you@example.com"
CONTACT = os.environ.get("WIKI_CONTACT", "set WIKI_CONTACT to your email or project URL")
USER_AGENT = f"BDA-WikiPageRank/1.0 ({CONTACT}) college mini-project"

for d in (DATA_DIR, RAW_DIR, CACHE_DIR, RESULTS_DIR):
    d.mkdir(parents=True, exist_ok=True)
