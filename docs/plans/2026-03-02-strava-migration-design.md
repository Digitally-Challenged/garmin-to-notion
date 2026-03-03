# Strava Migration Design

**Date:** 2026-03-02
**Status:** Approved
**Goal:** Replace Garmin with Strava as the data source, rename project to `health-to-notion`

## Context

The garmin-to-notion project syncs fitness data to Notion databases. We're migrating from Garmin Connect to Strava as the primary activity source. Sleep, steps, and personal records will be re-added later via Withings or Apple Health.

## Approach: Direct Swap

Replace `garminconnect` with `stravalib`, update client/formatters/mappings, rename package. No abstraction layers — YAGNI.

## Package Structure

```
src/health_to_notion/
    __init__.py
    __main__.py                # CLI (auth, activities, workouts, summary, cleanup)
    config.py                  # Settings (Strava OAuth + Notion)
    clients.py                 # Strava + Notion client setup
    log.py                     # Logging (unchanged)
    notion_helpers.py          # Shared Notion utilities (unchanged)
    formatters.py              # Strava-adapted formatting
    mappings.py                # Strava sport_type → emojis, modality maps
    syncers/
        activities.py          # Strava → Activities DB
        personal_records.py    # Stub (future: Withings/Apple Health)
        daily_steps.py         # Stub (future: Withings/Apple Health)
        sleep.py               # Stub (future: Withings/Apple Health)
        workouts.py            # Activities DB → Workouts DB
        summary.py             # Aggregation (no sleep/steps until Withings)
    tools/
        cleanup_duplicates.py  # Unchanged
        auth.py                # NEW: Strava OAuth helper
```

## Authentication

### One-Time Setup
1. User runs `python -m health_to_notion auth`
2. Script opens browser to Strava OAuth page
3. User authorizes → script captures auth code via local callback
4. Exchanges code for access_token + refresh_token
5. User stores as env vars / GitHub Secrets:
   - `STRAVA_CLIENT_ID`
   - `STRAVA_CLIENT_SECRET`
   - `STRAVA_REFRESH_TOKEN`

### Runtime
- `clients.py` calls `stravalib.Client.refresh_access_token()` using the refresh token
- Returns a fresh access token (valid ~6 hours)
- Strava refresh tokens don't expire until revoked

## Configuration

```python
@dataclass(frozen=True)
class Settings:
    strava_client_id: str
    strava_client_secret: str
    strava_refresh_token: str
    notion_token: str
    activities_db_id: str | None
    workouts_db_id: str | None
    summary_db_id: str | None
    pr_db_id: str | None        # Stub
    steps_db_id: str | None     # Stub
    sleep_db_id: str | None     # Stub
    timezone: ZoneInfo
    fetch_limit: int
    days_back: int
```

### Environment Variables
| Variable | Required | Description |
|---|---|---|
| `STRAVA_CLIENT_ID` | Yes | Strava API app client ID |
| `STRAVA_CLIENT_SECRET` | Yes | Strava API app client secret |
| `STRAVA_REFRESH_TOKEN` | Yes | OAuth refresh token (from auth flow) |
| `NOTION_TOKEN` | Yes | Notion integration token |
| `TIMEZONE` | No (UTC) | IANA timezone |
| `STRAVA_DAYS_BACK` | No (30) | Days of history to sync |
| `STRAVA_ACTIVITIES_FETCH_LIMIT` | No (200) | Max activities per sync |

## Activity Field Mapping

| Notion Property | Garmin Source (old) | Strava Source (new) |
|---|---|---|
| Name | `activityName` | `name` |
| Type | `activityType.typeKey` (mapped) | `sport_type` (mapped) |
| SubType | `activityType.typeKey` (mapped) | `sport_type` (same as Type for Strava) |
| Date | `startTimeGMT` → local | `start_date_local` |
| Distance (km) | `distance / 1000` | `distance / 1000` |
| Duration | `duration` (sec) | `moving_time` (sec) |
| Calories | `calories` | `calories` (estimated by Strava) |
| Avg Pace | from `averageSpeed` | from `average_speed` |
| Avg HR | `averageHR` | `average_heartrate` |
| Max HR | `maxHR` | `max_heartrate` |
| Avg Power | `avgPower` | `average_watts` |
| Steps | `steps` | N/A (removed) |
| Strava ID | N/A | `id` (replaces Garmin ID) |
| Day of Week | computed | computed (same) |
| Hour Block | computed | computed (same) |
| Source | N/A | `https://www.strava.com/activities/{id}` |

### Removed Properties (Garmin-specific)
- Training Effect (Garmin proprietary)
- Aerobic Effect (Garmin proprietary)
- Anaerobic Effect (Garmin proprietary)

## Strava sport_type Mapping

Strava uses `sport_type` enum values. Key mappings:

| Strava sport_type | Notion Type | Emoji |
|---|---|---|
| Run | Running | 🏃 |
| TrailRun | Running | 🏔️ |
| Ride | Cycling | 🚴 |
| MountainBikeRide | Cycling | 🚵 |
| VirtualRide | Cycling | 🚴 |
| Swim | Swimming | 🏊 |
| Walk | Walking | 🚶 |
| Hike | Walking | 🥾 |
| WeightTraining | Strength | 🏋️ |
| Yoga | Yoga/Pilates | 🧘 |
| CrossFit | Crossfit | 🔥 |
| Rowing | Rowing | 🚣 |
| RockClimbing | Climbing | 🧗 |
| Tennis | Racquet Sports | 🎾 |
| Pickleball | Racquet Sports | 🏓 |
| Soccer | Team Sports | ⚽ |
| Golf | Golf | ⛳ |
| Skateboard | Other | 🛹 |
| Surfing | Water Sports | 🏄 |
| Snowboard | Winter Sports | 🏂 |
| AlpineSki | Winter Sports | ⛷️ |

## Intensity Mapping (Workouts)

Without Garmin's Training Effect, intensity is derived from Strava's `suffer_score` (Relative Effort):

| Suffer Score Range | Intensity |
|---|---|
| 0-50 | Easy |
| 51-150 | Moderate |
| 151-300 | Hard |
| 300+ | Maximum |

Fallback: HR-based intensity when suffer_score is unavailable:
- Avg HR < 60% max → Easy
- 60-75% → Moderate
- 75-90% → Hard
- 90%+ → Maximum

## Workouts Syncer Changes

Minimal — reads from Activities DB (Notion), not directly from Strava:
- Remove Training Effect / Aerobic Effect references
- Use suffer_score-based intensity (stored as a new Activities property)
- `Garmin ID` → `Strava ID`
- Source URL → `https://www.strava.com/activities/{id}`

## Summary Syncer Changes

- Sleep/steps averages: empty until Withings is added
- Properties stay in DB schema but will be null
- Workout aggregation: unchanged

## Stub Syncers

`personal_records.py`, `daily_steps.py`, `sleep.py` each contain:
- Module docstring explaining "Not yet implemented — coming with Withings/Apple Health"
- A `sync_*()` function that logs "Skipping: not yet implemented" and returns
- Registered in CLI as valid commands

## GitHub Actions

### Secrets (new)
| Secret | Description |
|---|---|
| `STRAVA_CLIENT_ID` | Strava API client ID |
| `STRAVA_CLIENT_SECRET` | Strava API client secret |
| `STRAVA_REFRESH_TOKEN` | OAuth refresh token |
| `NOTION_TOKEN` | Notion integration token |

### Workflow Changes
- Remove `GARMIN_EMAIL` / `GARMIN_PASSWORD` env vars
- Add Strava env vars
- Rename `GARMIN_DAYS_BACK` → `STRAVA_DAYS_BACK`
- Rename `GARMIN_ACTIVITIES_FETCH_LIMIT` → `STRAVA_ACTIVITIES_FETCH_LIMIT`

## Dependencies

### Remove
- `garminconnect>=0.2.19,<0.3`

### Add
- `stravalib>=2.0,<3.0`

### Keep
- `notion-client==2.2.1`
- `python-dotenv>=1.0,<2.0`

## Deduplication

Activities are deduplicated by `Strava ID` (number property in Notion). Same pattern as current Garmin ID lookup — query Notion by ID before creating.

## Migration Path for Existing Users

1. Existing Garmin data stays in Notion databases (not deleted)
2. New Strava activities get `Strava ID` instead of `Garmin ID`
3. Both ID fields can coexist in the Activities DB
4. Users should add `Strava ID` property to their Notion databases
