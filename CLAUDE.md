# garmin-to-notion

<!-- AUTO-MANAGED: project-description -->
Syncs fitness data from Strava to Notion databases. Python package (`health-to-notion`) with a CLI and GitHub Actions workflow. Runs on a 6-hour schedule via GitHub Actions.
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: build-commands -->
## Commands

```bash
# Install
pip install -e .

# Run CLI (PYTHONPATH=src required when not installed)
PYTHONPATH=src python -m health_to_notion <command>

# CLI commands
python -m health_to_notion              # Run all syncs (activities, workouts, body, summary)
python -m health_to_notion activities   # Sync Strava activities to Activities DB
python -m health_to_notion workouts     # Transform Activities DB to Workouts DB
python -m health_to_notion body         # Sync Withings body composition to Body Composition DB
python -m health_to_notion summary      # Aggregate Workouts into monthly/yearly summaries
python -m health_to_notion cleanup      # Deduplicate workouts (dry run)
python -m health_to_notion cleanup --execute  # Actually remove duplicates
python -m health_to_notion auth         # Run Strava OAuth setup
python -m health_to_notion records      # Stub: future personal records sync
python -m health_to_notion steps        # Stub: future daily steps sync
python -m health_to_notion sleep        # Stub: future sleep sync

# Flags
--verbose / -v    # Enable debug logging
```
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: environment-variables -->
## Environment Variables

Copy `.env.example` to `.env` and fill in values.

**Required — Strava OAuth:**
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REFRESH_TOKEN`

**Required — Notion:**
- `NOTION_TOKEN`

**Optional — Database IDs** (auto-discovered via `discover_databases()` if not set):
- `NOTION_DB_ID`, `NOTION_PR_DB_ID`, `NOTION_STEPS_DB_ID`
- `NOTION_SLEEP_DB_ID`, `NOTION_WORKOUTS_DB_ID`, `NOTION_SUMMARY_DB_ID`
- `NOTION_BODY_DB_ID`

**Optional — Withings OAuth:**
- `WITHINGS_CLIENT_ID`
- `WITHINGS_CLIENT_SECRET`
- `WITHINGS_REFRESH_TOKEN`
- `WITHINGS_REDIRECT_URI` (used during OAuth setup; default: `http://localhost:8791/callback`)

**Optional — Settings:**
- `TIMEZONE` (default: `UTC`)
- `STRAVA_DAYS_BACK` (default: `30`)
- `STRAVA_ACTIVITIES_FETCH_LIMIT` (default: `200`)
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
src/health_to_notion/
    __init__.py             # Package version
    __main__.py             # CLI entry point (argparse)
    config.py               # Settings frozen dataclass; all env vars loaded here
    clients.py              # Strava + Notion client initialization
    log.py                  # Logging setup
    notion_helpers.py       # Shared Notion utilities (fetch_all_pages, get_prop, discover_databases)
    formatters.py           # Strava data → Notion display values
    mappings.py             # Activity type → emoji, modality, intensity maps
    withings_client.py      # Withings OAuth token refresh + API wrapper (POST /measure)
    syncers/
        __init__.py
        activities.py       # Strava → Activities DB
        workouts.py         # Activities DB → Workouts DB
        summary.py          # Workouts DB → Summary DB (month/year aggregations)
        body_composition.py # Withings → Body Composition DB (weight, fat %, muscle mass)
        personal_records.py # Stub (future: Apple Health)
        daily_steps.py      # Stub (future: Apple Health)
        sleep.py            # Stub (future: Apple Health)
    tools/
        cleanup_duplicates.py  # Deduplicate Workouts DB entries
        auth.py                # Strava OAuth helper
.github/workflows/
    sync.yml                # Runs every 6 hours: python -m health_to_notion all
    cleanup.yml             # Manual trigger: python -m health_to_notion cleanup --execute
docs/
    notion-ai-prompt.txt        # Notion AI prompt to scaffold the full Fitness Tracker workspace
    notion-ai-update-prompt.txt # Notion AI prompt to add chart/table views to existing databases (15 views across Body Composition, Workouts, Activities, Activity Summary)
    notion-template-setup.md    # Manual setup guide for the Notion workspace
```

**Data flow:** Strava API → Activities DB → Workouts DB → Summary DB; Withings API → Body Composition DB

**Target Notion workspace (7 inline databases):**
- `Activity Summary` — monthly/yearly aggregations per modality
- `Workouts` — cleaned workout entries derived from Activities
- `Body Composition` — daily weight, fat %, muscle mass from Withings Body+
- `Daily Steps` — step count per day (stub; future Apple Health)
- `Sleep` — sleep duration and score per night (stub; future Apple Health)
- `Activities` — raw Strava activities
- `Personal Records` — PRs (stub; future Apple Health)
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Conventions

- `Settings` is a frozen dataclass in `config.py`; all env vars loaded there via `load_settings()`
- `require_strava=False` in `load_settings()` for commands that only need Notion (cleanup, summary, stubs)
- Syncers read from one source and write to one target; never mix sources in the same syncer call
- Deduplication: bulk-prefetch all existing Strava IDs at the start of each sync (`_prefetch_existing_ids` / `_prefetch_workout_ids`) to avoid N+1 Notion queries; Activities syncer updates existing entries on re-sync; Workouts syncer skips existing entries
- Emoji icon is set on both `pages.create` and `pages.update` for activities; body composition icon set only on create
- `_get_icon_emoji` applies name-based overrides for combat sports (BJJ/jiu-jitsu/MMA, boxing/kickboxing) before falling back to `ACTIVITY_EMOJIS` sport_type lookup
- Activities DB writes heatmap properties: `Day of Week` (select) and `Hour Block` (select, 2-hour blocks e.g. `"06:00-08:00"`)
- `getattr` with defaults for `DetailedActivity`-only fields (calories, suffer_score) to stay compatible with `SummaryActivity`
- Stub syncers for records/steps/sleep just return — do not raise, do not log "not implemented" as error
- Withings body comp dedup: query Notion by date before creating; one entry per calendar day (keep first reading, skip subsequent)
- Withings API response values decoded as `value * 10^unit`; only sync groups with all 3 fields (weight + fat % + muscle mass)
- `init_notion_only()` for cleanup/summary/stubs; `init_clients()` only when Strava is needed
- DB IDs are optional env vars; missing ones are auto-discovered via `notion_helpers.discover_databases()`
- `PYTHONPATH=src` required when running directly (not installed); set automatically in GitHub Actions
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: git-insights -->
## Key Architectural Decisions

- **Data source:** Strava via `stravalib>=2.0,<3.0`; OAuth refresh token flow
- **Intensity:** Derived from `suffer_score` (Relative Effort) via `SUFFER_SCORE_THRESHOLDS`; `INTENSITY_FLOOR` enforces minimums per modality (e.g. HIIT/BJJ/Crossfit floor at Moderate)
- **Modality:** `MODALITY_MAP` for sport_type; `NAME_OVERRIDE_MAP` for name-based overrides (BJJ, Boxing, Sauna tagged as "Workout" in Strava)
- **Summary aggregation:** Per period (Month/Year): one "All" row + one row per modality; keyed by Start date + Period + Modality
- **Withings body comp:** Active integration via `withings_client.py`; OAuth 2.0 token refresh (access tokens last 3 hours, refresh tokens last 1 year; each refresh returns a new refresh token); meastypes=1,6,76 (Weight, Fat %, Muscle Mass)
- **Sleep/steps/PRs:** Stubs reserved for future Apple Health integration; Withings does not expose sleep/steps from Apple Health sync; lifestyle fields (Avg Sleep, Avg Steps, etc.) already present in Summary DB schema
- **No abstraction layers:** Direct field mapping from Strava model attributes to Notion properties
- **Bulk prefetch over N+1:** Syncers call `_prefetch_existing_ids()` / `_prefetch_workout_ids()` once at startup to load all existing Strava IDs into memory; per-record existence checks use dict/set lookups instead of Notion API calls
<!-- END AUTO-MANAGED -->
