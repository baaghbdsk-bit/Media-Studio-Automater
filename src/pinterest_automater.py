import os
import base64
import sys
import time
import json
from pathlib import Path
from typing import Optional, Tuple, Union, List
from playwright.sync_api import sync_playwright
import config

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

class PinterestAutomater:
    """Publishes vertical infographic pins to Pinterest (@neubench) with destination links."""

    def __init__(self, headless: bool = True, dry_run: bool = False):
        self.headless = headless
        self.dry_run = dry_run
        self.user_data_dir = config.BASE_DIR / "pinterest_session"
        self.last_outcome_unknown = False
        self.last_message = ""
        self._ensure_cookies()

    def _ensure_cookies(self):
        """Restores cookies from environment variable if missing from disk."""
        import base64
        env_b64 = os.environ.get("PINTEREST_COOKIES_BASE64")
        cookie_file = self.user_data_dir / "cookies.json"
        if env_b64 and not cookie_file.exists():
            try:
                self.user_data_dir.mkdir(parents=True, exist_ok=True)
                raw = base64.b64decode(env_b64).decode("utf-8")
                with open(cookie_file, "w", encoding="utf-8") as cf:
                    cf.write(raw)
                print("[PinterestAutomater] Restored Pinterest session from PINTEREST_COOKIES_BASE64")
            except Exception as e:
                print(f"[PinterestAutomater] Failed to restore PINTEREST_COOKIES_BASE64: {e}")

    def is_session_available(self) -> bool:
        cookie_file = self.user_data_dir / "cookies.json"
        return cookie_file.exists()

    def create_pin(
        self,
        image_path: Union[str, List[str]],
        title: str,
        description: str,
        link: str = "https://app.neubench.workers.dev",
        board_name: Optional[str] = "Social"
    ) -> Tuple[bool, str]:
        """Uploads an image or multi-slide carousel as a Pin on Pinterest with title, description, and website destination link."""
        self.last_outcome_unknown = False
        self.last_message = ""
        if self.dry_run:
            print(f"[PinterestAutomater] [DRY RUN] Would pin '{title}' to board '{board_name}' linking to {link}")
            return True, f"Simulated Pinterest Pin: {title}"

        if not self.is_session_available():
            return False, "Pinterest session not authenticated. Run 'python main.py login-pinterest'."

        if isinstance(image_path, (list, tuple)):
            valid_files = [str(Path(p).resolve()) for p in image_path if Path(p).exists()]
        else:
            p_res = Path(image_path).resolve()
            valid_files = [str(p_res)] if p_res.exists() else []

        if not valid_files:
            return False, f"Image file(s) not found: {image_path}"

        cookie_file = self.user_data_dir / "cookies.json"

        with sync_playwright() as p:
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ]
            browser = p.chromium.launch(headless=self.headless, args=args)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )

            try:
                with open(cookie_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    if isinstance(cookies, list):
                        context.add_cookies(cookies)
            except Exception as e:
                print(f"[PinterestAutomater] Cookie restore warning: {e}")

            page = context.new_page()

            try:
                print("[PinterestAutomater] Navigating to Pinterest Pin creation studio...")
                page.goto("https://www.pinterest.com/pin-creation-tool/", wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(3500)

                # Check if redirected to login
                if "login" in page.url:
                    return False, "Pinterest session expired or invalid. Please re-run 'python main.py login-pinterest'."

                # 1. Upload Pin media (single image or multi-slide carousel)
                file_input = page.locator("input[type='file']").first
                file_input.wait_for(state="attached", timeout=15000)
                if len(valid_files) > 1:
                    print(f"[PinterestAutomater] Uploading {len(valid_files)} carousel slides...")
                    try:
                        file_input.set_input_files(valid_files)
                    except Exception:
                        file_input.set_input_files(valid_files[0])
                else:
                    print(f"[PinterestAutomater] Uploading pin media: {Path(valid_files[0]).name}...")
                    file_input.set_input_files(valid_files[0])

                # Wait for media upload & transcoding to finish and form inputs to become enabled
                print("[PinterestAutomater] Awaiting media upload & form readiness (up to 120s)...")
                # Wake the page so inputs become interactive
                try:
                    page.press_blank()
                except Exception:
                    pass
                title_ready = False
                title_selectors = [
                    "#storyboard-selector-title:not([disabled])",
                    "[data-test-id='storyboard-selector-title']",
                    "input[placeholder*='title' i]:not([type='checkbox']):not([type='file'])",
                    "input[type='text']:not([disabled])",
                    "textarea[placeholder*='title' i]",
                    'div[role="textbox"][aria-label*="title" i]',
                    'div[role="textbox"]:not([disabled])',
                ]
                for t_sel in title_selectors:
                    try:
                        page.wait_for_selector(t_sel, timeout=20000, state="visible")
                        title_ready = True
                        break
                    except Exception:
                        continue
                if not title_ready:
                    print("[PinterestAutomater] Warning: no enabled title field detected; proceeding anyway.")

                page.wait_for_timeout(2000)

                # 2. Enter Title (resilient input discovery)
                print(f"[PinterestAutomater] Setting Pin title: {title[:40]}...")
                title_input = None
                for t_sel in title_selectors:
                    try:
                        cand = page.locator(t_sel).first
                        if cand.count() > 0 and cand.is_visible(timeout=3000):
                            i_type = (cand.get_attribute("type") or "").lower()
                            if i_type not in ("checkbox", "radio", "file", "hidden"):
                                title_input = cand
                                break
                    except Exception:
                        continue
                if title_input is None:
                    try:
                        for cand in page.locator("input[type='text'], textarea, [role='textbox']").all():
                            if cand.is_visible():
                                i_type = (cand.get_attribute("type") or "").lower()
                                if i_type not in ("checkbox", "radio", "file", "hidden"):
                                    title_input = cand
                                    break
                    except Exception:
                        title_input = None
                if title_input is not None:
                    title_input.click()
                    title_input.fill(title[:100])
                    page.wait_for_timeout(1000)

                # 2b. Enter Description if provided
                if description:
                    print("[PinterestAutomater] Setting Pin description...")
                    desc_selectors = [
                        "#storyboard-selector-description",
                        "[data-test-id='storyboard-selector-description']",
                        "div[role='textbox'][aria-label*='description' i]",
                        "div[role='textbox']",
                        "textarea[placeholder*='description' i]",
                        "textarea"
                    ]
                    for d_sel in desc_selectors:
                        try:
                            d_elem = page.locator(d_sel).first
                            if d_elem.is_visible(timeout=1500):
                                d_elem.click()
                                d_elem.fill(description[:500])
                                page.wait_for_timeout(800)
                                break
                        except Exception:
                            continue

                # 3. Enter Destination Link
                print(f"[PinterestAutomater] Setting destination link: {link}...")
                link_input = page.locator("#WebsiteField, input[placeholder*='link' i]").first
                link_input.click()
                link_input.fill(link)
                page.wait_for_timeout(1000)

                # 4. Select Board (Required to enable Publish button)
                print(f"[PinterestAutomater] Selecting Pinterest board: {board_name}...")
                board_btn = page.locator("[data-test-id='board-dropdown-select-button']").first
                if board_btn.is_visible(timeout=3000):
                    board_btn.click()
                    page.wait_for_timeout(1500)

                    board_row = page.locator(f"div[role='button']:has-text('{board_name}'), div:text-is('{board_name}')").last
                    if board_row.is_visible(timeout=2000):
                        board_row.click()
                    else:
                        page.locator("[role='option'], div[role='button']").last.click()
                    page.wait_for_timeout(1500)

                # 5. Publish Pin (resilient publish button discovery)
                print("[PinterestAutomater] Clicking Publish button...")
                publish_selectors = [
                    "[data-test-id='storyboard-creation-nav-done'] button",
                    "[data-test-id*='publish']",
                    "button:has-text('Publish')",
                    "a:has-text('Publish')",
                    'button[type="submit"]',
                    'div[role="button"]:has-text("Publish")',
                ]
                publish_btn = None
                for p_sel in publish_selectors:
                    try:
                        cand = page.locator(p_sel).first
                        if cand.count() > 0 and cand.is_visible(timeout=5000):
                            publish_btn = cand
                            break
                    except Exception:
                        continue
                if publish_btn is None:
                    publish_btn = page.locator("button:has-text('Publish')").first
                publish_btn.wait_for(state="visible", timeout=15000)

                for _ in range(30):
                    try:
                        if not publish_btn.is_disabled():
                            break
                    except Exception:
                        break
                    page.wait_for_timeout(1000)

                try:
                    publish_btn.click()
                except Exception:
                    publish_btn.click(force=True)
                print("[PinterestAutomater] Clicked Publish. Awaiting network confirmation...")

                # Wait up to 30s for URL change or live pin confirmation
                published = False
                for _ in range(30):
                    page.wait_for_timeout(1000)
                    cur_url = page.url
                    if "/pin/" in cur_url and "pin-creation-tool" not in cur_url and "pin-builder" not in cur_url:
                        published = True
                        break

                    confirmations = [
                        '[data-test-id="toast"]',
                        '[role="alert"]:has-text("published")',
                        'text="Your Pin is live"',
                        'text="See your Pin"',
                        'button:has-text("View")',
                        'a:has-text("View")'
                    ]
                    for sel in confirmations:
                        try:
                            if page.locator(sel).first.is_visible():
                                published = True
                                break
                        except Exception:
                            pass
                    if published:
                        break

                if not published:
                    debug_img = config.BASE_DIR / "generated_visuals" / "pinterest_publish_debug.png"
                    try:
                        page.screenshot(path=str(debug_img))
                    except Exception:
                        pass
                    self.last_outcome_unknown = True
                    self.last_message = f"Pinterest submission confirmation timed out (URL: {page.url}). Debug screenshot saved."
                    return False, self.last_message

                print("[PinterestAutomater] ✅ Successfully published Pin to Pinterest!")
                self.last_message = "Published Pin to Pinterest"
                return True, self.last_message

            except Exception as e:
                print(f"[PinterestAutomater] ❌ Pin creation error: {e}")
                self.last_message = f"Pinterest error: {e}"
                return False, self.last_message
            finally:
                context.close()
                browser.close()
