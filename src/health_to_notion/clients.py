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
