"""
Professional Script Generator
Generates original, engaging scripts with proper storytelling structure
for YouTube Shorts, Instagram Reels, and YouTube Long-form Explainers.
"""
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

from src.video_config import VIDEO_FORMATS, get_format
from src.ai_generator import AIGenerator


@dataclass
class ScriptSegment:
    """A segment of the script with timing and visual notes"""
    segment_id: str
    title: str
    content: str
    narration: str
    duration: float
    start_time: float
    end_time: float
    visual_description: str
    animation_type: str
    hook_level: int
    b_roll_suggestion: Optional[str] = None


@dataclass
class VideoScript:
    """Complete video script"""
    script_id: str
    title: str
    topic: str
    format_key: str
    format_config: Dict[str, Any]
    total_duration: float
    hook: str
    introduction: str
    body_segments: List[ScriptSegment]
    conclusion: str
    call_to_action: Optional[str]
    narration_full: str
    visual_theme: str
    color_palette: str
    created_at: str
    source_topic: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScriptGenerator:
    """Generates professional video scripts with storytelling structure"""

    def __init__(self, ai_generator: Optional[AIGenerator] = None):
        self.ai = ai_generator or AIGenerator()
        self.output_dir = Path(__file__).resolve().parent.parent / "output" / "scripts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_script(
        self,
        topic: str,
        format_key: str = "youtube_shorts",
        visual_theme: str = "dark_tech",
        color_palette: str = "dark_tech",
        source_topic: Optional[Dict[str, Any]] = None,
        used_topics: Optional[List[str]] = None,
    ) -> VideoScript:
        fmt = get_format(format_key)
        script_id = self._generate_script_id(topic, format_key)

        if format_key in ("youtube_shorts", "instagram_reels"):
            script = self._generate_short_form_script(
                topic, format_key, fmt, script_id, visual_theme, color_palette,
                source_topic, used_topics
            )
        else:
            script = self._generate_long_form_script(
                topic, format_key, fmt, script_id, visual_theme, color_palette,
                source_topic, used_topics
            )

        self._save_script(script)
        return script

    def _generate_long_form_script(
        self,
        topic: str,
        format_key: str,
        fmt: VideoFormat,
        script_id: str,
        visual_theme: str,
        color_palette: str,
        source_topic: Optional[Dict[str, Any]],
        used_topics: Optional[List[str]],
    ) -> VideoScript:
        prompt = f"""
        You are a professional educational video scriptwriter for YouTube long-form content.
        Create a COMPREHENSIVE script for a {fmt.target_duration}-second explainer video.

        TOPIC: {topic}
        FORMAT: {format_key} ({fmt.aspect_ratio}, {fmt.width}x{fmt.height})
        DURATION: {fmt.min_duration}-{fmt.max_duration} seconds (target: {fmt.target_duration}s)

        STORYTELLING STRUCTURE (LONG-FORM):
        1. CINEMATIC OPENING & HOOK (0-15 seconds): Cinematic opening, strong hook
        2. CONTEXT & INTRODUCTION (15-60 seconds): Why this topic matters
        3. FUNDAMENTAL CONCEPTS (60-30% of duration): Core ideas explained
        4. CHAPTERS (30-80% of duration): Logical chapters with examples
        5. PRACTICAL APPLICATIONS (80-90%): Real-world use cases
        6. ADVANCED INSIGHTS (90-95%): Deep dive where relevant
        7. SUMMARY (95-98%): Key learnings recap
        8. CONCLUSION (98-100%): Memorable ending

        REQUIREMENTS:
        - Cinematic opening that establishes authority
        - Logical chapter structure with clear transitions
        - Each chapter should have visual demonstrations
        - Include mathematical equations or diagrams where relevant
        - Narration should be professional, clear, and educational
        - Each segment needs detailed visual descriptions for Manim animations
        - Synchronize narration timing with animation scenes
        - NO generic content - be specific, original, and educational

        OUTPUT FORMAT (JSON):
        {{
            "title": "Video title (max 80 chars)",
            "hook": "Cinematic opening hook (15 seconds)",
            "introduction": "Context and why it matters",
            "segments": [
                {{
                    "title": "Chapter/segment title",
                    "narration": "Narrator text for this segment",
                    "duration": 45.0,
                    "visual_description": "Detailed visual description for Manim animation",
                    "animation_type": "concept|flow|analogy|takeaway|code|chart",
                    "hook_level": 1-5,
                    "b_roll_suggestion": "optional visual reference"
                }}
            ],
            "conclusion": "Summary and key takeaways",
            "call_to_action": "Optional CTA",
            "narration_full": "Complete narration text",
            "visual_theme": "{visual_theme}",
            "color_palette": "{color_palette}"
        }}

        Return ONLY valid JSON. No markdown formatting.
        """

        result = self.ai._generate_with_fallback(
            prompt,
            system_p="You are an expert educational video scriptwriter. Output only valid JSON.",
            temperature=0.7,
        )

        try:
            script_data = json.loads(result)
        except json.JSONDecodeError:
            script_data = self._fallback_long_script(topic, fmt)

        segments = []
        current_time = 0.0
        for i, seg_data in enumerate(script_data.get("segments", [])):
            duration = seg_data.get("duration", 45.0)
            segment = ScriptSegment(
                segment_id=f"{script_id}_seg_{i}",
                title=seg_data.get("title", f"Segment {i+1}"),
                content=seg_data.get("narration", ""),
                narration=seg_data.get("narration", ""),
                duration=duration,
                start_time=current_time,
                end_time=current_time + duration,
                visual_description=seg_data.get("visual_description", ""),
                animation_type=seg_data.get("animation_type", "concept"),
                hook_level=seg_data.get("hook_level", 3),
                b_roll_suggestion=seg_data.get("b_roll_suggestion"),
            )
            segments.append(segment)
            current_time += duration

        total_duration = sum(s.duration for s in segments)

        script = VideoScript(
            script_id=script_id,
            title=script_data.get("title", topic),
            topic=topic,
            format_key=format_key,
            format_config={
                "aspect_ratio": fmt.aspect_ratio,
                "width": fmt.width,
                "height": fmt.height,
                "fps": fmt.fps,
            },
            total_duration=total_duration,
            hook=script_data.get("hook", ""),
            introduction=script_data.get("introduction", ""),
            body_segments=segments,
            conclusion=script_data.get("conclusion", ""),
            call_to_action=script_data.get("call_to_action"),
            narration_full=script_data.get("narration_full", ""),
            visual_theme=visual_theme,
            color_palette=color_palette,
            created_at=datetime.now().isoformat(),
            source_topic=source_topic,
            metadata={
                "generated_by": "ScriptGenerator",
                "format": format_key,
                "theme": visual_theme,
                "palette": color_palette,
            },
        )

        return script

    def _fallback_short_script(self, topic: str, fmt) -> Dict[str, Any]:
        return {
            "title": f"Understanding {topic}",
            "hook": f"Most people get {topic} wrong. Here's why.",
            "introduction": f"{topic} is more important than you think.",
            "segments": [
                {
                    "title": "The Core Concept",
                    "narration": f"Let's break down {topic} in simple terms.",
                    "duration": 30.0,
                    "visual_description": f"Animated diagram showing {topic} core concept",
                    "animation_type": "concept",
                    "hook_level": 4,
                },
                {
                    "title": "Real Example",
                    "narration": f"Here's how {topic} works in practice.",
                    "duration": 30.0,
                    "visual_description": f"Real-world example of {topic}",
                    "animation_type": "analogy",
                    "hook_level": 3,
                },
                {
                    "title": "Key Takeaway",
                    "narration": f"The most important thing about {topic} is...",
                    "duration": 15.0,
                    "visual_description": f"Highlight card with key takeaway about {topic}",
                    "animation_type": "takeaway",
                    "hook_level": 5,
                },
            ],
            "conclusion": f"Now you understand {topic}. Apply it.",
            "call_to_action": "Like and subscribe for more explainers.",
            "narration_full": f"Most people get {topic} wrong. Here's why. {topic} is more important than you think. Let's break down {topic} in simple terms. Here's how {topic} works in practice. The most important thing about {topic} is... Apply it today.",
            "visual_theme": "dark_tech",
            "color_palette": "dark_tech",
        }

    def _fallback_long_script(self, topic: str, fmt) -> Dict[str, Any]:
        return {
            "title": f"The Complete Guide to {topic}",
            "hook": f"{topic} is changing everything. Here's what you need to know.",
            "introduction": f"In this comprehensive guide, we'll explore {topic} from fundamentals to advanced applications.",
            "segments": [
                {
                    "title": "Introduction & Context",
                    "narration": f"Why {topic} matters in today's landscape.",
                    "duration": 60.0,
                    "visual_description": f"Opening cinematic sequence with {topic} title card",
                    "animation_type": "concept",
                    "hook_level": 5,
                },
                {
                    "title": "Core Concepts",
                    "narration": f"The fundamental principles of {topic} explained.",
                    "duration": 120.0,
                    "visual_description": f"Animated diagrams breaking down {topic} components",
                    "animation_type": "concept",
                    "hook_level": 4,
                },
                {
                    "title": "Practical Applications",
                    "narration": f"How {topic} is applied in real-world scenarios.",
                    "duration": 120.0,
                    "visual_description": f"Case studies and real examples of {topic}",
                    "animation_type": "analogy",
                    "hook_level": 4,
                },
                {
                    "title": "Advanced Insights",
                    "narration": f"Advanced techniques and future directions for {topic}.",
                    "duration": 60.0,
                    "visual_description": f"Complex visualizations showing advanced {topic} concepts",
                    "animation_type": "chart",
                    "hook_level": 3,
                },
            ],
            "conclusion": f"Summary of key learnings about {topic}.",
            "call_to_action": "Subscribe for more deep-dive explainers.",
            "narration_full": f"Complete narration about {topic}.",
            "visual_theme": "dark_tech",
            "color_palette": "dark_tech",
        }

    def _save_script(self, script: VideoScript) -> Path:
        script_path = self.output_dir / f"{script.script_id}.json"
        md_path = self.output_dir / f"{script.script_id}.md"

        script_dict = asdict(script)
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script_dict, f, indent=2, ensure_ascii=False)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {script.title}\n\n")
            f.write(f"**Format:** {script.format_key}\n")
            f.write(f"**Duration:** {script.total_duration:.1f} seconds\n")
            f.write(f"**Theme:** {script.visual_theme}\n")
            f.write(f"**Created:** {script.created_at}\n\n")
            f.write(f"## Hook\n\n{script.hook}\n\n")
            f.write(f"## Introduction\n\n{script.introduction}\n\n")
            f.write(f"## Segments\n\n")
            for seg in script.body_segments:
                f.write(f"### {seg.title} ({seg.duration:.1f}s)\n\n")
                f.write(f"{seg.narration}\n\n")
                f.write(f"*Visual:* {seg.visual_description}\n\n")
                f.write(f"*Animation:* {seg.animation_type}\n\n")
            f.write(f"## Conclusion\n\n{script.conclusion}\n\n")
            if script.call_to_action:
                f.write(f"## Call to Action\n\n{script.call_to_action}\n\n")
            f.write(f"## Full Narration\n\n{script.narration_full}\n")

        return script_path

    def _generate_script_id(self, topic: str, format_key: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic_hash = hashlib.md5(topic.encode()).hexdigest()[:8]
        return f"script_{format_key}_{topic_hash}_{timestamp}"