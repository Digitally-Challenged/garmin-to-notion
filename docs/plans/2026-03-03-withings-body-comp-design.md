# Withings Body Composition Integration Design

**Date:** 2026-03-03
**Status:** Approved
**Goal:** Sync Withings Body+ scale data (weight, fat %, muscle mass) to a new Notion database

## Context

The health-to-notion project syncs Strava fitness data to Notion. Adding Withings as a second data source for body composition tracking from a Body+ scale. Sleep and steps are not available from Withings (Apple Health doesn't sync those to Withings), so those remain as stubs.

## Approach

Same pattern as Strava — direct API calls with `requests`, no third-party wrapper library. Thin client module for Withings OAuth token refresh + API calls.

## New Files

```
src/health_to_notion/
    withings_client.py          # Withings OAuth token refresh + API wrapper
    syncers/
        body_composition.py     # Withings → Body Composition DB (NEW)
```

## Modified Files

```
src/health_to_notion/
    config.py                   # Add Withings credentials to Settings
    __main__.py                 # Add 'body' command
    .env.example                # Add Withings env vars
```

## Withings API Details

**Authentication:** OAuth 2.0, no HMAC signing needed for token exchange (confirmed by testing). Access tokens last 3 hours, refresh tokens last 1 year. Each refresh returns a new refresh token.

**Endpoint:** `POST https://wbsapi.withings.net/measure` with `action=getmeas`
- `meastypes=1,6,76` (Weight, Fat %, Muscle Mass)
- `category=1` (real measures only)
- Date range via `startdate`/`enddate` (unix timestamps)

**Response format:** Values returned as `value * 10^unit` (e.g., weight 98200 with unit -3 = 98.2 kg)

## Body Composition DB Schema (New Notion Database)

| Property | Type | Source |
|---|---|---|
| Name (Title) | Title | "98.2 kg" |
| Date | Date | Measurement date |
| Weight (kg) | Number (1 decimal) | MeasType 1 |
| Fat % | Number (1 decimal) | MeasType 6 |
| Muscle Mass (kg) | Number (1 decimal) | MeasType 76 |

## Data Filtering

- Only sync measurement groups that have all 3 fields (weight + fat + muscle)
- One entry per calendar day (keep first reading, skip duplicates)
- Dedup against Notion by date before creating

## Config Changes

```python
@dataclass(frozen=True)
class Settings:
    # ... existing fields ...
    withings_client_id: str
    withings_client_secret: str
    withings_refresh_token: str
    body_db_id: str | None
```

New env vars:
- `WITHINGS_CLIENT_ID`
- `WITHINGS_CLIENT_SECRET`
- `WITHINGS_REFRESH_TOKEN`
- `NOTION_BODY_DB_ID`

## CLI

```bash
python -m health_to_notion body          # Sync body composition
python -m health_to_notion all           # Now includes: activities, workouts, body, summary
```

## Rate Limits

Withings: 120 requests/minute. With ~1 API call per sync, no concern.
