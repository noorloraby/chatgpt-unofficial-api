import asyncio
import platform
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
try:
    from playwright_stealth import Stealth
except ImportError:
    Stealth = None


COMPOSER_SELECTOR = "#prompt-textarea[contenteditable=\"true\"]"
SEND_BUTTON_SELECTOR = "button[aria-label=\"Send prompt\"]"
STOP_BUTTON_SELECTORS = [
    "button[aria-label=\"Stop generating\"]",
    "button[aria-label=\"Stop streaming\"]",
]
TEMP_CHAT_ON_SELECTOR = "button[aria-label=\"Turn on temporary chat\"]"
TEMP_CHAT_OFF_SELECTOR = "button[aria-label=\"Turn off temporary chat\"]"
CONVERSATION_TURN_SELECTOR = "article[data-testid^=\"conversation-turn-\"]"
MESSAGE_ROLE_SELECTOR = (
    "div[data-message-author-role=\"assistant\"],"
    " div[data-message-author-role=\"user\"]"
)


@dataclass
class ChatGPTResponse:
    response: str
    conversation_id: Optional[str]
    failed: bool = False


class ChatGPTBrowserClient:
    def __init__(
        self,
        session_token: str,
        headless: bool,
        base_url: str = "https://chatgpt.com",
        cookie_names: Optional[list[str]] = None,
        browser_channel: Optional[str] = None,
        user_data_dir: Optional[str] = None,
        ignore_default_args: Optional[list[str]] = None,
        launch_args: Optional[list[str]] = None,
        use_stealth: bool = True,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session_token = session_token
        self._headless = headless
        self._cookie_names = cookie_names or [
            "__Secure-next-auth.session-token",
            "next-auth.session-token",
        ]
        self._browser_channel = browser_channel
        self._user_data_dir = user_data_dir
        self._ignore_default_args = ignore_default_args
        self._launch_args = launch_args or []
        self._use_stealth = use_stealth
        self._stealth = None
        self._stealth_context_applied = False
        self._stealth_page_ids: set[int] = set()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    @classmethod
    async def create(
        cls,
        session_token: str,
        headless: bool,
        base_url: str = "https://chatgpt.com",
        cookie_names: Optional[list[str]] = None,
        browser_channel: Optional[str] = None,
        user_data_dir: Optional[str] = None,
        ignore_default_args: Optional[list[str]] = None,
        launch_args: Optional[list[str]] = None,
        use_stealth: bool = True,
    ) -> "ChatGPTBrowserClient":
        client = cls(
            session_token=session_token,
            headless=headless,
            base_url=base_url,
            cookie_names=cookie_names,
            browser_channel=browser_channel,
            user_data_dir=user_data_dir,
            ignore_default_args=ignore_default_args,
            launch_args=launch_args,
            use_stealth=use_stealth,
        )
        await client._start()
        return client

    async def close(self) -> None:
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def send_message(
        self,
        message: str,
        timeout: int = 240,
        input_mode: str = "INSTANT",
        input_delay: float = 0.1,
        conversation_id: Optional[str] = None,
        temporary_chat: Optional[bool] = None,
    ) -> ChatGPTResponse:
        await self._ensure_page()
        if conversation_id and temporary_chat:
            raise ValueError(
                "temporary_chat cannot be enabled when conversation_id is set"
            )
        if conversation_id:
            await self._goto_conversation(conversation_id)
            await self._wait_for_conversation_ready(conversation_id)
        else:
            await self._goto_home()
            if temporary_chat is not None:
                await self._set_temporary_chat(temporary_chat)
        await self._wait_for_composer()
        previous_id = await self._get_last_assistant_id()
        await self._fill_prompt(message, input_mode, input_delay)
        await self._click_send()
        response_text = await self._wait_for_response(previous_id, timeout)
        conversation_id = self._get_conversation_id()
        return ChatGPTResponse(response=response_text, conversation_id=conversation_id)

    async def _start(self) -> None:
        self._playwright = await async_playwright().start()
        if self._user_data_dir:
            self._context = await self._playwright.chromium.launch_persistent_context(
                self._user_data_dir,
                headless=self._headless,
                channel=self._browser_channel,
                ignore_default_args=self._ignore_default_args,
                args=self._launch_args,
            )
            pages = self._context.pages
            self._page = pages[0] if pages else await self._context.new_page()
        else:
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                channel=self._browser_channel,
                ignore_default_args=self._ignore_default_args,
                args=self._launch_args,
            )
            self._context = await self._browser.new_context()
            self._page = await self._context.new_page()
        await self._apply_stealth()
        await self._set_session_cookie(self._session_token)
        self._page.set_default_timeout(10000)
        await self._page.goto(self._base_url, wait_until="domcontentloaded")

    async def _set_session_cookie(self, session_token: str) -> None:
        parsed = urlparse(self._base_url)
        if not parsed.scheme or not parsed.hostname:
            raise ValueError("Invalid base_url for ChatGPT client")
        cookie_url = f"{parsed.scheme}://{parsed.hostname}/"
        cookies = []
        for name in self._cookie_names:
            cookies.append(
                {
                    "name": name,
                    "value": session_token,
                    "url": cookie_url,
                    "httpOnly": True,
                    "secure": parsed.scheme == "https",
                    "sameSite": "Lax",
                }
            )
        await self._context.add_cookies(cookies)

    async def _ensure_page(self) -> None:
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
            await self._apply_stealth()
            self._page.set_default_timeout(10000)
            await self._page.goto(self._base_url, wait_until="domcontentloaded")

    async def _goto_conversation(self, conversation_id: str) -> None:
        conversation_id = conversation_id.strip()
        if not conversation_id:
            raise ValueError("conversation_id must be a non-empty string")
        target = f"{self._base_url}/c/{conversation_id}"
        if self._page.url.startswith(target):
            return
        await self._page.goto(target, wait_until="domcontentloaded")

    async def _wait_for_conversation_ready(self, conversation_id: str) -> None:
        target = f"{self._base_url}/c/{conversation_id}"
        try:
            await self._page.wait_for_url(f"{target}*", timeout=15000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Timed out waiting for conversation to load") from exc
        try:
            await self._page.wait_for_selector(COMPOSER_SELECTOR, timeout=15000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("ChatGPT composer not available") from exc
        try:
            await self._page.wait_for_selector(
                f"{CONVERSATION_TURN_SELECTOR}, {MESSAGE_ROLE_SELECTOR}",
                timeout=10000,
            )
        except PlaywrightTimeoutError:
            try:
                await self._page.wait_for_load_state("networkidle", timeout=5000)
            except PlaywrightTimeoutError:
                pass

    async def _goto_home(self) -> None:
        if not self._page.url.startswith(self._base_url):
            await self._page.goto(self._base_url, wait_until="domcontentloaded")
            return
        if "/c/" in self._page.url:
            await self._page.goto(self._base_url, wait_until="domcontentloaded")

    async def _set_temporary_chat(self, enabled: bool) -> None:
        selector = f"{TEMP_CHAT_ON_SELECTOR}, {TEMP_CHAT_OFF_SELECTOR}"
        try:
            await self._page.wait_for_selector(selector, timeout=5000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Temporary chat toggle not found") from exc
        turn_on = self._page.locator(TEMP_CHAT_ON_SELECTOR)
        turn_off = self._page.locator(TEMP_CHAT_OFF_SELECTOR)
        if enabled:
            if await turn_off.is_visible():
                return
            await turn_on.click()
            await self._page.wait_for_selector(TEMP_CHAT_OFF_SELECTOR, timeout=5000)
        else:
            if await turn_on.is_visible():
                return
            await turn_off.click()
            await self._page.wait_for_selector(TEMP_CHAT_ON_SELECTOR, timeout=5000)

    async def _apply_stealth(self) -> None:
        if not self._use_stealth:
            return
        if Stealth is None:
            raise RuntimeError(
                "playwright-stealth is required when stealth is enabled. "
                "Install it with `pip install playwright-stealth`."
            )
        if self._stealth is None:
            self._stealth = Stealth()
        if self._context is not None and not self._stealth_context_applied:
            await self._stealth.apply_stealth_async(self._context)
            self._stealth_context_applied = True
        if self._page is None:
            return
        page_id = id(self._page)
        if page_id in self._stealth_page_ids:
            return
        await self._stealth.apply_stealth_async(self._page)
        self._stealth_page_ids.add(page_id)

    async def _wait_for_composer(self) -> None:
        try:
            await self._page.wait_for_selector(COMPOSER_SELECTOR, timeout=15000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("ChatGPT composer not available; check session token") from exc

    async def _fill_prompt(self, message: str, input_mode: str, input_delay: float) -> None:
        box = self._page.locator(COMPOSER_SELECTOR)
        await box.click()
        modifier = "Meta" if platform.system() == "Darwin" else "Control"
        await self._page.keyboard.press(f"{modifier}+A")
        await self._page.keyboard.press("Backspace")
        if input_mode == "SLOW":
            delay_ms = max(int(input_delay * 1000), 0)
            await self._page.keyboard.type(message, delay=delay_ms)
        else:
            await self._page.keyboard.type(message, delay=0)

    async def _click_send(self) -> None:
        await self._page.wait_for_selector(SEND_BUTTON_SELECTOR, timeout=10000)
        send_button = self._page.locator(SEND_BUTTON_SELECTOR)
        if await send_button.is_disabled():
            await self._page.wait_for_function(
                """
                (selector) => {
                  const button = document.querySelector(selector);
                  return button && !button.disabled;
                }
                """,
                arg=SEND_BUTTON_SELECTOR,
                timeout=10000,
            )
        await send_button.click()

    async def _wait_for_response(self, previous_id: Optional[str], timeout: int) -> str:
        timeout_ms = max(timeout, 1) * 1000
        try:
            await self._page.wait_for_function(
                """
                (prevId) => {
                  const nodes = document.querySelectorAll(
                    'div[data-message-author-role="assistant"]'
                  );
                  if (!nodes.length) return false;
                  const last = nodes[nodes.length - 1];
                  const id = last.getAttribute('data-message-id');
                  const text = (last.textContent || '').trim();
                  if (!text) return false;
                  if (prevId && id === prevId) return false;
                  return true;
                }
                """,
                arg=previous_id,
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Timed out waiting for ChatGPT response") from exc

        end_time = time.monotonic() + timeout
        last_text = ""
        stable_since = time.monotonic()
        while time.monotonic() < end_time:
            text = await self._get_last_assistant_text()
            if text and text != last_text:
                last_text = text
                stable_since = time.monotonic()
            if last_text and not await self._is_generating():
                if time.monotonic() - stable_since >= 1.5:
                    return last_text
            await asyncio.sleep(0.25)
        raise RuntimeError("Timed out waiting for ChatGPT to finish responding")

    async def _get_last_assistant_id(self) -> Optional[str]:
        return await self._page.evaluate(
            """
            () => {
              const nodes = document.querySelectorAll(
                'div[data-message-author-role="assistant"]'
              );
              if (!nodes.length) return null;
              const last = nodes[nodes.length - 1];
              return last.getAttribute('data-message-id');
            }
            """
        )

    async def _get_last_assistant_text(self) -> str:
        return await self._page.evaluate(
            """
            () => {
              const nodes = document.querySelectorAll(
                'div[data-message-author-role="assistant"]'
              );
              if (!nodes.length) return '';
              const last = nodes[nodes.length - 1];
              return (last.textContent || '').trim();
            }
            """
        )

    async def _is_generating(self) -> bool:
        selector = ", ".join(STOP_BUTTON_SELECTORS)
        return (await self._page.query_selector(selector)) is not None

    def _get_conversation_id(self) -> Optional[str]:
        url = self._page.url
        marker = "/c/"
        if marker not in url:
            return None
        tail = url.split(marker, 1)[1]
        return tail.split("?", 1)[0]
