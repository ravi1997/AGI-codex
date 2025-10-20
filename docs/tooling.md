# Tooling Overview

This project now includes two opt-in tools that enable controlled interaction
with browsers and HTTP APIs. Both tools are disabled by default and require
explicit configuration updates before they are exposed to the planner.

The shared tool configuration also controls whether the sandboxed terminal is
permitted to run networking commands:

```yaml
tools:
  allow_network: true
  network_allowlist:
    - curl
    - wget
```

When `allow_network` is `false`, commands such as `curl` and `wget` are rejected
outright. When `allow_network` is `true`, the optional `network_allowlist`
restricts which networking binaries are usable, allowing you to limit access to
trusted tooling.

## Browser Automation

The `browser_automation` tool wraps [Playwright](https://playwright.dev/) to
launch a headless Chromium instance. It can read HTML files from within the
sandbox, interact with simple selectors, extract text, and capture full-page
screenshots.

### Configuration

```yaml
tools:
  browser:
    enabled: true
    headless: true
    default_timeout_ms: 10000
    allowed_origins:
      - "https://example.internal/"
```

- `enabled`: toggles registration in the tool registry.
- `headless`: controls whether Chromium is launched without a GUI.
- `default_timeout_ms`: per-operation timeout passed to Playwright.
- `allowed_origins`: optional allow-list of URL prefixes when navigating over
  HTTP/HTTPS. File URLs are always restricted to the sandbox directory.

The tool expects JSON instructions with the following shape:

```json
{
  "url": "file:///workspace/sandbox/demo.html",
  "wait_for_selector": "#status",
  "extract_text": "#status",
  "screenshot": "artifacts/demo.png",
  "actions": [
    {"type": "click", "selector": "#submit"}
  ]
}
```

> **Note:** Playwright and the corresponding browser binaries must be installed
> (`pip install playwright && playwright install chromium`) on the runtime
> environment for this tool to be operational.

## REST Client

The `rest_client` tool performs HTTP requests while enforcing a host allow-list
and sandboxed file persistence.

### Configuration

```yaml
tools:
  rest:
    enabled: true
    default_timeout_sec: 5.0
    allowed_hosts:
      - "127.0.0.1"
      - "internal.api"
    default_headers:
      User-Agent: "agi-core/0.1"
    auth_token: "Bearer example-token"
```

- `allowed_hosts`: hosts that the tool may contact; requests to any other host
  are rejected.
- `default_headers`: applied to every request, with per-call overrides.
- `auth_token`: optional bearer token injected when the caller does not specify
  an `Authorization` header.
- `default_timeout_sec`: request timeout (can be overridden per invocation).

Example invocation payload:

```json
{
  "method": "GET",
  "url": "http://127.0.0.1:8000/status",
  "params": {"verbose": "1"},
  "save_to": "responses/status.json"
}
```

The tool emits a JSON-encoded summary containing the status code, response
headers, the first 4KB of the body, and the sandbox-relative path of any saved
artifact.

## Planner Context

Once enabled, both tools are registered with the `ToolRegistry`. Their
descriptions are surfaced through the planner context, allowing the planning
pipeline to choose the appropriate capability when constructing plans.
