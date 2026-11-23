"""
One command for the whole pipeline:   python run_all.py

  1. builds the World Cup subgraph from the Wikipedia API      (~10 min, cached)
  2. downloads June + July 2026 clickstream (in parallel with 1) (~1 GB)
  3. MapReduce-aggregates the clickstream                        (~2-4 min)
  4. runs PageRank variants + evaluation                         (~1-2 min)
Then:  streamlit run app.py

If July 2026 is not published yet, it automatically falls back to May -> June.

  python run_all.py --mock   builds a fake dataset in the real formats (for testing only)
"""
import argparse
import threading

import config
import step1_subgraph
import step2_clickstream
import step3_analysis


def previous_month(m):
    y, mo = map(int, m.split("-"))
    y, mo = (y - 1, 12) if mo == 1 else (y, mo - 1)
    return f"{y}-{mo:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()

    train, test = config.TRAIN_MONTH, config.TEST_MONTH

    if args.mock:
        import mock_data
        mock_data.main(train, test)
    else:
        marker = config.RAW_DIR / "MOCK_FILES_HERE"
        if marker.exists():                       # never mistake fake files for real downloads
            for f in config.RAW_DIR.glob("clickstream-enwiki-*.tsv.gz"):
                f.unlink()
            marker.unlink()
            print("Removed mock clickstream files.")
        errors = {}
        months = [train, test]

        def download_all():
            for m in months:
                try:
                    step2_clickstream.download(m)
                except step2_clickstream.MonthNotAvailable as e:
                    errors[m] = e
                except Exception as e:            # network trouble: report, keep going
                    errors[m] = e

        dl = threading.Thread(target=download_all)
        dl.start()
        step1_subgraph.main()
        dl.join()

        if test in errors and isinstance(errors[test], step2_clickstream.MonthNotAvailable):
            print(f"\n{test} not published - falling back to {previous_month(train)} -> {train}")
            train, test = previous_month(train), train
            step2_clickstream.download(train)
        elif errors:
            raise SystemExit(f"Download failed: {errors} - just re-run, finished parts are kept.")

    step2_clickstream.main([train, test], skip_download=True)
    step3_analysis.main(train, test)
    print("\nAll done. Start the dashboard with:  streamlit run app.py")


if __name__ == "__main__":
    main()
