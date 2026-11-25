"""Raíz — the roots see what the surface hides.

Usage:
  python -m raiz query 62701                    # What's affecting this zip code?
  python -m raiz query 62701 --actions          # Include suggested actions
  python -m raiz query 62701 --demo             # Use mock data (no API calls)
"""
from __future__ import annotations

import argparse
import asyncio
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="raiz",
        description="Raíz — environmental justice intelligence",
    )
    subparsers = parser.add_subparsers(dest="command")

    query_parser = subparsers.add_parser(
        "query", help="Query environmental data for a zip code",
    )
    query_parser.add_argument("zip_code", help="US zip code to investigate")
    query_parser.add_argument("--actions", action="store_true",
                              help="Include suggested action items")
    query_parser.add_argument("--demo", action="store_true",
                              help="Use mock data (no API calls)")
    query_parser.add_argument("--airnow-key", default="",
                              help="AirNow API key")
    query_parser.add_argument("--purpleair-key", default="",
                              help="PurpleAir API key")

    args = parser.parse_args()

    if args.command == "query":
        asyncio.run(run_query(args))
    else:
        parser.print_help()
        print("\nQuick start:")
        print("  python -m raiz query 62701 --demo    # See what Raíz finds")


DEMO_BANNER = (
    "*** DEMO: INVENTED DATA ***\n"
    "No source was contacted. The facilities, companies, numbers and demographics below are made up, "
    "come from a few fixed examples (the same facilities and companies whatever zip code you give), "
    "and are not about {zip} or anywhere real.\n")

DEMO_FOOTER = (
    "*** DEMO: INVENTED DATA. The 'Data sources' line above names where real data would come from; "
    "none was used. Nothing here describes {zip}. ***")


async def run_query(args) -> None:
    from raiz.community.query import CommunityQueryEngine

    engine = CommunityQueryEngine(
        airnow_key=args.airnow_key,
        purpleair_key=args.purpleair_key,
        dry_run=args.demo,
    )

    print(f"\nRaíz — investigating zip code {args.zip_code}...")
    if args.demo:
        print(DEMO_BANNER.format(zip=args.zip_code))
    else:
        print("Querying EPA ECHO, TRI, AirNow, PurpleAir...\n")

    report = await engine.query(args.zip_code)
    print(report.summarize())

    if args.actions:
        actions = report.action_items()
        print(f"\nSUGGESTED ACTIONS:")
        for i, action in enumerate(actions, 1):
            print(f"  {i}. {action}")

    if args.demo:
        print("\n" + DEMO_FOOTER.format(zip=args.zip_code))
    print()


if __name__ == "__main__":
    main()
