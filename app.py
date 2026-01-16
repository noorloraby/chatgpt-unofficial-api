import asyncio
import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

from chatgpt_client import ChatGPTBrowserClient

load_dotenv()

SESSION_TOKEN_ENV = "UNLIMITEDGPT_SESSION_TOKEN"
SESSION_TOKEN_ENV_FALLBACK = "CHATGPT_SESSION_TOKEN"
HEADLESS_ENV = "UNLIMITEDGPT_HEADLESS"
BASE_URL_ENV = "CHATGPT_BASE_URL"
COOKIE_NAMES_ENV = "CHATGPT_SESSION_COOKIE_NAMES"
REAL_BROWSER_ENV = "CHATGPT_REAL_BROWSER"
USER_DATA_DIR_ENV = "CHATGPT_USER_DATA_DIR"
BROWSER_CHANNEL_ENV = "CHATGPT_BROWSER_CHANNEL"
IGNORE_AUTOMATION_ENV = "CHATGPT_IGNORE_AUTOMATION"
LAUNCH_ARGS_ENV = "CHATGPT_LAUNCH_ARGS"
STEALTH_ENV = "CHATGPT_USE_STEALTH"
DEFAULT_TIMEOUT_ENV = "CHATGPT_DEFAULT_TIMEOUT"
API_KEY_ENV = "CHATGPT_API_KEY"


def _read_default_timeout() -> int:
    raw = os.environ.get(DEFAULT_TIMEOUT_ENV, "").strip()
    if not raw:
        return 240
    try:
        value = int(raw)
    except ValueError:
        return 240
    return max(value, 1)

app = FastAPI()
_client = None
_client_lock = asyncio.Lock()
DEFAULT_TIMEOUT = _read_default_timeout()

# API Key authentication
security = HTTPBearer(auto_error=False)
_api_key = os.environ.get(API_KEY_ENV, "").strip()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> None:
    """Verify the API key if one is configured."""
    if not _api_key:
        # No API key configured - allow all requests
        return
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.credentials != _api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


class ChatRequest(BaseModel):
    message: str
    timeout: int | None = None
    input_mode: Literal["INSTANT", "SLOW"] = "INSTANT"
    input_delay: float = 0.1
    conversation_id: str | None = None
    temporary_chat: bool | None = None


@app.on_event("startup")
async def startup() -> None:
    global _client
    session_token = os.environ.get(SESSION_TOKEN_ENV) or os.environ.get(
        SESSION_TOKEN_ENV_FALLBACK
    )
    if not session_token:
        raise RuntimeError(
            f"Set {SESSION_TOKEN_ENV} (or {SESSION_TOKEN_ENV_FALLBACK}) before starting the server"
        )

    headless = os.environ.get(HEADLESS_ENV, "false").lower() in {"1", "true", "yes"}
    use_real_browser = os.environ.get(REAL_BROWSER_ENV, "false").lower() in {
        "1",
        "true",
        "yes",
    }
    base_url = os.environ.get(BASE_URL_ENV, "https://chatgpt.com")
    cookie_names_raw = os.environ.get(COOKIE_NAMES_ENV, "")
    cookie_names = [name.strip() for name in cookie_names_raw.split(",") if name.strip()]
    user_data_dir = os.environ.get(USER_DATA_DIR_ENV)
    browser_channel = os.environ.get(
        BROWSER_CHANNEL_ENV, "chrome" if use_real_browser else None
    )
    ignore_automation = os.environ.get(IGNORE_AUTOMATION_ENV, "false").lower() in {
        "1",
        "true",
        "yes",
    }
    launch_args_raw = os.environ.get(LAUNCH_ARGS_ENV, "")
    launch_args = [arg.strip() for arg in launch_args_raw.split(",") if arg.strip()]
    use_stealth = os.environ.get(STEALTH_ENV, "true").lower() in {"1", "true", "yes"}
    if use_real_browser:
        headless = False
        if not user_data_dir:
            user_data_dir = os.path.join(os.getcwd(), ".chatgpt-browser-profile")
    ignore_default_args = ["--enable-automation"] if ignore_automation else None
    _client = await ChatGPTBrowserClient.create(
        session_token=session_token,
        headless=headless,
        base_url=base_url,
        cookie_names=cookie_names or None,
        browser_channel=browser_channel,
        user_data_dir=user_data_dir,
        ignore_default_args=ignore_default_args,
        launch_args=launch_args or None,
        use_stealth=use_stealth,
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    global _client
    if _client is None:
        return
    try:
        await _client.close()
    except Exception:
        pass
    _client = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", dependencies=[Depends(verify_api_key)])
async def chat(req: ChatRequest) -> dict:
    if _client is None:
        raise HTTPException(status_code=500, detail="Client not initialized")

    try:
        async with _client_lock:
            response = await _client.send_message(
                req.message,
                timeout=req.timeout if req.timeout is not None else DEFAULT_TIMEOUT,
                input_mode=req.input_mode,
                input_delay=req.input_delay,
                conversation_id=req.conversation_id,
                temporary_chat=req.temporary_chat,
            )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if response is None or response.failed:
        raise HTTPException(status_code=502, detail="No response from ChatGPT")

    return {
        "response": response.response,
        "conversation_id": response.conversation_id,
    }
