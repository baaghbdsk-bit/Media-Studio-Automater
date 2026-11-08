import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from playwright.sync_api import sync_playwright
import config

console = Console()

def login_threads():
    console.print("\n" + "="*60, style="bold magenta")
    console.print("🧵 THREADS AUTONOMOUS BROWSER SESSION SETUP", style="bold white on magenta")
    console.print("="*60, style="bold magenta")
    console.print("\n[cyan]A visible Chrome/Chromium browser window will open now.[/cyan]")
    console.print("[yellow]1. Log in with your Instagram or Threads credentials.[/yellow]")
    console.print("[yellow]2. Complete any 2FA or verification prompt if asked.[/yellow]")
    console.print("[green]3. Once you reach your Threads feed, return here and press ENTER to save.[/green]\n")

    user_data_dir = config.BASE_DIR / "threads_session"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": str(user_data_dir),
            "headless": False,
            "viewport": {"width": 1280, "height": 800},
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized"
            ]
        }
        try:
            context = p.chromium.launch_persistent_context(**launch_kwargs, channel="chrome")
        except Exception:
            context = p.chromium.launch_persistent_context(**launch_kwargs)

        page = context.pages[0] if context.pages else context.new_page()

        try:
            console.print("[dim]Navigating to https://www.threads.net/login ...[/dim]")
            page.goto("https://www.threads.net/login", wait_until="domcontentloaded", timeout=45000)

            input("\n👉 Press ENTER here in this console AFTER you have successfully logged in...\n")

            # ✅ NEW: Verify login by checking auth cookies
            try:
                page.goto("https://www.threads.net/", wait_until="domcontentloaded", timeout=30000)
                cookies = context.cookies()
                # Check for sessionid on threads.net or instagram.com domains
                auth_cookies = [c for c in cookies 
                              if (c.get('domain', '').endswith('.threads.net') or c.get('domain', '').endswith('threads.net') or c.get('domain', '').endswith('.instagram.com'))
                              and c.get('name') in ('sessionid', 'csrftoken', 'ds_user_id')]
                if not auth_cookies:
                    console.print("[red]❌ Login not detected: no valid Threads auth cookies found.[/red]")
                    console.print("[dim]Make sure you completed login and the browser redirected to your feed.[/dim]")
                    context.close()
                    return False
                console.print(f"[bold green]✅ Auth cookies verified! Saving session...[/bold green]")
                
                # Save cookies to cookies.json
                import json
                cookie_file = user_data_dir / "cookies.json"
                with open(cookie_file, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, indent=2)
                console.print(f"[bold green]✅ Saved {len(cookies)} cookies to: {cookie_file}[/bold green]")

                # Sync to tools/THREADS_COOKIES_BASE64.txt and GitHub secret
                try:
                    import base64
                    import subprocess
                    b64 = base64.b64encode(cookie_file.read_bytes()).decode("utf-8")
                    out_txt = BASE_DIR / "tools" / "THREADS_COOKIES_BASE64.txt"
                    out_txt.write_text(b64, encoding="utf-8")
                    res = subprocess.run(["gh", "secret", "set", "THREADS_COOKIES_BASE64", "--body", b64], capture_output=True, text=True)
                    if res.returncode == 0:
                        console.print("[bold green]🚀 Synced THREADS_COOKIES_BASE64 to GitHub Secrets![/bold green]")
                except Exception as se:
                    console.print(f"[dim]Note on secret sync: {se}[/dim]")

            except Exception as e:
                console.print(f"[red]❌ Error verifying login: {e}[/red]")
                context.close()
                return False

            # Try to capture the logged-in handle (best-effort)
            account_name = "Threads User"
            try:
                page.goto("https://www.threads.net/", wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                loc = page.locator('a[href*="/@"]').first
                if loc and loc.is_visible():
                    href = loc.get_attribute("href") or ""
                    name = href.split("/@")[-1].split("/")[0].split("?")[0]
                    if name:
                        account_name = "@" + name
            except Exception:
                pass

            # Save a marker file so the dashboard knows login succeeded
            try:
                if account_name == "Threads User":
                    existing = user_data_dir / "account.txt"
                    if existing.exists():
                        val = existing.read_text(encoding="utf-8").strip()
                        if val and val != "Threads User":
                            account_name = val
                    else:
                        account_name = "@neubench"
                (user_data_dir / "account.txt").write_text(account_name, encoding="utf-8")
            except Exception:
                pass

            console.print(f"\n[bold green]🎉 SUCCESS! Logged into Threads as {account_name}![/bold green]")
            time.sleep(2)
            console.print(f"[bold cyan]✅ Session saved into: {user_data_dir}[/bold cyan]")
            return True

        except Exception as e:
            console.print(f"\n[red]Browser error during Threads login: {e}[/red]")
            return False
        finally:
            try:
                context.close()
            except Exception:
                pass

if __name__ == "__main__":
    login_threads()