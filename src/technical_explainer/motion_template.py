"""
Premium Motion-Graphics Explainer Template.

Generates a 1080x1920 (9:16) HTML/SVG motion-graphics studio that is driven
deterministically frame-by-frame through ``window.renderFrame(frame, time)``.

Design goals (vs. the old WebGL primitive scene):
- Full-frame editorial composition (no dead zones)
- Crisp SVG diagrams that actually explain the narration
- Kinetic typography, staggered reveals, smooth eased motion
- Glass HUD, color-graded background, film grain
- No placeholder 3D mascot
"""
import base64
import io
import json
import random
from typing import Any, Dict, List

_FONTS = [
    ("Inter 400", 400, "fonts/inter-400.woff2"),
    ("Inter 600", 600, "fonts/inter-600.woff2"),
    ("Inter 700", 700, "fonts/inter-700.woff2"),
    ("Inter 800", 800, "fonts/inter-800.woff2"),
    ("Inter 900", 900, "fonts/inter-900.woff2"),
]


def _grain_data_uri() -> str:
    """Tiny tileable grayscale noise tile used as a film-grain overlay."""
    try:
        from PIL import Image

        w = h = 140
        rnd = random.Random(1337)
        img = Image.new("L", (w, h))
        img.putdata([rnd.randint(0, 255) for _ in range(w * h)])
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


def _font_faces() -> str:
    rules = []
    for _name, weight, path in _FONTS:
        rules.append(
            "@font-face{font-family:'StudioSans';font-style:normal;"
            f"font-weight:{weight};src:url('{path}') format('woff2');font-display:block;}}"
        )
    return "\n".join(rules)


_SCENE_GROUPS = r"""
<!-- ===================== ECOSYSTEM ===================== -->
<g class="scene-grp" data-kind="ecosystem" transform="translate(0,90)">
  <text x="540" y="112" class="t-label" text-anchor="middle">DUAL-CHAIN ARCHITECTURE</text>
  <path class="beam-glow" d="M330 500 C 430 400, 650 400, 750 500"/>
  <path class="beam-core" d="M330 500 C 430 400, 650 400, 750 500"/>
  <circle class="eco-packet" r="9" fill="#fbbf24"/>
  <circle class="eco-packet2" r="6" fill="#fde68a"/>
  <g transform="translate(300,500)">
    <g class="eco-ring"><circle r="122" class="ring-stroke"/><circle r="156" class="ring-stroke faint"/></g>
    <circle r="92" class="node-fill glow"/>
    <circle r="70" class="hub-inner"/>
    <text y="20" class="t-hub" text-anchor="middle">B</text>
  </g>
  <text x="300" y="712" class="t-title" text-anchor="middle">BEACON CHAIN</text>
  <text x="300" y="748" class="t-fine" text-anchor="middle">GOVERNANCE LAYER</text>
  <g transform="translate(780,500)">
    <g class="eco-ring2"><circle r="122" class="ring-stroke"/><circle r="156" class="ring-stroke faint"/></g>
    <circle r="92" class="node-fill glow"/>
    <circle r="70" class="hub-inner"/>
    <text y="20" class="t-hub" text-anchor="middle">C</text>
  </g>
  <text x="780" y="712" class="t-title" text-anchor="middle">SMART CHAIN</text>
  <text x="780" y="748" class="t-fine" text-anchor="middle">EVM EXECUTION</text>
  <g class="anim" data-d="0.15">
    <rect x="430" y="292" width="220" height="48" rx="24" class="chip"/>
    <text x="540" y="323" class="t-chip" text-anchor="middle">BSC TOKEN HUB</text>
  </g>
</g>

<!-- ===================== BRIDGE FLOW ===================== -->
<g class="scene-grp" data-kind="bridge_flow">
  <text x="540" y="132" class="t-label" text-anchor="middle">LOCK &#183; VERIFY &#183; MINT</text>
  <g class="anim" data-d="0.00">
    <rect x="85" y="420" width="220" height="170" rx="24" class="node-fill"/>
    <text x="195" y="498" class="t-title" text-anchor="middle">LOCK</text>
    <text x="195" y="538" class="t-fine" text-anchor="middle">VAULT &#183; CHAIN A</text>
  </g>
  <g class="anim" data-d="0.12">
    <rect x="430" y="420" width="220" height="170" rx="24" class="node-fill"/>
    <text x="540" y="498" class="t-title" text-anchor="middle">VERIFY</text>
    <text x="540" y="538" class="t-fine" text-anchor="middle">MERKLE PROOF</text>
  </g>
  <g class="anim" data-d="0.24">
    <rect x="775" y="420" width="220" height="170" rx="24" class="node-fill"/>
    <text x="885" y="498" class="t-title" text-anchor="middle">MINT</text>
    <text x="885" y="538" class="t-fine" text-anchor="middle">HUB &#183; CHAIN B</text>
  </g>
  <path class="flow-arrow" d="M312 505 H420"/>
  <path class="flow-arrow" d="M657 505 H766"/>
  <path class="flow-arrow-head" d="M411 497 L425 505 L411 513"/>
  <path class="flow-arrow-head" d="M757 497 L771 505 L757 513"/>
  <circle class="flow-token" r="11" fill="#fbbf24"/>
  <text x="540" y="690" class="t-fine" text-anchor="middle">ASSET ROUTED ACROSS THE BRIDGE CONDUIT</text>
</g>

<!-- ===================== MERKLE TREE ===================== -->
<g class="scene-grp" data-kind="merkle_tree" transform="translate(0,52)">
  <text x="540" y="92" class="t-label" text-anchor="middle">IAVL MERKLE TREE</text>
  <text x="540" y="128" class="t-fine" text-anchor="middle">CANONICAL ROOT</text>
  <g class="tree-lines">
    <path d="M540 200 L340 380"/><path d="M540 200 L740 380"/>
    <path d="M340 380 L200 560"/><path d="M340 380 L460 560"/>
    <path d="M740 380 L620 560"/><path d="M740 380 L880 560"/>
    <path d="M200 560 L140 760"/><path d="M200 560 L260 760"/>
    <path d="M460 560 L400 760"/><path d="M460 560 L520 760"/>
    <path d="M620 560 L560 760"/><path d="M620 560 L680 760"/>
    <path d="M880 560 L820 760"/><path d="M880 560 L940 760"/>
  </g>
  <g transform="translate(540,200)"><g class="tree-root"><circle r="34" class="node-fill glow"/></g></g>
  <g transform="translate(340,380)"><circle r="22" class="node-soft"/></g>
  <g transform="translate(740,380)"><circle r="22" class="node-soft"/></g>
  <g transform="translate(200,560)"><circle r="17" class="node-soft"/></g>
  <g transform="translate(460,560)"><circle r="17" class="node-soft"/></g>
  <g transform="translate(620,560)"><circle r="17" class="node-soft"/></g>
  <g transform="translate(880,560)"><circle r="17" class="node-soft"/></g>
  <rect x="128" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="247" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="387" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="507" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="547" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="667" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="807" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="927" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
</g>

<!-- ===================== VULNERABILITY ===================== -->
<g class="scene-grp" data-kind="vulnerability" transform="translate(0,52)">
  <text x="540" y="92" class="t-label" text-anchor="middle">ARCHITECTURAL FLAW</text>
  <text x="540" y="128" class="t-fine" text-anchor="middle">INTERMEDIATE BRANCH UNANCHORED</text>
  <g class="tree-lines">
    <path d="M540 200 L340 380" class="dim-line"/><path d="M540 200 L740 380"/>
    <path d="M340 380 L200 560" class="dim-line"/><path d="M340 380 L460 560" class="dim-line"/>
    <path d="M740 380 L620 560" class="hl-line"/><path d="M740 380 L880 560" class="dim-line"/>
    <path d="M200 560 L140 760" class="dim-line"/><path d="M200 560 L260 760" class="dim-line"/>
    <path d="M460 560 L400 760" class="dim-line"/><path d="M460 560 L520 760" class="dim-line"/>
    <path d="M620 560 L560 760" class="hl-line"/><path d="M620 560 L680 760" class="dim-line"/>
    <path d="M880 560 L820 760" class="dim-line"/><path d="M880 560 L940 760" class="dim-line"/>
  </g>
  <path class="missing-anchor" d="M620 560 L540 200"/>
  <g transform="translate(540,200)"><g class="tree-root"><circle r="34" class="node-warn glow"/></g></g>
  <g transform="translate(340,380)"><circle r="22" class="node-soft"/></g>
  <g transform="translate(740,380)"><circle r="24" class="node-hl glow"/></g>
  <g transform="translate(200,560)"><circle r="17" class="node-soft"/></g>
  <g transform="translate(460,560)"><circle r="17" class="node-soft"/></g>
  <g transform="translate(620,560)"><circle r="18" class="node-hl glow"/></g>
  <g transform="translate(880,560)"><circle r="17" class="node-soft"/></g>
  <rect x="128" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="247" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="387" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="507" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="547" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="667" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="807" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <rect x="927" y="748" width="26" height="24" rx="6" class="node-soft leaf"/>
  <g transform="translate(880,300)"><g class="anim" data-d="0.2">
    <path d="M0 -34 L34 26 L-34 26 Z" class="warn-tri"/>
    <text y="16" class="warn-excl" text-anchor="middle">!</text>
  </g></g>
</g>

<!-- ===================== ATTACK ===================== -->
<g class="scene-grp" data-kind="attack_injection">
  <text x="540" y="92" class="t-label" text-anchor="middle">FORGED PROOF INJECTION</text>
  <text x="540" y="128" class="t-fine" text-anchor="middle">LEAF ACCEPTED WITHOUT STATE ANCHOR</text>
  <g class="tree-lines">
    <path d="M540 200 L340 380" class="dim-line"/><path d="M540 200 L740 380"/>
    <path d="M740 380 L620 560"/><path d="M620 560 L680 760"/>
    <path d="M340 380 L200 560" class="dim-line"/><path d="M340 380 L460 560" class="dim-line"/>
    <path d="M200 560 L140 760" class="dim-line"/><path d="M200 560 L260 760" class="dim-line"/>
    <path d="M460 560 L400 760" class="dim-line"/><path d="M460 560 L520 760" class="dim-line"/>
    <path d="M740 380 L880 560" class="dim-line"/>
    <path d="M880 560 L820 760" class="dim-line"/><path d="M880 560 L940 760" class="dim-line"/>
  </g>
  <path class="attack-beam" d="M880 800 L680 760"/>
  <g transform="translate(540,200)"><g class="tree-root"><circle r="30" class="node-fill"/></g></g>
  <g transform="translate(340,380)"><circle r="20" class="node-soft"/></g>
  <g transform="translate(740,380)"><circle r="24" class="node-bad glow"/></g>
  <g transform="translate(200,560)"><circle r="16" class="node-soft"/></g>
  <g transform="translate(460,560)"><circle r="16" class="node-soft"/></g>
  <g transform="translate(620,560)"><circle r="19" class="node-bad glow"/></g>
  <g transform="translate(880,560)"><circle r="16" class="node-soft"/></g>
  <rect x="667" y="748" width="26" height="24" rx="6" class="node-bad"/>
  <g transform="translate(880,820)"><g class="forged-node"><path d="M0 -40 L34 0 L0 40 L-34 0 Z" class="forged-fill glow"/></g></g>
  <text x="880" y="900" class="t-fine" text-anchor="middle">FORGED LEAF</text>
  <g transform="translate(540,440)"><g class="anim" data-d="0.45">
    <rect x="-150" y="-40" width="300" height="80" rx="14" class="stamp-box"/>
    <text y="14" class="stamp-text" text-anchor="middle">VALID &#10003; (FORGED)</text>
  </g></g>
</g>

<!-- ===================== FUND DRAIN ===================== -->
<g class="scene-grp" data-kind="fund_drain">
  <text x="540" y="100" class="t-label" text-anchor="middle">CAPITAL FLIGHT</text>
  <text x="540" y="240" class="t-num" id="drain-counter" text-anchor="middle">$0M</text>
  <text x="540" y="286" class="t-fine" id="drain-sub" text-anchor="middle">2,000,000 BNB SIPHONED</text>
  <g transform="translate(540,500)">
    <polygon points="0,-120 104,-60 104,60 0,120 -104,60 -104,-60" class="node-bad glow"/>
    <text y="12" class="t-hub2" text-anchor="middle">VAULT</text>
  </g>
  <path class="drain-line" d="M540 620 L180 800"/>
  <path class="drain-line" d="M540 620 L540 840"/>
  <path class="drain-line" d="M540 620 L900 800"/>
  <g transform="translate(170,820)"><circle r="46" class="node-soft"/><text y="10" class="t-tiny" text-anchor="middle">VENUS</text></g>
  <g transform="translate(540,870)"><circle r="46" class="node-soft"/><text y="10" class="t-tiny" text-anchor="middle">UNISWAP</text></g>
  <g transform="translate(910,820)"><circle r="46" class="node-soft"/><text y="10" class="t-tiny" text-anchor="middle">WALLET</text></g>
</g>

<!-- ===================== PREVENTION ===================== -->
<g class="scene-grp" data-kind="prevention_shield">
  <text x="540" y="96" class="t-label" text-anchor="middle">HARDENED ARCHITECTURE</text>
  <g transform="translate(540,470)">
    <g class="shield-ring"><circle r="210" class="ring-stroke"/><circle r="250" class="ring-stroke faint"/></g>
    <path d="M0 -150 L130 -100 L130 40 C130 110 70 150 0 178 C-70 150 -130 110 -130 40 L-130 -100 Z" class="shield-fill glow"/>
    <path d="M-42 -10 L-6 30 L54 -46" class="shield-check"/>
  </g>
  <text x="540" y="700" class="t-fine" text-anchor="middle">CANONICAL ROOT ENFORCED</text>
  <g transform="translate(200,330)"><circle r="40" class="node-ok"/><path d="M-18 0 L-4 14 L20 -14" class="gate-check"/></g>
  <g transform="translate(880,330)"><circle r="40" class="node-ok"/><path d="M-18 0 L-4 14 L20 -14" class="gate-check"/></g>
  <g transform="translate(540,870)"><circle r="40" class="node-ok"/><path d="M-18 0 L-4 14 L20 -14" class="gate-check"/></g>
  <text x="200" y="404" class="t-tiny" text-anchor="middle">VALIDATOR 1</text>
  <text x="880" y="404" class="t-tiny" text-anchor="middle">VALIDATOR 2</text>
  <text x="540" y="944" class="t-tiny" text-anchor="middle">VALIDATOR 3</text>
  <g class="anim" data-d="0.25">
    <rect x="410" y="752" width="260" height="46" rx="23" class="chip chip-ok"/>
    <text x="540" y="783" class="t-chip" text-anchor="middle">3-of-5 QUORUM</text>
  </g>
</g>
"""

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>__TITLE__</title>
<style>
__FONT_FACES__
:root{
  --accent:#22d3ee; --accent2:#3b82f6;
  --bg0:#04060c; --bg1:#080d18; --ink:#f8fafc; --muted:#9aa8bd; --dim:#5b6b82;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:var(--bg0);
  font-family:'StudioSans','Inter','Segoe UI',system-ui,-apple-system,Arial,sans-serif;
  color:var(--ink);-webkit-font-smoothing:antialiased}
#page{position:relative;width:1080px;height:1920px;overflow:hidden;
  background:
    radial-gradient(120% 80% at 50% 8%, rgba(30,64,120,0.28) 0%, rgba(6,10,20,0) 55%),
    radial-gradient(90% 60% at 50% 100%, rgba(10,20,40,0.55) 0%, rgba(4,6,12,0) 60%),
    linear-gradient(180deg,#05080f 0%,#04060c 45%,#02040a 100%);}
#glow{position:absolute;left:50%;top:760px;width:1200px;height:1200px;margin-left:-600px;
  margin-top:-600px;border-radius:50%;opacity:.5;
  background:radial-gradient(circle, color-mix(in srgb, var(--accent) 22%, transparent) 0%, transparent 60%);
  transition:none;pointer-events:none;will-change:transform}
#topbar{position:absolute;top:64px;left:64px;right:64px;display:flex;align-items:center;justify-content:space-between}
.pill{display:flex;align-items:center;gap:12px;padding:11px 24px;border-radius:999px;
  background:rgba(34,211,238,.08);border:1px solid color-mix(in srgb,var(--accent) 55%, transparent);
  color:color-mix(in srgb,var(--accent) 88%, white);font-size:19px;font-weight:800;letter-spacing:2.4px;
  text-transform:uppercase;box-shadow:0 0 22px color-mix(in srgb,var(--accent) 22%, transparent)}
.pill .dot{width:10px;height:10px;border-radius:50%;background:var(--accent);
  box-shadow:0 0 10px var(--accent);animation:none}
.brand{font-size:21px;font-weight:900;letter-spacing:3px;color:#6d7e96}
.brand b{color:#c7d5ea;font-weight:900}
#inspector{position:absolute;top:160px;left:64px;max-width:560px;
  background:rgba(12,19,34,.72);border:1px solid rgba(120,160,210,.20);
  border-left:4px solid var(--accent);border-radius:14px;padding:15px 24px}
#inspector .ib{font-size:14px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
  color:color-mix(in srgb,var(--accent) 85%, white)}
#inspector .im{font-size:21px;font-weight:700;color:#dbe6f5;margin-top:4px;line-height:1.25}

#stage-wrap{position:absolute;top:280px;left:0;width:1080px;height:1000px}
#stage{width:1080px;height:1000px;display:block;overflow:visible;transform:scale(1.15);transform-origin:50% 0%}
.scene-grp{display:none}
.scene-grp.active{display:block}
.anim{transform-box:fill-box;transform-origin:center;opacity:0}

/* --- shared svg styles --- */
.t-label{fill:#7d8ea6;font-size:21px;font-weight:800;letter-spacing:5px}
.t-title{fill:#f8fafc;font-size:30px;font-weight:800;letter-spacing:.5px}
.t-fine{fill:#65758c;font-size:17px;font-weight:700;letter-spacing:2.2px;text-transform:uppercase}
.t-tiny{fill:#9aa8bd;font-size:15px;font-weight:800;letter-spacing:1.5px}
.t-hub{fill:#f8fafc;font-size:64px;font-weight:900}
.t-hub2{fill:#f8fafc;font-size:34px;font-weight:900;letter-spacing:2px}
.t-chip{fill:color-mix(in srgb,var(--accent) 85%, white);font-size:18px;font-weight:800;letter-spacing:2px}
.t-num{fill:#f8fafc;font-size:78px;font-weight:900;letter-spacing:-1px}
.chip{fill:rgba(12,19,34,.82);stroke:color-mix(in srgb,var(--accent) 55%, transparent);stroke-width:1.5}
.chip-ok{stroke:rgba(52,211,153,.6)}
.node-fill{fill:rgba(11,18,32,.94);stroke:var(--accent);stroke-width:2.5}
.node-soft{fill:rgba(18,27,44,.9);stroke:rgba(120,155,200,.35);stroke-width:2}
.node-warn{fill:rgba(40,26,6,.94);stroke:#fbbf24;stroke-width:3}
.node-hl{fill:rgba(46,30,6,.95);stroke:#fbbf24;stroke-width:3}
.node-bad{fill:rgba(40,10,14,.95);stroke:#ef4444;stroke-width:3}
.node-ok{fill:rgba(8,32,24,.95);stroke:#34d399;stroke-width:3}
.ring-stroke{fill:none;stroke:var(--accent);stroke-opacity:.22;stroke-width:2;stroke-dasharray:5 11}
.ring-stroke.faint{stroke-opacity:.10}
.hub-inner{fill:none;stroke:var(--accent2);stroke-opacity:.5;stroke-width:2}
.glow{filter:drop-shadow(0 0 9px color-mix(in srgb,var(--accent) 70%, transparent))}
.beam-glow{fill:none;stroke:var(--accent);stroke-opacity:.20;stroke-width:16;stroke-linecap:round}
.beam-core{fill:none;stroke:var(--accent);stroke-opacity:.85;stroke-width:3.5;stroke-linecap:round}
.tree-lines path{fill:none;stroke:rgba(120,160,210,.5);stroke-width:2.5}
.tree-lines .dim-line{stroke:rgba(90,120,160,.22)}
.tree-lines .hl-line{stroke:#fbbf24;stroke-width:3.5;stroke-opacity:.9}
.flow-arrow{fill:none;stroke:rgba(120,160,210,.5);stroke-width:2.5;stroke-dasharray:2 8;stroke-linecap:round}
.flow-arrow-head{fill:none;stroke:rgba(120,160,210,.6);stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}
.missing-anchor{fill:none;stroke:#fbbf24;stroke-width:2.5;stroke-dasharray:10 12;stroke-opacity:.85}
.warn-tri{fill:rgba(40,26,6,.9);stroke:#fbbf24;stroke-width:2.5;stroke-linejoin:round}
.warn-excl{fill:#fbbf24;font-size:34px;font-weight:900}
.attack-beam{fill:none;stroke:#ef4444;stroke-width:4;stroke-dasharray:12 10;stroke-linecap:round}
.forged-fill{fill:rgba(40,10,14,.95);stroke:#ef4444;stroke-width:3}
.stamp-box{fill:rgba(30,6,10,.55);stroke:#ef4444;stroke-width:3}
.stamp-text{fill:#fca5a5;font-size:26px;font-weight:900;letter-spacing:3px}
.drain-line{fill:none;stroke:rgba(239,68,68,.45);stroke-width:3;stroke-dasharray:3 9;stroke-linecap:round}
.drain-coin{fill:#fbbf24}
.shield-fill{fill:rgba(6,26,22,.85);stroke:#34d399;stroke-width:3}
.shield-check{fill:none;stroke:#34d399;stroke-width:9;stroke-linecap:round;stroke-linejoin:round}
.gate-check{fill:none;stroke:#34d399;stroke-width:5;stroke-linecap:round;stroke-linejoin:round}

/* --- lower third --- */
#lower{position:absolute;left:64px;right:64px;bottom:120px}
#act-pill{display:inline-flex;align-items:center;gap:10px;padding:8px 20px;border-radius:999px;
  background:rgba(34,211,238,.10);border:1px solid color-mix(in srgb,var(--accent) 45%, transparent);
  color:color-mix(in srgb,var(--accent) 82%, white);
  font-size:17px;font-weight:800;letter-spacing:2.6px;text-transform:uppercase}
#scene-title{font-size:57px;font-weight:900;line-height:1.04;letter-spacing:-1.2px;margin-top:20px;
  color:#f8fafc;text-shadow:0 8px 30px rgba(0,0,0,.55)}
#scene-caption{font-size:26px;font-weight:500;line-height:1.42;color:#b3c1d6;margin-top:15px;max-width:940px}
#progress{position:absolute;left:64px;right:64px;bottom:62px;height:6px;border-radius:3px;
  background:rgba(40,55,80,.55);overflow:hidden}
#progress-fill{height:100%;width:0%;border-radius:3px;
  background:linear-gradient(90deg,var(--accent),var(--accent2));box-shadow:0 0 14px var(--accent)}

/* --- code card --- */
#code-card{position:absolute;right:64px;top:150px;width:344px;padding:14px 16px;border-radius:16px;
  background:rgba(6,11,20,.9);border:1px solid rgba(80,130,190,.3);
  box-shadow:0 18px 46px rgba(0,0,0,.6);opacity:0;transform:translateY(12px)}
#code-card .ch{display:flex;align-items:center;justify-content:space-between;padding-bottom:10px;
  border-bottom:1px solid rgba(80,130,190,.2);margin-bottom:10px}
#code-card .ct{font-size:12px;font-weight:800;letter-spacing:1.6px;color:#7fb2dc;text-transform:uppercase}
#code-card .dots{display:flex;gap:5px}
#code-card .dots i{width:9px;height:9px;border-radius:50%}
#code-body{font-family:'Cascadia Code','Consolas','Courier New',monospace;font-size:13.5px;
  line-height:1.5;color:#9fd2f0;white-space:pre-wrap;word-break:break-word}

#grain{position:absolute;inset:0;pointer-events:none;z-index:50;opacity:.055;
  background-image:url('__GRAIN__');background-repeat:repeat;background-size:140px 140px;mix-blend-mode:overlay}
#vig{position:absolute;inset:0;pointer-events:none;z-index:49;
  background:radial-gradient(120% 90% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,.55) 100%)}
</style>
</head>
<body>
<div id="page">
  <div id="glow"></div>

  <div id="topbar">
    <div class="pill"><span class="dot"></span><span>__CATEGORY__</span></div>
    <div class="brand">NEU<b>BENCH</b></div>
  </div>

  <div id="inspector">
    <div class="ib" id="inspector-badge">SYSTEM</div>
    <div class="im" id="inspector-metric">Live telemetry</div>
  </div>

  <div id="stage-wrap">
    <svg id="stage" viewBox="0 0 1080 1000" xmlns="http://www.w3.org/2000/svg">
__SCENE_GROUPS__
    </svg>
  </div>

  <div id="code-card">
    <div class="ch">
      <span class="ct">CODE // INSPECTION</span>
      <span class="dots"><i style="background:#ef4444"></i><i style="background:#f59e0b"></i><i style="background:#10b981"></i></span>
    </div>
    <div id="code-body"></div>
  </div>

  <div id="lower">
    <div id="act-pill">ACT 01 // OVERVIEW</div>
    <div id="scene-title">Loading</div>
    <div id="scene-caption">Preparing the explainer&hellip;</div>
  </div>

  <div id="progress"><div id="progress-fill"></div></div>
  <div id="vig"></div>
  <div id="grain"></div>
</div>

<script>
const TOTAL_FRAMES = __TOTAL_FRAMES__;
const FPS = __FPS__;
const SCENES = __SCENES_JSON__;

const THEME = {
  ecosystem:'cyan', bridge_flow:'cyan', merkle_tree:'cyan',
  vulnerability:'amber', attack_injection:'red', fund_drain:'red', prevention_shield:'emerald'
};
const THEME_CLASS = {cyan:'theme-cyan', amber:'theme-amber', red:'theme-red', emerald:'theme-emerald'};

const stage = document.getElementById('stage');
const glowEl = document.getElementById('glow');
const lowerEl = document.getElementById('lower');
const titleEl = document.getElementById('scene-title');
const captionEl = document.getElementById('scene-caption');
const actEl = document.getElementById('act-pill');
const badgeEl = document.getElementById('inspector-badge');
const metricEl = document.getElementById('inspector-metric');
const progressEl = document.getElementById('progress-fill');
const codeCard = document.getElementById('code-card');
const codeBody = document.getElementById('code-body');

const clamp01 = x => Math.max(0, Math.min(1, x));
const seg = (p,a,b) => clamp01((p-a)/(b-a));
const easeOut = t => 1 - Math.pow(1-t, 3);
const easeInOut = t => t<0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2,3)/2;
function cubicPoint(p0,p1,p2,p3,t){
  const u=1-t;
  return {
    x: u*u*u*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t*t*t*p3[0],
    y: u*u*u*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t*t*t*p3[1]
  };
}

let activeGroup = null;
let activeKind = null;
let lastSceneIndex = -1;

function setTheme(kind){
  const theme = THEME[kind] || 'cyan';
  Object.values(THEME_CLASS).forEach(c => stage.classList.remove(c));
  stage.classList.add(THEME_CLASS[theme]);
  stage.parentElement.style.setProperty('--accent',
      {cyan:'#22d3ee',amber:'#fbbf24',red:'#ef4444',emerald:'#34d399'}[theme]);
  document.documentElement.style.setProperty('--accent',
      {cyan:'#22d3ee',amber:'#fbbf24',red:'#ef4444',emerald:'#34d399'}[theme]);
  document.documentElement.style.setProperty('--accent2',
      {cyan:'#3b82f6',amber:'#f59e0b',red:'#f97316',emerald:'#10b981'}[theme]);
}

function resetGroup(grp){
  if(!grp) return;
  grp.querySelectorAll('.anim').forEach(el => { el.style.opacity = 0; el.style.transform='scale(.94)'; });
}

function activateScene(index){
  const sc = SCENES[index];
  const kind = (sc.active_layer in THEME) ? sc.active_layer : 'ecosystem';
  if(index === lastSceneIndex) return;
  lastSceneIndex = index;
  activeKind = kind;
  setTheme(kind);

  stage.querySelectorAll('.scene-grp').forEach(g => g.classList.remove('active'));
  activeGroup = stage.querySelector('.scene-grp[data-kind="'+kind+'"]');
  if(activeGroup){ activeGroup.classList.add('active'); resetGroup(activeGroup); }

  actEl.textContent = sc.act_tag || 'ACT';
  titleEl.textContent = sc.title || '';
  captionEl.textContent = sc.caption || '';
  badgeEl.textContent = sc.hud_badge || 'SYSTEM STATUS';
  metricEl.textContent = sc.hud_metric || 'Live telemetry';

  if(sc.code_snippet){
    codeBody.textContent = sc.code_snippet;
    codeCard.style.opacity = '1';
  } else {
    codeCard.style.opacity = '0';
  }

  // entrance for lower third
  lowerEl.style.transition = 'none';
  lowerEl.style.opacity = '0';
  lowerEl.style.transform = 'translateY(24px)';
}

function animateLower(p){
  const e = easeOut(seg(p, 0.0, 0.16));
  lowerEl.style.opacity = e.toFixed(3);
  lowerEl.style.transform = 'translateY(' + ((1-e)*24).toFixed(1) + 'px)';
}

function animateEntrance(grp, p){
  if(!grp) return;
  grp.querySelectorAll('.anim').forEach(el => {
    const d = parseFloat(el.dataset.d || '0');
    const e = easeOut(clamp01((p - d) / 0.26));
    el.style.opacity = e.toFixed(3);
    el.style.transform = 'scale(' + (0.94 + 0.06*e).toFixed(4) + ')';
  });
}

function animateContinuous(kind, p, t){
  if(!activeGroup) return;
  const g = activeGroup;

  if(kind === 'ecosystem'){
    const r1 = g.querySelector('.eco-ring');
    const r2 = g.querySelector('.eco-ring2');
    if(r1) r1.setAttribute('transform','rotate(' + (t*26).toFixed(2) + ')');
    if(r2) r2.setAttribute('transform','rotate(' + (-t*20).toFixed(2) + ')');
    const p0=[330,500],p1=[430,400],p2=[650,400],p3=[750,500];
    g.querySelectorAll('.eco-packet,.eco-packet2').forEach((el,i) => {
      const pr = ((t*0.16) + i*0.5) % 1;
      const pt = cubicPoint(p0,p1,p2,p3,pr);
      el.setAttribute('cx', pt.x.toFixed(2));
      el.setAttribute('cy', pt.y.toFixed(2));
    });
  }

  if(kind === 'bridge_flow'){
    const tok = g.querySelector('.flow-token');
    if(tok){
      const pr = (t*0.20) % 1;
      tok.setAttribute('cx', (195 + pr*690).toFixed(2));
      tok.setAttribute('cy', (380 - Math.sin(pr*Math.PI)*12).toFixed(2));
      tok.setAttribute('opacity', (0.35 + 0.65*Math.sin(pr*Math.PI)).toFixed(3));
    }
  }

  if(kind === 'merkle_tree'){
    const root = g.querySelector('.tree-root');
    if(root){
      const s = 1 + Math.sin(t*4.0)*0.05;
      root.setAttribute('transform','scale(' + s.toFixed(3) + ')');
    }
    g.querySelectorAll('.leaf').forEach((el,i) => {
      el.setAttribute('opacity', (0.55 + 0.45*Math.sin(t*3.0 + i*0.7)).toFixed(3));
    });
  }

  if(kind === 'vulnerability'){
    const hl = g.querySelectorAll('.hl-line');
    hl.forEach(el => el.setAttribute('stroke-opacity', (0.45 + 0.45*Math.sin(t*5.0)).toFixed(3)));
    const root = g.querySelector('.tree-root');
    if(root){ const s = 1 + Math.sin(t*6.0)*0.08; root.setAttribute('transform','scale(' + s.toFixed(3) + ')'); }
    const anchor = g.querySelector('.missing-anchor');
    if(anchor) anchor.setAttribute('stroke-dashoffset', (-(t*40)%22).toFixed(2));
  }

  if(kind === 'attack_injection'){
    const forged = g.querySelector('.forged-node');
    if(forged){
      forged.setAttribute('transform','rotate(' + (t*60).toFixed(2) + ')');
      const s = 1 + Math.sin(t*7.0)*0.12;
      forged.setAttribute('transform','rotate(' + (t*60).toFixed(2) + ') scale(' + s.toFixed(3) + ')');
    }
    const beam = g.querySelector('.attack-beam');
    if(beam) beam.setAttribute('stroke-dashoffset', (-(t*60)%22).toFixed(2));
  }

  if(kind === 'fund_drain'){
    const origin = [540,500];
    const dests = [[170,820],[540,870],[910,820]];
    if(!g._coins){
      g._coins = [];
      dests.forEach((d,si) => {
        for(let i=0;i<4;i++){
          const c = document.createElementNS('http://www.w3.org/2000/svg','circle');
          c.setAttribute('r', (6 + (i%2)*2).toString());
          c.setAttribute('class','drain-coin');
          g.appendChild(c);
          g._coins.push({el:c, si:si, i:i});
        }
      });
    }
    g._coins.forEach(c => {
      const pr = ((t*0.22) + c.i*0.25 + c.si*0.13) % 1;
      const e = easeInOut(pr);
      const d = dests[c.si];
      c.el.setAttribute('cx', (origin[0] + (d[0]-origin[0])*e).toFixed(2));
      c.el.setAttribute('cy', (origin[1] + (d[1]-origin[1])*e).toFixed(2));
      c.el.setAttribute('opacity', (0.2 + 0.8*Math.sin(pr*Math.PI)).toFixed(3));
    });
    const counter = g.querySelector('#drain-counter');
    if(counter){
      const val = Math.floor(easeOut(clamp01(p*1.15)) * 566);
      counter.textContent = '$' + val + 'M';
    }
  }

  if(kind === 'prevention_shield'){
    const ring = g.querySelector('.shield-ring');
    if(ring) ring.setAttribute('transform','rotate(' + (t*12).toFixed(2) + ')');
    const checks = g.querySelectorAll('.gate-check');
    checks.forEach((el,i) => {
      const e = easeOut(clamp01((p - 0.25 - i*0.12) / 0.2));
      el.setAttribute('opacity', e.toFixed(3));
    });
  }
}

window.renderFrame = function(frameIndex, timeSeconds){
  const totalDuration = TOTAL_FRAMES / FPS;
  let acc = 0, idx = 0, localP = 0, sceneDur = totalDuration;
  for(let i=0;i<SCENES.length;i++){
    const sc = SCENES[i];
    const d = (sc.fraction || (1/SCENES.length)) * totalDuration;
    if(timeSeconds >= acc && timeSeconds <= acc + d){ idx = i; localP = (timeSeconds-acc)/d; sceneDur = d; break; }
    acc += d; idx = i;
  }
  activeKind = activeKind || 'ecosystem';
  activateScene(idx);

  animateLower(localP);
  animateEntrance(activeGroup, localP);
  animateContinuous(activeKind, localP, timeSeconds);

  progressEl.style.width = ((frameIndex / TOTAL_FRAMES) * 100).toFixed(2) + '%';

  // gentle glow drift
  const gx = 540 + Math.sin(timeSeconds*0.35)*110;
  const gy = 760 + Math.cos(timeSeconds*0.3)*90;
  glowEl.style.left = gx + 'px';
  glowEl.style.top = gy + 'px';

  return true;
};

// initial state
setTheme('ecosystem');
activateScene(0);
window.renderFrame(0, 0);
</script>
</body>
</html>
"""


def generate_motion_html(
    storyboard: Dict[str, Any],
    visemes: List[float],
    total_frames: int,
    fps: int = 30,
) -> str:
    """Build the deterministic motion-graphics studio HTML."""
    title = storyboard.get("title", "Technical Explainer")
    category = storyboard.get("category", "SYSTEMS").upper()
    scenes_json = json.dumps(storyboard.get("scenes", []))

    html = _HTML
    html = html.replace("__TITLE__", title.replace("<", "").replace(">", ""))
    html = html.replace("__CATEGORY__", category)
    html = html.replace("__FONT_FACES__", _font_faces())
    html = html.replace("__SCENE_GROUPS__", _SCENE_GROUPS)
    html = html.replace("__SCENES_JSON__", scenes_json)
    html = html.replace("__TOTAL_FRAMES__", str(int(total_frames)))
    html = html.replace("__FPS__", str(int(fps)))
    html = html.replace("__GRAIN__", _grain_data_uri())
    return html
