import os
import sys
import base64
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def sync_secret(name: str, value: str):
    try:
        res = subprocess.run(
            ["gh", "secret", "set", name, "--body", value],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            print(f"🚀 Auto-synced {name} to GitHub Secrets!")
        else:
            print(f"Note on {name} GitHub sync: {res.stderr.strip()}")
    except Exception:
        pass

print("="*60)
print("GITHUB ACTIONS SECRETS HELPER (BASE64 EXPORTER & AUTO-SYNC)")
print("="*60)

# 1. Instagram
ig_cookies = BASE_DIR / "instagram_session" / "cookies.json"
if ig_cookies.exists():
    with open(ig_cookies, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        print("\n[SECRET: INSTAGRAM_COOKIES_BASE64]")
        print(f"Length: {len(b64)} chars")
        (BASE_DIR / "tools" / "INSTAGRAM_COOKIES_BASE64.txt").write_text(b64, encoding="utf-8")
        print("Saved to: tools/INSTAGRAM_COOKIES_BASE64.txt")
        sync_secret("INSTAGRAM_COOKIES_BASE64", b64)

# 2. Pinterest
pin_cookies = BASE_DIR / "pinterest_session" / "cookies.json"
if pin_cookies.exists():
    with open(pin_cookies, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        print("\n[SECRET: PINTEREST_COOKIES_BASE64]")
        print(f"Length: {len(b64)} chars")
        (BASE_DIR / "tools" / "PINTEREST_COOKIES_BASE64.txt").write_text(b64, encoding="utf-8")
        print("Saved to: tools/PINTEREST_COOKIES_BASE64.txt")
        sync_secret("PINTEREST_COOKIES_BASE64", b64)

# 3. Threads
threads_cookies = BASE_DIR / "threads_session" / "cookies.json"
if threads_cookies.exists():
    with open(threads_cookies, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        print("\n[SECRET: THREADS_COOKIES_BASE64]")
        print(f"Length: {len(b64)} chars")
        (BASE_DIR / "tools" / "THREADS_COOKIES_BASE64.txt").write_text(b64, encoding="utf-8")
        print("Saved to: tools/THREADS_COOKIES_BASE64.txt")
        sync_secret("THREADS_COOKIES_BASE64", b64)

# 4. YouTube
yt_token = BASE_DIR / "youtube_token.json"
if yt_token.exists():
    with open(yt_token, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        print("\n[SECRET: YOUTUBE_TOKEN_BASE64]")
        print(f"Length: {len(b64)} chars")
        (BASE_DIR / "tools" / "YOUTUBE_TOKEN_BASE64.txt").write_text(b64, encoding="utf-8")
        print("Saved to: tools/YOUTUBE_TOKEN_BASE64.txt")
        sync_secret("YOUTUBE_TOKEN_BASE64", b64)
