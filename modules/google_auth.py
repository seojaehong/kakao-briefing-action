from __future__ import annotations

import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


def get_google_token_json() -> str:
    token_json = os.environ.get("GOOGLE_TOKEN_JSON", "").strip()
    if not token_json:
        raise KeyError("GOOGLE_TOKEN_JSON")
    return token_json


def build_google_credentials() -> Credentials:
    data = json.loads(get_google_token_json())
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

