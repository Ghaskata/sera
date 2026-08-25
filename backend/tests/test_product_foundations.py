import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.connectors.google_drive.oauth import scopes_for_provider
from app.models.oauth_state import OAuthState
from app.models.work_intelligence import AutomationCandidate
from app.services.oauth_state import consume_oauth_state, create_oauth_state
from app.services.work_intelligence import explain_candidate, make_action_key


def test_google_scope_routing_is_narrow_and_provider_specific():
    drive_scopes = scopes_for_provider("google_drive")
    gmail_scopes = scopes_for_provider("google_gmail")
    calendar_scopes = scopes_for_provider("google_calendar")

    assert "openid" in drive_scopes
    assert "https://www.googleapis.com/auth/drive.readonly" in drive_scopes
    assert "https://www.googleapis.com/auth/gmail.readonly" in gmail_scopes
    assert "https://www.googleapis.com/auth/calendar.readonly" in calendar_scopes
    assert "https://www.googleapis.com/auth/gmail.readonly" not in drive_scopes


def test_unknown_google_provider_is_rejected():
    with pytest.raises(ValueError, match="Unsupported Google connector"):
        scopes_for_provider("google_maps")


@pytest.mark.asyncio
async def test_oauth_state_is_short_lived_and_one_time():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    state = await create_oauth_state(session, uuid.uuid4())

    assert len(state.state) >= 32
    session.commit.assert_awaited_once()

    consume_session = MagicMock()
    consume_session.scalar = AsyncMock(return_value=state)
    consume_session.commit = AsyncMock()
    consumed = await consume_oauth_state(consume_session, state.state)

    assert consumed is state
    assert state.used_at is not None
    consume_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_expired_oauth_state_cannot_be_consumed():
    state = OAuthState(
        id=uuid.uuid4(),
        state="expired-state",
        user_id=uuid.uuid4(),
        provider="google_drive",
        purpose="login_and_drive",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=state)
    session.commit = AsyncMock()

    assert await consume_oauth_state(session, state.state) is None
    session.commit.assert_not_awaited()


def test_work_intelligence_explanation_exposes_time_saved_metrics():
    candidate = AutomationCandidate(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        action_key="weekly-sales-report",
        name="Weekly sales report",
        description="Repeated task",
        frequency_count=17,
        total_minutes=306,
        first_seen_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
        status="detected",
        workflow=[],
    )
    explanation = explain_candidate(candidate)

    assert explanation["frequency"] == 17
    assert explanation["average_minutes"] == 18.0
    assert explanation["total_hours"] == 5.1
    assert explanation["first_detected"] == "2026-08-02"
    assert make_action_key("Weekly Sales Report") == "weekly-sales-report"
