import argparse
from src.pipeline import run_pipeline
from src.report import generate_report, generate_html_report, _latest_snapshot


def main():
    parser = argparse.ArgumentParser(
        description="Crypto ETL Pipeline — fetches, transforms and stores crypto market data"
    )
    parser.add_argument("--run", action="store_true", help="Run the ETL pipeline")
    parser.add_argument("--report", action="store_true", help="Generate text report + PNG chart")
    parser.add_argument("--html", action="store_true", help="Generate HTML dashboard")
    parser.add_argument("--all", action="store_true", help="Run pipeline then generate all reports")
    args = parser.parse_args()

    if args.run or args.all:
        run_pipeline()
    if args.report or args.all:
        generate_report()
    if args.html or args.all:
        df = _latest_snapshot()
        if df.empty:
            print("No data found. Run the pipeline first: python main.py --run")
        else:
            generate_html_report(df)
    if not any([args.run, args.report, args.html, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
