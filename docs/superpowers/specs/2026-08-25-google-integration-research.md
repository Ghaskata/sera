# Google integration research — 2026-08-25

Google’s official Gmail scope documentation classifies Gmail user-data scopes by sensitivity and notes that OAuth verification may be required; restricted-scope server storage can trigger a security assessment. The first Gmail integration should therefore remain read-only and should not request send/modify permissions.

Google’s official Drive authorization documentation says the app must declare scopes in the Cloud Console and request the specific scopes in code. `drive.readonly` permits viewing and downloading all Drive files but is classified as restricted. Sera should disclose this clearly, keep the first implementation read-only, and request the narrowest scope needed for the feature.

Sources:
- https://developers.google.com/workspace/gmail/api/auth/scopes
- https://developers.google.com/workspace/drive/api/guides/api-specific-auth
- https://developers.google.com/identity/protocols/oauth2/web-server
