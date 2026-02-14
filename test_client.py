import argparse
import json
import os
import sys
import urllib.request
from dotenv import load_dotenv

from response_filter import filter_response


load_dotenv() 
API_URL = os.environ.get("CHATGPT_API_URL", "http://127.0.0.1:8000/chat")
API_KEY = os.environ.get("CHATGPT_API_KEY", "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test prompt to the API.")
    parser.add_argument(
        "message",
        nargs="*",
        default=["What is the capital of France? Reply with one word."],
        help="Prompt text to send.",
    )
    parser.add_argument(
        "--conversation-id",
        dest="conversation_id",
        help="Send the message to an existing conversation id.",
    )
    parser.add_argument(
        "--temporary-chat",
        action="store_true",
        help="Enable temporary chat before sending the message.",
    )
    parser.add_argument(
        "--no-temporary-chat",
        action="store_true",
        help="Disable temporary chat before sending the message.",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        default=API_KEY,
        help="API key for authentication (or set CHATGPT_API_KEY env var).",
    )
    args = parser.parse_args()

    if args.temporary_chat and args.no_temporary_chat:
        raise SystemExit("Choose only one of --temporary-chat or --no-temporary-chat.")

    message = " ".join(args.message)
    payload = {"message": message}
    if args.conversation_id:
        payload["conversation_id"] = args.conversation_id
    if args.temporary_chat:
        payload["temporary_chat"] = True
    elif args.no_temporary_chat:
        payload["temporary_chat"] = False
    data = json.dumps(payload).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    req = urllib.request.Request(
        API_URL,
        data=data,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        body = resp.read().decode("utf-8")
    
    # Parse and filter the response
    result = json.loads(body)
    if "response" in result:
        result["response"] = filter_response(result["response"])
    
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    
    # Print response as plain text (with real newlines)
    print(result.get("response", ""))
    
    # Print metadata if present
    if result.get("conversation_id"):
        print(f"\n--- conversation_id: {result['conversation_id']} ---")


if __name__ == "__main__":
    main()
