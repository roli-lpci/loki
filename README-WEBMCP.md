# WebMCP in LokiAgent

LokiAgent now has a first-class `webmcp` toolset for structured browser-page actions.

## User experience

`/go shopping` automatically enables:

- `terminal`
- `browser`
- `webmcp`
- `link-wallet`

The shopping workflow prefers a structured path before DOM automation:

1. `webmcp_lookup` / `webmcp_list_tools` on the live retailer page.
2. `webmcp_call` for appropriate product search, cart, form, or other exposed actions.
3. `browser_exec` when the site does not expose the needed WebMCP tool.
4. Link spend approval and `link_checkout_fill` for model-blind one-time payment credentials.
5. Human handoff for CAPTCHA, identity checks, or logins that cannot be completed safely by the agent.

WebMCP is also enabled by `/ops` so business web applications can expose structured actions to the operations workflow.

## Model-visible tools

- `webmcp_lookup`
- `webmcp_list_tools`
- `webmcp_describe_tool`
- `webmcp_call`
- `webmcp_search_sites`

`webmcp_search_sites` and the directory half of `webmcp_lookup` use the read-only JSON API at `https://webmcp.com/api/v1/...`.

Live page execution uses the current WebMCP surface (`document.modelContext`) and supports compatibility fallbacks for older/preview implementations. Loki performs discovery and execution inside the current Browser Use tab through CDP, so WebMCP actions share the same cookies, login state, cart, and visible page as `browser_exec`.

## Sensitive actions

WebMCP tool metadata is inspected before invocation. A tool is treated as sensitive when one of the following is true:

- its live WebMCP annotations set `consequentialHint: true`;
- the webmcp.com directory classifies it as `transact`;
- its name strongly indicates an irreversible external commitment such as checkout, purchase, booking, payment, subscription, deletion, transfer, or sending a message.

Sensitive calls use Loki's human approval transport and fail closed if approval cannot be obtained.

For `/go shopping`, WebMCP must not be used to bypass Link spend approval. Product discovery and cart actions can be WebMCP-native; payment credentials remain model-blind and are injected by the trusted Link checkout bridge.

## Tool configuration

WebMCP is intentionally default-off outside workflows. It can be enabled manually with Loki's normal tool configuration interface. It remains a direct model-facing toolset when enabled rather than being hidden behind progressive Tool Search.

## Browser support

A site appearing in the webmcp.com directory does not guarantee the currently active browser exposes a live WebMCP API. Loki therefore keeps directory discovery and live capability detection separate and falls back to normal browser automation when needed.

Current WebMCP references:

- https://github.com/webmachinelearning/webmcp
- https://webmcp.com/api-docs
