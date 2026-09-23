# Guardian Search MCP integration

LokiAgent 0.21.22 connects to Guardian Search MCP out of the box:

```text
https://mcp.guardianbrowser.sh/v1
```

The first-party server is defined in `loki_cli/config_defaults.py` as `guardian_search`. User configuration deep-merges over the default, so it can be disabled or replaced in `~/.loki/config.yaml` without patching source.

When the remote service is available, registered MCP tools are exposed to the model as:

```text
mcp__guardian_search__search_web
mcp__guardian_search__search_shopping
mcp__guardian_search__discover_sites
mcp__guardian_search__finance_quote
```

## Shopping routing

`/go shopping` now follows a deterministic discovery policy:

1. If the user names a merchant, probe that merchant with `webmcp_lookup(url=...)`. URL-only lookup is directory-only and does not launch Browser Use.
2. If no merchant is specified, call `mcp__guardian_search__search_shopping` first.
3. Use `mcp__guardian_search__discover_sites` when the task is to find destination sites rather than products.
4. Use `webmcp_search_sites` only for WebMCP capability discovery, never as a product-search engine.
5. If Guardian Search is unavailable or returns nothing useful, use Loki's normal `web_search` tool (keyless/DuckDuckGo when configured).
6. Never drive Google, Bing, DuckDuckGo, Yahoo, or other search-result pages with `browser_exec`.
7. Browser Use is reserved for a known merchant/service when live WebMCP does not expose the required action.
8. Checkout still uses Link spend approval and secure model-blind payment fill.

The workflow has a two-call discovery budget before it chooses a viable merchant or asks one concise question. Guardian MCP is optional at runtime: shopping still starts and uses Loki's regular `web_search` if the remote server is offline, while browser navigation stays restricted to known destination websites.

## Verify

After Guardian backend deployment:

```bash
loki mcp test guardian_search
```

Then:

```text
/go shopping
buy me some paper towels, pick a store
```

The trace should start with Guardian Search MCP rather than browser-based DuckDuckGo/Bing searching.
