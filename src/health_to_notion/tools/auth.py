"""One-time Strava OAuth authorization helper.

Usage:
    python -m health_to_notion auth

Opens a browser for Strava authorization, captures the auth code via a
local HTTP server, and exchanges it for access + refresh tokens.
"""

from __future__ import annotations

import http.server
import logging
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
