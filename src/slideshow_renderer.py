"""Clear 9:16 slideshow renderer for narration beats.

This is the improved version of the original card-based slideshow: large,
readable text, one idea per slide, distinct layouts, and gentle continuous
motion so the result never reads as a static deck.
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, List

GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"

PALETTES = {
    "news": ("#fbbf24", "#f43f5e", "251,191,36", "244,63,94"),
    "concept": ("#38bdf8", "#34d399", "56,189,248", "52,211,153"),
    "comparison": ("#a78bfa", "#fbbf24", "167,139,250", "251,191,36"),
}


def _esc(text: Any) -> str:
    return html.escape(str(text or ""), quote=True)


def _support_line(beat: Dict[str, Any], focus: str) -> str:
    narration = re.sub(r"\s+", " ", str(beat.get("narration") or "")).strip()
    first = re.split(r"(?<=[.!?])\s+", narration)[0].strip() if narration else ""
    if first:
        return " ".join(first.split()[:16]).rstrip(",;:") + ("" if first.endswith((".", "!", "?")) else ".")
    for line in beat.get("lines") or []:
        text = re.sub(r"\s+", " ", str(line)).strip()
        if text and text.lower() != focus.strip().lower() and len(text.split()) > 3:
            return " ".join(text.split()[:16])
    return "One idea at a time."


def _stat(narration: str) -> str:
    match = re.search(r"\b\d[\d,.]*\s*(?:%|x|seconds?|minutes?|hours?|days?|cores?|chips?)\b", narration, re.I)
    return match.group(0).upper() if match else ""


CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);overflow:hidden}
body{font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--ink)}
#root{width:1080px;height:1920px;position:relative;overflow:hidden;background:var(--bg)}
#world{position:absolute;inset:0;transform-origin:50% 42%}
.bg{position:absolute;inset:0;background:radial-gradient(circle at 50% 36%,rgba(var(--c1rgb),.18) 0%,rgba(var(--c2rgb),.07) 42%,var(--bg) 80%)}
.grid{position:absolute;inset:-260px;background-image:linear-gradient(rgba(var(--c1rgb),.38) 2px,transparent 2px),linear-gradient(90deg,rgba(var(--c1rgb),.38) 2px,transparent 2px);background-size:84px 84px;opacity:.8}
.sweep{position:absolute;top:-15%;left:0;width:32%;height:140%;z-index:3;opacity:.34;transform:skewX(-18deg);background:linear-gradient(90deg,transparent,rgba(255,255,255,.6) 48%,rgba(255,255,255,.85) 52%,transparent)}
.slide{position:absolute;inset:0;z-index:5;clip-path:inset(0 100% 0 0);padding:280px 80px 420px;display:flex;flex-direction:column;justify-content:center}
.panel{position:absolute;left:60px;right:60px;top:330px;bottom:700px;border-radius:36px;background:rgba(10,18,32,.58);border:1px solid rgba(var(--c1rgb),.28);box-shadow:0 30px 90px rgba(0,0,0,.38);z-index:-1;transform-origin:50% 50%}
.kicker{font-size:22px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--c1);margin-bottom:26px;opacity:0}
.word{font-size:104px;font-weight:900;line-height:1.02;letter-spacing:-.03em;color:var(--ink);opacity:0;text-shadow:0 10px 40px rgba(0,0,0,.6)}
.support{margin-top:34px;font-size:38px;font-weight:650;line-height:1.28;color:#dbe4f2;opacity:0;max-width:880px}
.rule{margin-top:40px;width:150px;height:8px;border-radius:99px;background:var(--c1);opacity:0}
.stat{margin-top:26px;font-size:30px;font-weight:800;letter-spacing:.06em;color:var(--c2);opacity:0}
.card{margin-top:54px;padding:40px 44px;border-radius:28px;background:rgba(10,18,32,.82);border:2px solid rgba(var(--c1rgb),.55);box-shadow:0 24px 70px rgba(0,0,0,.55)}
.slide.left{align-items:flex-start;text-align:left}
.slide.right{align-items:flex-end;text-align:right}
.slide.center{align-items:center;text-align:center}
.progress{position:absolute;left:0;top:0;height:8px;width:1080px;background:rgba(255,255,255,.10);z-index:30}
.progress-fill{height:100%;width:100%;background:linear-gradient(90deg,var(--c1),var(--c2));transform:scaleX(0);transform-origin:left center}
.counter{position:absolute;right:60px;bottom:52px;font-size:22px;font-weight:800;letter-spacing:.12em;color:var(--ink);z-index:30;opacity:0}
"""


def build_slideshow_html(script: Dict[str, Any], duration: float, pillar: str = "") -> str:
    """Return a complete HyperFrames HTML document for the narration beats."""
    beats: List[Dict[str, Any]] = [b for b in (script.get("beats") or []) if isinstance(b, dict)]
    count = len(beats) or 7
    span = duration / max(count, 1)
    key = "news" if str(pillar).upper() == "NEWS" else "concept"
    c1, c2, c1rgb, c2rgb = PALETTES.get(key, PALETTES["concept"])

    body: List[str] = [
        '<div id="root" data-composition-id="main" data-start="0" '
        'data-duration="%.1f" data-width="1080" data-height="1920">' % duration,
        '<audio id="narration" src="narration_master.wav" data-start="0" '
        'data-duration="%.1f" data-volume="1"></audio>' % duration,
        '<div id="world"><div class="bg"></div><div class="grid" id="grid"></div></div>',
        '<div class="sweep" id="sweep"></div>',
    ]

    for index, beat in enumerate(beats[:7]):
        start = index * span
        focus = _esc(str(beat.get("focus_word") or "KEY IDEA")[:40])
        support = _esc(_support_line(beat, str(beat.get("focus_word") or "")))
        stat = _esc(_stat(str(beat.get("narration") or "")))
        layout = ("left", "center", "right", "center", "left", "right", "center")[index % 7]
        kicker = _esc(str(beat.get("label") or "BEAT %d" % (index + 1))[:30])
        body.append(
            '<div id="slide%d" class="slide %s">' % (index, layout)
            + '<div class="panel" id="p%d"></div>' % index
            + '<div class="kicker" id="k%d">%s</div>' % (index, kicker)
            + '<div class="word" id="w%d">%s</div>' % (index, focus)
            + '<div class="support" id="s%d">%s</div>' % (index, support)
            + '<div class="rule" id="r%d"></div>' % index
            + (('<div class="stat" id="t%d">%s</div>' % (index, stat)) if stat else "")
            + "</div>"
        )
        body.append(
            '<div class="counter" id="c%d">%02d / %02d</div>' % (index, index + 1, count)
        )

    body.append('<div class="progress"><div class="progress-fill" id="progress"></div></div>')
    body.append("</div>")  # /root

    js: List[str] = [
        "window.__timelines = window.__timelines || {};",
        'window.__timelines["main"] = gsap.timeline({paused:true});',
        "const tl = window.__timelines['main'];",
        'tl.fromTo("#world",{scale:1},{scale:1.07,duration:%.3f,ease:"none",immediateRender:false},0);' % duration,
        'tl.fromTo("#sweep",{x:-420},{x:1500,duration:%.3f,ease:"none",immediateRender:false},0);' % duration,
        'tl.fromTo("#progress",{scaleX:0},{scaleX:1,duration:%.3f,ease:"none",immediateRender:false},0);' % duration,
    ]

    for index in range(count):
        start = index * span
        exit_at = min(duration, start + span - 0.25)
        js.append(
            'tl.fromTo("#slide%d",{clipPath:"inset(0 100%% 0 0)"},'
            '{clipPath:"inset(0 0%% 0 0)",duration:0.45,ease:"power2.inOut",immediateRender:false},%.3f);'
            % (index, start)
        )
        js.append(
            'tl.fromTo("#slide%d",{clipPath:"inset(0 0%% 0 0)"},'
            '{clipPath:"inset(0 0 0 100%%)",duration:0.22,ease:"power2.in",immediateRender:false},%.3f);'
            % (index, exit_at)
        )
        for selector in ("k", "w", "s", "r", "t"):
            js.append(
                'tl.fromTo("#%s%d",{y:38,opacity:0},{y:0,opacity:1,duration:0.5,'
                'ease:"power3.out",immediateRender:false},%.3f);' % (selector, index, start + 0.08)
            )
            js.append(
                'tl.fromTo("#%s%d",{y:0,opacity:1},{y:-20,opacity:0,duration:0.22,'
                'ease:"power2.in",immediateRender:false},%.3f);' % (selector, index, exit_at)
            )
        js.append(
            'tl.fromTo("#c%d",{opacity:0},{opacity:1,duration:0.2,immediateRender:false},%.3f);'
            % (index, start + 0.1)
        )
        js.append(
            'tl.fromTo("#c%d",{opacity:1},{opacity:0,duration:0.2,immediateRender:false},%.3f);'
            % (index, exit_at)
        )

        # Continuous, bounded idle motion on the focal text keeps every frame
        # alive after the entrance settles (no freeze between transitions).
        t = start + 0.62
        flip = False
        while t < exit_at - 0.18:
            seg = min(0.55, exit_at - 0.18 - t)
            if seg < 0.12:
                break
            if not flip:
                js.append(
                    'tl.fromTo("#w%d",{y:0,scale:1},{y:-9,scale:1.018,duration:%.3f,'
                    'ease:"sine.inOut",immediateRender:false},%.3f);' % (index, seg, t)
                )
            else:
                js.append(
                    'tl.fromTo("#w%d",{y:-9,scale:1.018},{y:0,scale:1,duration:%.3f,'
                    'ease:"sine.inOut",immediateRender:false},%.3f);' % (index, seg, t)
                )
            js.append(
                'tl.fromTo("#p%d",{scale:1,opacity:.92},{scale:1.035,opacity:1,duration:%.3f,'
                'ease:"sine.inOut",immediateRender:false},%.3f);' % (index, seg, t)
                if not flip else
                'tl.fromTo("#p%d",{scale:1.035,opacity:1},{scale:1,opacity:.92,duration:%.3f,'
                'ease:"sine.inOut",immediateRender:false},%.3f);' % (index, seg, t)
            )
            flip = not flip
            t += seg

    # Faster grid drift (one cell repeatedly) also guarantees pixel change.
    t = 0.0
    flip = False
    while t < duration - 0.2:
        seg = min(0.8, duration - 0.2 - t)
        if seg < 0.15:
            break
        if not flip:
            js.append(
                'tl.fromTo("#grid",{x:0,y:0},{x:84,y:-84,duration:%.3f,ease:"none",immediateRender:false},%.3f);'
                % (seg, t)
            )
        else:
            js.append(
                'tl.fromTo("#grid",{x:84,y:-84},{x:0,y:0,duration:%.3f,ease:"none",immediateRender:false},%.3f);'
                % (seg, t)
            )
        flip = not flip
        t += seg

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/><title>Short</title>
<script src="{GSAP_CDN}"></script>
<style>
:root{{--bg:#070d18;--ink:#f6f8fc;--c1:{c1};--c2:{c2};--c1rgb:{c1rgb};--c2rgb:{c2rgb}}}
{CSS}
</style></head><body>
{''.join(body)}
<script>{''.join(js)}</script>
</body></html>"""
