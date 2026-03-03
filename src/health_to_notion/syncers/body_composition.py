"""Sync Withings body composition data to the Notion Body Composition database."""

from __future__ import annotations

import logging

from notion_client import Client as NotionClient

from health_to_notion.config import Settings
from health_to_notion.notion_helpers import fetch_all_pages, get_prop
from health_to_notion.withings_client import (
    get_body_measurements,
    refresh_access_token,
)

logger = logging.getLogger(__name__)


def _prefetch_existing_dates(
    notion: NotionClient,
    database_id: str,
) -> set[str]:
    """Bulk-fetch all existing dates from Body Composition DB."""
    pages = fetch_all_pages(notion, database_id)
    result: set[str] = set()
    for page in pages:
        date_str = get_prop(page["properties"], "Date", "date")
        if date_str:
            result.add(date_str[:10])
    return result


def _build_properties(measurement: dict) -> dict:
    """Build Notion properties from a body composition measurement."""
    return {
        "Name": {"title": [{"text": {"content": f"{measurement['weight']} kg"}}]},
        "Date": {"date": {"start": measurement["date"]}},
        "Weight (kg)": {"number": measurement["weight"]},
        "Fat %": {"number": measurement["fat_pct"]},
        "Muscle Mass (kg)": {"number": measurement["muscle_mass"]},
    }


def sync_body_composition(
    notion: NotionClient,
    settings: Settings,
) -> None:
    """Sync Withings body composition data to Notion."""
    if not settings.body_db_id:
        logger.info("No body composition database configured, skipping")
        return

    if not settings.withings_client_id:
        logger.info("No Withings credentials configured, skipping body composition sync")
        return

    # Refresh Withings access token
    logger.info("Authenticating with Withings...")
    token_data = refresh_access_token(
        settings.withings_client_id,
        settings.withings_client_secret,
        settings.withings_refresh_token,
    )
    access_token = token_data["access_token"]
    new_refresh_token = token_data["refresh_token"]
    logger.info("Withings authentication successful")

    if new_refresh_token != settings.withings_refresh_token:
        logger.warning(
            "Withings issued a new refresh token. Update WITHINGS_REFRESH_TOKEN in .env: %s",
            new_refresh_token,
        )

    # Pre-fetch existing dates
    logger.info("Pre-fetching existing body composition entries...")
    existing_dates = _prefetch_existing_dates(notion, settings.body_db_id)
    logger.info("Found %d existing entries in Notion", len(existing_dates))

    # Fetch measurements from Withings
    measurements = get_body_measurements(access_token, days_back=settings.days_back)

    created, skipped = 0, 0

    for m in measurements:
        if m["date"] in existing_dates:
            skipped += 1
            continue

        props = _build_properties(m)
        notion.pages.create(
            parent={"database_id": settings.body_db_id},
            properties=props,
            icon={"emoji": "\u2696\ufe0f"},
        )
        created += 1

    logger.info(
        "Body composition sync complete: %d created, %d skipped (already existed)",
        created, skipped,
    )
