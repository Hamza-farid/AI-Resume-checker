"""
🔌 API CONNECTION TEST (tiny, almost free)

WHAT
  • Step 1: checks the KIND of key in .env (never prints the key)
  • Step 2: sends "Hi" to Claude and prints the reply

WHY
  • Quick way to know if the key works BEFORE running real evaluations
  • Costs almost nothing (a few tokens)

KEY TYPES
  sk-ant-api...  ✅ API key       → from console.anthropic.com → works in apps
  sk-ant-oat...  ❌ OAuth token   → from `claude setup-token` → only for Claude Code

RUN
  python tests/test_api_connection.py
"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import anthropic  # noqa: E402

import config  # noqa: E402

# ✏️ Change the message if you like
PROMPT = "Hi! Reply in one short sentence."


def main() -> None:
    key = config.CLAUDE_API_KEY or ""

    # Step 1: key type (only the prefix is checked, the key is never printed)
    print("\n🔑 Step 1: checking the key in .env")
    if not key:
        print("   ❌ No key found. Add a line like  claude=sk-ant-api...  to .env")
        return
    if key.startswith("sk-ant-oat"):
        print("   ❌ This is a Claude Code subscription token (from `claude setup-token`), not an API key.")
        print("      👉 Get an API key: console.anthropic.com → API Keys → Create Key")
        print("      👉 Put it in .env as:  claude=sk-ant-api...")
        return
    if not key.startswith("sk-ant-api"):
        print("   ⚠️ Unknown key format. API keys start with  sk-ant-api")
    else:
        print("   ✅ Looks like an API key")

    # Step 2: tiny real call
    print(f"\n📨 Step 2: sending \"{PROMPT}\" to {config.CLAUDE_MODEL}")
    client = anthropic.Anthropic(api_key=key, timeout=config.CLAUDE_TIMEOUT_SEC, max_retries=config.CLAUDE_MAX_RETRIES)
    try:
        message = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=200,
            thinking={"type": "disabled"},  # no thinking needed for "hi" → cheapest
            messages=[{"role": "user", "content": PROMPT}],
        )
    except anthropic.AuthenticationError as e:
        print(f"   ❌ Key rejected (401): {e}")
        return
    except anthropic.NotFoundError as e:
        print(f"   ❌ Model '{config.CLAUDE_MODEL}' not found: {e}")
        return
    except anthropic.APIConnectionError as e:
        print(f"   ❌ No connection: {e}")
        return
    except anthropic.APIStatusError as e:
        print(f"   ❌ API error {e.status_code}: {e}")
        return

    reply = next((b.text for b in message.content if b.type == "text"), "(no text)")
    print(f"   ✅ Claude says: {reply}")
    print(f"   🔢 Tokens: in {message.usage.input_tokens} / out {message.usage.output_tokens}")
    print("\n🎉 The key works! You can now run  python tests/test_milestone4.py")


if __name__ == "__main__":
    main()
