from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorDefinition:
    provider: str
    display_name: str
    auth_family: str
    capabilities: tuple[str, ...]
    status: str


CONNECTOR_CATALOG: tuple[ConnectorDefinition, ...] = (
    ConnectorDefinition(
        provider="google_drive",
        display_name="Google Drive",
        auth_family="google",
        capabilities=("read", "search", "index"),
        status="implemented",
    ),
    ConnectorDefinition(
        provider="google_gmail",
        display_name="Gmail",
        auth_family="google",
        capabilities=("read", "search", "index", "draft"),
        status="next",
    ),
    ConnectorDefinition(
        provider="google_calendar",
        display_name="Google Calendar",
        auth_family="google",
        capabilities=("read", "search", "index", "sync_meetings"),
        status="implemented",
    ),
    ConnectorDefinition(
        provider="google_meet",
        display_name="Google Meet",
        auth_family="google",
        capabilities=("read", "index_transcripts", "sync_meetings"),
        status="implemented",
    ),
    ConnectorDefinition(
        provider="google_maps",
        display_name="Google Maps",
        auth_family="google_api_key",
        capabilities=("search_places", "directions"),
        status="planned",
    ),
    ConnectorDefinition(
        provider="google_keep",
        display_name="Google Keep / Notes",
        auth_family="google",
        capabilities=("read", "index"),
        status="planned",
    ),
    ConnectorDefinition(
        provider="slack",
        display_name="Slack",
        auth_family="slack",
        capabilities=("read", "search", "index", "draft_message"),
        status="oauth_foundation",
    ),
    ConnectorDefinition(
        provider="microsoft_teams",
        display_name="Microsoft Teams",
        auth_family="microsoft",
        capabilities=("read", "search", "index", "draft_message", "sync_meetings"),
        status="oauth_foundation",
    ),
    ConnectorDefinition(
        provider="telegram",
        display_name="Telegram",
        auth_family="telegram_bot",
        capabilities=("receive_messages", "send_approved_messages"),
        status="implemented_interface",
    ),
)


def get_connector_definition(provider: str) -> ConnectorDefinition | None:
    return next((definition for definition in CONNECTOR_CATALOG if definition.provider == provider), None)
