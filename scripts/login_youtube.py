import os
import sys
import subprocess
from pathlib import Path

# Auto-switch to local virtual environment Python if present
_BASE_DIR = Path(__file__).resolve().parent.parent
_LOCAL_VENV = _BASE_DIR / "venv" / "Scripts" / "python.exe"
if _LOCAL_VENV.exists() and Path(sys.executable).resolve() != _LOCAL_VENV.resolve():
    try:
        sys.exit(subprocess.call([str(_LOCAL_VENV)] + sys.argv))
    except Exception:
        pass

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtubepartner"
]

BASE_DIR = Path(__file__).resolve().parent.parent
CLIENT_SECRETS_FILE = BASE_DIR / "client_secret.json"
TOKEN_FILE = BASE_DIR / "youtube_token.json"

def login_youtube():
    if not CLIENT_SECRETS_FILE.exists():
        print(f"\n[ERROR] '{CLIENT_SECRETS_FILE.name}' not found in {BASE_DIR}!")
        return False

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        refreshed = False
        if creds and creds.expired and creds.refresh_token:
            print("[YouTube Auth] Refreshing expired token...")
            try:
                creds.refresh(Request())
                refreshed = True
            except Exception as e:
                print(f"[YouTube Auth] Token refresh failed ({e}). Re-authenticating...")
                creds = None

        if not refreshed or not creds or not creds.valid:
            print("\n[YouTube Auth] Starting local OAuth authorization server...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=8088, open_browser=True)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
        print(f"\n[YouTube Auth] ✅ Saved authorized credentials to: {TOKEN_FILE}")

    print("[YouTube Auth] ✅ Logged in successfully!")
    return True

if __name__ == "__main__":
    login_youtube()
