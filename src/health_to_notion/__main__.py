"""CLI entry point for health-to-notion.

Usage:
    python -m health_to_notion              # Run all syncs
    python -m health_to_notion activities   # Sync only activities
    python -m health_to_notion records      # Sync only personal records (stub)
    python -m health_to_notion steps        # Sync only daily steps (stub)
    python -m health_to_notion sleep        # Sync only sleep data (stub)
    python -m health_to_notion workouts     # Sync only workouts
    python -m health_to_notion summary      # Sync only summary aggregations
    python -m health_to_notion cleanup      # Deduplicate workouts (dry run)
    python -m health_to_notion cleanup --execute  # Actually remove duplicates
    python -m health_to_notion auth         # Run Strava OAuth setup
"""

from __future__ import annotations

import argparse
import logging
import sys

from health_to_notion.config import load_settings
from health_to_notion.log import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync fitness data to Notion databases",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=[
            "all", "activities", "records", "steps", "sleep",
            "workouts", "body", "summary", "cleanup", "auth",
        ],
        help="Which sync to run (default: all)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="For cleanup: actually archive duplicates (default is dry run)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(__name__)

    # Auth command doesn't need full settings
    if args.command == "auth":
        import os
        from health_to_notion.tools.auth import run_auth

        client_id = os.getenv("STRAVA_CLIENT_ID")
        client_secret = os.getenv("STRAVA_CLIENT_SECRET")
        if not client_id or not client_secret:
            print("Error: Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env first.")
            sys.exit(1)
        run_auth(int(client_id), client_secret)
        return

    # Cleanup, summary, and stubs only need Notion
    require_strava = args.command in ("all", "activities")
    settings = load_settings(require_strava=require_strava)

    # Auto-discover database IDs from Notion if any are missing
    if not settings.has_all_db_ids:
        from notion_client import Client as NotionClient
        from health_to_notion.notion_helpers import discover_databases

        logger.info("Some database IDs missing, running auto-discovery...")
        notion = NotionClient(auth=settings.notion_token)
        discovered = discover_databases(notion)
        settings = settings.with_discovered_ids(discovered)
        if discovered:
            logger.info("Auto-discovered %d database(s)", len(discovered))

    if args.command == "cleanup":
        from health_to_notion.clients import init_notion_only
        from health_to_notion.tools.cleanup_duplicates import cleanup_duplicates

        notion = init_notion_only(settings)
        cleanup_duplicates(notion, settings, dry_run=not args.execute)
        return

    if args.command == "summary":
        from health_to_notion.clients import init_notion_only
        from health_to_notion.syncers.summary import sync_summary

        notion = init_notion_only(settings)
        sync_summary(notion, settings)
        return

    if args.command == "body":
        from health_to_notion.clients import init_notion_only
        from health_to_notion.syncers.body_composition import sync_body_composition

        notion = init_notion_only(settings)
        sync_body_composition(notion, settings)
        return

    # Stub commands
    if args.command in ("records", "steps", "sleep"):
        from health_to_notion.syncers.personal_records import sync_personal_records
        from health_to_notion.syncers.daily_steps import sync_daily_steps
        from health_to_notion.syncers.sleep import sync_sleep

        stub_map = {
            "records": sync_personal_records,
            "steps": sync_daily_steps,
            "sleep": sync_sleep,
        }
        stub_map[args.command]()
        return

    from health_to_notion.clients import init_clients
    from health_to_notion.syncers.activities import sync_activities
    from health_to_notion.syncers.body_composition import sync_body_composition
    from health_to_notion.syncers.summary import sync_summary
    from health_to_notion.syncers.workouts import sync_workouts

    clients = init_clients(settings)

    sync_map = {
        "activities": lambda: sync_activities(clients.strava, clients.notion, settings),
        "workouts": lambda: sync_workouts(clients.notion, settings),
        "body": lambda: sync_body_composition(clients.notion, settings),
        "summary": lambda: sync_summary(clients.notion, settings),
    }

    db_check = {
        "activities": settings.activities_db_id,
        "workouts": settings.workouts_db_id,
        "body": settings.body_db_id,
        "summary": settings.summary_db_id,
    }

    commands = list(sync_map.keys()) if args.command == "all" else [args.command]

    for cmd in commands:
        if not db_check.get(cmd):
            logger.info("Skipping %s (no database ID configured)", cmd)
            continue
        try:
            logger.info("Starting %s sync...", cmd)
            sync_map[cmd]()
        except Exception as e:
            logger.error("Error during %s sync: %s", cmd, e, exc_info=args.verbose)
            if args.command != "all":
                sys.exit(1)


if __name__ == "__main__":
    main()
