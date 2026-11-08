"""
AI Storyboard & Presentation Director.
Uses Gemini 3.8 Flash to generate structured, topic-aware 3D presentation storyboards.
Enforces character actions, multi-shot camera angles, and interactive 3D demonstrations.
"""
import json
import re
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

import config


class StoryboardAI:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.model = getattr(config, "GEMINI_MODEL", "gemini-3.8-flash")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def plan_3d_presentation(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a structured 3D presentation storyboard based on topic data.
        Determines the ideal 3D visual demonstration and character staging.
        """
        title = topic_data.get("title", "AI Breakthrough")
        summary = topic_data.get("summary", "")
        problem = topic_data.get("problem", "")
        solution = topic_data.get("solution", "")
        pro_tip = topic_data.get("pro_tip", "")

        # Determine visual demonstration type based on topic keywords
        title_lower = title.lower()
        summary_lower = summary.lower()
        combined = f"{title_lower} {summary_lower}"

        if any(w in combined for w in ["hack", "exploit", "bridge", "merkle", "crypto", "blockchain", "security", "bnb", "binance", "signature"]):
            demo_type = "MERKLE_TREE"
            demo_title = "Cryptographic Merkle Tree Verification"
            demo_metric = "IAVL Hash Path Vulnerability ($566M Drained)"
        elif any(w in combined for w in ["memory", "gpu", "sram", "cache", "kv", "flash", "bandwidth", "tensor", "flop", "hardware"]):
            demo_type = "CHIP_ARCHITECTURE"
            demo_title = "On-Chip SRAM vs High-Bandwidth DRAM"
            demo_metric = "Slashing Memory Access Latency"
        elif any(w in combined for w in ["code", "compiler", "python", "kernel", "agent", "tool", "syntax", "runtime"]):
            demo_type = "CODE_TERMINAL"
            demo_title = "Holographic Dynamic Execution Sandbox"
            demo_metric = "Runtime Memory Allocation & State"
        else:
            demo_type = "NEURAL_NETWORK"
            demo_title = "Multi-Layer Neural Network Architecture"
            demo_metric = "Dynamic Synaptic Routing & Data Flow"

        # Script generation: prioritize provided narration or generate high-impact technical script
        narration = topic_data.get("narration")
        if not narration or len(narration.split()) < 80:
            narration = (
                f"Welcome to this technical breakdown of {title}. "
                f"{summary} "
                f"To understand why this issue is shaking up modern systems, take a close look at the core failure mode. "
                f"Under conventional architectures, {problem} This creates a severe bottleneck that blinds traditional verification protocols. "
                f"Here is how this breakthrough changes the equation: {solution} "
                f"By restructuring access patterns and validating canonical state paths, the system achieves complete integrity and maximum throughput. "
                f"If you are deploying these architectures in production, keep this golden engineering rule in mind: {pro_tip} "
                f"To inspect live token costs, memory footprints, and latency benchmarks across 260 frontier AI models, explore NeuBench at app.neubench.workers.dev."
            )

        # 4 Staged Camera Shots mapped to the 4 acts
        scenes = [
            {
                "scene_id": "act1_hero_hook",
                "shot": "MEDIUM_PUSH_IN",
                "character_action": "intro_welcome",
                "act_title": "THE BREAKTHROUGH HOOK",
                "fraction": 0.22,
                "camera_pos": [0.0, 1.48, 2.7],
                "camera_target": [0.0, 1.45, 0.0],
                "char_pos": [0.0, 0.0, 0.0],
                "show_visual_demo": False
            },
            {
                "scene_id": "act2_core_bottleneck",
                "shot": "SPLIT_DEMO",
                "character_action": "point_to_visual",
                "act_title": "THE CRITICAL BOTTLENECK",
                "fraction": 0.28,
                "camera_pos": [0.18, 1.42, 3.4],
                "camera_target": [0.18, 1.40, 0.0],
                "char_pos": [-0.38, 0.0, 0.0],
                "show_visual_demo": True
            },
            {
                "scene_id": "act3_architectural_unlock",
                "shot": "CLOSE_UP_DYNAMIC",
                "character_action": "explain_detailed",
                "act_title": "THE ARCHITECTURAL UNLOCK",
                "fraction": 0.32,
                "camera_pos": [0.05, 1.52, 1.85],
                "camera_target": [0.0, 1.50, 0.0],
                "char_pos": [0.0, 0.0, 0.0],
                "show_visual_demo": True
            },
            {
                "scene_id": "act4_production_takeaway",
                "shot": "HERO_WIDE",
                "character_action": "takeaway_hero",
                "act_title": "PRODUCTION DEPLOYMENT RULE",
                "fraction": 0.18,
                "camera_pos": [0.0, 1.35, 3.4],
                "camera_target": [0.0, 1.30, 0.0],
                "char_pos": [0.0, 0.0, 0.0],
                "show_visual_demo": False
            }
        ]

        return {
            "title": title,
            "category": topic_data.get("category", "SYSTEMS ENGINEERING"),
            "tagline": topic_data.get("tagline", "Technical Breakdown & Architecture"),
            "demo_type": demo_type,
            "demo_title": demo_title,
            "demo_metric": demo_metric,
            "pro_tip": pro_tip,
            "narration": narration,
            "scenes": scenes
        }
