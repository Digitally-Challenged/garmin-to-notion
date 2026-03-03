"""Formatting functions for Strava data -> Notion display values."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from health_to_notion.mappings import (
    MODALITY_MAP,
    NAME_OVERRIDE_MAP,
    SUFFER_SCORE_MAX_INTENSITY,
    SUFFER_SCORE_THRESHOLDS,
    TYPE_MAP,
)


def format_sport_type(sport_type: str, activity_name: str = "") -> tuple[str, str]:
    """Map a Strava sport_type to (main_type, subtype) for Notion.

    Returns (Type, SubType). For Strava, SubType equals the readable sport_type
    and Type is the broad category.
    """
    # Activity name overrides for combat sports etc.
    if activity_name:
        name_lower = activity_name.lower()
        for keyword, override_type in NAME_OVERRIDE_MAP.items():
            if keyword.lower() in name_lower:
                return override_type, override_type

    main_type = TYPE_MAP.get(sport_type, "Other")
    # SubType: human-readable version of sport_type
    subtype = _humanize_sport_type(sport_type)
    return main_type, subtype


def _humanize_sport_type(sport_type: str) -> str:
    """Convert PascalCase sport_type to readable form.

    Examples: 'MountainBikeRide' -> 'Mountain Bike Ride'
              'HighIntensityIntervalTraining' -> 'HIIT'
    """
    overrides = {
        "HighIntensityIntervalTraining": "HIIT",
        "StandUpPaddling": "Stand Up Paddling",
        "EBikeRide": "E-Bike Ride",
        "EMountainBikeRide": "E-Mountain Bike Ride",
        "VirtualRide": "Virtual Ride",
        "VirtualRun": "Virtual Run",
        "VirtualRow": "Virtual Row",
        "TrailRun": "Trail Run",
        "MountainBikeRide": "Mountain Bike Ride",
        "GravelRide": "Gravel Ride",
        "AlpineSki": "Alpine Ski",
        "BackcountrySki": "Backcountry Ski",
        "NordicSki": "Nordic Ski",
        "IceSkate": "Ice Skate",
        "RockClimbing": "Rock Climbing",
        "InlineSkate": "Inline Skate",
        "RollerSki": "Roller Ski",
        "TableTennis": "Table Tennis",
        "WeightTraining": "Weight Training",
        "StairStepper": "Stair Stepper",
    }
    if sport_type in overrides:
        return overrides[sport_type]
    # Default: insert spaces before capital letters
    result = ""
    for i, char in enumerate(sport_type):
        if char.isupper() and i > 0:
            result += " "
        result += char
    return result


def format_pace(average_speed: float) -> str:
    """Convert m/s average speed to 'M:SS min/km' pace string."""
    if average_speed <= 0:
        return ""
    pace_min_km = 1000 / (average_speed * 60)
    minutes = int(pace_min_km)
    seconds = int((pace_min_km - minutes) * 60)
    return f"{minutes}:{seconds:02d} min/km"


def format_duration(seconds: int | float | None) -> str:
    """Convert seconds to a clean duration string.

    Examples: 2700 -> "45m", 5400 -> "1h 30m", 0 -> "0m"
    """
    total_minutes = int((seconds or 0)) // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_intensity_from_suffer_score(suffer_score: int | None) -> str:
    """Map Strava suffer_score (Relative Effort) to intensity level."""
    if not suffer_score:
        return "Moderate"
    for threshold, intensity in SUFFER_SCORE_THRESHOLDS:
        if suffer_score <= threshold:
            return intensity
    return SUFFER_SCORE_MAX_INTENSITY


def parse_strava_datetime(dt_str: str, tz: ZoneInfo) -> datetime:
    """Parse a Strava datetime string to a timezone-aware datetime.

    Strava returns start_date_local as ISO 8601 without timezone info.
    We attach the configured timezone.
    """
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)
