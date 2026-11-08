"""
Premium Motion-Graphics Explainer Template — 16:9 Landscape.

Landscape companion to ``motion_template``. It reuses the exact same hand-built
SVG diagrams and per-frame animation logic, but arranges the composition for
1920x1080: diagram on the left, editorial copy and code inspection on the right.

Driven deterministically through ``window.renderFrame(frame, time)``.
"""
import json
from typing import Any, Dict, List

from .motion_template import _SCENE_GROUPS, _font_faces, _grain_data_uri

_WIDE_HTML = r"""<!DOCTYPE html>
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
html,body{width:1920px;height:1080px;overflow:hidden;background:var(--bg0);
  font-family:'StudioSans','Inter','Segoe UI',system-ui,-apple-system,Arial,sans-serif;
  color:var(--ink);-webkit-font-smoothing:antialiased}
#page{position:relative;width:1920px;height:1080px;overflow:hidden;
  background:
    radial-gradient(80% 100% at 26% 42%, rgba(30,64,120,0.26) 0%, rgba(6,10,20,0) 60%),
    radial-gradient(70% 90% at 82% 88%, rgba(10,20,40,0.5) 0%, rgba(4,6,12,0) 65%),
    linear-gradient(105deg,#05080f 0%,#04060c 55%,#02040a 100%);}
#glow{position:absolute;left:500px;top:560px;width:1200px;height:1200px;
  margin-left:-600px;margin-top:-600px;border-radius:50%;opacity:.5;
  background:radial-gradient(circle, color-mix(in srgb, var(--accent) 22%, transparent) 0%, transparent 60%);
  transition:none;pointer-events:none;will-change:transform}
#topbar{position:absolute;top:40px;left:72px;right:72px;display:flex;align-items:center;justify-content:space-between}
.pill{display:flex;align-items:center;gap:10px;padding:9px 20px;border-radius:999px;
  background:rgba(34,211,238,.08);border:1px solid color-mix(in srgb,var(--accent) 55%, transparent);
  color:color-mix(in srgb,var(--accent) 88%, white);font-size:17px;font-weight:800;letter-spacing:2.2px;
  text-transform:uppercase;box-shadow:0 0 22px color-mix(in srgb,var(--accent) 22%, transparent)}
.pill .dot{width:9px;height:9px;border-radius:50%;background:var(--accent);
  box-shadow:0 0 10px var(--accent);animation:none}
.brand{font-size:19px;font-weight:900;letter-spacing:3px;color:#6d7e96}
.brand b{color:#c7d5ea;font-weight:900}
#inspector{position:absolute;top:104px;left:72px;max-width:560px;
  background:rgba(12,19,34,.72);border:1px solid rgba(120,160,210,.20);
  border-left:4px solid var(--accent);border-radius:14px;padding:13px 22px}
#inspector .ib{font-size:13px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
  color:color-mix(in srgb,var(--accent) 85%, white)}
#inspector .im{font-size:19px;font-weight:700;color:#dbe6f5;margin-top:4px;line-height:1.25}

#stage-wrap{position:absolute;top:150px;left:36px;width:960px;height:880px}
#stage{width:1080px;height:1000px;display:block;overflow:visible;
  transform:scale(0.85);transform-origin:0 0}
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

/* --- editorial column --- */
#lower{position:absolute;left:1050px;right:80px;top:170px}
#act-pill{display:inline-flex;align-items:center;gap:10px;padding:8px 18px;border-radius:999px;
  background:rgba(34,211,238,.10);border:1px solid color-mix(in srgb,var(--accent) 45%, transparent);
  color:color-mix(in srgb,var(--accent) 82%, white);
  font-size:16px;font-weight:800;letter-spacing:2.2px;text-transform:uppercase}
#scene-title{font-size:46px;font-weight:900;line-height:1.06;letter-spacing:-1px;margin-top:18px;
  color:#f8fafc;text-shadow:0 8px 30px rgba(0,0,0,.55)}
#scene-caption{font-size:21px;font-weight:500;line-height:1.45;color:#b3c1d6;margin-top:14px;max-width:790px}
#progress{position:absolute;left:72px;right:72px;bottom:44px;height:6px;border-radius:3px;
  background:rgba(40,55,80,.55);overflow:hidden}
#progress-fill{height:100%;width:0%;border-radius:3px;
  background:linear-gradient(90deg,var(--accent),var(--accent2));box-shadow:0 0 14px var(--accent)}

/* --- code card --- */
#code-card{position:absolute;right:80px;top:560px;width:620px;padding:14px 18px;border-radius:16px;
  background:rgba(6,11,20,.9);border:1px solid rgba(80,130,190,.3);
  box-shadow:0 18px 46px rgba(0,0,0,.6);opacity:0;transform:translateY(12px)}
#code-card .ch{display:flex;align-items:center;justify-content:space-between;padding-bottom:10px;
  border-bottom:1px solid rgba(80,130,190,.2);margin-bottom:10px}
#code-card .ct{font-size:12px;font-weight:800;letter-spacing:1.6px;color:#7fb2dc;text-transform:uppercase}
#code-card .dots{display:flex;gap:5px}
#code-card .dots i{width:9px;height:9px;border-radius:50%}
#code-body{font-family:'Cascadia Code','Consolas','Courier New',monospace;font-size:14px;
  line-height:1.55;color:#9fd2f0;white-space:pre-wrap;word-break:break-word}

#grain{position:absolute;inset:0;pointer-events:none;z-index:50;opacity:.055;
  background-image:url('__GRAIN__');background-repeat:repeat;background-size:140px 140px;mix-blend-mode:overlay}
#vig{position:absolute;inset:0;pointer-events:none;z-index:49;
  background:radial-gradient(120% 110% at 40% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,.55) 100%)}
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
const GLOW_CX = __GLOW_CX__;
const GLOW_CY = __GLOW_CY__;
const GLOW_AX = __GLOW_AX__;
const GLOW_AY = __GLOW_AY__;

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
  const accent = {cyan:'#22d3ee',amber:'#fbbf24',red:'#ef4444',emerald:'#34d399'}[theme];
  const accent2 = {cyan:'#3b82f6',amber:'#f59e0b',red:'#f97316',emerald:'#10b981'}[theme];
  stage.parentElement.style.setProperty('--accent', accent);
  document.documentElement.style.setProperty('--accent', accent);
  document.documentElement.style.setProperty('--accent2', accent2);
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
  let acc = 0, idx = 0, localP = 0;
  for(let i=0;i<SCENES.length;i++){
    const sc = SCENES[i];
    const d = (sc.fraction || (1/SCENES.length)) * totalDuration;
    if(timeSeconds >= acc && timeSeconds <= acc + d){ idx = i; localP = (timeSeconds-acc)/d; break; }
    acc += d; idx = i;
  }
  activeKind = activeKind || 'ecosystem';
  activateScene(idx);

  animateLower(localP);
  animateEntrance(activeGroup, localP);
  animateContinuous(activeKind, localP, timeSeconds);

  progressEl.style.width = ((frameIndex / TOTAL_FRAMES) * 100).toFixed(2) + '%';

  const gx = GLOW_CX + Math.sin(timeSeconds*0.35)*GLOW_AX;
  const gy = GLOW_CY + Math.cos(timeSeconds*0.3)*GLOW_AY;
  glowEl.style.left = gx + 'px';
  glowEl.style.top = gy + 'px';

  return true;
};

setTheme('ecosystem');
activateScene(0);
window.renderFrame(0, 0);
</script>
</body>
</html>
"""


def generate_motion_html_wide(
    storyboard: Dict[str, Any],
    visemes: List[float],
    total_frames: int,
    fps: int = 30,
) -> str:
    """Build the deterministic 1920x1080 motion-graphics studio HTML."""
    title = storyboard.get("title", "Technical Explainer")
    category = storyboard.get("category", "SYSTEMS").upper()
    scenes_json = json.dumps(storyboard.get("scenes", []))

    html = _WIDE_HTML
    html = html.replace("__TITLE__", title.replace("<", "").replace(">", ""))
    html = html.replace("__CATEGORY__", category)
    html = html.replace("__FONT_FACES__", _font_faces())
    html = html.replace("__SCENE_GROUPS__", _SCENE_GROUPS)
    html = html.replace("__SCENES_JSON__", scenes_json)
    html = html.replace("__TOTAL_FRAMES__", str(int(total_frames)))
    html = html.replace("__FPS__", str(int(fps)))
    html = html.replace("__GRAIN__", _grain_data_uri())
    html = html.replace("__GLOW_CX__", "500")
    html = html.replace("__GLOW_CY__", "560")
    html = html.replace("__GLOW_AX__", "90")
    html = html.replace("__GLOW_AY__", "60")
    return html
