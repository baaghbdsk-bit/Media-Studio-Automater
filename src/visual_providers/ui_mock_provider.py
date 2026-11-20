"""Self-contained HTML/CSS mock-UI provider (browser, terminal, dashboard, chat)."""
from __future__ import annotations

import hashlib
import html
from typing import Any, Dict, Optional

from .base import VisualProvider, make_asset, scene_concept, scene_visual_type

_SUPPORTED_TYPES = {
    "ui_mock", "uimock", "ui", "mock", "mockup", "screenshot", "interface",
    "app", "dashboard", "terminal", "browser", "chat", "screen",
}

_KEYWORDS = (
    ("terminal", ("terminal", "cli", "command", "shell", "code", "console")),
    ("dashboard", ("dashboard", "analytics", "metrics", "stats", "chart", "data")),
    ("chat", ("chat", "message", "conversation", "assistant", "bot", "dm")),
    ("browser", ("browser", "web", "page", "site", "search", "window")),
)

_STYLE = (
    '<style>.vp-ui{--vp-bg:#0e1420;--vp-panel:#151e2e;--vp-ink:#e8eef8;'
    '--vp-line:#32405c;--vp-accent:#4cc9f0;font-family:system-ui,-apple-system,'
    'sans-serif;color:var(--vp-ink);background:var(--vp-bg);border:1px solid '
    'var(--vp-line);border-radius:14px;overflow:hidden;max-width:960px;'
    'box-shadow:0 18px 50px rgba(0,0,0,.35)}.vp-ui *{box-sizing:border-box}'
    '.vp-bar{display:flex;align-items:center;gap:8px;padding:12px 16px;'
    'background:var(--vp-panel);border-bottom:1px solid var(--vp-line)}'
    '.vp-dot{width:12px;height:12px;border-radius:50%;background:var(--vp-line)}'
    '.vp-title{margin-left:12px;font-size:14px;opacity:.8}.vp-body{padding:22px}'
    '.vp-row{height:14px;border-radius:6px;background:var(--vp-line);margin:12px 0;'
    'opacity:.55}.vp-card{border:1px solid var(--vp-line);border-radius:10px;'
    'padding:16px;margin:10px 0}.vp-key{color:var(--vp-accent)}</style>'
)


def pick_style(scene: Dict[str, Any], topic: Any) -> str:
    raw = scene_visual_type(scene).lower()
    text = scene_concept(scene, topic).lower()
    for kind, words in _KEYWORDS:
        if kind in raw or any(word in text for word in words):
            return kind
    return "browser"


def _browser(title: str) -> str:
    return (
        '<div class="vp-bar"><span class="vp-dot"></span><span class="vp-dot"></span>'
        '<span class="vp-dot"></span><span class="vp-title">%s</span></div>'
        '<div class="vp-body"><div class="vp-card">'
        '<div class="vp-row" style="width:70%%"></div>'
        '<div class="vp-row" style="width:92%%"></div>'
        '<div class="vp-row" style="width:54%%"></div></div></div>' % html.escape(title)
    )


def _terminal(title: str) -> str:
    return (
        '<div class="vp-bar"><span class="vp-dot"></span><span class="vp-dot"></span>'
        '<span class="vp-dot"></span><span class="vp-title">%s — bash</span></div>'
        '<div class="vp-body"><div class="vp-card">'
        '<div><span class="vp-key">$</span> run pipeline --fast</div>'
        '<div class="vp-row" style="width:64%%"></div>'
        '<div><span class="vp-key">✓</span> done in 1.2s</div></div></div>' % html.escape(title)
    )


def _dashboard(title: str) -> str:
    bars = "".join(
        '<div class="vp-card" style="display:inline-block;width:28%%;vertical-align:top">'
        '<div class="vp-row" style="width:40%%"></div>'
        '<div style="font-size:28px;color:var(--vp-accent)">%d%%</div></div>' % v
        for v in (82, 47, 96)
    )
    return (
        '<div class="vp-bar"><span class="vp-title">%s — Analytics</span></div>'
        '<div class="vp-body">%s<div class="vp-row" style="width:88%%"></div>'
        '<div class="vp-row" style="width:72%%"></div></div>' % (html.escape(title), bars)
    )


def _chat(title: str) -> str:
    return (
        '<div class="vp-bar"><span class="vp-title">%s — Chat</span></div>'
        '<div class="vp-body"><div class="vp-card" style="width:72%%">'
        '<div class="vp-row" style="width:80%%"></div></div>'
        '<div class="vp-card" style="width:72%%;margin-left:auto">'
        '<div class="vp-row" style="width:60%%"></div></div>'
        '<div class="vp-card" style="width:72%%">'
        '<div class="vp-row" style="width:88%%"></div></div></div>' % html.escape(title)
    )


_RENDER = {
    "browser": _browser,
    "terminal": _terminal,
    "dashboard": _dashboard,
    "chat": _chat,
}


class UiMockProvider(VisualProvider):
    name = "ui_mock"

    def supports(self, scene: Dict[str, Any], topic: Any) -> bool:
        kind = scene_visual_type(scene)
        return kind in _SUPPORTED_TYPES or any(word in kind for word in ("ui", "mock", "screen"))

    def resolve(self, scene: Dict[str, Any], topic: Any, cache: Any, ledger: Any) -> Optional[dict]:
        try:
            kind = pick_style(scene, topic)
            title = str(scene.get("main_visual_concept") or "Interface")[:60]
            markup = (
                _STYLE
                + '<div class="vp-ui" data-ui="%s">%s</div>'
                % (html.escape(kind), _RENDER[kind](title))
            )
            digest = hashlib.sha256(markup.encode("utf-8")).hexdigest()
            return make_asset(
                self.name,
                "markup",
                inline_markup=markup,
                license="MIT/Own-generated",
                attribution="Own-generated HTML/CSS mock UI (%s)" % kind,
                sha256=digest,
                relevance_score=0.9,
            )
        except Exception:
            return None
