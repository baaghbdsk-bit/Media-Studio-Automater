# Media Studio Automater - Automation Setup

This automation system schedules video production and publishing through Windows Task Scheduler.

## What's Automated

| Content | Schedule | Platforms |
|---------|----------|-----------|
| Instagram Reels + YouTube Shorts | 5:15 PM daily | Instagram Reels → Threads → Pinterest |
| Instagram Reels + YouTube Shorts | 7:15 PM daily | Instagram Reels → Threads → Pinterest |
| Manim Explainer Video | 9:15 PM (alternate days) | YouTube → Instagram Reel → Pinterest |

## How to Start Automation

### Option 1: Windows Task Scheduler (Recommended)

Run:
```cmd
setup_automation.bat
```

This registers three daily tasks for the current Windows account. Each task launches the matching one-shot pipeline with the project directory set correctly. Tasks start when available after a missed trigger and request that Windows wake the computer.

The account must be signed in for the tasks to run. A sleeping computer may not wake if its power settings, hardware, or battery policy prevent it; a shut-down computer cannot run scheduled posts. Keep the computer powered and signed in for reliable posting.

### Option 2: Background Daemon (Keeps running in terminal)

```cmd
python src\automation_daemon.py
```

Or with dry-run (no actual posting):
```cmd
python src\automation_daemon.py --dry-run
```

The daemon also accepts one-shot actions, useful for Task Scheduler or diagnostics:
```cmd
python src\automation_daemon.py schedule-reels-shorts --dry-run
python src\automation_daemon.py schedule-explainer --dry-run
```

### Option 3: Test Today's Schedule

```cmd
python main.py schedule-today
```

This runs the appropriate workflow only when invoked during a scheduled time: Reels/Shorts at 5:15 PM or 7:15 PM, or the alternate-day explainer at 9:15 PM. Times use the computer's local clock.

## How It Works

1. **Task Scheduler launches each job** at the configured local time. The optional daemon checks the clock every minute.
2. **Reels/Shorts pipeline** generates a fresh topic, creates a vertical video, and publishes to:
   - Instagram Reel → auto-shares to Threads → Pinterest
   - YouTube Shorts
3. **Explainer pipeline** (alternate days only) generates a Manim-based explainer video and publishes to:
   - YouTube → Instagram Reel → Pinterest

## Verify Automation

```cmd
python main.py metrics
```

View your posted history and statistics. Task run output and failures are appended to `output\automation.log`.

## Stop Automation

- **Task Scheduler:** Delete tasks via Task Scheduler GUI or `schtasks /delete /tn "Media Studio - *"`
- **Daemon:** Press `Ctrl+C` in the terminal window

## Requirements

- Python installed and in PATH
- All platform sessions authenticated (Instagram, Pinterest, YouTube)
- FFmpeg installed
- Playwright browsers installed
