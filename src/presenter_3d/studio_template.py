"""
Three.js 3D Presenter Studio HTML Generator.
Builds the complete offline WebGL application with:
- 3D Presenter Character ("Nova") with skeletal rig, viseme mouth controls, and gestures
- Topic-specific 3D visual demonstration (Merkle Tree, Neural Network, Chip Architecture)
- Cinematic multi-shot camera controller
- Offline Three.js r128 bundle
"""
import json
from pathlib import Path
from typing import Dict, Any, List


def generate_studio_html(
    storyboard: Dict[str, Any],
    visemes: List[float],
    total_frames: int,
    fps: int = 30
) -> str:
    title = storyboard.get("title", "AI Architecture")
    category = storyboard.get("category", "SYSTEMS").upper()
    demo_type = storyboard.get("demo_type", "NEURAL_NETWORK")
    demo_title = storyboard.get("demo_title", "3D Architectural Demonstration")
    demo_metric = storyboard.get("demo_metric", "Live System Verification")
    pro_tip = storyboard.get("pro_tip", "Always validate production latency.")
    scenes_json = json.dumps(storyboard.get("scenes", []))
    visemes_json = json.dumps(visemes)

    three_js_path = "three.min.js"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>3D Educational Presenter - {title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      width: 1080px;
      height: 1920px;
      overflow: hidden;
      background-color: #050811;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}
    #canvas-container {{
      position: absolute;
      top: 0;
      left: 0;
      width: 1080px;
      height: 1920px;
      z-index: 1;
    }}
    /* Cinematic Broadcast Overlay */
    #ui-overlay {{
      position: absolute;
      top: 0;
      left: 0;
      width: 1080px;
      height: 1920px;
      z-index: 10;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 100px 70px 140px 70px;
    }}
    .header-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .category-badge {{
      background: rgba(6, 182, 212, 0.18);
      border: 2px solid #06B6D4;
      color: #22D3EE;
      padding: 12px 28px;
      border-radius: 999px;
      font-size: 24px;
      font-weight: 800;
      letter-spacing: 2px;
      text-transform: uppercase;
      box-shadow: 0 0 20px rgba(6, 182, 212, 0.35);
    }}
    .brand-tag {{
      font-size: 26px;
      font-weight: 900;
      color: #94A3B8;
      letter-spacing: 3px;
    }}
    .brand-tag span {{ color: #38BDF8; }}
    .title-banner {{
      margin-top: 30px;
    }}
    .main-title {{
      font-size: 52px;
      font-weight: 900;
      line-height: 1.15;
      color: #FFFFFF;
      text-shadow: 0 4px 20px rgba(0,0,0,0.8);
      max-width: 900px;
    }}
    /* Act indicator */
    .act-indicator {{
      position: absolute;
      bottom: 220px;
      left: 70px;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-left: 6px solid #06B6D4;
      padding: 16px 28px;
      border-radius: 12px;
      backdrop-filter: blur(12px);
      transition: all 0.3s ease;
    }}
    .act-tag {{
      font-size: 18px;
      font-weight: 800;
      color: #38BDF8;
      letter-spacing: 2px;
      text-transform: uppercase;
    }}
    .act-text {{
      font-size: 26px;
      font-weight: 800;
      color: #F8FAFC;
      margin-top: 4px;
    }}
    /* Visual demo callout box */
    #demo-callout {{
      position: absolute;
      top: 380px;
      right: 70px;
      width: 440px;
      background: rgba(15, 23, 42, 0.9);
      border: 2px solid rgba(6, 182, 212, 0.5);
      border-radius: 20px;
      padding: 24px;
      backdrop-filter: blur(16px);
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      opacity: 0;
      transition: opacity 0.5s ease;
    }}
    .demo-callout-title {{
      font-size: 20px;
      font-weight: 800;
      color: #22D3EE;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    .demo-callout-desc {{
      font-size: 22px;
      color: #E2E8F0;
      line-height: 1.35;
      margin-top: 8px;
    }}
    /* Floating Takeaway Card */
    #takeaway-card {{
      position: absolute;
      bottom: 340px;
      left: 70px;
      right: 70px;
      background: rgba(6, 30, 25, 0.92);
      border: 2px solid #10B981;
      border-radius: 24px;
      padding: 32px;
      backdrop-filter: blur(20px);
      box-shadow: 0 30px 60px rgba(0,0,0,0.8);
      opacity: 0;
      transition: opacity 0.5s ease;
    }}
    .takeaway-badge {{
      font-size: 20px;
      font-weight: 800;
      color: #34D399;
      letter-spacing: 2px;
      text-transform: uppercase;
    }}
    .takeaway-text {{
      font-size: 26px;
      font-weight: 700;
      color: #ECFDF5;
      line-height: 1.4;
      margin-top: 10px;
    }}
  </style>
  <script src="{three_js_path}"></script>
</head>
<body>
  <div id="canvas-container"></div>

  <div id="ui-overlay">
    <div>
      <div class="header-bar">
        <div class="category-badge">{category} BREAKTHROUGH</div>
        <div class="brand-tag">NEU<span>BENCH</span> LABS</div>
      </div>
      <div class="title-banner">
        <h1 class="main-title">{title}</h1>
      </div>
    </div>

    <div id="demo-callout">
      <div class="demo-callout-title">{demo_title}</div>
      <div class="demo-callout-desc">{demo_metric}</div>
    </div>

    <div id="takeaway-card">
      <div class="takeaway-badge">CRITICAL PRODUCTION RULE</div>
      <div class="takeaway-text">{pro_tip}</div>
    </div>

    <div class="act-indicator">
      <div id="act-tag" class="act-tag">ACT 1 // HOOK</div>
      <div id="act-text" class="act-text">The 566 Million Dollar Exploit</div>
    </div>
  </div>

  <script>
    // =========================================================================
    // 3D EDUCATIONAL PRESENTER STUDIO ENGINE (Three.js WebGL)
    // =========================================================================
    const VISUAL_DEMO_TYPE = "{demo_type}";
    const TOTAL_FRAMES = {total_frames};
    const FPS = {fps};
    const SCENES = {scenes_json};
    const VISEMES = {visemes_json};

    let renderer, scene, camera;
    let character, bones = {{}}, materials = {{}};
    let visualDemoGroup = new THREE.Group();
    let demoNodes = [], demoLines = [];
    let backgroundParticles;

    // Initialize 3D Engine
    function init() {{
      const container = document.getElementById("canvas-container");
      scene = new THREE.Scene();
      scene.background = new THREE.Color("#050811");
      scene.fog = new THREE.FogExp2("#050811", 0.08);

      camera = new THREE.PerspectiveCamera(42, 1080 / 1920, 0.1, 50);
      camera.position.set(0, 1.45, 2.7);

      renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
      renderer.setSize(1080, 1920);
      renderer.setPixelRatio(1);
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.15;
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      container.appendChild(renderer.domElement);

      setupLighting();
      setupEnvironment();
      buildCharacterPresenter();
      buildVisualDemonstration();
      setupParticles();
    }}

    // Cinematic Lighting Setup
    function setupLighting() {{
      const ambientLight = new THREE.AmbientLight("#1E293B", 1.8);
      scene.add(ambientLight);

      // Warm key light
      const keyLight = new THREE.DirectionalLight("#FFFFFF", 2.2);
      keyLight.position.set(-2, 3.5, 3);
      keyLight.castShadow = true;
      scene.add(keyLight);

      // Cyan fill light
      const fillLight = new THREE.DirectionalLight("#06B6D4", 1.5);
      fillLight.position.set(2.5, 2, 2);
      scene.add(fillLight);

      // Strong magenta/cyan rim light for hair and silhouette
      const rimLight = new THREE.DirectionalLight("#38BDF8", 3.0);
      rimLight.position.set(0, 3, -2.5);
      scene.add(rimLight);
    }}

    // Cyber Lab Stage & Environment
    function setupEnvironment() {{
      // Reflective hexagonal platform floor
      const floorGeo = new THREE.CylinderGeometry(4.5, 4.5, 0.3, 32);
      const floorMat = new THREE.MeshStandardMaterial({{
        color: "#0A0F1D",
        roughness: 0.25,
        metalness: 0.85
      }});
      const floor = new THREE.Mesh(floorGeo, floorMat);
      floor.position.y = -0.15;
      floor.receiveShadow = true;
      scene.add(floor);

      // Glowing cyan circular stage ring
      const ringGeo = new THREE.RingGeometry(3.6, 3.75, 48);
      const ringMat = new THREE.MeshBasicMaterial({{ color: "#06B6D4", side: THREE.DoubleSide }});
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      ring.position.y = 0.01;
      scene.add(ring);

      // Background vertical glowing tech pillars
      for (let i = -3; i <= 3; i++) {{
        if (i === 0) continue;
        const colGeo = new THREE.BoxGeometry(0.2, 5.0, 0.2);
        const colMat = new THREE.MeshStandardMaterial({{
          color: "#0F172A",
          emissive: "#0284C7",
          emissiveIntensity: 0.3,
          roughness: 0.3
        }});
        const col = new THREE.Mesh(colGeo, colMat);
        col.position.set(i * 1.5, 2.5, -4.5 + Math.abs(i) * 0.3);
        scene.add(col);
      }}
    }}

    // Build the Stylized 3D Presenter Character ("Nova")
    function buildCharacterPresenter() {{
      character = new THREE.Group();
      character.position.set(0, 0, 0);

      // Materials
      const skinMat = new THREE.MeshStandardMaterial({{ color: "#FBCFE8", roughness: 0.55, metalness: 0.05 }});
      const jacketMat = new THREE.MeshStandardMaterial({{ color: "#0F172A", roughness: 0.4, metalness: 0.3 }});
      const neonTrimMat = new THREE.MeshBasicMaterial({{ color: "#06B6D4" }});
      const hairMat = new THREE.MeshStandardMaterial({{ color: "#1E1B4B", roughness: 0.3, metalness: 0.2 }});
      const eyeWhiteMat = new THREE.MeshBasicMaterial({{ color: "#FFFFFF" }});
      const irisMat = new THREE.MeshBasicMaterial({{ color: "#0284C7" }});
      const pupilMat = new THREE.MeshBasicMaterial({{ color: "#09090B" }});
      const mouthMat = new THREE.MeshBasicMaterial({{ color: "#881337" }});

      // 1. Root & Hips
      const hips = new THREE.Group();
      hips.position.y = 1.0;
      character.add(hips);
      bones.hips = hips;

      // 2. Spine & Torso
      const spine = new THREE.Group();
      hips.add(spine);
      bones.spine = spine;

      // Torso / Jacket
      const torsoGeo = new THREE.CylinderGeometry(0.28, 0.24, 0.65, 16);
      const torso = new THREE.Mesh(torsoGeo, jacketMat);
      torso.position.y = 0.32;
      torso.castShadow = true;
      spine.add(torso);

      // Cyan Jacket Zipper / Trim
      const trimGeo = new THREE.BoxGeometry(0.04, 0.66, 0.05);
      const trim = new THREE.Mesh(trimGeo, neonTrimMat);
      trim.position.set(0, 0.32, 0.26);
      spine.add(trim);

      // NeuBench Badge on Chest
      const badgeGeo = new THREE.CylinderGeometry(0.05, 0.05, 0.02, 16);
      const badgeMat = new THREE.MeshBasicMaterial({{ color: "#38BDF8" }});
      const badge = new THREE.Mesh(badgeGeo, badgeMat);
      badge.rotation.x = Math.PI / 2;
      badge.position.set(-0.14, 0.45, 0.26);
      spine.add(badge);

      // 3. Neck & Head Group
      const neck = new THREE.Group();
      neck.position.y = 0.65;
      spine.add(neck);

      const headGroup = new THREE.Group();
      headGroup.position.y = 0.22;
      neck.add(headGroup);
      bones.head = headGroup;

      // Stylized Head Mesh
      const headGeo = new THREE.SphereGeometry(0.26, 24, 24);
      headGeo.scale(1.0, 1.15, 0.95);
      const headMesh = new THREE.Mesh(headGeo, skinMat);
      headMesh.castShadow = true;
      headGroup.add(headMesh);

      // Stylized Cyber Hair
      const hairGeo = new THREE.SphereGeometry(0.285, 20, 20);
      hairGeo.scale(1.02, 1.05, 1.02);
      const hair = new THREE.Mesh(hairGeo, hairMat);
      hair.position.set(0, 0.08, -0.04);
      headGroup.add(hair);

      // Neon Hair Streak Highlight
      const streakGeo = new THREE.BoxGeometry(0.08, 0.28, 0.06);
      const streak = new THREE.Mesh(streakGeo, neonTrimMat);
      streak.position.set(0.16, 0.12, 0.22);
      streak.rotation.z = -0.3;
      headGroup.add(streak);

      // Expressive Eyes
      bones.eyes = [];
      bones.eyelids = [];
      [-0.09, 0.09].forEach(x => {{
        const eyeG = new THREE.Group();
        eyeG.position.set(x, 0.03, 0.23);

        const white = new THREE.Mesh(new THREE.SphereGeometry(0.045, 16, 16), eyeWhiteMat);
        eyeG.add(white);

        const iris = new THREE.Mesh(new THREE.SphereGeometry(0.026, 16, 16), irisMat);
        iris.position.z = 0.032;
        eyeG.add(iris);

        const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.014, 16, 16), pupilMat);
        pupil.position.z = 0.042;
        eyeG.add(pupil);

        // Blinking Eyelid Plane
        const lidGeo = new THREE.BoxGeometry(0.09, 0.05, 0.02);
        const lid = new THREE.Mesh(lidGeo, skinMat);
        lid.position.set(0, 0.06, 0.04);
        eyeG.add(lid);
        bones.eyelids.push(lid);

        headGroup.add(eyeG);
        bones.eyes.push(eyeG);
      }});

      // Stylized Eyebrows
      bones.brows = [];
      [-0.09, 0.09].forEach(x => {{
        const brow = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.015, 0.02), hairMat);
        brow.position.set(x, 0.10, 0.245);
        brow.rotation.z = x > 0 ? 0.08 : -0.08;
        headGroup.add(brow);
        bones.brows.push(brow);
      }});

      // Active Animated Mouth / Jaw
      const mouthGroup = new THREE.Group();
      mouthGroup.position.set(0, -0.12, 0.235);
      headGroup.add(mouthGroup);
      bones.mouth = mouthGroup;

      const upperLip = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.015, 0.02), skinMat);
      upperLip.position.y = 0.015;
      mouthGroup.add(upperLip);

      const mouthInterior = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.04, 0.02), mouthMat);
      mouthGroup.add(mouthInterior);
      bones.mouthOpening = mouthInterior;

      const lowerJaw = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.018, 0.02), skinMat);
      lowerJaw.position.y = -0.02;
      mouthGroup.add(lowerJaw);
      bones.jaw = lowerJaw;

      // 4. Arms & Hands Setup (Left & Right)
      bones.leftArm = buildArm(spine, -0.32, 0.55, 1);
      bones.rightArm = buildArm(spine, 0.32, 0.55, -1);

      // 5. Legs Setup
      buildLegs(hips, jacketMat);

      scene.add(character);
    }}

    function buildArm(parent, x, y, side) {{
      const shoulder = new THREE.Group();
      shoulder.position.set(x, y, 0);
      parent.add(shoulder);

      const upperArm = new THREE.Group();
      shoulder.add(upperArm);

      const armMat = new THREE.MeshStandardMaterial({{ color: "#0F172A", roughness: 0.4 }});
      const sleeve = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.065, 0.35, 12), armMat);
      sleeve.position.y = -0.17;
      upperArm.add(sleeve);

      const forearm = new THREE.Group();
      forearm.position.y = -0.35;
      upperArm.add(forearm);

      const forearmMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.055, 0.32, 12), armMat);
      forearmMesh.position.y = -0.16;
      forearm.add(forearmMesh);

      const hand = new THREE.Mesh(new THREE.SphereGeometry(0.055, 12, 12), new THREE.MeshStandardMaterial({{ color: "#FBCFE8" }}));
      hand.position.y = -0.34;
      hand.scale.set(1.0, 1.3, 0.6);
      forearm.add(hand);

      return {{ shoulder, upperArm, forearm, hand }};
    }}

    function buildLegs(parent, mat) {{
      [-0.14, 0.14].forEach(x => {{
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.07, 0.95, 12), mat);
        leg.position.set(x, -0.48, 0);
        parent.add(leg);

        const shoe = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.10, 0.22), new THREE.MeshStandardMaterial({{ color: "#0284C7" }}));
        shoe.position.set(x, -0.95, 0.05);
        parent.add(shoe);
      }});
    }}

    // Build the Topic-Specific 3D Demonstration (Merkle Tree / Neural Network / Chip)
    function buildVisualDemonstration() {{
      visualDemoGroup.position.set(0.75, 1.45, 0);
      scene.add(visualDemoGroup);

      if (VISUAL_DEMO_TYPE === "MERKLE_TREE") {{
        buildMerkleTreeDemo();
      }} else if (VISUAL_DEMO_TYPE === "CHIP_ARCHITECTURE") {{
        buildChipDemo();
      }} else {{
        buildNeuralNetworkDemo();
      }}
    }}

    // 3D Cryptographic Merkle Tree Demo (for Security / Binance Bridge Exploit)
    function buildMerkleTreeDemo() {{
      // Root Node (Top)
      const rootNode = createDemoBlock("ROOT: 0x7F2A... [VERIFIED]", 0, 0.7, 0, "#0284C7");
      demoNodes.push(rootNode);

      // Intermediate Hash Parents
      const p1 = createDemoBlock("Hash A0", -0.5, 0.2, 0, "#0284C7");
      const p2 = createDemoBlock("Hash B0 (IAVL)", 0.5, 0.2, 0, "#0284C7");
      demoNodes.push(p1, p2);

      // Leaf Nodes (Bottom)
      const l1 = createDemoBlock("TX 001", -0.75, -0.35, 0, "#10B981");
      const l2 = createDemoBlock("TX 002", -0.25, -0.35, 0, "#10B981");
      const l3 = createDemoBlock("TX 003", 0.25, -0.35, 0, "#10B981");
      const l4 = createDemoBlock("FORGED LEAF (2M BNB)", 0.75, -0.35, 0, "#EF4444"); // Crimson Forged Leaf
      demoNodes.push(l1, l2, l3, l4);

      // Connect with Glowing Lines
      connectNodes(rootNode, p1);
      connectNodes(rootNode, p2);
      connectNodes(p1, l1);
      connectNodes(p1, l2);
      connectNodes(p2, l3);
      connectNodes(p2, l4, "#EF4444");
    }}

    // 3D Neural Network Architecture Demo
    function buildNeuralNetworkDemo() {{
      const layerCounts = [3, 4, 2];
      const layers = [];
      layerCounts.forEach((count, lIdx) => {{
        const x = (lIdx - 1) * 0.75;
        const layerNodes = [];
        for (let i = 0; i < count; i++) {{
          const y = (i - (count - 1) / 2) * 0.38;
          const node = createDemoSphere(x, y, 0, lIdx === 2 ? "#10B981" : "#0284C7");
          layerNodes.push(node);
          demoNodes.push(node);
        }}
        layers.push(layerNodes);
      }});

      for (let l = 0; l < layers.length - 1; l++) {{
        layers[l].forEach(n1 => {{
          layers[l+1].forEach(n2 => {{
            connectNodes(n1, n2, "#06B6D4");
          }});
        }});
      }}
    }}

    // 3D Chip & SRAM Memory Architecture Demo
    function buildChipDemo() {{
      const substrate = new THREE.Mesh(
        new THREE.BoxGeometry(1.6, 1.2, 0.08),
        new THREE.MeshStandardMaterial({{ color: "#0F172A", metalness: 0.8, roughness: 0.2 }})
      );
      visualDemoGroup.add(substrate);

      const sramTile1 = createDemoBlock("SRAM TILE 0", -0.4, 0.25, 0.08, "#10B981");
      const sramTile2 = createDemoBlock("SRAM TILE 1", 0.4, 0.25, 0.08, "#10B981");
      const coreBlock = createDemoBlock("TENSOR CORES", 0, -0.25, 0.08, "#0284C7");
      demoNodes.push(sramTile1, sramTile2, coreBlock);
      connectNodes(coreBlock, sramTile1, "#34D399");
      connectNodes(coreBlock, sramTile2, "#34D399");
    }}

    function createDemoBlock(label, x, y, z, color) {{
      const group = new THREE.Group();
      group.position.set(x, y, z);

      const geo = new THREE.BoxGeometry(0.38, 0.16, 0.12);
      const mat = new THREE.MeshStandardMaterial({{
        color: color,
        emissive: color,
        emissiveIntensity: 0.35,
        roughness: 0.3
      }});
      const mesh = new THREE.Mesh(geo, mat);
      group.add(mesh);
      visualDemoGroup.add(group);
      return group;
    }}

    function createDemoSphere(x, y, z, color) {{
      const geo = new THREE.SphereGeometry(0.08, 16, 16);
      const mat = new THREE.MeshStandardMaterial({{
        color: color,
        emissive: color,
        emissiveIntensity: 0.5,
        roughness: 0.2
      }});
      const sphere = new THREE.Mesh(geo, mat);
      sphere.position.set(x, y, z);
      visualDemoGroup.add(sphere);
      return sphere;
    }}

    function connectNodes(n1, n2, color = "#06B6D4") {{
      const p1 = n1.position;
      const p2 = n2.position;
      const points = [p1, p2];
      const geo = new THREE.BufferGeometry().setFromPoints(points);
      const mat = new THREE.LineBasicMaterial({{ color: color, linewidth: 2 }});
      const line = new THREE.Line(geo, mat);
      visualDemoGroup.add(line);
      demoLines.push(line);
    }}

    function setupParticles() {{
      const partCount = 120;
      const geo = new THREE.BufferGeometry();
      const pos = new Float32Array(partCount * 3);
      for (let i = 0; i < partCount * 3; i += 3) {{
        pos[i] = (Math.random() - 0.5) * 8;
        pos[i+1] = Math.random() * 4;
        pos[i+2] = (Math.random() - 0.5) * 6;
      }}
      geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      const mat = new THREE.PointsMaterial({{ color: "#38BDF8", size: 0.025, transparent: true, opacity: 0.6 }});
      backgroundParticles = new THREE.Points(geo, mat);
      scene.add(backgroundParticles);
    }}

    // =========================================================================
    // DETERMINISTIC FRAME RENDERER (Invoked frame-by-frame by Playwright)
    // =========================================================================
    window.renderFrame = function(frameIndex, timeSeconds) {{
      // 1. Current Scene & Shot Determination
      let currentScene = SCENES[0] || {{}};
      let sceneProgress = 0;
      let accTime = 0;
      const totalDuration = TOTAL_FRAMES / FPS;

      for (let i = 0; i < SCENES.length; i++) {{
        const sc = SCENES[i];
        const scDur = (sc.fraction || (1.0 / (SCENES.length || 1))) * totalDuration;
        if (timeSeconds >= accTime && timeSeconds <= accTime + scDur) {{
          currentScene = sc;
          sceneProgress = (timeSeconds - accTime) / scDur;
          break;
        }}
        accTime += scDur;
      }}

      // 2. Camera Positioning & Motion
      const cPos = currentScene.camera_pos || [0.0, 1.48, 2.7];
      const cTar = currentScene.camera_target || [0.0, 1.45, 0.0];
      camera.position.set(cPos[0], cPos[1], cPos[2]);
      camera.lookAt(cTar[0], cTar[1], cTar[2]);

      // Subtle dynamic camera drift
      camera.position.x += Math.sin(timeSeconds * 0.4) * 0.03;
      camera.position.y += Math.cos(timeSeconds * 0.3) * 0.02;

      // 3. UI Overlay Updating
      const sceneId = currentScene.scene_id || "ACT 1";
      const actTitle = currentScene.act_title || "";
      document.getElementById("act-tag").innerText = sceneId.toUpperCase().replace(/_/g, " ");
      document.getElementById("act-text").innerText = actTitle;

      const demoCallout = document.getElementById("demo-callout");
      if (currentScene.show_visual_demo) {{
        demoCallout.style.opacity = "1";
        visualDemoGroup.visible = true;
      }} else {{
        demoCallout.style.opacity = "0";
        visualDemoGroup.visible = false;
      }}

      const takeawayCard = document.getElementById("takeaway-card");
      if (currentScene.character_action === "takeaway_hero") {{
        takeawayCard.style.opacity = "1";
      }} else {{
        takeawayCard.style.opacity = "0";
      }}

      // 4. Character Animation & Posing
      const charPos = currentScene.char_pos || [0.0, 0.0, 0.0];
      character.position.set(charPos[0], charPos[1], charPos[2]);

      // Continuous Living Breathing & Posture Sway
      bones.spine.rotation.x = Math.sin(timeSeconds * 1.5) * 0.03;
      bones.spine.position.y = Math.sin(timeSeconds * 1.5) * 0.008;

      // Blinking Engine (Blinks every 100 frames for 4 frames)
      const blinkCycle = frameIndex % 110;
      const isBlinking = blinkCycle >= 104 && blinkCycle <= 108;
      bones.eyelids.forEach(lid => {{
        lid.position.y = isBlinking ? 0.0 : 0.06;
      }});

      // Speech Lip-Sync (Jaw & Mouth controlled frame-by-frame by viseme energy)
      const visemeVal = VISEMES[frameIndex] || 0.0;
      bones.mouthOpening.scale.y = 0.2 + visemeVal * 1.8;
      bones.jaw.position.y = -0.02 - (visemeVal * 0.035);

      // Character Gestures according to Action State
      const action = currentScene.character_action;

      if (action === "point_to_visual") {{
        // Presenter turns torso and points with right arm toward visual demo
        bones.spine.rotation.y = -0.28;
        bones.head.rotation.y = Math.sin(timeSeconds * 1.2) * 0.15 - 0.25;

        // Right Arm Raised & Pointing
        bones.rightArm.shoulder.rotation.x = -1.2;
        bones.rightArm.shoulder.rotation.z = -0.4;
        bones.rightArm.forearm.rotation.x = -0.6;

        // Left arm relaxed
        bones.leftArm.shoulder.rotation.x = 0.1;
        bones.leftArm.shoulder.rotation.z = 0.2;
      }}
      else if (action === "explain_detailed") {{
        // Both hands active at chest level with cadence
        bones.spine.rotation.y = Math.sin(timeSeconds * 1.8) * 0.06;
        bones.head.rotation.y = Math.sin(timeSeconds * 1.2) * 0.08;
        bones.head.rotation.x = Math.sin(timeSeconds * 2.4) * 0.04;

        bones.leftArm.shoulder.rotation.x = -0.7 + Math.sin(timeSeconds * 3.0) * 0.15;
        bones.leftArm.shoulder.rotation.z = 0.35;
        bones.leftArm.forearm.rotation.x = -0.8;

        bones.rightArm.shoulder.rotation.x = -0.7 + Math.cos(timeSeconds * 3.0) * 0.15;
        bones.rightArm.shoulder.rotation.z = -0.35;
        bones.rightArm.forearm.rotation.x = -0.8;
      }}
      else if (action === "takeaway_hero") {{
        // Heroic, confident presentation stance
        bones.spine.rotation.y = 0.0;
        bones.head.rotation.set(0.04, 0.0, 0.0);

        bones.leftArm.shoulder.rotation.set(0.0, 0.0, 0.25);
        bones.leftArm.forearm.rotation.x = -0.2;
        bones.rightArm.shoulder.rotation.set(0.0, 0.0, -0.25);
        bones.rightArm.forearm.rotation.x = -0.2;
      }}
      else {{
        // intro_welcome: Welcoming open hands gesture
        bones.spine.rotation.y = 0.0;
        bones.head.rotation.set(0.02, 0.0, 0.0);

        bones.leftArm.shoulder.rotation.x = -0.4 + Math.sin(timeSeconds * 2.0) * 0.08;
        bones.leftArm.shoulder.rotation.z = 0.3;
        bones.rightArm.shoulder.rotation.x = -0.4 + Math.cos(timeSeconds * 2.0) * 0.08;
        bones.rightArm.shoulder.rotation.z = -0.3;
      }}

      // 5. Visual Demo Animation (Glow pulsation, data particle flow)
      visualDemoGroup.rotation.y = Math.sin(timeSeconds * 0.5) * 0.12;
      demoNodes.forEach((n, idx) => {{
        n.position.y += Math.sin(timeSeconds * 2.0 + idx) * 0.001;
      }});

      // Render Frame
      renderer.render(scene, camera);
      return true;
    }};

    // Start
    init();
    window.renderFrame(0, 0);
  </script>
</body>
</html>
"""
    return html
