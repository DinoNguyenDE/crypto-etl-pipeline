import argparse
from src.pipeline import run_pipeline
from src.report import generate_report


def main():
    parser = argparse.ArgumentParser(
        description="Crypto ETL Pipeline — fetches, transforms and stores crypto market data"
    )
    parser.add_argument("--run", action="store_true", help="Run the ETL pipeline")
    parser.add_argument("--report", action="store_true", help="Generate report from latest data")
    parser.add_argument("--all", action="store_true", help="Run pipeline then generate report")
    args = parser.parse_args()

    if args.run or args.all:
        run_pipeline()
    if args.report or args.all:
        generate_report()
    if not any([args.run, args.report, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
