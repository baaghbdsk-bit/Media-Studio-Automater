"""
Media Studio Self-Healing Watchdog.
Runs every 2 hours to verify that daily scheduled broadcasts are on track.
If GitHub Actions dropped a scheduled cron run, the watchdog automatically
detects the gap and triggers a catch-up broadcast.
"""
import sys
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def ist_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

def is_run_in_progress() -> bool:
    try:
        res = subprocess.run(
            ["gh", "run", "list", "--workflow", "media_studio.yml", "-L", "5", "--json", "status"],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            runs = json.loads(res.stdout)
            for r in runs:
                if r.get("status") in ("in_progress", "queued", "waiting"):
                    return True
    except Exception as e:
        print(f"[Watchdog] Warning checking active runs: {e}")
    return False

def get_last_successful_run_time():
    # 1. Check GitHub Action runs
    try:
        res = subprocess.run(
            ["gh", "run", "list", "--workflow", "media_studio.yml", "--status", "success", "-L", "1", "--json", "createdAt"],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            runs = json.loads(res.stdout)
            if runs and runs[0].get("createdAt"):
                dt_str = runs[0]["createdAt"].replace("Z", "+00:00")
                return datetime.fromisoformat(dt_str)
    except Exception as e:
        print(f"[Watchdog] Warning checking last successful run: {e}")

    # 2. Fallback to studio_history.json topic_log
    history_file = Path(__file__).resolve().parent.parent / "studio_history.json"
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            log = data.get("topic_log", [])
            for entry in reversed(log):
                t_str = entry.get("time")
                if t_str and "T" in t_str:
                    return datetime.fromisoformat(t_str)
        except Exception:
            pass
    return None

def check_and_heal():
    now_ist = ist_now()
    now_utc = datetime.now(timezone.utc)
    print("=" * 60)
    print(f"🛡️ MEDIA STUDIO WATCHDOG (IST: {now_ist.strftime('%Y-%m-%d %I:%M %p')})")
    print("=" * 60)

    # 1. Check if a run is already running
    if is_run_in_progress():
        print("[Watchdog] ⏳ A broadcast run is currently in progress or queued. Standing by.")
        return

    # 2. Check last successful run time
    last_run_utc = get_last_successful_run_time()
    if last_run_utc:
        last_run_ist = last_run_utc + timedelta(hours=5, minutes=30)
        hours_since = (now_utc - last_run_utc).total_seconds() / 3600.0
        print(f"[Watchdog] Last successful broadcast: {last_run_ist.strftime('%Y-%m-%d %I:%M %p')} IST ({hours_since:.1f} hours ago)")
    else:
        hours_since = 999.0
        print("[Watchdog] No previous successful broadcast found.")

    # 3. Target slots today (IST decimal hours: 08:40=8.66, 12:40=12.66, 17:40=17.66, 19:40=19.66, 21:40=21.66)
    slot_hours = [8.66, 12.66, 17.66, 19.66, 21.66]
    current_hour_float = now_ist.hour + (now_ist.minute / 60.0)

    # Outside active broadcasting hours (08:30 - 22:30 IST)
    if current_hour_float < 8.5 or current_hour_float > 22.5:
        print("[Watchdog] 🌙 Outside active broadcasting hours (08:30 - 22:30 IST). Sleep mode active.")
        return

    # Check if any passed slot was missed
    missed_slot = False
    for slot in slot_hours:
        # Slot considered overdue if current time is at least 30 mins past slot
        if current_hour_float >= (slot + 0.5):
            slot_today_ist = now_ist.replace(hour=int(slot), minute=int((slot % 1) * 60), second=0, microsecond=0)
            slot_today_utc = slot_today_ist - timedelta(hours=5, minutes=30)
            if not last_run_utc or last_run_utc < slot_today_utc:
                print(f"[Watchdog] ⚠️ Missed slot detected: {slot_today_ist.strftime('%I:%M %p')} IST was not fulfilled!")
                missed_slot = True
                break

    if missed_slot:
        print("[Watchdog] 🚨 Triggering autonomous catch-up broadcast now...")
        action = "schedule-autopilot"
        if current_hour_float >= 21.5:
            action = "long-explainer"
        res = subprocess.run(
            ["gh", "workflow", "run", "media_studio.yml", "-f", f"action={action}", "-f", "dry_run=false"],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            print(f"[Watchdog] 🚀 Catch-up workflow '{action}' dispatched successfully!")
        else:
            print(f"[Watchdog] Error triggering workflow: {res.stderr}")
    else:
        print("[Watchdog] ✅ All scheduled slots are currently on track. No action needed.")

if __name__ == "__main__":
    check_and_heal()
