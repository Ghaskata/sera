from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorDefinition:
    provider: str
    display_name: str
    auth_family: str
    capabilities: tuple[str, ...]
    status: str
    setup_mode: str = "oauth"
    note: str = ""


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
        capabilities=("read", "search", "index"),
        status="implemented",
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
        display_name="Google Maps / Places",
        auth_family="google_api_key",
        capabilities=("search_places", "place_details", "directions"),
        status="implemented_foundation",
        setup_mode="api_key",
        note="Uses a restricted Google Maps Platform API key; it is not part of Google account OAuth.",
    ),
    ConnectorDefinition(
        provider="google_keep",
        display_name="Google Keep / Notes",
        auth_family="google_workspace_admin",
        capabilities=("read", "index", "list_notes", "retrieve_attachments"),
        status="implemented_foundation",
        note="Requires Workspace administrator-approved Keep API access; ordinary consumer Google login is insufficient.",
    ),
    ConnectorDefinition(
        provider="slack",
        display_name="Slack",
        auth_family="slack",
        capabilities=("read", "search", "index", "draft_message"),
        status="implemented",
        note="OAuth v2 and read-only channel history sync are implemented; the user must install the Slack app.",
    ),
    ConnectorDefinition(
        provider="microsoft_teams",
        display_name="Microsoft Teams",
        auth_family="microsoft",
        capabilities=("read", "search", "index", "draft_message", "sync_meetings"),
        status="implemented",
        note="Delegated Microsoft Graph consent is required; transcript access may require tenant admin consent.",
    ),
    ConnectorDefinition(
        provider="discord",
        display_name="Discord",
        auth_family="discord",
        capabilities=("read", "index"),
        status="catalog_foundation",
        note="Requires a Discord application, bot installation, and guild/channel permissions.",
    ),
    ConnectorDefinition(
        provider="linkedin",
        display_name="LinkedIn",
        auth_family="linkedin",
        capabilities=("read_profile", "read_posts"),
        status="catalog_foundation",
        note="Capabilities depend on LinkedIn product approval; do not assume unrestricted personal-feed access.",
    ),
    ConnectorDefinition(
        provider="reddit",
        display_name="Reddit",
        auth_family="reddit",
        capabilities=("read", "search", "index"),
        status="catalog_foundation",
        note="Requires a Reddit script/web application and OAuth scopes for the user’s permitted resources.",
    ),
    ConnectorDefinition(
        provider="twitter_x",
        display_name="X / Twitter",
        auth_family="twitter_x",
        capabilities=("read", "search", "index"),
        status="catalog_foundation",
        note="Requires an X developer project and API access tier; quota and billing vary by endpoint.",
    ),
    ConnectorDefinition(
        provider="facebook",
        display_name="Facebook",
        auth_family="meta",
        capabilities=("read_pages", "read_posts"),
        status="catalog_foundation",
        note="Meta permissions are product-specific and commonly require app review; personal timeline access must not be assumed.",
    ),
    ConnectorDefinition(
        provider="telegram",
        display_name="Telegram",
        auth_family="telegram_bot",
        capabilities=("receive_messages", "send_approved_messages"),
        status="implemented_interface",
        setup_mode="bot_token",
    ),
)


def get_connector_definition(provider: str) -> ConnectorDefinition | None:
    return next((definition for definition in CONNECTOR_CATALOG if definition.provider == provider), None)
