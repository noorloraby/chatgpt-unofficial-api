# ChatGPT Integration Review (Current Unofficial API)

This file captures how the project connects to the ChatGPT interface, the
linking approach used, and the exact values and workflow observed in code. It is
based on `app.py` and `chatgpt_client.py` only.

## Integration approach

- **Client library**: Playwright automation (`chatgpt_client.py`).
- **Stealth mode**: Playwright stealth scripts enabled by default
  (`CHATGPT_USE_STEALTH`, set to `false` to disable).
- **Auth linking**: Reuses an existing ChatGPT web session via
  `UNLIMITEDGPT_SESSION_TOKEN` or `CHATGPT_SESSION_TOKEN` (environment
  variables).
- **Runtime mode**: Headless or visible browser controlled via
  `UNLIMITEDGPT_HEADLESS` environment variable.
- **Base URL**: Defaults to `https://chatgpt.com` (override with
  `CHATGPT_BASE_URL`).

## Startup workflow

1. Load environment variables (`dotenv`).
2. Read `UNLIMITEDGPT_SESSION_TOKEN` (or `CHATGPT_SESSION_TOKEN`) and fail fast
   if missing.
3. Read `UNLIMITEDGPT_HEADLESS` (defaults to `false`) and instantiate the
   Playwright client with cookies set on the ChatGPT domain.

## Request flow to ChatGPT

- API endpoint: `POST /chat`.
- Requests are serialized using a single global lock because the browser session
  is shared.
- The server uses `asyncio.to_thread` to run the blocking send in a thread.
- Core call into ChatGPT:
  - Method: `_client.send_message(...)`
  - Arguments passed:
    - `message`: required prompt text from request.
    - `timeout`: default 240 seconds.
    - `input_mode`: `"INSTANT"` or `"SLOW"` (default `"INSTANT"`).
    - `input_delay`: default `0.1` seconds between keystrokes (used for slow
      typing).
- UI selectors used:
  - Composer: `#prompt-textarea[contenteditable="true"]`
  - Send: `button[aria-label="Send prompt"]`
  - Assistant message: `div[data-message-author-role="assistant"]`

## Response handling from ChatGPT

- Expected response object fields used:
  - `response`: the model output text returned to the API caller.
  - `conversation_id`: returned to the API caller.
  - `failed`: if true (or response is `None`), the API returns HTTP 502.

## Shutdown behavior

- On shutdown, the server calls `_client.close()` to close Playwright resources.

## Values and interfaces to compare with new ChatGPT interface

- Session token auth:
  - Environment variable names: `UNLIMITEDGPT_SESSION_TOKEN` or
    `CHATGPT_SESSION_TOKEN`.
  - Assumes a web-session token from the ChatGPT website.
  - Cookie names set: `__Secure-next-auth.session-token` and
    `next-auth.session-token` by default (override via
    `CHATGPT_SESSION_COOKIE_NAMES`).
- Headless browser mode:
  - Environment variable name: `UNLIMITEDGPT_HEADLESS`.
  - Accepted values: `"1"`, `"true"`, `"yes"` (case-insensitive).
- Playwright stealth mode:
  - Environment variable name: `CHATGPT_USE_STEALTH`.
  - Accepted values: `"1"`, `"true"`, `"yes"` (case-insensitive).
  - Defaults to enabled.
- Default response timeout:
  - Environment variable name: `CHATGPT_DEFAULT_TIMEOUT`.
  - Value is seconds; defaults to `240` when unset/invalid.
- Message input behavior:
  - `input_mode`: `"INSTANT"` or `"SLOW"`.
  - `input_delay`: float seconds between keystrokes for `"SLOW"` mode.
- Per-request conversation control:
  - `conversation_id`: navigate to `/c/<conversation_id>` before sending.
  - `temporary_chat`: toggle temporary chat on/off before sending.
  - If `conversation_id` is omitted, the client navigates to the base URL to
    start a fresh chat for the request.
- Response fields expected:
  - `response` (text).
  - `conversation_id`.
  - `failed` (boolean).

## Notes

- This integration depends on the ChatGPT web UI (browser automation), not the
  official API. The DOM or workflow changes can break it.
- The single-session lock means only one active request at a time.
