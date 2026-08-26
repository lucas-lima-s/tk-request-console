# Describing a protocol in config

`tk-request-console` does not hardcode any endpoint shape. Everything about how a
request is built lives under the `endpoint` section of `config.json` (see
`config.example.json` for the full annotated shape), and the GUI/CLI just fill in
values for whatever placeholders you declare.

## The building blocks

- **`path_template`** — a Python format string. Any `{name}` inside it must be one
  of the known placeholders (see below).
- **`query`** — an ordered map of query-parameter name to a format string, rendered
  the same way as `path_template`. A rendered value that comes out empty is dropped
  from the URL when `omit_empty_params` is `true`.
- **`format_codes`** — maps the human-readable names shown in the Format dropdown
  (`text`, `json`, ...) to whatever wire value your service expects. Unknown names
  pass through unchanged, so you can also type a raw code directly.
- **`bool_style`** — how boolean fields (currently just "was the payload base64
  encoded") render as text: `true_false` (`true`/`false`), `one_zero` (`1`/`0`), or
  `yes_no` (`yes`/`no`).
- **`token_mode`** — how the token field is normalized before it goes on the wire:
  - `auto` (default): blank becomes absent; a purely numeric string becomes an
    integer; a `0x...`/`0X...` hex string is re-cased to `0x` + uppercase digits;
    anything else is uppercased.
  - `upper`: always uppercase, blank becomes absent.
  - `int`: always parsed as an integer; raises on anything non-numeric.
  - `raw`: sent exactly as typed, blank becomes absent.

### Known placeholders

`host`, `port`, `group`, `action`, `token`, `format`, `timeout`, `encoded`,
`timestamp`. Using anything else in `path_template` or in a `query` value is
rejected at config-load time, naming the offending placeholder.

## Worked example 1 — a JSON REST endpoint

A service that expects `POST /api/{group}/{action}` with the token, format, and a
millisecond timestamp as query parameters (this is the config shipped as
`config.example.json`, and it's what the bundled echo server understands):

```json
{
  "endpoint": {
    "path_template": "/api/{group}/{action}",
    "query": {
      "token": "{token}",
      "format": "{format}",
      "timeout": "{timeout}",
      "encoded": "{encoded}",
      "_ts": "{timestamp}"
    },
    "format_codes": { "text": 0, "json": 1, "xml": 2, "form": 3 },
    "bool_style": "true_false",
    "token_mode": "auto"
  }
}
```

Filling in host `127.0.0.1`, group `echo`, action `ping`, an empty token and format
`text` builds:

```
http://127.0.0.1:8080/api/echo/ping?format=0&timeout=-1&encoded=false&_ts=1717000000000
```

(the `token` parameter is entirely absent because the token field was empty and
`omit_empty_params` is `true`).

## Worked example 2 — a query-param RPC style

Some legacy-flavoured services put everything, including the routing info, in the
query string instead of the path. That's just a different `path_template` and
`query` map — nothing else about the app changes:

```json
{
  "endpoint": {
    "path_template": "/rpc",
    "query": {
      "group": "{group}",
      "action": "{action}",
      "token": "{token}",
      "fmt": "{format}",
      "async": "{encoded}"
    },
    "format_codes": { "param": 2, "string": 6, "xml": 1, "json": 4 },
    "bool_style": "one_zero",
    "token_mode": "int"
  }
}
```

With group `orders`, action `list`, token `77`, format `param` and the base64
checkbox off, this builds:

```
http://127.0.0.1:8080/rpc?group=orders&action=list&token=77&fmt=2&async=0
```

Notice `token_mode: "int"` here: a non-numeric token would raise instead of being
silently uppercased, which is the right failure mode for a service that only
accepts integer tokens.

## How the three settings interact

`format_codes`, `bool_style` and `token_mode` are independent knobs applied in this
order when a request is built: the token is normalized first (`token_mode`), then
the format name is looked up (`format_codes`), then the base64 flag is rendered as
text (`bool_style`) — and only then are `path_template` and every `query` value
filled in and percent-encoded. Because they're independent, you can mix and match:
keep `token_mode: "auto"` with a `one_zero` bool style, or `int` tokens with
`yes_no` booleans — whatever your target service expects.
