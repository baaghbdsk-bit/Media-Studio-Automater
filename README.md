# Media Studio Automater 🎬

Autonomous high-production visual and video studio engine for **YouTube Shorts**, **Instagram Reels**, **Instagram Carousels**, and **Pinterest**.

---

## 🌟 Key Capabilities

1. **YouTube Shorts (50–58s Full Vertical HD 1080×1920)**:
   - AI topic curation via arXiv, GitHub trending, and Hugging Face.
   - Dynamic HTML5 canvas & CSS animated infographics.
   - High-fidelity Microsoft Edge neural TTS voiceover (`en-US-ChristopherNeural` / `en-US-GuyNeural`).
   - Synced word-level highlighted SRT captions.
   - Strict duration clamping (`<= 58s`) adhering to YouTube Shorts eligibility rules.

2. **Instagram Reels (9:16 Uncropped Vertical)**:
   - Full 1080×1920 uncropped direct upload via Playwright stealth browser automation.
   - Authentic interaction handling, tag injection, and confirmation verification.

3. **Instagram Educational Carousels (4:5 1080×1350)**:
   - 5-slide visual cheatsheets with syntax highlighting, architectural diagrams, metric breakdowns, and summary slides.
   - Multi-slide carousel creation via Playwright.

4. **Pinterest Cheatsheet Pins (Multi-Slide 1080×1350)**:
   - Multi-image carousel pin upload with direct backlink to `https://app.neubench.workers.dev`.

---

## 🚀 Quick Start

### Installation & Environment
Use the existing Python environment or create a dedicated virtualenv:
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### CLI Commands

| Command | Action |
|---|---|
| `python main.py studio-all --dry-run` | Test complete visual pipeline across all 4 platforms in simulation mode |
| `python main.py studio-all` | Autonomous production & broadcast cycle across all 4 platforms |
| `python main.py youtube` | Produce and publish YouTube Short |
| `python main.py instagram-reel` | Produce and publish 9:16 Instagram Reel |
| `python main.py instagram-carousel` | Render and publish 5-slide educational cheatsheet to Instagram |
| `python main.py pinterest` | Render and publish multi-slide Pin to Pinterest |
| `python main.py generate-video` | Render 50–58s vertical video only (saved to `generated_visuals/videos`) |
| `python main.py generate-carousel` | Render 5-slide carousel images only (saved to `generated_visuals/carousels`) |
| `python main.py login-instagram` | Headed browser login for Instagram session |
| `python main.py login-pinterest` | Headed browser login for Pinterest session |
| `python main.py login-youtube` | OAuth browser authorization for YouTube Data API v3 |
| `python main.py ig-diagnose` | Run headless cloud diagnostic on Instagram session cookies |
| `python main.py metrics` | View publication history and recent events |

---

## 📁 Project Structure

```
Media-Studio-Automater/
├── config.py                 # Core configurations and credential loaders
├── main.py                   # Master CLI entrypoint
├── studio_history.json       # Publication log & duplicate prevention
├── scripts/
│   ├── ig_diagnose.py        # Cloud-ready session diagnostic
│   ├── login_instagram.py    # Playwright Instagram session authorizer
│   ├── login_pinterest.py    # Playwright Pinterest session authorizer
│   └── login_youtube.py      # OAuth2 YouTube authorizer
├── src/
│   ├── studio_engine.py      # Unified broadcast pipeline engine
│   ├── video_generator.py    # 50-58s vertical HD video rendering engine
│   ├── instagram_carousel.py # 5-slide 4:5 carousel generator
│   ├── instagram_automater.py# Playwright Instagram publisher
│   ├── youtube_automater.py  # YouTube Data API v3 publisher
│   ├── pinterest_automater.py# Playwright Pinterest publisher
│   ├── trend_hunter.py       # ArXiv / HuggingFace trend synthesizer
│   ├── ai_generator.py       # Gemini API visual & script copywriter
│   ├── templates/            # HTML5 Canvas & SVG render templates
│   └── tracker.py            # Event logging
└── tests/
    ├── test_instagram_confirmation.py
    └── test_studio_engine.py
```
