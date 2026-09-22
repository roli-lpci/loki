# LokiAgent WunderCorp SSO + Link integration

Commands:

- `/sso` or `/sso status` — show the local WunderCorp SSO session
- `/sso login` — authenticate through `https://auth.wundercorp.co`
- `/sso logout` — clear/revoke the local WunderCorp SSO session; Link stays connected
- `/link` or `/link status` — show Link connection status
- `/link connect` — ensure WunderCorp SSO, open Link authorization, and poll until connected
- `/link disconnect` — revoke/remove the Link grant without signing out of WunderCorp SSO
- `/link user` — fetch Link user info
- `/link payment-methods` — fetch Link payment methods
- `/wallet` — alias for `/link`

Defaults:

- WunderCorp SSO domain: `https://auth.wundercorp.co`
- Cognito app client: `42s62lgsghpne2r3gf8ret6ojf`
- Local callback: `http://127.0.0.1:48741/auth/callback`
- Link API: `https://link-auth.wundercorp.co`

Optional overrides:

- `LOKI_WUNDERCORP_SSO_DOMAIN`
- `LOKI_WUNDERCORP_SSO_CLIENT_ID`
- `LOKI_WUNDERCORP_SSO_REDIRECT_URI`
- `LOKI_WUNDERCORP_SSO_SCOPE`
- `LOKI_LINK_API_URL`

The WunderCorp SSO refresh/access token state is stored at `$LOKI_HOME/wundercorp-sso.json` with mode `0600`.

`/link connect` is the normal combined flow. It refreshes/reuses WunderCorp SSO when possible, opens WunderCorp SSO only when needed, then opens Link authorization and polls the Link backend until the callback completes.
