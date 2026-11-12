"""
Video Configuration for Media Studio Automater
Defines formats, durations, quality settings, and visual standards
for YouTube Shorts, Instagram Reels, and YouTube Long-form Explainers.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class VideoFormat:
    """Video format specification"""
    name: str
    aspect_ratio: str  # "9:16" or "16:9"
    width: int
    height: int
    fps: int
    min_duration: int  # seconds
    max_duration: int  # seconds
    target_duration: int  # seconds
    codec: str = "libx264"
    preset: str = "medium"
    crf: int = 18
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    audio_sample_rate: int = 48000
    pix_fmt: str = "yuv420p"
    faststart: bool = True
    profile: str = "main"
    level: Optional[str] = None


# Format definitions per the requirements
VIDEO_FORMATS: Dict[str, VideoFormat] = {
    "youtube_shorts": VideoFormat(
        name="YouTube Shorts",
        aspect_ratio="9:16",
        width=1080,
        height=1920,
        fps=30,
        min_duration=20,
        max_duration=58,
        target_duration=48,
    ),
    "instagram_reels": VideoFormat(
        name="Instagram Reels",
        aspect_ratio="9:16",
        width=1080,
        height=1920,
        fps=30,
        min_duration=20,
        max_duration=90,
        target_duration=48,
    ),
    "youtube_explainer": VideoFormat(
        name="YouTube Explainer",
        aspect_ratio="16:9",
        width=1920,
        height=1080,
        fps=30,
        min_duration=300,
        max_duration=600,
        target_duration=420,
    ),
}


def get_format(format_key: str) -> VideoFormat:
    """Get video format configuration by key"""
    if format_key not in VIDEO_FORMATS:
        raise ValueError(f"Unknown video format: {format_key}. Available: {list(VIDEO_FORMATS.keys())}")
    return VIDEO_FORMATS[format_key]


@dataclass
class VisualStyle:
    """Professional visual design configuration"""
    theme: str  # "dark" or "light"
    primary_color: str
    secondary_color: str
    accent_color: str
    text_color: str
    bg_color: str
    card_bg: str
    border_color: str
    font_main: str = "Arial"
    font_title: str = "Arial"
    font_code: str = "Consolas"
    font_size_title: int = 48
    font_size_body: int = 28
    font_size_caption: int = 24
    safe_zone_margin: int = 120  # pixels from edges for mobile overlays


# Professional color palettes
COLOR_PALETTES: Dict[str, VisualStyle] = {
    "dark_tech": VisualStyle(
        theme="dark",
        primary_color="#00D4FF",      # Cyan accent
        secondary_color="#7B2CBF",    # Purple
        accent_color="#FF6B35",       # Orange accent
        text_color="#FFFFFF",         # White text
        bg_color="#0A0A0F",           # Deep dark background
        card_bg="#1A1A2E",            # Card background
        border_color="#333344",       # Subtle borders
    ),
    "light_tech": VisualStyle(
        theme="light",
        primary_color="#0066CC",      # Blue accent
        secondary_color="#6A0DAD",    # Purple
        accent_color="#FF4500",       # Orange accent
        text_color="#1A1A2E",         # Dark text
        bg_color="#F5F7FA",           # Light background
        card_bg="#FFFFFF",            # White cards
        border_color="#E1E5EA",       # Light borders
    ),
}


def get_visual_style(palette_name: str = "dark_tech") -> VisualStyle:
    """Get visual style configuration"""
    if palette_name not in COLOR_PALETTES:
        raise ValueError(f"Unknown color palette: {palette_name}. Available: {list(COLOR_PALETTES.keys())}")
    return COLOR_PALETTES[palette_name]


# Output directories
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_BASE = BASE_DIR / "output"
VIDEO_OUTPUT_DIR = OUTPUT_BASE / "videos"
SCRIPT_OUTPUT_DIR = OUTPUT_BASE / "scripts"
SUBTITLE_OUTPUT_DIR = OUTPUT_BASE / "subtitles"
AUDIO_OUTPUT_DIR = OUTPUT_BASE / "audio"
THUMBNAIL_OUTPUT_DIR = OUTPUT_BASE / "thumbnails"
PROJECTS_DIR = OUTPUT_BASE / "projects"

# Manim configuration
MANIM_QUALITY = "high"  # low, medium, high, production
MANIM_FRAME_RATE = 30
MANIM_RENDERER = "cairo"  # cairo or opengl

# TTS configuration
TTS_VOICE = "en-US-AndrewMultilingualNeural"
TTS_RATE = "+10%"
TTS_PITCH = "+0%"

# Quality thresholds
MIN_VIDEO_SIZE_KB = 100
MAX_RENDER_RETRIES = 3