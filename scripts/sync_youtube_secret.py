"""Sync the locally generated YouTube OAuth token to the GitHub repo secret.

Uses the GitHub credential already stored in Windows Git Credential Manager,
so no interactive `gh auth login` is needed.
"""
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = BASE_DIR / "tools" / "YOUTUBE_TOKEN_BASE64.txt"
SECRET_NAME = "YOUTUBE_TOKEN_BASE64"


def _git_credential_token() -> str:
    """Read the stored GitHub PAT via Git Credential Manager."""
    payload = "protocol=https\nhost=github.com\n\n"
    try:
        result = subprocess.run(
            ["git", "credential", "fill"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:
        raise RuntimeError(f"Could not read Git credentials: {exc}")
    for line in result.stdout.splitlines():
        if line.startswith("password="):
            token = line.split("=", 1)[1].strip()
            if token:
                return token
    raise RuntimeError(
        "No GitHub credential found on this machine. "
        "Either run `git credential fill` once, or set the GH_TOKEN environment variable."
    )


def sync_secret(b64: str | None = None) -> tuple[bool, str]:
    """Write b64 (or read it from disk) to the GitHub secret. Returns (ok, message)."""
    if b64 is None:
        if not TOKEN_FILE.exists():
            return False, f"Token file missing: {TOKEN_FILE}"
        b64 = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not b64:
        return False, "Token file is empty."

    try:
        token = (os.environ.get("GH_TOKEN") or "").strip() or _git_credential_token()
    except RuntimeError as exc:
        return False, str(exc)

    env = dict(os.environ)
    env["GH_TOKEN"] = token
    try:
        result = subprocess.run(
            ["gh", "secret", "set", SECRET_NAME, "--body", b64],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(BASE_DIR),
            timeout=60,
        )
    except Exception as exc:
        return False, f"Could not run gh: {exc}"

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return False, (
            f"GitHub secret sync failed: {detail}. "
            f"Set {SECRET_NAME} manually from {TOKEN_FILE}."
        )
    return True, f"GitHub secret {SECRET_NAME} updated."


def main() -> int:
    ok, message = sync_secret()
    print(f"[sync] {message}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
