# Media Studio Automater - Automation Setup

This automation system runs your Media Studio in the background like an X automater — even if you close your laptop.

## What's Automated

| Content | Schedule | Platforms |
|---------|----------|-----------|
| Instagram Reels + YouTube Shorts | 5:15 PM daily | Instagram Reels → Threads → Pinterest |
| Instagram Reels + YouTube Shorts | 7:15 PM daily | Instagram Reels → Threads → Pinterest |
| Manim Explainer Video | 9:15 PM (alternate days) | YouTube → Instagram Reel → Pinterest |

## How to Start Automation

### Option 1: Windows Task Scheduler (Recommended - Keeps running after laptop close)

Run as Administrator:
```cmd
setup_automation.bat
```

This creates 3 Windows Task Scheduler tasks that run automatically at the specified times.

### Option 2: Background Daemon (Keeps running in terminal)

```cmd
python src\automation_daemon.py
```

Or with dry-run (no actual posting):
```cmd
python src\automation_daemon.py --dry-run
```

### Option 3: Test Today's Schedule

```cmd
python main.py schedule-today
```

This checks the current time and runs the appropriate scheduled task if it matches.

## How It Works

1. **Daemon checks time every minute** - triggers tasks at scheduled times
2. **Reels/Shorts pipeline** generates a fresh topic, creates a vertical video, and publishes to:
   - Instagram Reel → auto-shares to Threads → Pinterest
   - YouTube Shorts
3. **Explainer pipeline** (alternate days only) generates a Manim-based explainer video and publishes to:
   - YouTube → Instagram Reel → Pinterest

## Verify Automation

```cmd
python main.py metrics
```

View your posted history and statistics.

## Stop Automation

- **Task Scheduler:** Delete tasks via Task Scheduler GUI or `schtasks /delete /tn "Media Studio - *"`
- **Daemon:** Press `Ctrl+C` in the terminal window

## Requirements

- Python installed and in PATH
- All platform sessions authenticated (Instagram, Pinterest, YouTube)
- FFmpeg installed
- Playwright browsers installed
