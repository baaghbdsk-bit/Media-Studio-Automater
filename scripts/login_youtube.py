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

    print("=" * 65)
    print("🎬 YOUTUBE PERMANENT OAUTH AUTHENTICATION")
    print("=" * 65)
    print("💡 TO MAKE THIS TOKEN PERMANENT (NEVER EXPIRE EVERY 7 DAYS):")
    print("   1. Open Google Cloud Console:")
    print("      https://console.cloud.google.com/apis/credentials/consent?project=neubench-yt")
    print("   2. Under 'Publishing status', click 'PUBLISH APP' (change from 'Testing' to 'In production').")
    print("   3. Confirm the dialog. Even unverified apps in production status grant")
    print("      permanent refresh tokens for your own channel.")
    print("=" * 65)

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            creds = None

    refreshed = False
    if creds and creds.refresh_token:
        print("[YouTube Auth] Testing token refresh...")
        try:
            creds.refresh(Request())
            refreshed = True
            print("[YouTube Auth] ✅ Existing refresh token is valid!")
        except Exception as e:
            print(f"[YouTube Auth] Existing token is invalid or expired ({e}). Re-authenticating...")
            creds = None

    if not refreshed or not creds or not creds.valid:
        print("\n[YouTube Auth] Starting local OAuth authorization server...")
        print("[YouTube Auth] A browser window will open. Sign in to your YouTube channel account.")
        print("[YouTube Auth] If Google displays 'Google hasn't verified this app', click 'Advanced' -> 'Go to ... (unsafe)'.")
        
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
        # Try port 8088, fallback to port 8089 or dynamic free port if occupied
        port_to_use = 8088
        for test_port in [8088, 8089, 8090, 0]:
            try:
                creds = flow.run_local_server(
                    port=test_port,
                    open_browser=True,
                    prompt="consent",
                    access_type="offline"
                )
                break
            except OSError as sock_err:
                if "10048" in str(sock_err) or "address already in use" in str(sock_err).lower():
                    continue
                raise sock_err

    if not creds.refresh_token:
        print("[YouTube Auth] ⚠️ Warning: No refresh token returned. Re-running with explicit consent prompt...")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
        # Try port 8088, fallback to port 8089 or dynamic free port if occupied
        port_to_use = 8088
        for test_port in [8088, 8089, 8090, 0]:
            try:
                creds = flow.run_local_server(
                    port=test_port,
                    open_browser=True,
                    prompt="consent",
                    access_type="offline"
                )
                break
            except OSError as sock_err:
                if "10048" in str(sock_err) or "address already in use" in str(sock_err).lower():
                    continue
                raise sock_err

    # Save to youtube_token.json
    with open(TOKEN_FILE, "w", encoding="utf-8") as token:
        token.write(creds.to_json())
    print(f"\n[YouTube Auth] ✅ Saved authorized credentials to: {TOKEN_FILE}")

    # Verify that the newly generated token can refresh successfully
    try:
        creds.refresh(Request())
        print("[YouTube Auth] ✅ Verified: Refresh token works properly.")
    except Exception as e:
        print(f"[YouTube Auth] ⚠️ Token verification warning: {e}")

    # Automatically update tools/YOUTUBE_TOKEN_BASE64.txt and GitHub secret
    try:
        import base64
        import subprocess
        b64 = base64.b64encode(TOKEN_FILE.read_bytes()).decode("utf-8")
        out_txt = BASE_DIR / "tools" / "YOUTUBE_TOKEN_BASE64.txt"
        out_txt.write_text(b64, encoding="utf-8")
        print(f"[YouTube Auth] ✅ Saved Base64 token to: {out_txt}")

        # Sync to GitHub Secrets via gh CLI
        res = subprocess.run(
            ["gh", "secret", "set", "YOUTUBE_TOKEN_BASE64", "--body", b64],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            print("[YouTube Auth] 🚀 Successfully synced YOUTUBE_TOKEN_BASE64 to GitHub Repository Secrets!")
        else:
            print(f"[YouTube Auth] Note on GitHub secret sync: {res.stderr.strip()}")
    except Exception as ex:
        print(f"[YouTube Auth] Secret auto-sync note: {ex}")

    print("\n[YouTube Auth] 🎉 Logged in successfully! Permanent YouTube OAuth setup is ready.")
    return True

if __name__ == "__main__":
    login_youtube()
