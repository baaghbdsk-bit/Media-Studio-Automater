import os
import sys
import base64
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

print("="*60)
print("GITHUB ACTIONS SECRETS HELPER (BASE64 EXPORTER)")
print("="*60)

# 1. Instagram
ig_cookies = BASE_DIR / "instagram_session" / "cookies.json"
if ig_cookies.exists():
    with open(ig_cookies, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        print("\n[SECRET: INSTAGRAM_COOKIES_BASE64]")
        print(f"Length: {len(b64)} chars")
        # Save to file for easy copying
        (BASE_DIR / "tools" / "INSTAGRAM_COOKIES_BASE64.txt").write_text(b64, encoding="utf-8")
        print("Saved to: tools/INSTAGRAM_COOKIES_BASE64.txt")

# 2. Pinterest
pin_cookies = BASE_DIR / "pinterest_session" / "cookies.json"
if pin_cookies.exists():
    with open(pin_cookies, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        print("\n[SECRET: PINTEREST_COOKIES_BASE64]")
        print(f"Length: {len(b64)} chars")
        (BASE_DIR / "tools" / "PINTEREST_COOKIES_BASE64.txt").write_text(b64, encoding="utf-8")
        print("Saved to: tools/PINTEREST_COOKIES_BASE64.txt")

# 3. Threads
threads_cookies = BASE_DIR / "threads_session" / "cookies.json"
if not threads_cookies.exists() and ig_cookies.exists():
    # Instagram and Threads share cookies
    with open(ig_cookies, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        print("\n[SECRET: THREADS_COOKIES_BASE64 (Using Instagram session)]")
        (BASE_DIR / "tools" / "THREADS_COOKIES_BASE64.txt").write_text(b64, encoding="utf-8")
        print("Saved to: tools/THREADS_COOKIES_BASE64.txt")
elif threads_cookies.exists():
    with open(threads_cookies, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        print("\n[SECRET: THREADS_COOKIES_BASE64]")
        (BASE_DIR / "tools" / "THREADS_COOKIES_BASE64.txt").write_text(b64, encoding="utf-8")
        print("Saved to: tools/THREADS_COOKIES_BASE64.txt")

# 4. YouTube
yt_token = BASE_DIR / "youtube_token.json"
if yt_token.exists():
    with open(yt_token, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        print("\n[SECRET: YOUTUBE_TOKEN_BASE64]")
        print(f"Length: {len(b64)} chars")
        (BASE_DIR / "tools" / "YOUTUBE_TOKEN_BASE64.txt").write_text(b64, encoding="utf-8")
        print("Saved to: tools/YOUTUBE_TOKEN_BASE64.txt")
