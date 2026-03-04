"""Sync Strava activities to the Notion Activities database."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from notion_client import Client as NotionClient
from stravalib.client import Client as StravaClient

from health_to_notion.config import Settings
from health_to_notion.formatters import (
    format_duration,
    format_pace,
    format_sport_type,
    get_intensity_from_suffer_score,
    parse_strava_datetime,
)
from health_to_notion.mappings import ACTIVITY_EMOJIS, DEFAULT_EMOJI

logger = logging.getLogger(__name__)

STRAVA_ACTIVITY_URL = "https://www.strava.com/activities/"


def _build_properties(activity: object, settings: Settings) -> dict:
    """Build the Notion properties payload from a Strava activity.

    stravalib returns model objects with typed attributes. Distance is in
    meters (float), moving_time in seconds (int), average_speed in m/s (float).
    """
    name = activity.name or "Unnamed Activity"
    sport_type = activity.sport_type.root if activity.sport_type else "Workout"
    main_type, subtype = format_sport_type(sport_type, name)

    # Parse local datetime
    local_dt = parse_strava_datetime(
        str(activity.start_date_local), settings.timezone
    )

    # Heatmap properties
    day_of_week = local_dt.strftime("%A")
    hour = local_dt.hour
    block_start = (hour // 2) * 2
    hour_block = f"{block_start:02d}:00-{block_start + 2:02d}:00"

    # Extract numeric values from stravalib model objects.
    # Some fields (calories, suffer_score, kilojoules) are only on DetailedActivity,
    # so use getattr with defaults for SummaryActivity compatibility.
    distance_m = float(activity.distance) if activity.distance else 0
    moving_time_s = int(float(activity.moving_time)) if activity.moving_time else 0
    avg_speed = float(activity.average_speed) if activity.average_speed else 0
    avg_hr = round(activity.average_heartrate) if activity.average_heartrate else 0
    max_hr = round(activity.max_heartrate) if activity.max_heartrate else 0
    avg_watts = round(activity.average_watts, 1) if activity.average_watts else 0
    calories_raw = getattr(activity, "calories", None)
    calories = round(calories_raw) if calories_raw else 0
    suffer_score = getattr(activity, "suffer_score", None) or 0

    props: dict = {
        "Date": {"date": {"start": local_dt.isoformat()}},
        "Type": {"select": {"name": main_type}},
        "SubType": {"select": {"name": subtype}},
        "Name": {"title": [{"text": {"content": name}}]},
        "Distance (km)": {"number": round(distance_m / 1000, 2)},
        "Duration": {
            "rich_text": [
                {"text": {"content": format_duration(moving_time_s)}}
            ]
        },
        "Calories": {"number": calories},
        "Avg Pace": {
            "rich_text": [
                {"text": {"content": format_pace(avg_speed)}}
            ]
        },
        "Avg HR": {"number": avg_hr},
        "Max HR": {"number": max_hr},
        "Avg Power": {"number": avg_watts},
        "Strava ID": {"number": activity.id},
        "Day of Week": {"select": {"name": day_of_week}},
        "Hour Block": {"select": {"name": hour_block}},
        "Suffer Score": {"number": suffer_score},
        "Intensity": {"select": {"name": get_intensity_from_suffer_score(suffer_score)}},
    }

    return props


def _get_icon_emoji(sport_type: str, activity_name: str = "") -> str:
    """Get the emoji icon for an activity based on its sport type."""
    if activity_name:
        name_lower = activity_name.lower()
        if any(k.lower() in name_lower for k in ("bjj", "jiu jitsu", "mma")):
            return "\U0001f94b"
        if any(k.lower() in name_lower for k in ("boxing", "kickboxing")):
            return "\U0001f94a"
    return ACTIVITY_EMOJIS.get(sport_type, DEFAULT_EMOJI)


def _activity_exists(
    notion: NotionClient,
    database_id: str,
    strava_id: int,
) -> dict | None:
    """Check if an activity already exists in the Notion database by Strava ID."""
    query = notion.databases.query(
        database_id=database_id,
        filter={"property": "Strava ID", "number": {"equals": strava_id}},
    )
    return query["results"][0] if query["results"] else None


def _prefetch_existing_ids(
    notion: NotionClient,
    database_id: str,
) -> dict[int, str]:
    """Bulk-fetch all existing Strava IDs from Notion. Returns {strava_id: page_id}."""
    from health_to_notion.notion_helpers import fetch_all_pages, get_prop

    pages = fetch_all_pages(notion, database_id)
    result: dict[int, str] = {}
    for page in pages:
        sid = get_prop(page["properties"], "Strava ID", "number")
        if sid:
            result[int(sid)] = page["id"]
    return result


def sync_activities(
    strava: StravaClient,
    notion: NotionClient,
    settings: Settings,
) -> None:
    """Sync Strava activities to the Notion Activities database."""
    if not settings.activities_db_id:
        logger.info("No activities database configured, skipping")
        return

    # Pre-fetch existing Strava IDs in one bulk query (avoids N+1)
    logger.info("Pre-fetching existing activities from Notion...")
    existing_map = _prefetch_existing_ids(notion, settings.activities_db_id)
    logger.info("Found %d existing activities in Notion", len(existing_map))

    after_date = datetime.now(settings.timezone) - timedelta(days=settings.days_back)
    activities = list(strava.get_activities(
        after=after_date,
        limit=settings.fetch_limit,
    ))
    logger.info("Fetched %d activities from Strava", len(activities))

    created, updated, skipped = 0, 0, 0

    for activity in activities:
        strava_id = activity.id
        sport_type = activity.sport_type.root if activity.sport_type else "Workout"

        existing_page_id = existing_map.get(strava_id)

        props = _build_properties(activity, settings)
        emoji = _get_icon_emoji(sport_type, activity.name or "")

        if existing_page_id:
            notion.pages.update(
                page_id=existing_page_id,
                properties=props,
                icon={"emoji": emoji},
            )
            updated += 1
            if updated % 100 == 0:
                logger.info("Progress: %d updated so far...", updated)
        else:
            notion.pages.create(
                parent={"database_id": settings.activities_db_id},
                properties=props,
                icon={"emoji": emoji},
            )
            created += 1
            if created % 50 == 0:
                logger.info("Progress: %d created so far...", created)

    logger.info(
        "Activities sync complete: %d created, %d updated, %d unchanged",
        created,
        updated,
        skipped,
    )
