# Unofficial ChatGPT API (Legacy)

This project exposes a minimal HTTP API around an unofficial ChatGPT client
implemented with Playwright browser automation. It launches a FastAPI server
that reuses a single browser session to send prompts and return responses. The
code is small and intentionally simple, but it relies on web automation and a
session token, so it is fragile by nature and may break if the upstream site
changes.

## What it does

- Starts a FastAPI app with two endpoints: `GET /health` and `POST /chat`.
- Initializes a single Playwright-backed ChatGPT client on startup.
- Uses a global lock to serialize requests through the shared browser session.
- Returns the model response text and conversation id.

## Project layout

- `app.py`: FastAPI server and request handling.
- `chatgpt_client.py`: Playwright automation client for the ChatGPT web UI.
- `test_client.py`: Tiny script that posts a sample prompt to the API.
- `.env`: Local environment file for the session token and settings.

## Requirements

Python 3.10+ is recommended.

Key packages used by the app:

- `fastapi`
- `pydantic`
- `python-dotenv`
- `playwright`
- `playwright-stealth`
- An ASGI server such as `uvicorn`

After installing Playwright, install the browser binaries:

```bash
python -m playwright install
```

## Configuration

The server reads configuration from environment variables:

- `UNLIMITEDGPT_SESSION_TOKEN` (required): ChatGPT session token (legacy name).
- `CHATGPT_SESSION_TOKEN` (optional): Alternate session token variable name.
- `UNLIMITEDGPT_HEADLESS` (optional): `"true"` or `"false"`; defaults to
  `false`. When true, runs the browser headless.
- `CHATGPT_BASE_URL` (optional): Defaults to `https://chatgpt.com`.
- `CHATGPT_SESSION_COOKIE_NAMES` (optional): Comma-separated cookie names
  to set with the session token. Defaults to
  `__Secure-next-auth.session-token,next-auth.session-token`.
- `CHATGPT_REAL_BROWSER` (optional): `"true"` to launch a visible, persistent
  Chrome profile (forces `headless=false`).
- `CHATGPT_USER_DATA_DIR` (optional): Path to a persistent profile directory
  used when `CHATGPT_REAL_BROWSER=true`. Defaults to
  `.chatgpt-browser-profile` in the project directory.
- `CHATGPT_BROWSER_CHANNEL` (optional): Playwright browser channel (defaults to
  `chrome` when `CHATGPT_REAL_BROWSER=true`).
- `CHATGPT_IGNORE_AUTOMATION` (optional): `"true"` to drop the default
  `--enable-automation` flag.
- `CHATGPT_LAUNCH_ARGS` (optional): Comma-separated Chromium launch args.
- `CHATGPT_USE_STEALTH` (optional): `"true"` or `"false"`; defaults to `true`.
  When true, applies Playwright stealth scripts to better simulate a real
  browser.
- `CHATGPT_DEFAULT_TIMEOUT` (optional): Default response timeout in seconds
  when requests omit `timeout` (defaults to `240`).

You can place them in `.env` for local use.

## Running the server

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Check health:

```bash
curl http://127.0.0.1:8000/health
```

## Browser view in Docker/Coolify

The Docker image now includes `TigerVNC (Xvnc) + noVNC` and runs without nginx.
Expose two services through Coolify:

- API service: container port `8000` (FastAPI/uvicorn)
- noVNC service: container port `6080` (browser viewer/control)

Once routed, open the noVNC endpoint and use:

- `/vnc.html?autoconnect=1&resize=remote`

Useful env vars:

- `ENABLE_VNC` (default `true`): enable/disable noVNC process.
- `VNC_PASSWORD` (optional): enables password auth in the VNC server.
- `VNC_PORT` (default `5900`): internal VNC TCP port exposed by Xvnc.
- `NOVNC_PORT` (default `6080`): noVNC web endpoint port.
- `APP_PORT` (default `8000`): FastAPI/uvicorn port.
- `DISPLAY_NUM` (default `:99`): X display number used by Xvnc.
- `VNC_GEOMETRY` (default `1920x1080`): virtual desktop size.
- `VNC_DEPTH` (default `24`): virtual desktop color depth.

## Using the API

### `POST /chat`

Request body:

```json
{
  "message": "Hello!",
  "timeout": 240,
  "input_mode": "INSTANT",
  "input_delay": 0.1,
  "conversation_id": "existing-chat-id",
  "temporary_chat": true,
  "images": [
    {
      "name": "photo.jpg",
      "content_type": "image/jpeg",
      "data_base64": "BASE64_ENCODED_IMAGE_BYTES"
    }
  ]
}
```

Fields:

- `message` (string, required): Prompt text.
- `timeout` (int, optional): Max wait time for a response in seconds. Defaults
  to `CHATGPT_DEFAULT_TIMEOUT` (or `240`).
- `input_mode` (string, optional): `"INSTANT"` or `"SLOW"`.
- `input_delay` (float, optional): Delay between keystrokes when using slow
  typing.
- `conversation_id` (string, optional): When set, the request navigates to
  `/c/<conversation_id>` before sending the prompt.
- `temporary_chat` (bool, optional): When `true`, attempts to toggle temporary
  chat before sending. Cannot be combined with `conversation_id`.
- `images` (array, optional): One or more images to attach before sending:
  - `name` (string, required): Filename shown in the composer (for example,
    `receipt.png`).
  - `content_type` (string, optional): MIME type like `image/png`.
  - `data_base64` (string, required): Base64 bytes, or a full data URL such as
    `data:image/png;base64,...`.
- If `conversation_id` is omitted, the client navigates to the base URL to
  start a new chat for the request.

Response body:

```json
{
  "response": "Hi there!",
  "conversation_id": "..."
}
```

### Example client

Run the included test client:

```bash
python test_client.py
```

## Notes and limitations

- This is an unofficial client. It depends on browser automation and may break
  without notice.
- The server uses a single shared browser session and serializes requests with
  a lock, so it is not designed for high concurrency.
- Errors from the upstream client are returned as HTTP 502 responses.

## Troubleshooting

- If startup fails, confirm `UNLIMITEDGPT_SESSION_TOKEN` (or
  `CHATGPT_SESSION_TOKEN`) is set.
- If requests hang or fail, try running with `UNLIMITEDGPT_HEADLESS=false` to
  observe the browser session.
- If you need a more user-like profile, set `CHATGPT_REAL_BROWSER=true` and
  reuse a persistent profile directory.
