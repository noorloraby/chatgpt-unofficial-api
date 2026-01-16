# ChatGPT UI Update Notes (Playwright Review)

Observed on https://chatgpt.com/ via Playwright. This documents UI elements
relevant to browser automation and the updates needed for the current
Playwright-based integration.

## Current UI elements (automation-relevant)

- **Domain**: `https://chatgpt.com/` (not `chat.openai.com`).
- **Composer container**: `form[data-type="unified-composer"]`.
- **Prompt input**:
  - Visible editor: `div#prompt-textarea[contenteditable="true"]` (ProseMirror).
  - Hidden fallback: `textarea[name="prompt-textarea"]` with `display: none`.
- **Send button**:
  - Appears after text is entered.
  - Selector: `button[aria-label="Send prompt"]`.
  - No `data-testid` observed for send.
- **Attachment button**:
  - Selector: `button[data-testid="composer-plus-btn"][aria-label="Add files and more"]`.
  - Hidden file input: `input[type="file"][multiple]` inside the composer.
- **Voice controls**:
  - `button[aria-label="Dictate button"]`.
  - `button[aria-label="Start voice mode"]`.
- **Model selector**:
  - Selector: `button[data-testid="model-switcher-dropdown-button"]`.
  - Example label: "Model selector, current model is 5.2".
- **Temporary chat toggle**:
  - `button[aria-label="Turn on temporary chat"]`.
- **Group chat**:
  - `button[aria-label="Start a group chat"]`.
- **Conversation URLs**:
  - Chat history links use `/c/<uuid>` paths.
- **Message containers**:
  - Role-based: `div[data-message-author-role="assistant"]` and
    `div[data-message-author-role="user"]`.
  - Turn wrapper: `article[data-testid="conversation-turn-<n>"]`.

## Likely required updates for this project

1. **Base URL change**
   - If `UnlimitedGPT` still targets `chat.openai.com`, update to
     `https://chatgpt.com/`.

2. **Prompt input selector**
   - If the client types into a `textarea`, update to use the visible
     `div#prompt-textarea[contenteditable="true"]`.
   - The fallback `textarea[name="prompt-textarea"]` is hidden and will not
     receive user-visible input.

3. **Send button selector**
   - Update send logic to wait for and click
     `button[aria-label="Send prompt"]` after text is present.
   - Do not rely on a `data-testid` for send (none observed).

4. **Composer structure changes**
   - The composer is now a unified form (`data-type="unified-composer"`).
   - DOM classes are heavily hashed; avoid class-based selectors.

5. **Optional features that can interfere**
   - Voice mode and dictate buttons are present in the composer area; ensure
     automation does not click them accidentally.
   - The model selector and temporary chat toggles are in the header; avoid
     unintended clicks that switch model or conversation type.

## Gaps to verify (not observed in this session)

- **Stop/Cancel generation button**: identify its selector during streaming.
- **Auth/session token changes**: confirm whether the session token name or
  cookie storage changed for `chatgpt.com`.

## Suggested next steps

- Keep the client selectors aligned with the composer, send button, and message
  containers listed above.
- Validate with a real send/receive cycle and record any changes to stop or
  streaming controls.
