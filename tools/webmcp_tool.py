from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from tools.registry import registry, tool_error, tool_result

_DIRECTORY_BASE = "https://webmcp.com"
_RESULT_MARKER = "__LOKI_WEBMCP_RESULT__"
_DEFAULT_TIMEOUT_SECONDS = 45
_MAX_DIRECTORY_RESULTS = 25


def _directory_request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        [(str(key), str(value)) for key, raw in (params or {}).items() for value in (raw if isinstance(raw, (list, tuple)) else [raw]) if value not in (None, "")]
    )
    url = f"{_DIRECTORY_BASE}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "LokiAgent-WebMCP/1.0 (+https://loki.computer)",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"WebMCP directory returned HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"WebMCP directory request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("WebMCP directory returned an unexpected response")
    return payload


def _browser_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        outer = raw
    elif isinstance(raw, str):
        try:
            outer = json.loads(raw)
        except ValueError:
            return {"success": False, "error": "Browser Use returned a non-JSON result"}
    else:
        return {"success": False, "error": "Browser Use returned an unexpected result"}

    if not isinstance(outer, dict):
        return {"success": False, "error": "Browser Use returned an unexpected result"}
    if outer.get("success") is False:
        return {
            "success": False,
            "error": str(outer.get("error") or outer.get("stderr") or "Browser Use execution failed")[:1200],
        }

    output = str(outer.get("output") or "")
    marker_lines = [line for line in output.splitlines() if line.startswith(_RESULT_MARKER)]
    if not marker_lines:
        return {
            "success": False,
            "error": "The active browser did not return a WebMCP result. Verify Browser Use is active and retry.",
        }
    encoded = marker_lines[-1][len(_RESULT_MARKER):]
    try:
        payload = json.loads(encoded)
    except ValueError:
        return {"success": False, "error": "The active browser returned malformed WebMCP data"}
    return payload if isinstance(payload, dict) else {"success": True, "result": payload}


def _run_browser_expression(expression: str, *, session: str = "", task_id: str | None = None,
                            timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    from tools.browser_use_cli import browser_exec

    expression_literal = json.dumps(expression, ensure_ascii=False)
    marker_literal = json.dumps(_RESULT_MARKER)
    code = f'''# Using the page's WebMCP interface\nimport json\n_expression = {expression_literal}\n_response = cdp("Runtime.evaluate", expression=_expression, awaitPromise=True, returnByValue=True, userGesture=True)\nif _response.get("exceptionDetails"):\n    _details = _response.get("exceptionDetails") or {{}}\n    _text = _details.get("text") or ((_details.get("exception") or {{}}).get("description")) or "WebMCP JavaScript execution failed"\n    _payload = {{"success": False, "error": str(_text)[:1200]}}\nelse:\n    _remote = _response.get("result") or {{}}\n    _value = _remote.get("value")\n    if isinstance(_value, dict):\n        _payload = _value\n    else:\n        _payload = {{"success": True, "result": _value}}\nprint({marker_literal} + json.dumps(_payload, ensure_ascii=False))\n'''
    raw = browser_exec(
        code=code,
        session=str(session or ""),
        timeout_s=max(5, min(int(timeout_seconds or _DEFAULT_TIMEOUT_SECONDS), 120)),
        task_id=task_id,
    )
    return _browser_payload(raw)


def _live_list_expression() -> str:
    return r'''(async () => {
  const clean = (value) => {
    try { return JSON.parse(JSON.stringify(value)); }
    catch (_) { return null; }
  };
  const mc = document.modelContext || navigator.modelContext;
  if (mc && typeof mc.getTools === "function") {
    const tools = await mc.getTools();
    return {
      success: true,
      supported: true,
      api_surface: document.modelContext ? "document.modelContext" : "navigator.modelContext",
      url: location.href,
      origin: location.origin,
      title: document.title,
      tool_count: tools.length,
      tools: tools.map((tool) => ({
        name: String(tool.name || ""),
        description: String(tool.description || ""),
        inputSchema: clean(tool.inputSchema) || {type: "object", properties: {}},
        annotations: clean(tool.annotations),
        origin: String(tool.origin || location.origin)
      }))
    };
  }
  const testing = navigator.modelContextTesting;
  if (testing && typeof testing.listTools === "function") {
    const tools = await testing.listTools();
    return {
      success: true,
      supported: true,
      api_surface: "navigator.modelContextTesting",
      url: location.href,
      origin: location.origin,
      title: document.title,
      tool_count: Array.isArray(tools) ? tools.length : 0,
      tools: clean(tools) || []
    };
  }
  return {
    success: true,
    supported: false,
    api_surface: null,
    url: location.href,
    origin: location.origin,
    title: document.title,
    tool_count: 0,
    tools: [],
    message: "This page does not expose a live WebMCP interface in the active browser."
  };
})()'''


def webmcp_list_tools(*, session: str = "", task_id: str | None = None) -> str:
    return tool_result(_run_browser_expression(_live_list_expression(), session=session, task_id=task_id))


def webmcp_lookup(url: str = "", *, session: str = "", task_id: str | None = None) -> str:
    live = _run_browser_expression(_live_list_expression(), session=session, task_id=task_id)
    probe_url = str(url or live.get("url") or "").strip()
    directory: dict[str, Any] | None = None
    if probe_url:
        try:
            directory = _directory_request("/api/v1/lookup", {"url": probe_url})
        except RuntimeError as exc:
            directory = {"ok": False, "error": str(exc)}
    return tool_result({
        "success": bool(live.get("success", True)),
        "url": probe_url or None,
        "live": live,
        "directory": directory,
        "note": "Directory support is stored metadata, not proof that the current browser exposes a live WebMCP API.",
    })


def webmcp_describe_tool(name: str, *, session: str = "", task_id: str | None = None) -> str:
    tool_name = str(name or "").strip()
    if not tool_name:
        return tool_error("tool name is required")
    name_literal = json.dumps(tool_name)
    expression = rf'''(async () => {{
  const clean = (value) => {{ try {{ return JSON.parse(JSON.stringify(value)); }} catch (_) {{ return null; }} }};
  const wanted = {name_literal};
  const mc = document.modelContext || navigator.modelContext;
  if (mc && typeof mc.getTools === "function") {{
    const tools = await mc.getTools();
    const tool = tools.find((candidate) => String(candidate.name || "") === wanted);
    if (!tool) return {{success: false, error: `WebMCP tool '${{wanted}}' is not exposed by the current page`}};
    return {{
      success: true,
      url: location.href,
      tool: {{
        name: String(tool.name || ""),
        description: String(tool.description || ""),
        inputSchema: clean(tool.inputSchema) || {{type: "object", properties: {{}}}},
        annotations: clean(tool.annotations),
        origin: String(tool.origin || location.origin)
      }}
    }};
  }}
  const testing = navigator.modelContextTesting;
  if (testing && typeof testing.listTools === "function") {{
    const tools = await testing.listTools();
    const tool = (Array.isArray(tools) ? tools : []).find((candidate) => String(candidate.name || "") === wanted);
    return tool ? {{success: true, url: location.href, tool: clean(tool)}} : {{success: false, error: `WebMCP tool '${{wanted}}' is not exposed by the current page`}};
  }}
  return {{success: false, error: "This page does not expose a live WebMCP interface in the active browser."}};
}})()'''
    return tool_result(_run_browser_expression(expression, session=session, task_id=task_id))


def _tool_risk_from_live(tool: dict[str, Any] | None) -> tuple[bool, bool]:
    annotations = (tool or {}).get("annotations")
    annotations = annotations if isinstance(annotations, dict) else {}
    read_only = annotations.get("readOnlyHint") is True
    consequential = annotations.get("consequentialHint") is True
    return read_only, consequential


def _directory_tool_kind(url: str, tool_name: str) -> str:
    if not url:
        return ""
    try:
        lookup = _directory_request("/api/v1/lookup", {"url": url})
    except RuntimeError:
        return ""
    site = lookup.get("site") if isinstance(lookup, dict) else None
    tools = site.get("tools") if isinstance(site, dict) else None
    if not isinstance(tools, list):
        return ""
    for item in tools:
        if isinstance(item, dict) and str(item.get("name") or "") == tool_name:
            return str(item.get("kind") or "").strip().lower()
    return ""


def _looks_consequential(tool_name: str) -> bool:
    lowered = tool_name.lower().replace("-", "_")
    consequential_tokens = (
        "checkout", "purchase", "place_order", "submit_order", "confirm_order", "pay", "payment",
        "book", "reserve", "subscribe", "unsubscribe", "delete", "cancel_order", "send_message",
        "send_email", "transfer", "withdraw", "deposit", "sign", "accept_offer",
    )
    return any(token in lowered for token in consequential_tokens)


def _request_consequential_consent(tool_name: str, url: str) -> bool:
    try:
        from tools.approval_prompt import request_elicitation_consent
        answer = request_elicitation_consent(
            f"WebMCP tool '{tool_name}' wants to perform a sensitive action on {url or 'the current website'}.",
            "This action may create a purchase, booking, subscription, message, deletion, or other external commitment. Approve this invocation once to continue.",
            surface="webmcp-transact",
        )
    except Exception:
        return False
    return answer == "accept"


def webmcp_call(name: str, arguments: dict[str, Any] | None = None, *, session: str = "",
                task_id: str | None = None) -> str:
    tool_name = str(name or "").strip()
    if not tool_name:
        return tool_error("tool name is required")
    args = arguments if isinstance(arguments, dict) else {}

    described_raw = webmcp_describe_tool(tool_name, session=session, task_id=task_id)
    try:
        described = json.loads(described_raw)
    except ValueError:
        described = {"success": False, "error": "Could not inspect the live WebMCP tool"}
    if not described.get("success"):
        return tool_result(described)

    live_tool = described.get("tool") if isinstance(described.get("tool"), dict) else {}
    current_url = str(described.get("url") or "")
    read_only, consequential = _tool_risk_from_live(live_tool)
    directory_kind = _directory_tool_kind(current_url, tool_name)
    sensitive = consequential or directory_kind == "transact" or (not read_only and _looks_consequential(tool_name))
    if sensitive and not _request_consequential_consent(tool_name, current_url):
        return tool_error(
            f"WebMCP tool '{tool_name}' was not run because the user did not approve the sensitive action. Do not retry it or pursue the same commitment through another route without explicit user direction.",
            blocked=True,
            kind=directory_kind or "transact",
        )

    name_literal = json.dumps(tool_name)
    args_literal = json.dumps(args, ensure_ascii=False)
    expression = rf'''(async () => {{
  const clean = (value) => {{
    try {{ return JSON.parse(JSON.stringify(value)); }}
    catch (_) {{ return String(value); }}
  }};
  const wanted = {name_literal};
  const input = {args_literal};
  const mc = document.modelContext || navigator.modelContext;
  if (mc && typeof mc.getTools === "function" && typeof mc.executeTool === "function") {{
    const tools = await mc.getTools();
    const tool = tools.find((candidate) => String(candidate.name || "") === wanted);
    if (!tool) return {{success: false, error: `WebMCP tool '${{wanted}}' is not exposed by the current page`}};
    try {{
      const result = await mc.executeTool(tool, input);
      return {{success: true, tool: wanted, url: location.href, result: clean(result)}};
    }} catch (firstError) {{
      try {{
        const result = await mc.executeTool(tool, JSON.stringify(input));
        return {{success: true, tool: wanted, url: location.href, result: clean(result), compatibility: "json-string-input"}};
      }} catch (secondError) {{
        return {{success: false, tool: wanted, error: String(secondError && (secondError.message || secondError) || firstError)}};
      }}
    }}
  }}
  const testing = navigator.modelContextTesting;
  if (testing && typeof testing.executeTool === "function") {{
    try {{
      const result = await testing.executeTool(wanted, input);
      return {{success: true, tool: wanted, url: location.href, result: clean(result), api_surface: "navigator.modelContextTesting"}};
    }} catch (error) {{
      return {{success: false, tool: wanted, error: String(error && (error.message || error))}};
    }}
  }}
  return {{success: false, error: "This page does not expose a callable WebMCP interface in the active browser."}};
}})()'''
    payload = _run_browser_expression(expression, session=session, task_id=task_id)
    if isinstance(payload, dict):
        payload.setdefault("directory_kind", directory_kind or None)
    return tool_result(payload)


def webmcp_search_sites(query: str = "", tool: str = "", kind: str = "", limit: int = 10) -> str:
    normalized_kind = str(kind or "").strip().lower()
    if normalized_kind and normalized_kind not in {"answer", "act", "transact"}:
        return tool_error("kind must be answer, act, or transact")
    try:
        payload = _directory_request(
            "/api/v1/sites",
            {
                "q": str(query or "").strip(),
                "tool": str(tool or "").strip(),
                "kind": normalized_kind,
                "fields": "minimal",
                "limit": max(1, min(int(limit or 10), _MAX_DIRECTORY_RESULTS)),
            },
        )
    except (RuntimeError, ValueError) as exc:
        return tool_error(str(exc))
    return tool_result(payload)


_LOOKUP = {
    "name": "webmcp_lookup",
    "description": "Inspect the current browser page for live WebMCP tools and, when a URL is available, compare that with webmcp.com's read-only directory metadata. Use this near the start of a website task before falling back to DOM clicking. Directory metadata is not proof that the current browser exposes a live WebMCP API.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Optional URL to probe in the WebMCP directory. Omit to use the current browser page."},
            "session": {"type": "string", "description": "Optional Browser Use session name; reuse the same session as browser_exec."},
        },
        "required": [],
    },
}
_LIST = {
    "name": "webmcp_list_tools",
    "description": "List live WebMCP tools exposed by the current page through document.modelContext (or a supported compatibility surface). This reads the real browser page, not only directory metadata.",
    "parameters": {
        "type": "object",
        "properties": {"session": {"type": "string", "description": "Optional Browser Use session name; reuse the same session as browser_exec."}},
        "required": [],
    },
}
_DESCRIBE = {
    "name": "webmcp_describe_tool",
    "description": "Return the live schema, description, annotations, and origin for one WebMCP tool on the current browser page.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "session": {"type": "string", "description": "Optional Browser Use session name."},
        },
        "required": ["name"],
    },
}
_CALL = {
    "name": "webmcp_call",
    "description": "Invoke one WebMCP tool exposed by the current browser page. Prefer this over brittle DOM interaction when an appropriate page tool exists. Sensitive/transact actions are human-gated before execution. Do not use a transact/checkout WebMCP tool to bypass Link spend approval or the user's final purchase authorization.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "arguments": {"type": "object", "additionalProperties": True},
            "session": {"type": "string", "description": "Optional Browser Use session name."},
        },
        "required": ["name", "arguments"],
    },
}
_SEARCH = {
    "name": "webmcp_search_sites",
    "description": "Search webmcp.com's read-only directory for sites and capabilities by site text, tool name, or action category. Use to discover WebMCP-capable retailers/services before browser fallback. Categories: answer=read-only, act=reversible action, transact=sensitive external commitment.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "tool": {"type": "string", "description": "Optional tool-name substring such as cart, product, checkout, booking."},
            "kind": {"type": "string", "enum": ["answer", "act", "transact"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": _MAX_DIRECTORY_RESULTS, "default": 10},
        },
        "required": [],
    },
}

registry.register(name="webmcp_lookup", toolset="webmcp", schema=_LOOKUP,
                  handler=lambda args, **kw: webmcp_lookup(args.get("url", ""), session=args.get("session", ""), task_id=kw.get("task_id")), emoji="🧩")
registry.register(name="webmcp_list_tools", toolset="webmcp", schema=_LIST,
                  handler=lambda args, **kw: webmcp_list_tools(session=args.get("session", ""), task_id=kw.get("task_id")), emoji="🧩")
registry.register(name="webmcp_describe_tool", toolset="webmcp", schema=_DESCRIBE,
                  handler=lambda args, **kw: webmcp_describe_tool(args.get("name", ""), session=args.get("session", ""), task_id=kw.get("task_id")), emoji="🧩")
registry.register(name="webmcp_call", toolset="webmcp", schema=_CALL,
                  handler=lambda args, **kw: webmcp_call(args.get("name", ""), args.get("arguments", {}), session=args.get("session", ""), task_id=kw.get("task_id")), emoji="🧩")
registry.register(name="webmcp_search_sites", toolset="webmcp", schema=_SEARCH,
                  handler=lambda args, **kw: webmcp_search_sites(args.get("query", ""), args.get("tool", ""), args.get("kind", ""), args.get("limit", 10)), emoji="🧩")
