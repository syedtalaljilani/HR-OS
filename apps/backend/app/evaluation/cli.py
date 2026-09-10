"""CLI entry for the evaluation harness.

Example::

    python -m app.evaluation.cli --features ocr,screening
    python -m app.evaluation.cli --dry-run --limit 200
"""
import argparse
import sys

from app.evaluation import FEATURES, evaluate


def _render(result: dict) -> None:
    print(f"\n[{result['name']}] {result['id']}")
    if result.get("reports"):
        for r in result["reports"]:
            print(f"  ! {r}")
    for entry in result["scores"]:
        if entry.get("skipped"):
            status = "skipped"
        else:
            status = "ingested" if entry["name"] in result["ingested"] else "not-ingested"
        print(f"  {entry['name']:<26} {entry['value'] if entry['value'] is not None else 'n/a':>6}  {status}")
        if entry.get("comment"):
            print(f"      {entry['comment']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.evaluation.cli")
    parser.add_argument(
        "--features",
        default=",".join(FEATURES),
        help="comma-separated features to evaluate (default: all)",
    )
    parser.add_argument("--limit", type=int, default=50, help="recent traces to scan")
    parser.add_argument(
        "--dry-run", action="store_true", help="compute scores but do not ingest"
    )
    args = parser.parse_args()

    requested = [f.strip() for f in args.features.split(",") if f.strip()]
    unknown = [f for f in requested if f not in FEATURES]
    if unknown:
        parser.error(f"unknown features: {', '.join(unknown)} (choices: {', '.join(FEATURES)})")

    results = evaluate(features=requested, limit=args.limit, ingest=not args.dry_run)
    if not results:
        print("No matching traces found in Langfuse.")
        return

    for result in results:
        _render(result)

    print(f"\nEvaluated {len(results)} traces across: {', '.join(requested)}")
    print("(dry-run: scores computed but not written)" if args.dry_run else "(scores ingested to Langfuse)")


if __name__ == "__main__":
    sys.exit(main())