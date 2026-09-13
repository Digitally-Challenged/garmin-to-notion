"""Withings API client for body composition data."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://wbsapi.withings.net"

# MeasType IDs we care about
WEIGHT = 1
FAT_RATIO = 6
MUSCLE_MASS = 76


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict:
    """Refresh the Withings access token. Returns the full token response body.

    IMPORTANT: Withings returns a NEW refresh_token on every refresh.
    The caller should persist the new refresh_token for next time.
    """
    resp = requests.post(f"{API_BASE}/v2/oauth2", data={
        "action": "requesttoken",
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    })
    data = resp.json()
    if data.get("status") != 0:
        raise RuntimeError(f"Withings token refresh failed: {data}")
    return data["body"]


def _default_env_path() -> Path:
    """The repo's .env, derived from this file's location (src/health_to_notion/x.py -> root)."""
    return Path(__file__).resolve().parents[2] / ".env"


def persist_refresh_token(new_refresh_token: str, env_path: str | Path | None = None) -> bool:
    """Write the rotated refresh token back into .env, atomically.

    Withings invalidates the previous refresh token on every refresh, so the old behaviour of only
    *logging* the replacement guaranteed that the next run failed with `503 invalid refresh_token`
    (which is how this integration died). Returns True when the file now holds the new token; a write
    failure is logged and reported as False so a read-only checkout cannot break an otherwise good sync.
    """
    path = Path(env_path) if env_path else _default_env_path()
    try:
        lines = path.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("WITHINGS_REFRESH_TOKEN="):
                lines[i] = f"WITHINGS_REFRESH_TOKEN={new_refresh_token}"
                break
        else:
            lines.append(f"WITHINGS_REFRESH_TOKEN={new_refresh_token}")
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text("\n".join(lines) + "\n")
        os.chmod(tmp, 0o600)
        tmp.replace(path)
        logger.info("Persisted rotated Withings refresh token to %s", path)
        return True
    except OSError as exc:
        logger.error("Could not persist rotated Withings refresh token to %s: %s", path, exc)
        return False


def get_body_measurements(
    access_token: str,
    days_back: int = 30,
) -> list[dict]:
    """Fetch body composition measurements from Withings.

    Returns a list of dicts with keys: date, weight, fat_pct, muscle_mass.
    Only includes measurement groups that have all 3 fields.
    Deduplicates to one entry per calendar day (keeps first reading).
    """
    now = datetime.now()
    start = now - timedelta(days=days_back)

    resp = requests.post(f"{API_BASE}/measure", headers={
        "Authorization": f"Bearer {access_token}",
    }, data={
        "action": "getmeas",
        "meastypes": f"{WEIGHT},{FAT_RATIO},{MUSCLE_MASS}",
        "category": "1",
        "startdate": str(int(start.timestamp())),
        "enddate": str(int(now.timestamp())),
    })
    data = resp.json()
    if data.get("status") != 0:
        raise RuntimeError(f"Withings getmeas failed: {data}")

    groups = data["body"].get("measuregrps", [])
    logger.info("Fetched %d measurement groups from Withings", len(groups))

    results: list[dict] = []
    seen_dates: set[str] = set()

    for group in groups:
        measures: dict[int, float] = {}
        for m in group["measures"]:
            measures[m["type"]] = m["value"] * 10 ** m["unit"]

        # Skip groups missing any of the 3 required fields
        if not all(t in measures for t in (WEIGHT, FAT_RATIO, MUSCLE_MASS)):
            continue

        dt = datetime.fromtimestamp(group["date"])
        date_key = dt.strftime("%Y-%m-%d")

        # One entry per day
        if date_key in seen_dates:
            continue
        seen_dates.add(date_key)

        kg_to_lbs = 2.20462
        results.append({
            "date": date_key,
            "weight": round(measures[WEIGHT] * kg_to_lbs, 1),
            "fat_pct": round(measures[FAT_RATIO], 1),
            "muscle_mass": round(measures[MUSCLE_MASS] * kg_to_lbs, 1),
        })

    logger.info("Filtered to %d unique daily measurements", len(results))
    return results
