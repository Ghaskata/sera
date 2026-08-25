import logging

from sqlalchemy import select

from app.config import settings
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.connectors.google_drive.oauth import build_authorization_url
from app.connectors.google_drive.sync import run_full_sync
from app.connectors.google_keep.sync import run_keep_sync
from app.connectors.google_workspace.meet_sync import run_google_meet_sync
from app.connectors.google_workspace.sync import run_calendar_sync, run_gmail_sync
from app.connectors.microsoft_teams.oauth import build_microsoft_authorization_url
from app.connectors.microsoft_teams.sync import run_teams_sync
from app.connectors.slack.oauth import build_slack_authorization_url
from app.connectors.slack.sync import run_slack_sync
from app.database import async_session_factory
from app.models.connector import Connector, ConnectorStatus
from app.models.work_intelligence import AutomationCandidate
from app.services.accounts import get_or_create_user_and_workspace
from app.services.connectors import (
    GOOGLE_CALENDAR,
    GOOGLE_DRIVE,
    GOOGLE_GMAIL,
    GOOGLE_MEET,
    GOOGLE_KEEP,
    get_or_create_pending_connector,
)
from app.services.notifications import send_telegram_message
from app.services.oauth_state import create_oauth_state
from app.search.rag import answer_question
from app.telegram_bot.registry import get_bot
from app.services.work_intelligence import detect_automation_candidates, explain_candidate

logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096


async def _split_and_send(update: Update, text: str) -> None:
    for i in range(0, len(text), TELEGRAM_MESSAGE_LIMIT):
        await update.message.reply_text(text[i : i + TELEGRAM_MESSAGE_LIMIT])


async def _google_login_url(tg_user, provider: str = GOOGLE_DRIVE) -> str:
    async with async_session_factory() as session:
        user, _ = await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)
        oauth_state = await create_oauth_state(session, user.id, provider=provider)
        return build_authorization_url(state=oauth_state.state, provider=provider)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with async_session_factory() as session:
        user, _ = await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)

    if user.google_sub is None:
        auth_url = await _google_login_url(tg_user)
        await update.message.reply_text(
            "Welcome to Sera. Sera needs your Google sign-in before it can safely understand your work context.\n\n"
            f"Tap this link to continue:\n{auth_url}\n\n"
            "After approval, return here and ask your question."
        )
        return

    await update.message.reply_text(
        "Welcome back to Sera. Your Google account is connected.\n\n"
        "Ask me what happened, where something is documented, or what was decided."
    )


async def login_google(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    auth_url = await _google_login_url(update.effective_user)
    await update.message.reply_text(f"Sign in with Google to connect Sera:\n{auth_url}")


async def connect_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    auth_url = await _google_login_url(update.effective_user, GOOGLE_GMAIL)
    await update.message.reply_text(f"Connect Gmail with Google:\n{auth_url}")


async def connect_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    auth_url = await _google_login_url(update.effective_user, GOOGLE_CALENDAR)
    await update.message.reply_text(f"Connect Google Calendar:\n{auth_url}")


async def connect_meet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    auth_url = await _google_login_url(update.effective_user, GOOGLE_MEET)
    await update.message.reply_text(f"Connect Google Meet meeting history and transcripts:\n{auth_url}")


async def connect_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    auth_url = await _google_login_url(update.effective_user, GOOGLE_KEEP)
    await update.message.reply_text(
        "Google Notes / Keep requires Workspace administrator-approved access. Continue here:\n"
        f"{auth_url}"
    )


async def _external_login_url(tg_user, provider: str, builder) -> str:
    async with async_session_factory() as session:
        user, _ = await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)
        oauth_state = await create_oauth_state(session, user.id, provider=provider)
        return builder(oauth_state.state)


async def connect_slack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    auth_url = await _external_login_url(update.effective_user, "slack", build_slack_authorization_url)
    await update.message.reply_text(
        "Continue setup in Slack. Sera will request only the configured read-only workspace permissions.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Continue setup in Slack", url=auth_url)]]
        ),
    )


async def connect_teams(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    auth_url = await _external_login_url(
        update.effective_user,
        "microsoft_teams",
        build_microsoft_authorization_url,
    )
    await update.message.reply_text(
        "Connect Microsoft Teams with read-only calendar and meeting-transcript access:\n" f"{auth_url}"
    )


async def connect_drive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Backwards-compatible command; Google login and Drive consent are combined
    # in the first product slice.
    await login_google(update, context)


async def connections_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with async_session_factory() as session:
        user, workspace = await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)
        connectors = (
            await session.scalars(
                select(Connector).where(Connector.workspace_id == workspace.id)
            )
        ).all()
    by_provider = {connector.provider: connector for connector in connectors}
    display_names = {
        "google_drive": "Google Drive",
        "google_gmail": "Gmail",
        "google_calendar": "Google Calendar",
        "google_meet": "Google Meet",
        "google_keep": "Google Notes / Keep",
        "slack": "Slack",
        "microsoft_teams": "Microsoft Teams",
        "discord": "Discord",
        "linkedin": "LinkedIn",
        "reddit": "Reddit",
        "twitter_x": "X / Twitter",
        "facebook": "Facebook",
    }
    lines = ["Sera connected accounts:"]
    maps_state = "configured" if settings.google_maps_api_key else "not configured"
    lines.append(f"• Google Maps / Places API: {maps_state}")
    for provider, name in display_names.items():
        connector = by_provider.get(provider)
        if connector is None:
            lines.append(f"• {name}: Not connected")
            continue
        last_sync = connector.last_sync_at.isoformat(timespec="minutes") if connector.last_sync_at else "not synced yet"
        lines.append(f"• {name}: {connector.status} · last sync: {last_sync}")
    lines.append("\nUse /connect_<provider> to add a supported account. Social catalog entries may require provider-specific app review.")
    await _split_and_send(update, "\n".join(lines))


async def insights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with async_session_factory() as session:
        user, workspace = await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)
        if user.google_sub is None:
            await update.message.reply_text("Please complete Google sign-in first with /login.")
            return
        candidates = await detect_automation_candidates(session, workspace.id)

    if not candidates:
        await update.message.reply_text(
            "I do not have enough repeated activity yet to identify an automation opportunity. "
            "Keep using your connected sources and try /insights again later."
        )
        return

    lines = ["Work patterns I noticed:"]
    for candidate in candidates:
        info = explain_candidate(candidate)
        lines.append(
            f"\n{candidate.name}\n"
            f"• {info['frequency']} times · {info['total_hours']} hours total · "
            f"~{info['average_minutes']} min each\n"
            f"• First: {info['first_detected']} · Last: {info['last_performed']}\n"
            f"• Use /why {candidate.action_key} for details."
        )
    await _split_and_send(update, "\n".join(lines))


async def why(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    action_key = context.args[0] if context.args else None
    if not action_key:
        await update.message.reply_text("Usage: /why <action-key>. Start with /insights to see detected work patterns.")
        return

    tg_user = update.effective_user
    async with async_session_factory() as session:
        _, workspace = await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)
        candidate = await session.scalar(
            select(AutomationCandidate).where(
                AutomationCandidate.workspace_id == workspace.id,
                AutomationCandidate.action_key == action_key,
            )
        )
    if candidate is None:
        await update.message.reply_text("I could not find that work pattern in your workspace.")
        return

    info = explain_candidate(candidate)
    await update.message.reply_text(
        f"{candidate.name}\n\n{info['message']}\n"
        f"First detected: {info['first_detected']}\n"
        f"Last performed: {info['last_performed']}\n"
        f"Total time: {info['total_hours']} hours\n\n"
        "This can likely be automated, but Sera will ask for approval before any external action."
    )


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    question = update.message.text

    async with async_session_factory() as session:
        user, workspace = await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)
        connector = await get_or_create_pending_connector(session, workspace.id, GOOGLE_DRIVE)
        if user.google_sub is None or connector.status != ConnectorStatus.CONNECTED:
            auth_url = await _google_login_url(tg_user)
            await update.message.reply_text("Please complete Google sign-in first.\n\n" f"{auth_url}")
            return

        result = await answer_question(session, workspace.id, question)

    text = result.answer
    if result.sources:
        source_lines = []
        for source in result.sources:
            details = [value for value in (source.source, source.date, source.person) if value]
            label = f"- {source.title}"
            if details:
                label += f" — {' · '.join(details)}"
            link = source.url or source.drive_link
            if link:
                label += f" ({link})"
            source_lines.append(label)
        text += "\n\nSources:\n" + "\n".join(source_lines)
    await _split_and_send(update, text)


async def trigger_connector_sync_and_notify(
    connector_id,
    telegram_user_id: int,
    provider: str = GOOGLE_DRIVE,
) -> None:
    async with async_session_factory() as session:
        connector = await session.get(Connector, connector_id)
        if connector is None:
            return
        try:
            if provider == GOOGLE_GMAIL:
                await run_gmail_sync(session, connector)
            elif provider == GOOGLE_CALENDAR:
                await run_calendar_sync(session, connector)
            elif provider == GOOGLE_MEET:
                await run_google_meet_sync(session, connector)
            elif provider == GOOGLE_KEEP:
                await run_keep_sync(session, connector)
            elif provider == "slack":
                await run_slack_sync(session, connector)
            elif provider == "microsoft_teams":
                await run_teams_sync(session, connector)
            else:
                await run_full_sync(session, connector)
        except Exception:
            logger.exception("Initial %s sync failed for connector %s", provider, connector_id)

    text = (
        f"{provider.replace('_', ' ').title()} connected. Your source has been indexed "
        "or is still processing. Ask me anything!"
    )
    bot = get_bot()
    if bot is not None:
        await bot.send_message(chat_id=telegram_user_id, text=text)
    else:
        await send_telegram_message(telegram_user_id, text)


# Backwards-compatible names used by existing callback code.
trigger_google_sync_and_notify = trigger_connector_sync_and_notify
trigger_sync_and_notify = trigger_connector_sync_and_notify


CONNECTOR_BUTTON_NAMES = {
    "google_drive": "Google Drive",
    "google_gmail": "Gmail",
    "google_calendar": "Google Calendar",
    "google_meet": "Google Meet",
    "google_keep": "Google Notes / Keep",
    "google_maps": "Google Maps / Places",
    "slack": "Slack",
    "microsoft_teams": "Microsoft Teams",
    "discord": "Discord",
    "linkedin": "LinkedIn",
    "reddit": "Reddit",
    "twitter_x": "X / Twitter",
    "facebook": "Facebook",
}


async def connect_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = []
    providers = list(CONNECTOR_BUTTON_NAMES)
    for index in range(0, len(providers), 2):
        row = []
        for provider in providers[index : index + 2]:
            row.append(
                InlineKeyboardButton(
                    CONNECTOR_BUTTON_NAMES[provider],
                    callback_data=f"setup:{provider}",
                )
            )
        buttons.append(row)
    await update.message.reply_text(
        "Choose an account or service to connect to Sera:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def connector_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    provider = (query.data or "").removeprefix("setup:")
    if provider not in CONNECTOR_BUTTON_NAMES:
        await query.edit_message_text("That connector is not available.")
        return

    if provider == "google_maps":
        configured = "configured" if settings.google_maps_api_key else "not configured"
        await query.edit_message_text(
            "Google Maps / Places uses a restricted server-side API key, not user OAuth. "
            f"Current status: {configured}. Set GOOGLE_MAPS_API_KEY in the backend environment."
        )
        return

    if provider in {"discord", "linkedin", "reddit", "twitter_x", "facebook"}:
        await query.edit_message_text(
            f"{CONNECTOR_BUTTON_NAMES[provider]} is listed in Sera’s social connector catalog. "
            "Its provider-specific OAuth app, permissions, and review are not enabled yet; "
            "no account will be connected from this button."
        )
        return

    if provider == "slack":
        auth_url = await _external_login_url(update.effective_user, "slack", build_slack_authorization_url)
        await query.edit_message_text(
            "Continue setup in Slack:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Continue setup in Slack", url=auth_url)]]
            ),
        )
        return

    if provider == "microsoft_teams":
        auth_url = await _external_login_url(
            update.effective_user,
            "microsoft_teams",
            build_microsoft_authorization_url,
        )
        await query.edit_message_text(
            "Continue setup in Microsoft Teams:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Continue setup in Teams", url=auth_url)]]
            ),
        )
        return

    auth_url = await _google_login_url(update.effective_user, provider)
    await query.edit_message_text(
        f"Continue setup for {CONNECTOR_BUTTON_NAMES[provider]}:",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Continue with Google", url=auth_url)]]
        ),
    )
