"""Transform the Activities database into the Workouts database.

Reads from the Activities database and creates/updates entries in the
Workouts database with modality classification and intensity mapping.

Runs AFTER the activities sync.
"""

from __future__ import annotations

import logging

from notion_client import Client as NotionClient

from health_to_notion.config import Settings
from health_to_notion.mappings import INTENSITY_FLOOR, MODALITY_MAP, NAME_OVERRIDE_MAP, SKIP_TYPES
from health_to_notion.notion_helpers import fetch_all_pages, get_prop

logger = logging.getLogger(__name__)

STRAVA_ACTIVITY_URL = "https://www.strava.com/activities/"


def _get_modality(
    activity_type: str,
    subactivity_type: str,
    activity_name: str = "",
) -> str:
    """Determine workout modality from activity type/name."""
    if activity_name:
        name_lower = activity_name.lower()
        for keyword, override in NAME_OVERRIDE_MAP.items():
            if keyword.lower() in name_lower:
                return override
    if subactivity_type and subactivity_type in MODALITY_MAP:
        return MODALITY_MAP[subactivity_type]
    if activity_type and activity_type in MODALITY_MAP:
        return MODALITY_MAP[activity_type]
    return "Other"


def _get_intensity(intensity_str: str | None, modality: str) -> str:
    """Get intensity from Activities DB, apply floor if needed."""
    intensity = intensity_str or "Moderate"
    floor = INTENSITY_FLOOR.get(modality)
    if not floor:
        return intensity
    rank = {"Easy": 0, "Moderate": 1, "Hard": 2, "Maximum": 3}
    if rank.get(intensity, 1) < rank.get(floor, 1):
        return floor
    return intensity


def _workout_exists(
    notion: NotionClient,
    db_id: str,
    strava_id: int | None,
    date_str: str | None,
    modality: str,
) -> dict | None:
    """Check if a workout already exists by Strava ID or date+modality."""
    if strava_id:
        query = notion.databases.query(
            database_id=db_id,
            filter={"property": "Strava ID", "number": {"equals": strava_id}},
        )
        if query["results"]:
            return query["results"][0]

    if date_str:
        date_only = date_str[:10]
        query2 = notion.databases.query(
            database_id=db_id,
            filter={
                "and": [
                    {"property": "Date", "date": {"equals": date_only}},
                    {"property": "Modality", "select": {"equals": modality}},
                ]
            },
        )
        if query2["results"]:
            return query2["results"][0]

    return None


def _build_properties(activity_page: dict) -> tuple[dict, str, str, str | None, int | None]:
    """Build Workouts properties from an Activities page.

    Returns (properties_dict, title, modality, date_start, strava_id).
    """
    props = activity_page["properties"]

    activity_type = get_prop(props, "Type", "select") or ""
    subactivity_type = get_prop(props, "SubType", "select") or ""
    activity_name = get_prop(props, "Name", "title") or ""
    date_start = get_prop(props, "Date", "date")
    duration = get_prop(props, "Duration", "rich_text") or ""
    calories = get_prop(props, "Calories", "number")
    distance = get_prop(props, "Distance (km)", "number")
    avg_pace = get_prop(props, "Avg Pace", "rich_text") or ""
    avg_hr = get_prop(props, "Avg HR", "number")
    intensity_str = get_prop(props, "Intensity", "select")
    strava_id = get_prop(props, "Strava ID", "number")

    modality = _get_modality(activity_type, subactivity_type, activity_name)
    intensity = _get_intensity(intensity_str, modality)
    title = modality

    workout_props: dict = {
        "Workout": {"title": [{"text": {"content": title}}]},
        "Modality": {"select": {"name": modality}},
        "Intensity": {"select": {"name": intensity}},
    }

    if date_start:
        workout_props["Date"] = {"date": {"start": date_start}}
    if duration and duration.strip():
        workout_props["Duration"] = {
            "rich_text": [{"text": {"content": duration}}]
        }
    if distance and distance > 0:
        workout_props["Distance (km)"] = {"number": round(distance, 2)}
    if calories and calories > 0:
        workout_props["Calories"] = {"number": round(calories)}
    if avg_pace and avg_pace.strip():
        workout_props["Avg Pace"] = {
            "rich_text": [{"text": {"content": avg_pace}}]
        }
    if avg_hr and avg_hr > 0:
        workout_props["Avg HR"] = {"number": round(avg_hr)}

    return workout_props, title, modality, date_start, strava_id


def _prefetch_workout_ids(
    notion: NotionClient,
    database_id: str,
) -> dict[int, str]:
    """Bulk-fetch all existing Strava IDs from Workouts DB. Returns {strava_id: page_id}."""
    pages = fetch_all_pages(notion, database_id)
    result: dict[int, str] = {}
    for page in pages:
        sid = get_prop(page["properties"], "Strava ID", "number")
        if sid:
            result[int(sid)] = page["id"]
    return result


def sync_workouts(notion: NotionClient, settings: Settings) -> None:
    """Sync Activities database entries to the Workouts database."""
    if not settings.workouts_db_id:
        logger.info("No workouts database configured, skipping")
        return

    # Pre-fetch existing workout Strava IDs (avoids N+1)
    logger.info("Pre-fetching existing workouts from Notion...")
    existing_ids = _prefetch_workout_ids(notion, settings.workouts_db_id)
    logger.info("Found %d existing workouts in Notion", len(existing_ids))

    logger.info("Fetching activities from Activities database...")
    activities = fetch_all_pages(notion, settings.activities_db_id)
    logger.info("Found %d activities", len(activities))

    created, updated, skipped = 0, 0, 0

    for activity in activities:
        props = activity["properties"]
        activity_type = get_prop(props, "Type", "select") or ""
        subactivity_type = get_prop(props, "SubType", "select") or ""

        if activity_type in SKIP_TYPES or subactivity_type in SKIP_TYPES:
            skipped += 1
            continue

        workout_props, title, modality, date_start, strava_id = _build_properties(activity)
        existing_page_id = existing_ids.get(strava_id) if strava_id else None

        if existing_page_id:
            notion.pages.update(page_id=existing_page_id, properties=workout_props)
            updated += 1
            if updated % 100 == 0:
                logger.info("Progress: %d workouts updated so far...", updated)
        else:
            if strava_id:
                workout_props["Source"] = {
                    "url": f"{STRAVA_ACTIVITY_URL}{strava_id}"
                }
                workout_props["Strava ID"] = {"number": strava_id}
            notion.pages.create(
                parent={"database_id": settings.workouts_db_id},
                properties=workout_props,
            )
            created += 1
            if created % 50 == 0:
                logger.info("Progress: %d workouts created so far...", created)

    logger.info(
        "Workouts sync complete: %d created, %d updated, %d skipped",
        created, updated, skipped,
    )
