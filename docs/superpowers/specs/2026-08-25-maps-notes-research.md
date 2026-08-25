# Google Maps and Notes research — 2026-08-25

## Google Maps

The official Places API (New) accepts REST requests and supports API-key and OAuth authentication. The documented Place Details endpoint is `https://places.googleapis.com/v1/places/{PLACE_ID}` and Text Search/Nearby Search are available as separate operations. For Sera, Maps should be an API-key-backed lookup connector, not an OAuth account connector; the key must be restricted and Places API billing must be enabled.

Source: https://developers.google.com/maps/documentation/places/web-service/overview

## Google Notes / Keep

The official Google Keep API is a REST API for enterprise administrators to create, list, delete, download attachments, and mutate permissions of Keep notes. Authorization supports domain-wide delegation with a service account or an OAuth client ID, and an OAuth client ID can be used for enterprise apps where an administrator approves access to authenticated users’ Keep data. This is not equivalent to ordinary consumer Google login. Sera should therefore implement a clearly gated Google Keep connector foundation and require Workspace admin-approved OAuth/domain-wide delegation before syncing notes.

Source: https://developers.google.com/workspace/keep/api/guides

## Exact endpoints and scopes

The official Keep `notes.list` endpoint is `GET https://keep.googleapis.com/v1/notes` and supports `pageSize`, `pageToken`, and `filter`. Its read-only OAuth scope is `https://www.googleapis.com/auth/keep.readonly`; full `https://www.googleapis.com/auth/keep` is also supported for broader access. Sera must use the read-only scope and report that the API is intended for Workspace/enterprise administration use.

Source: https://developers.google.com/workspace/keep/api/reference/rest/v1/notes/list
