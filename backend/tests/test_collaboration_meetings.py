from datetime import timezone
from urllib.parse import parse_qs, urlparse

from app.config import settings
from app.connectors.google_drive.oauth import scopes_for_provider
from app.connectors.google_workspace.meet_sync import _parse_time, _transcript_text
from app.connectors.microsoft_teams.oauth import MICROSOFT_SCOPES, build_microsoft_authorization_url
from app.connectors.slack.oauth import SLACK_BOT_SCOPES, build_slack_authorization_url
from app.connectors.microsoft_teams.sync import _parse_graph_datetime


def test_google_meet_scope_is_read_only():
    scopes = scopes_for_provider("google_meet")
    assert "https://www.googleapis.com/auth/meetings.space.readonly" in scopes
    assert "https://www.googleapis.com/auth/meetings.space.created" not in scopes


def test_slack_authorization_url_contains_state_and_read_scopes(monkeypatch):
    monkeypatch.setattr(settings, "slack_client_id", "slack-client")
    monkeypatch.setattr(settings, "slack_oauth_redirect_uri", "https://sera.example/oauth/slack/callback")
    query = parse_qs(urlparse(build_slack_authorization_url("state-123")).query)
    assert query["client_id"] == ["slack-client"]
    assert query["state"] == ["state-123"]
    assert set(query["scope"][0].split(",")) == set(SLACK_BOT_SCOPES)
    assert query["redirect_uri"] == ["https://sera.example/oauth/slack/callback"]


def test_microsoft_authorization_url_requests_delegated_meeting_permissions(monkeypatch):
    monkeypatch.setattr(settings, "microsoft_client_id", "microsoft-client")
    monkeypatch.setattr(settings, "microsoft_tenant_id", "common")
    monkeypatch.setattr(settings, "microsoft_oauth_redirect_uri", "https://sera.example/oauth/microsoft/callback")
    query = parse_qs(urlparse(build_microsoft_authorization_url("state-456")).query)
    assert query["client_id"] == ["microsoft-client"]
    assert query["state"] == ["state-456"]
    assert set(query["scope"][0].split()) == set(MICROSOFT_SCOPES)


def test_google_meet_transcript_text_and_timestamps_are_normalized():
    text = _transcript_text(
        [
            {"participant": "Rahul", "text": "We will migrate the API."},
            {"participant": "Priya", "text": "Security review is next."},
        ]
    )
    assert "Rahul: We will migrate the API." in text
    assert _parse_time("2026-08-25T10:30:00Z").tzinfo == timezone.utc
    assert _parse_graph_datetime("2026-08-25T10:30:00").tzinfo == timezone.utc
