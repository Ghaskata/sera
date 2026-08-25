# Collaboration and meeting integration research — 2026-08-25

## Slack

Slack’s official documentation describes OAuth v2 installation with granular bot and user scopes. The flow is authorize → redirect with a temporary code → exchange through `oauth.v2.access`; the redirect URI must use HTTPS and must match between authorization and token exchange. Slack message history is accessed through conversation APIs and requires the relevant channel/history permissions.

Source: https://docs.slack.dev/authentication/installing-with-oauth/

## Microsoft Teams

Microsoft’s official documentation exposes Teams meeting transcripts and recordings through Microsoft Graph. Transcript access requires delegated or application permissions, and tenant administrator controls can disable transcript access or speaker attribution. Teams can send change notifications when transcripts/recordings become available; the transcript content is available as `.vtt`. Transcript APIs are metered and tenant/application permissions must be configured explicitly.

Source: https://learn.microsoft.com/en-us/microsoftteams/platform/graph-api/meeting-transcripts/overview-transcripts

## Implementation boundary

Sera can safely add provider OAuth contracts and read-only sync modules, but Slack and Teams require provider-specific client credentials, redirect URIs, workspace/tenant consent, and secrets. Google Calendar can use the existing Google OAuth family with a read-only calendar scope. Google Meet transcript retrieval should use Meet/Drive-specific permissions and be treated as an artifact sync after a meeting; it is not equivalent to simply reading Calendar events.

## Google Meet

The official Google Meet `conferenceRecords.list` reference uses `GET https://meet.googleapis.com/v2/conferenceRecords`, supports `pageSize`, `pageToken`, and `filter`, and lists the required scopes as `https://www.googleapis.com/auth/meetings.space.created` or `https://www.googleapis.com/auth/meetings.space.readonly`. Sera’s Meet connector uses the read-only scope and then lists transcripts and transcript entries for completed conference records.

Source: https://developers.google.com/workspace/meet/api/reference/rest/v2/conferenceRecords/list

## Microsoft Graph transcript details

The official Microsoft Graph `list transcripts` reference identifies `OnlineMeetingTranscript.Read.All` as the least-privileged delegated permission for work/school accounts. Personal Microsoft accounts are not supported for that API. Application permissions require tenant-level application access policy and administrator consent. This makes Teams transcript sync a tenant-admin-dependent feature; the backend should fail gracefully when transcript permission is unavailable.

Source: https://learn.microsoft.com/en-us/graph/api/onlinemeeting-list-transcripts?view=graph-rest-1.0
