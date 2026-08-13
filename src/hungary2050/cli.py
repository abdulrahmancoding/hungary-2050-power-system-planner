"""Command-line interface for data preparation and model execution."""

from __future__ import annotations

import argparse
from pathlib import Path

from hungary2050.data import prepare_data
from hungary2050.runner import run_all, run_scenario


def _project_root() -> Path:
    return Path.cwd()


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI parser."""

    parser = argparse.ArgumentParser(
        prog="hungary2050",
        description="Run the Hungary 2050 synthetic electricity-system planning study.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-data", help="Generate deterministic hourly profiles")
    prepare.add_argument("--year", type=int, default=2021, help="Non-leap demonstration year")

    run = subparsers.add_parser("run", help="Run one YAML scenario")
    run.add_argument("scenario", type=Path, help="Scenario YAML path")
    run.add_argument("--hours", type=int, default=None, help="Use only the first N hours (testing only)")

    run_all_parser = subparsers.add_parser("run-all", help="Run all configured scenarios and charts")
    run_all_parser.add_argument(
        "--hours", type=int, default=None, help="Use only the first N hours (testing only)"
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Execute a command and print a compact result summary."""

    args = build_parser().parse_args(argv)
    root = _project_root()
    if args.command == "prepare-data":
        output = prepare_data(root / "data" / "processed" / "hourly_profiles.csv", year=args.year)
        print(f"Generated {output}")
    elif args.command == "run":
        result = run_scenario(args.scenario, root, hours=args.hours)
        print(
            f"{result['scenario']}: {result['optimization_status']}/"
            f"{result['termination_condition']}, cost EUR "
            f"{result['total_annualized_system_cost_eur']:,.0f}"
        )
    elif args.command == "run-all":
        results = run_all(root, hours=args.hours)
        for result in results:
            print(
                f"{result['scenario']}: {result['optimization_status']}/"
                f"{result['termination_condition']}, unserved energy "
                f"{result['unserved_energy_mwh']:,.3f} MWh"
            )

