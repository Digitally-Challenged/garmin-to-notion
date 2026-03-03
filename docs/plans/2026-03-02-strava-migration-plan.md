# Strava Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Garmin with Strava as the fitness data source, rename project to `health-to-notion`.

**Architecture:** Direct swap — replace `garminconnect` with `stravalib`, update config/clients/formatters/mappings/syncers. Stub out sleep/steps/PRs for future Withings/Apple Health integration. No abstraction layers.

**Tech Stack:** Python 3.11+, stravalib 2.x (Strava API wrapper), notion-client 2.2.1, GitHub Actions

**Design doc:** `docs/plans/2026-03-02-strava-migration-design.md`

---

### Task 1: Rename package from garmin_to_notion to health_to_notion

**Files:**
- Rename: `src/garmin_to_notion/` → `src/health_to_notion/` (entire directory)
- Modify: `src/health_to_notion/__init__.py`
- Modify: `src/health_to_notion/log.py:16`
- Modify: `src/health_to_notion/syncers/__init__.py`
- Modify: `pyproject.toml`

**Step 1: Move the package directory**

```bash
mv src/garmin_to_notion src/health_to_notion
```

**Step 2: Update `__init__.py`**

```python
"""Health to Notion - Sync your fitness data to Notion databases."""

__version__ = "4.0.0"
```

**Step 3: Update logger root name in `log.py:16`**

Change:
```python
root = logging.getLogger("garmin_to_notion")
```
To:
```python
root = logging.getLogger("health_to_notion")
```

**Step 4: Update `syncers/__init__.py`**

```python
"""Syncer modules for each fitness data source."""
```

**Step 5: Update `pyproject.toml`**

```toml
[project]
name = "health-to-notion"
version = "4.0.0"
description = "Sync your fitness data to Notion databases"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "stravalib>=2.0,<3.0",
    "notion-client==2.2.1",
    "python-dotenv>=1.0,<2.0",
]
```

**Step 6: Find and replace all `garmin_to_notion` imports across every file**

Search every `.py` file under `src/health_to_notion/` and replace:
- `from garmin_to_notion.` → `from health_to_notion.`
- `import garmin_to_notion` → `import health_to_notion`

Files that need import updates:
- `src/health_to_notion/__main__.py` (lines 21, 58, 69, 76, 83-89)
- `src/health_to_notion/clients.py` (line 11)
- `src/health_to_notion/syncers/activities.py` (lines 12-20)
- `src/health_to_notion/syncers/workouts.py` (lines 16-23)
- `src/health_to_notion/syncers/sleep.py` (lines 13-14)
- `src/health_to_notion/syncers/daily_steps.py` (line 12)
- `src/health_to_notion/syncers/personal_records.py` (lines 11-17)
- `src/health_to_notion/syncers/summary.py` (lines 20-21)
- `src/health_to_notion/tools/cleanup_duplicates.py` (lines 14-15)

**Step 7: Update `requirements.txt`**

```
stravalib>=2.0,<3.0
notion-client==2.2.1
python-dotenv>=1.0,<2.0
tzdata>=2024.1; sys_platform == "win32"
```

**Step 8: Verify the rename didn't break imports**

Run: `cd /Users/COLEMAN/Documents/GitHub/garmin-to-notion && PYTHONPATH=src python -c "import health_to_notion; print(health_to_notion.__version__)"`
Expected: `4.0.0`

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: rename package from garmin_to_notion to health_to_notion (v4.0.0)"
```

---

### Task 2: Update config.py for Strava OAuth credentials

**Files:**
- Modify: `src/health_to_notion/config.py`
- Modify: `src/health_to_notion/.env.example` (project root `.env.example`)

**Step 1: Rewrite `config.py`**

Replace entire contents of `src/health_to_notion/config.py` with:

```python
"""Settings and environment variable validation."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    strava_client_id: int
    strava_client_secret: str
    strava_refresh_token: str
    notion_token: str
    activities_db_id: str | None
    pr_db_id: str | None
    steps_db_id: str | None
    sleep_db_id: str | None
    workouts_db_id: str | None
    summary_db_id: str | None
    timezone: ZoneInfo
    fetch_limit: int
    days_back: int

    @property
    def has_all_db_ids(self) -> bool:
        """Check if all database IDs are configured."""
        return all([
            self.activities_db_id,
            self.workouts_db_id,
            self.summary_db_id,
        ])

    def with_discovered_ids(self, discovered: dict[str, str]) -> Settings:
        """Return a new Settings with missing DB IDs filled from discovered mapping."""
        overrides = {}
        for field in (
            "activities_db_id", "pr_db_id", "steps_db_id",
            "sleep_db_id", "workouts_db_id", "summary_db_id",
        ):
            current = getattr(self, field)
            if not current and field in discovered:
                overrides[field] = discovered[field]
        if not overrides:
            return self
        from dataclasses import replace
        return replace(self, **overrides)


def load_settings(require_strava: bool = True) -> Settings:
    """Load and validate all configuration from environment variables."""
    required = ["NOTION_TOKEN"]
    if require_strava:
        required += ["STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN"]

    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your values.")
        sys.exit(1)

    tz_name = os.getenv("TIMEZONE", "UTC")
    try:
        timezone = ZoneInfo(tz_name)
    except (KeyError, ValueError):
        print(f"Error: Invalid timezone '{tz_name}'. Use IANA format (e.g. America/Chicago).")
        sys.exit(1)

    return Settings(
        strava_client_id=int(os.getenv("STRAVA_CLIENT_ID", "0")),
        strava_client_secret=os.getenv("STRAVA_CLIENT_SECRET", ""),
        strava_refresh_token=os.getenv("STRAVA_REFRESH_TOKEN", ""),
        notion_token=os.environ["NOTION_TOKEN"],
        activities_db_id=os.getenv("NOTION_DB_ID"),
        pr_db_id=os.getenv("NOTION_PR_DB_ID"),
        steps_db_id=os.getenv("NOTION_STEPS_DB_ID"),
        sleep_db_id=os.getenv("NOTION_SLEEP_DB_ID"),
        workouts_db_id=os.getenv("NOTION_WORKOUTS_DB_ID"),
        summary_db_id=os.getenv("NOTION_SUMMARY_DB_ID"),
        timezone=timezone,
        fetch_limit=int(os.getenv("STRAVA_ACTIVITIES_FETCH_LIMIT", "200")),
        days_back=int(os.getenv("STRAVA_DAYS_BACK", "30")),
    )
```

**Step 2: Update `.env.example`**

```
# ============================================
# Health to Notion - Configuration
# ============================================
# Copy this file to .env and fill in your values.
# See README.md for setup instructions.

# --- Required: Strava OAuth ---
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REFRESH_TOKEN=your_refresh_token

# --- Required: Notion ---
NOTION_TOKEN=ntn_your_token_here

# --- Optional: Database IDs (auto-discovered if not set) ---
# NOTION_DB_ID=
# NOTION_PR_DB_ID=
# NOTION_STEPS_DB_ID=
# NOTION_SLEEP_DB_ID=
# NOTION_WORKOUTS_DB_ID=
# NOTION_SUMMARY_DB_ID=

# --- Optional: Settings ---
# TIMEZONE=UTC
# STRAVA_DAYS_BACK=30
# STRAVA_ACTIVITIES_FETCH_LIMIT=200
```

**Step 3: Verify config loads**

Run: `cd /Users/COLEMAN/Documents/GitHub/garmin-to-notion && PYTHONPATH=src python -c "from health_to_notion.config import Settings; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/health_to_notion/config.py .env.example
git commit -m "feat: update config for Strava OAuth credentials"
```

---

### Task 3: Rewrite clients.py for Strava + Notion

**Files:**
- Modify: `src/health_to_notion/clients.py`

**Step 1: Rewrite `clients.py`**

```python
"""Strava and Notion client initialization."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from notion_client import Client as NotionClient
from stravalib.client import Client as StravaClient

from health_to_notion.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class Clients:
    strava: StravaClient
    notion: NotionClient


def init_clients(settings: Settings) -> Clients:
    """Initialize and authenticate both Strava and Notion clients."""
    logger.info("Authenticating with Strava...")
    strava = StravaClient()
    try:
        token_response = strava.refresh_access_token(
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            refresh_token=settings.strava_refresh_token,
        )
        strava.access_token = token_response["access_token"]
    except Exception as e:
        logger.error("Failed to authenticate with Strava: %s", e)
        raise SystemExit(1) from e

    logger.info("Strava authentication successful")
    notion = NotionClient(auth=settings.notion_token)
    return Clients(strava=strava, notion=notion)


def init_notion_only(settings: Settings) -> NotionClient:
    """Initialize only the Notion client (for tools that don't need Strava)."""
    return NotionClient(auth=settings.notion_token)
```

**Step 2: Verify import**

Run: `PYTHONPATH=src python -c "from health_to_notion.clients import Clients; print('OK')"`
Expected: `OK` (requires stravalib installed)

**Step 3: Commit**

```bash
git add src/health_to_notion/clients.py
git commit -m "feat: rewrite clients.py for Strava OAuth"
```

---

### Task 4: Create Strava OAuth auth tool

**Files:**
- Create: `src/health_to_notion/tools/auth.py`
- Modify: `src/health_to_notion/__main__.py` (add `auth` command — done in Task 9)

**Step 1: Create `src/health_to_notion/tools/auth.py`**

```python
"""One-time Strava OAuth authorization helper.

Usage:
    python -m health_to_notion auth

Opens a browser for Strava authorization, captures the auth code via a
local HTTP server, and exchanges it for access + refresh tokens.
"""

from __future__ import annotations

import http.server
import logging
import threading
import urllib.parse
import webbrowser

from stravalib.client import Client as StravaClient

logger = logging.getLogger(__name__)

REDIRECT_PORT = 8000
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"


def _capture_auth_code() -> str:
    """Start a local HTTP server to capture the OAuth callback code."""
    code_holder: dict[str, str] = {}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            if "code" in params:
                code_holder["code"] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<h1>Authorization successful!</h1>"
                    b"<p>You can close this tab and return to the terminal.</p>"
                )
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing authorization code.")

        def log_message(self, format: str, *args: object) -> None:
            pass  # Suppress HTTP server logs

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)
    server.timeout = 120  # 2 minute timeout
    server.handle_request()
    server.server_close()

    if "code" not in code_holder:
        raise RuntimeError("No authorization code received. Did you authorize in the browser?")

    return code_holder["code"]


def run_auth(client_id: int, client_secret: str) -> None:
    """Run the full OAuth flow: open browser, capture code, exchange for tokens."""
    client = StravaClient()

    auth_url = client.authorization_url(
        client_id=client_id,
        redirect_uri=REDIRECT_URI,
        scope=["read", "activity:read_all"],
    )

    print(f"\nOpening Strava authorization page in your browser...")
    print(f"If it doesn't open, visit: {auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for authorization callback...")
    code = _capture_auth_code()

    print("Exchanging code for tokens...")
    token_response = client.exchange_code_for_token(
        client_id=client_id,
        client_secret=client_secret,
        code=code,
    )

    access_token = token_response["access_token"]
    refresh_token = token_response["refresh_token"]

    print("\n" + "=" * 50)
    print("Authorization successful!")
    print("=" * 50)
    print(f"\nSTRAVA_REFRESH_TOKEN={refresh_token}")
    print(f"\nAdd this to your .env file or GitHub Secrets.")
    print(f"Access token (temporary): {access_token[:10]}...")
    print("=" * 50)
```

**Step 2: Commit**

```bash
git add src/health_to_notion/tools/auth.py
git commit -m "feat: add Strava OAuth authorization helper"
```

---

### Task 5: Rewrite mappings.py for Strava sport_type values

**Files:**
- Modify: `src/health_to_notion/mappings.py`

**Step 1: Rewrite `mappings.py`**

Replace entire file. Key change: all keys are now Strava `sport_type` PascalCase values instead of Garmin type names.

```python
"""All mapping constants for Strava sport types, icons, modalities, and intensity."""

# ---------------------------------------------------------------------------
# Activity Emojis: Strava sport_type -> Notion emoji icon
# ---------------------------------------------------------------------------
ACTIVITY_EMOJIS: dict[str, str] = {
    # Running
    "Run": "\U0001f3c3",
    "TrailRun": "\U0001f3d4\ufe0f",
    "VirtualRun": "\U0001f3c3",
    # Cycling
    "Ride": "\U0001f6b4",
    "MountainBikeRide": "\U0001f6b5",
    "GravelRide": "\U0001f6b4",
    "EBikeRide": "\U0001f6b4",
    "EMountainBikeRide": "\U0001f6b5",
    "VirtualRide": "\U0001f6b4",
    "Velomobile": "\U0001f6b4",
    # Swimming
    "Swim": "\U0001f3ca",
    # Walking
    "Walk": "\U0001f6b6",
    "Hike": "\U0001f97e",
    # Strength & Fitness
    "WeightTraining": "\U0001f3cb\ufe0f",
    "Crossfit": "\U0001f525",
    "HighIntensityIntervalTraining": "\U0001f525",
    "Elliptical": "\U0001f3c3",
    "StairStepper": "\U0001f6b6",
    "Workout": "\U0001f4aa",
    # Yoga & Pilates
    "Yoga": "\U0001f9d8",
    "Pilates": "\U0001f9d8",
    # Rowing
    "Rowing": "\U0001f6a3",
    "VirtualRow": "\U0001f6a3",
    # Racquet Sports
    "Tennis": "\U0001f3be",
    "Racquetball": "\U0001f3be",
    "Badminton": "\U0001f3f8",
    "Pickleball": "\U0001f3d3",
    "Squash": "\U0001f3be",
    "TableTennis": "\U0001f3d3",
    # Team Sports
    "Soccer": "\u26bd",
    # Combat (Strava uses "Workout" for MMA/Boxing — handled via name override)
    # Winter Sports
    "AlpineSki": "\u26f7\ufe0f",
    "BackcountrySki": "\u26f7\ufe0f",
    "NordicSki": "\u26f7\ufe0f",
    "Snowboard": "\U0001f3c2",
    "Snowshoe": "\U0001f97e",
    "IceSkate": "\u26f8\ufe0f",
    # Water Sports
    "Kayaking": "\U0001f6f6",
    "Canoeing": "\U0001f6f6",
    "StandUpPaddling": "\U0001f3c4",
    "Surfing": "\U0001f3c4",
    "Kitesurf": "\U0001f3c4",
    "Windsurf": "\U0001f3c4",
    "Sail": "\u26f5",
    # Climbing
    "RockClimbing": "\U0001f9d7",
    # Other
    "Golf": "\u26f3",
    "Skateboard": "\U0001f6f9",
    "InlineSkate": "\u26f8\ufe0f",
    "Handcycle": "\U0001f6b4",
    "Wheelchair": "\U0001f9bd",
    "RollerSki": "\u26f7\ufe0f",
}

DEFAULT_EMOJI = "\U0001f3c5"

# ---------------------------------------------------------------------------
# Strava sport_type -> Notion "Type" (broad category)
# ---------------------------------------------------------------------------
TYPE_MAP: dict[str, str] = {
    "Run": "Running",
    "TrailRun": "Running",
    "VirtualRun": "Running",
    "Ride": "Cycling",
    "MountainBikeRide": "Cycling",
    "GravelRide": "Cycling",
    "EBikeRide": "Cycling",
    "EMountainBikeRide": "Cycling",
    "VirtualRide": "Cycling",
    "Velomobile": "Cycling",
    "Swim": "Swimming",
    "Walk": "Walking",
    "Hike": "Walking",
    "WeightTraining": "Strength",
    "Crossfit": "Crossfit",
    "HighIntensityIntervalTraining": "HIIT",
    "Elliptical": "Cardio",
    "StairStepper": "Cardio",
    "Workout": "Other",
    "Yoga": "Yoga/Pilates",
    "Pilates": "Yoga/Pilates",
    "Rowing": "Rowing",
    "VirtualRow": "Rowing",
    "Tennis": "Racquet Sports",
    "Racquetball": "Racquet Sports",
    "Badminton": "Racquet Sports",
    "Pickleball": "Racquet Sports",
    "Squash": "Racquet Sports",
    "TableTennis": "Racquet Sports",
    "Soccer": "Team Sports",
    "AlpineSki": "Winter Sports",
    "BackcountrySki": "Winter Sports",
    "NordicSki": "Winter Sports",
    "Snowboard": "Winter Sports",
    "Snowshoe": "Winter Sports",
    "IceSkate": "Winter Sports",
    "Kayaking": "Water Sports",
    "Canoeing": "Water Sports",
    "StandUpPaddling": "Water Sports",
    "Surfing": "Water Sports",
    "Kitesurf": "Water Sports",
    "Windsurf": "Water Sports",
    "Sail": "Water Sports",
    "RockClimbing": "Climbing",
    "Golf": "Golf",
    "Skateboard": "Other",
    "InlineSkate": "Other",
    "Handcycle": "Cycling",
    "Wheelchair": "Other",
    "RollerSki": "Winter Sports",
}

# ---------------------------------------------------------------------------
# Strava sport_type -> Workout Modality (more specific grouping)
# ---------------------------------------------------------------------------
MODALITY_MAP: dict[str, str] = {
    "Run": "Running",
    "TrailRun": "Running",
    "VirtualRun": "Running",
    "Ride": "Outdoor Cycling",
    "MountainBikeRide": "Outdoor Cycling",
    "GravelRide": "Outdoor Cycling",
    "EBikeRide": "Outdoor Cycling",
    "EMountainBikeRide": "Outdoor Cycling",
    "VirtualRide": "Indoor Cycling",
    "Velomobile": "Outdoor Cycling",
    "Swim": "Swimming",
    "Walk": "Walking",
    "Hike": "Walking",
    "WeightTraining": "Strength Training",
    "Crossfit": "Crossfit",
    "HighIntensityIntervalTraining": "HIIT",
    "Elliptical": "Cardio",
    "StairStepper": "Cardio",
    "Workout": "Other",
    "Yoga": "Yoga",
    "Pilates": "Pilates",
    "Rowing": "Rowing",
    "VirtualRow": "Rowing",
    "Tennis": "Racquet Sports",
    "Racquetball": "Racquet Sports",
    "Badminton": "Racquet Sports",
    "Pickleball": "Racquet Sports",
    "Squash": "Racquet Sports",
    "TableTennis": "Racquet Sports",
    "Soccer": "Team Sports",
    "AlpineSki": "Winter Sports",
    "BackcountrySki": "Winter Sports",
    "NordicSki": "Winter Sports",
    "Snowboard": "Winter Sports",
    "Snowshoe": "Winter Sports",
    "IceSkate": "Winter Sports",
    "Kayaking": "Water Sports",
    "Canoeing": "Water Sports",
    "StandUpPaddling": "Water Sports",
    "Surfing": "Water Sports",
    "Kitesurf": "Water Sports",
    "Windsurf": "Water Sports",
    "Sail": "Water Sports",
    "RockClimbing": "Climbing",
    "Golf": "Golf",
    "Skateboard": "Other",
    "InlineSkate": "Other",
    "Handcycle": "Outdoor Cycling",
    "Wheelchair": "Other",
    "RollerSki": "Winter Sports",
}

# ---------------------------------------------------------------------------
# Activity name overrides (for combat sports etc. tagged as "Workout" in Strava)
# ---------------------------------------------------------------------------
NAME_OVERRIDE_MAP: dict[str, str] = {
    "BJJ": "BJJ",
    "Jiu Jitsu": "BJJ",
    "Boxing": "Combat Sports",
    "Kickboxing": "Combat Sports",
    "MMA": "Combat Sports",
    "Sauna": "Sauna",
}

# ---------------------------------------------------------------------------
# Suffer Score -> Intensity (Strava Relative Effort)
# ---------------------------------------------------------------------------
SUFFER_SCORE_THRESHOLDS: list[tuple[int, str]] = [
    (50, "Easy"),
    (150, "Moderate"),
    (300, "Hard"),
]
SUFFER_SCORE_MAX_INTENSITY = "Maximum"

# ---------------------------------------------------------------------------
# Modalities where Easy intensity doesn't apply -> minimum
# ---------------------------------------------------------------------------
INTENSITY_FLOOR: dict[str, str] = {
    "HIIT": "Moderate",
    "BJJ": "Moderate",
    "Crossfit": "Moderate",
    "Combat Sports": "Moderate",
}

# ---------------------------------------------------------------------------
# Skip these activity types (not real workouts)
# ---------------------------------------------------------------------------
SKIP_TYPES: set[str] = set()
```

**Step 2: Commit**

```bash
git add src/health_to_notion/mappings.py
git commit -m "feat: rewrite mappings for Strava sport_type values"
```

---

### Task 6: Rewrite formatters.py for Strava data

**Files:**
- Modify: `src/health_to_notion/formatters.py`

**Step 1: Rewrite `formatters.py`**

Remove all Garmin-specific formatters (training effect, Garmin record values). Keep pace/duration/date formatters. Add Strava-specific helpers.

```python
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
```

**Step 2: Commit**

```bash
git add src/health_to_notion/formatters.py
git commit -m "feat: rewrite formatters for Strava data"
```

---

### Task 7: Rewrite activities syncer for Strava

**Files:**
- Modify: `src/health_to_notion/syncers/activities.py`

**Step 1: Rewrite `src/health_to_notion/syncers/activities.py`**

```python
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
    sport_type = str(activity.sport_type) if activity.sport_type else "Workout"
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

    # Extract numeric values from stravalib model objects
    distance_m = float(activity.distance) if activity.distance else 0
    moving_time_s = int(float(activity.moving_time)) if activity.moving_time else 0
    avg_speed = float(activity.average_speed) if activity.average_speed else 0
    avg_hr = round(activity.average_heartrate) if activity.average_heartrate else 0
    max_hr = round(activity.max_heartrate) if activity.max_heartrate else 0
    avg_watts = round(activity.average_watts, 1) if activity.average_watts else 0
    calories = round(activity.calories) if activity.calories else 0
    suffer_score = activity.suffer_score or 0

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
    # Check name overrides first (for combat sports etc.)
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


def sync_activities(
    strava: StravaClient,
    notion: NotionClient,
    settings: Settings,
) -> None:
    """Sync Strava activities to the Notion Activities database."""
    if not settings.activities_db_id:
        logger.info("No activities database configured, skipping")
        return

    after_date = datetime.now(settings.timezone) - timedelta(days=settings.days_back)
    activities = list(strava.get_activities(
        after=after_date,
        limit=settings.fetch_limit,
    ))
    logger.info("Fetched %d activities from Strava", len(activities))

    created, updated, skipped = 0, 0, 0

    for activity in activities:
        strava_id = activity.id
        sport_type = str(activity.sport_type) if activity.sport_type else "Workout"

        existing = _activity_exists(notion, settings.activities_db_id, strava_id)

        if existing:
            # Update existing entry
            props = _build_properties(activity, settings)
            emoji = _get_icon_emoji(sport_type, activity.name or "")
            notion.pages.update(
                page_id=existing["id"],
                properties=props,
                icon={"emoji": emoji},
            )
            updated += 1
        else:
            props = _build_properties(activity, settings)
            emoji = _get_icon_emoji(sport_type, activity.name or "")
            notion.pages.create(
                parent={"database_id": settings.activities_db_id},
                properties=props,
                icon={"emoji": emoji},
            )
            created += 1

    logger.info(
        "Activities sync complete: %d created, %d updated, %d unchanged",
        created,
        updated,
        skipped,
    )
```

**Step 2: Commit**

```bash
git add src/health_to_notion/syncers/activities.py
git commit -m "feat: rewrite activities syncer for Strava API"
```

---

### Task 8: Update workouts syncer and create stub syncers

**Files:**
- Modify: `src/health_to_notion/syncers/workouts.py`
- Modify: `src/health_to_notion/syncers/sleep.py`
- Modify: `src/health_to_notion/syncers/daily_steps.py`
- Modify: `src/health_to_notion/syncers/personal_records.py`
- Modify: `src/health_to_notion/syncers/summary.py`

**Step 1: Update `workouts.py`**

Key changes:
- Remove Garmin Training Effect / Aerobic Effect intensity logic
- Use `Suffer Score` + `Intensity` properties from Activities DB (set by activities syncer)
- Change `Garmin ID` → `Strava ID`
- Change source URL to Strava
- Modality now comes from Strava sport_type via Activities DB Type/SubType

Replace entire file:

```python
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
    # Try SubType first (more specific), then Type
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
    title = modality  # Clean title for Board/Calendar views

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


def sync_workouts(notion: NotionClient, settings: Settings) -> None:
    """Sync Activities database entries to the Workouts database."""
    if not settings.workouts_db_id:
        logger.info("No workouts database configured, skipping")
        return

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
        existing = _workout_exists(
            notion, settings.workouts_db_id, strava_id, date_start, modality
        )

        if existing:
            notion.pages.update(page_id=existing["id"], properties=workout_props)
            updated += 1
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

    logger.info(
        "Workouts sync complete: %d created, %d updated, %d skipped",
        created, updated, skipped,
    )
```

**Step 2: Replace `sleep.py` with stub**

```python
"""Sync sleep data to the Notion Sleep database.

Not yet implemented — coming with Withings or Apple Health integration.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def sync_sleep(*args: object, **kwargs: object) -> None:
    """Placeholder for sleep sync. Requires Withings or Apple Health."""
    logger.info("Sleep sync not yet implemented (coming with Withings/Apple Health)")
```

**Step 3: Replace `daily_steps.py` with stub**

```python
"""Sync daily step counts to the Notion Steps database.

Not yet implemented — coming with Withings or Apple Health integration.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def sync_daily_steps(*args: object, **kwargs: object) -> None:
    """Placeholder for daily steps sync. Requires Withings or Apple Health."""
    logger.info("Daily steps sync not yet implemented (coming with Withings/Apple Health)")
```

**Step 4: Replace `personal_records.py` with stub**

```python
"""Sync personal records to the Notion Personal Records database.

Not yet implemented — Strava does not have a dedicated PR endpoint.
Coming with Withings or Apple Health integration.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def sync_personal_records(*args: object, **kwargs: object) -> None:
    """Placeholder for personal records sync."""
    logger.info("Personal records sync not yet implemented")
```

**Step 5: Update `summary.py`**

Remove sleep/steps average computation. Keep workout aggregation logic. Remove all Garmin imports.

Key changes to `summary.py`:
- Remove `_compute_lifestyle_averages()` function entirely
- In `sync_summary()`, remove the call to `_compute_lifestyle_averages()`
- In `_build_properties()`, set sleep/steps fields to empty/null defaults
- Remove sleep/steps database fetching

Replace the `_compute_lifestyle_averages` function with a stub:

```python
def _compute_lifestyle_averages(
    notion: NotionClient,
    settings: Settings,
) -> dict[tuple[str, str], dict]:
    """Compute lifestyle averages per period.

    Currently returns empty data. Will be populated when Withings/Apple Health
    integration adds sleep and steps data.
    """
    return {}
```

No other changes needed in summary.py — the rest of the aggregation logic reads from Notion (Workouts DB), not from Strava directly.

**Step 6: Commit**

```bash
git add src/health_to_notion/syncers/
git commit -m "feat: update workouts syncer and stub out sleep/steps/PRs"
```

---

### Task 9: Rewrite CLI entry point (__main__.py)

**Files:**
- Modify: `src/health_to_notion/__main__.py`

**Step 1: Rewrite `__main__.py`**

```python
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
            "workouts", "summary", "cleanup", "auth",
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
    from health_to_notion.syncers.summary import sync_summary
    from health_to_notion.syncers.workouts import sync_workouts

    clients = init_clients(settings)

    sync_map = {
        "activities": lambda: sync_activities(clients.strava, clients.notion, settings),
        "workouts": lambda: sync_workouts(clients.notion, settings),
        "summary": lambda: sync_summary(clients.notion, settings),
    }

    db_check = {
        "activities": settings.activities_db_id,
        "workouts": settings.workouts_db_id,
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
```

**Step 2: Commit**

```bash
git add src/health_to_notion/__main__.py
git commit -m "feat: rewrite CLI for Strava commands and auth flow"
```

---

### Task 10: Update GitHub Actions workflows

**Files:**
- Modify: `.github/workflows/sync.yml`
- Modify: `.github/workflows/cleanup.yml`

**Step 1: Update `sync.yml`**

```yaml
name: Health to Notion Sync

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run sync
        env:
          STRAVA_CLIENT_ID: ${{ secrets.STRAVA_CLIENT_ID }}
          STRAVA_CLIENT_SECRET: ${{ secrets.STRAVA_CLIENT_SECRET }}
          STRAVA_REFRESH_TOKEN: ${{ secrets.STRAVA_REFRESH_TOKEN }}
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          TIMEZONE: ${{ vars.TIMEZONE || 'UTC' }}
          STRAVA_DAYS_BACK: ${{ vars.STRAVA_DAYS_BACK || '30' }}
          STRAVA_ACTIVITIES_FETCH_LIMIT: ${{ vars.STRAVA_ACTIVITIES_FETCH_LIMIT || '200' }}
          PYTHONPATH: src
        run: python -m health_to_notion all
```

**Step 2: Update `cleanup.yml`**

```yaml
name: Cleanup Workout Duplicates

on:
  workflow_dispatch:

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install -r requirements.txt

      - name: Run cleanup
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          PYTHONPATH: src
        run: python -m health_to_notion cleanup --execute
```

**Step 3: Commit**

```bash
git add .github/workflows/sync.yml .github/workflows/cleanup.yml
git commit -m "feat: update GitHub Actions for Strava credentials"
```

---

### Task 11: Update notion_helpers.py database discovery names

**Files:**
- Modify: `src/health_to_notion/notion_helpers.py`

**Step 1: Update `EXPECTED_DATABASES` dict (line 14-21)**

The database names in Notion stay the same, but the cleanup_duplicates tool references `Garmin ID` which needs to become `Strava ID`. The `notion_helpers.py` file itself only uses database names for discovery — those names stay unchanged since the Notion databases keep their names.

No changes needed in `notion_helpers.py` itself. The `EXPECTED_DATABASES` map and all helper functions work as-is.

**Step 2: Update `cleanup_duplicates.py` — no changes needed**

The cleanup tool groups by (date, title, modality) — it doesn't reference Garmin ID. It works as-is.

**Step 3: Verify no stale Garmin references remain**

Run: `grep -r "garmin" src/health_to_notion/ --include="*.py" -i`
Expected: No matches (all Garmin references replaced)

Run: `grep -r "Garmin ID" src/health_to_notion/ --include="*.py"`
Expected: No matches

**Step 4: Commit (only if changes were needed)**

---

### Task 12: Install dependencies and smoke test

**Step 1: Install new dependencies**

```bash
cd /Users/COLEMAN/Documents/GitHub/garmin-to-notion
pip install -r requirements.txt
```

**Step 2: Verify package imports**

```bash
PYTHONPATH=src python -c "
from health_to_notion.config import Settings, load_settings
from health_to_notion.clients import Clients, init_clients, init_notion_only
from health_to_notion.formatters import format_sport_type, format_pace, format_duration
from health_to_notion.mappings import ACTIVITY_EMOJIS, TYPE_MAP, MODALITY_MAP
from health_to_notion.notion_helpers import discover_databases, fetch_all_pages
from health_to_notion.syncers.activities import sync_activities
from health_to_notion.syncers.workouts import sync_workouts
from health_to_notion.syncers.summary import sync_summary
from health_to_notion.syncers.sleep import sync_sleep
from health_to_notion.syncers.daily_steps import sync_daily_steps
from health_to_notion.syncers.personal_records import sync_personal_records
from health_to_notion.tools.auth import run_auth
print('All imports OK')
"
```
Expected: `All imports OK`

**Step 3: Verify CLI help works**

```bash
PYTHONPATH=src python -m health_to_notion --help
```
Expected: Shows usage with `auth`, `activities`, `workouts`, `summary`, `cleanup`, etc.

**Step 4: Verify stubs log correctly**

```bash
PYTHONPATH=src python -c "
import logging; logging.basicConfig()
from health_to_notion.syncers.sleep import sync_sleep
from health_to_notion.syncers.daily_steps import sync_daily_steps
from health_to_notion.syncers.personal_records import sync_personal_records
sync_sleep()
sync_daily_steps()
sync_personal_records()
"
```
Expected: Three "not yet implemented" log messages

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "chore: install deps and verify all imports"
```

---

### Task 13: Final cleanup and verification

**Step 1: Search for any remaining Garmin references**

```bash
grep -r "garmin" src/ --include="*.py" -il
grep -r "garmin_to_notion" . --include="*.py" -il
grep -r "garmin_to_notion" . --include="*.yml" -il
grep -r "garmin_to_notion" . --include="*.toml" -il
```
Expected: No matches in any of these

**Step 2: Verify `pyproject.toml` is clean**

Ensure name is `health-to-notion`, version is `4.0.0`, dependencies list `stravalib` not `garminconnect`.

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup — remove all Garmin references"
```
