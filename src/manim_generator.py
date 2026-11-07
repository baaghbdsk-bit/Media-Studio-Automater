"""
Manim Dynamic Code Generator for Educational AI Videos.
Produces genuine, mathematically rigorous 3Blue1Brown-style vector animations
for both 9:16 Vertical (Shorts/Reels) and 16:9 Landscape (YouTube Explainers).
"""
import re
from typing import Dict, Any, List

def escape_str(text: str) -> str:
    """Sanitizes text for safe insertion into Python string literals."""
    if not text:
        return ""
    # Remove emojis or characters that Pango might render as tofu
    cleaned = re.sub(r'[^\x00-\x7F]+', ' ', text)
    cleaned = cleaned.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').strip()
    return re.sub(r'\s+', ' ', cleaned)

def generate_short_manim_code(topic: Dict[str, Any], target_duration: float = 75.0) -> str:
    """
    Generates a complete 9:16 Vertical (1080x1920) Manim Scene script.
    Duration: 1 to 3 minutes (60s to 180s, default 75s).
    Optimized for high-impact educational Shorts, Reels, and Pinterest pins.
    """
    title = escape_str(topic.get("title", "AI Architecture"))
    category = escape_str(topic.get("category", "SYSTEMS").upper())
    summary = escape_str(topic.get("summary", "Understanding modern artificial intelligence systems."))
    problem = escape_str(topic.get("problem", "Traditional models run into severe compute bottlenecks."))
    solution = escape_str(topic.get("solution", "Dynamic routing and memory optimization accelerate throughput."))
    pro_tip = escape_str(topic.get("pro_tip", "Always benchmark real latency on live workloads."))

    # Target duration strictly in 60s to 180s range
    target_duration = max(min(target_duration, 180.0), 60.0)

    # Calculate act durations to match target_duration
    t1 = round(target_duration * 0.22, 1)  # Concept & Hook (~16s)
    t2 = round(target_duration * 0.25, 1)  # The Core Bottleneck (~19s)
    t3 = round(target_duration * 0.35, 1)  # The Mechanism & Unlock (~26s)
    t4 = round(target_duration - (t1 + t2 + t3), 1)  # Production Rule (~14s)

    code = f'''from manim import *
import numpy as np

# 9:16 Vertical Configuration
config.pixel_width = 1080
config.pixel_height = 1920
config.frame_width = 9.0
config.frame_height = 16.0
config.frame_rate = 30
config.background_color = "#080C14"

class ShortExplainerScene(Scene):
    def construct(self):
        # ==========================================
        # ACT 1: HERO CONCEPT & INTUITION ({t1}s)
        # ==========================================
        badge = RoundedRectangle(corner_radius=0.15, width=4.0, height=0.6, color="#0284C7")
        badge.set_fill("#0369A1", opacity=0.3)
        badge_txt = Text("{category} BREAKTHROUGH", font_size=20, color="#38BDF8", weight=BOLD)
        badge_group = VGroup(badge, badge_txt).shift(UP * 6.2)

        hero_title = Text("{title}", font_size=36, color="#FFFFFF", weight=BOLD)
        if len("{title}") > 25:
            hero_title.font_size = 28
        hero_title.next_to(badge_group, DOWN, buff=0.4)

        underline = Line(LEFT * 3.5, RIGHT * 3.5, color="#38BDF8", stroke_width=3).next_to(hero_title, DOWN, buff=0.25)

        self.play(FadeIn(badge_group, shift=DOWN*0.3), Write(hero_title), Create(underline), run_time=1.8)

        # Concept Intro Card
        card1 = RoundedRectangle(corner_radius=0.2, width=7.8, height=3.2, color="#1E293B")
        card1.set_fill("#0F172A", opacity=0.85)
        card1.shift(UP * 2.2)

        summary_txt = Text("{summary[:110]}...", font_size=22, color="#E2E8F0", line_spacing=1.3)
        summary_txt.move_to(card1.get_center())
        card1_group = VGroup(card1, summary_txt)

        self.play(FadeIn(card1_group, shift=UP*0.5), run_time=1.5)
        self.wait({max(t1 - 4.5, 1.0)})
        self.play(FadeOut(card1_group), run_time=0.6)

        # ==========================================
        # ACT 2: THE CORE BOTTLENECK ({t2}s)
        # ==========================================
        bot_label = RoundedRectangle(corner_radius=0.15, width=4.2, height=0.6, color="#E11D48")
        bot_label.set_fill("#881337", opacity=0.3)
        bot_label_txt = Text("THE CORE BOTTLENECK", font_size=20, color="#FB7185", weight=BOLD)
        bot_header = VGroup(bot_label, bot_label_txt).shift(UP * 3.6)

        # Visual Demonstration of Bottleneck: Memory Wall / Dense Weight Overload
        dense_box = RoundedRectangle(corner_radius=0.2, width=7.4, height=4.2, color="#E11D48", stroke_width=2)
        dense_box.set_fill("#1C0812", opacity=0.85)
        dense_box.shift(DOWN * 0.2)

        problem_title = Text("Compute Bottleneck", font_size=24, color="#FDA4AF", weight=BOLD)
        problem_title.shift(UP * 1.3)
        problem_desc = Text("{problem[:110]}...", font_size=20, color="#F1F5F9", line_spacing=1.2)
        problem_desc.next_to(problem_title, DOWN, buff=0.35)

        # Memory transfer animated arrows
        wall_line = DashedLine(LEFT * 3.2, RIGHT * 3.2, color="#FB7185", stroke_width=3).next_to(problem_desc, DOWN, buff=0.4)
        warn_txt = Text("CRITICAL VRAM TRANSFER LATENCY", font_size=16, color="#FB7185", weight=BOLD).next_to(wall_line, DOWN, buff=0.15)

        act2_group = VGroup(bot_header, dense_box, problem_title, problem_desc, wall_line, warn_txt)
        self.play(FadeIn(act2_group, shift=UP*0.4), run_time=1.8)
        self.wait({max(t2 - 3.2, 1.5)})
        self.play(FadeOut(act2_group), run_time=0.6)

        # ==========================================
        # ACT 3: THE ARCHITECTURAL UNLOCK ({t3}s)
        # ==========================================
        sol_label = RoundedRectangle(corner_radius=0.15, width=4.6, height=0.6, color="#059669")
        sol_label.set_fill("#064E3B", opacity=0.3)
        sol_label_txt = Text("ENGINEERING UNLOCK", font_size=20, color="#34D399", weight=BOLD)
        sol_header = VGroup(sol_label, sol_label_txt).shift(UP * 3.6)

        # Dynamic Architectural Architecture Visualization
        # Diagram with Router / Active Nodes
        center_router = Circle(radius=0.75, color="#10B981", stroke_width=3)
        center_router.set_fill("#064E3B", opacity=0.85)
        router_txt = Text("Engine\\nCore", font_size=18, color="#A7F3D0")
        router_node = VGroup(center_router, router_txt).shift(UP * 1.5)

        # 3 Output Execution Blocks
        blocks = VGroup()
        for i, name in enumerate(["Fast SRAM", "Dynamic Tile", "Output Token"]):
            b = RoundedRectangle(corner_radius=0.15, width=2.2, height=1.1, color="#10B981")
            b.set_fill("#064E3B", opacity=0.7)
            b_txt = Text(name, font_size=16, color="#ECFDF5")
            b_grp = VGroup(b, b_txt).shift(LEFT * 2.5 + RIGHT * (i * 2.5) + DOWN * 0.8)
            blocks.add(b_grp)

        arrows = VGroup(*[
            Arrow(center_router.get_bottom(), b.get_top(), buff=0.1, color="#34D399", stroke_width=4)
            for b in blocks
        ])

        sol_box = RoundedRectangle(corner_radius=0.2, width=7.8, height=1.8, color="#047857")
        sol_box.set_fill("#022C22", opacity=0.9).shift(DOWN * 2.8)
        sol_txt = Text("{solution[:100]}...", font_size=19, color="#D1FAE5", line_spacing=1.2)
        sol_txt.move_to(sol_box.get_center())

        self.play(FadeIn(sol_header), Create(router_node), run_time=1.2)
        self.play(GrowArrow(arrows[0]), GrowArrow(arrows[1]), GrowArrow(arrows[2]), LaggedStart(*[FadeIn(b) for b in blocks]), run_time=1.5)
        self.play(FadeIn(VGroup(sol_box, sol_txt), shift=UP*0.3), run_time=1.2)
        self.wait({max(t3 - 5.5, 1.5)})

        act3_all = VGroup(sol_header, router_node, blocks, arrows, sol_box, sol_txt)
        self.play(FadeOut(act3_all), run_time=0.6)

        # ==========================================
        # ACT 4: PRODUCTION RULE & BENCHMARKS ({t4}s)
        # ==========================================
        rule_border = RoundedRectangle(corner_radius=0.25, width=8.0, height=4.2, color="#38BDF8", stroke_width=3)
        rule_border.set_fill("#0B192C", opacity=0.92)
        rule_border.shift(UP * 0.2)

        rule_tag = Text("PRODUCTION DEPLOYMENT RULE", font_size=20, color="#38BDF8", weight=BOLD).shift(UP * 1.6)
        rule_text = Text("{pro_tip[:120]}...", font_size=20, color="#F8FAFC", line_spacing=1.3).next_to(rule_tag, DOWN, buff=0.4)

        bench_badge = RoundedRectangle(corner_radius=0.2, width=7.2, height=1.0, color="#10B981")
        bench_badge.set_fill("#064E3B", opacity=0.9).next_to(rule_text, DOWN, buff=0.4)
        bench_txt = Text("Live 260+ Models: app.neubench.workers.dev", font_size=18, color="#ECFDF5", weight=BOLD).move_to(bench_badge.get_center())

        act4_group = VGroup(rule_border, rule_tag, rule_text, bench_badge, bench_txt)
        self.play(FadeIn(act4_group, shift=UP*0.4), run_time=1.5)
        self.wait({max(t4 - 2.5, 1.5)})
        self.play(FadeOut(act4_group), FadeOut(hero_title), FadeOut(badge_group), FadeOut(underline), run_time=0.6)
'''
    return code


def generate_explainer_manim_code(topic: Dict[str, Any], target_duration: float = 330.0) -> str:
    """
    Generates a complete 16:9 Landscape (1920x1080) Manim Scene script.
    Comprehensive 5 to 10 minute mathematical & architectural deep-dive for YouTube.
    Duration strictly clamped between 300.0s (5m) and 600.0s (10m).
    """
    title = escape_str(topic.get("title", "Frontier AI Architecture"))
    category = escape_str(topic.get("category", "SYSTEMS").upper())
    summary = escape_str(topic.get("summary", "Complete engineering breakdown of frontier AI architectures."))
    problem = escape_str(topic.get("problem", "Memory bandwidth and parameter scaling bottlenecks."))
    solution = escape_str(topic.get("solution", "Mathematical formulation and architectural decomposition."))
    pro_tip = escape_str(topic.get("pro_tip", "Production rules for scaling and deployment."))

    target_duration = max(min(target_duration, 600.0), 300.0)
    c1 = round(target_duration * 0.18, 1)  # Chapter 1 (~60s)
    c2 = round(target_duration * 0.22, 1)  # Chapter 2 (~72s)
    c3 = round(target_duration * 0.22, 1)  # Chapter 3 (~72s)
    c4 = round(target_duration * 0.20, 1)  # Chapter 4 (~66s)
    c5 = round(target_duration - (c1 + c2 + c3 + c4), 1)  # Chapter 5 (~60s)

    code = f'''from manim import *
import numpy as np

# 16:9 Widescreen Configuration (1920x1080)
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_width = 16.0
config.frame_height = 9.0
config.frame_rate = 30
config.background_color = "#070B14"

class LongExplainerScene(Scene):
    def construct(self):
        # ----------------------------------------------------
        # CHAPTER 1: INTRO & THE SCALING DILEMMA ({c1}s)
        # ----------------------------------------------------
        ch1_tag = Text("CHAPTER 1 // THE SCALING DILEMMA", font_size=20, color="#38BDF8", weight=BOLD).to_corner(UL, buff=0.8)
        title_txt = Text("{title}", font_size=42, color="#FFFFFF", weight=BOLD).shift(UP * 2.0)
        sub_txt = Text("{summary[:110]}...", font_size=22, color="#94A3B8").next_to(title_txt, DOWN, buff=0.35)

        self.play(FadeIn(ch1_tag), Write(title_txt), FadeIn(sub_txt), run_time=2.5)

        # Coordinate axes showing traditional exponential scaling cost
        axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 100, 20],
            x_length=6.5,
            y_length=3.2,
            axis_config={{"color": "#475569"}},
        ).shift(DOWN * 1.6 + LEFT * 2.5)

        curve_dense = axes.plot(lambda x: 1.2 * (x**2), color="#F43F5E", x_range=[0, 8.8])
        dense_label = Text("Dense Architecture: O(N^2) Latency", font_size=17, color="#FB7185").next_to(curve_dense, UP, buff=0.2)

        curve_sparse = axes.plot(lambda x: 4.5 * x, color="#10B981", x_range=[0, 9.5])
        sparse_label = Text("Optimized Unlock: O(N) Linear", font_size=17, color="#34D399").next_to(curve_sparse, RIGHT, buff=0.2)

        self.play(Create(axes), Create(curve_dense), Write(dense_label), run_time=3.0)
        self.play(Create(curve_sparse), Write(sparse_label), run_time=2.5)
        self.wait({max(c1 - 10.0, 5.0)})
        self.play(FadeOut(VGroup(ch1_tag, title_txt, sub_txt, axes, curve_dense, dense_label, curve_sparse, sparse_label)), run_time=1.0)

        # ----------------------------------------------------
        # CHAPTER 2: MATHEMATICAL DECOMPOSITION ({c2}s)
        # ----------------------------------------------------
        ch2_tag = Text("CHAPTER 2 // FORMAL MATHEMATICAL DECOMPOSITION", font_size=20, color="#818CF8", weight=BOLD).to_corner(UL, buff=0.8)
        self.play(FadeIn(ch2_tag), run_time=1.0)

        # Draw Tensor / Matrix Block Decomposition
        m_base = RoundedRectangle(corner_radius=0.2, width=4.5, height=3.5, color="#6366F1")
        m_base.set_fill("#1E1B4B", opacity=0.85).shift(LEFT * 4.5 + DOWN * 0.2)
        m_base_txt = Text("Base Weights W\\n[d x k]\\nFROZEN", font_size=22, color="#E0E7FF")
        m_base_grp = VGroup(m_base, m_base_txt)

        plus_sign = Text("+", font_size=48, color="#FFFFFF").shift(LEFT * 1.2 + DOWN * 0.2)

        m_a = RoundedRectangle(corner_radius=0.15, width=1.4, height=3.5, color="#10B981")
        m_a.set_fill("#064E3B", opacity=0.85).shift(RIGHT * 0.5 + DOWN * 0.2)
        m_a_txt = Text("A\\n[d x r]", font_size=18, color="#D1FAE5")
        m_a_grp = VGroup(m_a, m_a_txt)

        mult_dot = Text("x", font_size=28, color="#FFFFFF").shift(RIGHT * 1.8 + DOWN * 0.2)

        m_b = RoundedRectangle(corner_radius=0.15, width=3.5, height=1.4, color="#10B981")
        m_b.set_fill("#064E3B", opacity=0.85).shift(RIGHT * 4.2 + DOWN * 0.2)
        m_b_txt = Text("B [r x k]", font_size=18, color="#D1FAE5")
        m_b_grp = VGroup(m_b, m_b_txt)

        formula_desc = Text("{solution[:110]}...", font_size=21, color="#F8FAFC").shift(DOWN * 3.0)

        self.play(FadeIn(m_base_grp), Write(plus_sign), FadeIn(m_a_grp), Write(mult_dot), FadeIn(m_b_grp), run_time=3.5)
        self.play(FadeIn(formula_desc), run_time=1.5)
        self.wait({max(c2 - 8.0, 5.0)})
        self.play(FadeOut(VGroup(ch2_tag, m_base_grp, plus_sign, m_a_grp, mult_dot, m_b_grp, formula_desc)), run_time=1.0)

        # ----------------------------------------------------
        # CHAPTER 3: DYNAMIC TENSOR ROUTING & MEMORY ACCESS ({c3}s)
        # ----------------------------------------------------
        ch3_tag = Text("CHAPTER 3 // DYNAMIC TENSOR ROUTING & SRAM TILES", font_size=20, color="#34D399", weight=BOLD).to_corner(UL, buff=0.8)
        self.play(FadeIn(ch3_tag), run_time=1.0)

        core_node = Circle(radius=1.0, color="#10B981", stroke_width=3)
        core_node.set_fill("#064E3B", opacity=0.85).shift(LEFT * 4.0)
        core_txt = Text("Dispatch\\nRouter", font_size=20, color="#D1FAE5")
        core_grp = VGroup(core_node, core_txt)

        tiles = VGroup()
        for idx, tname in enumerate(["SRAM Tile 0", "SRAM Tile 1", "SRAM Tile 2"]):
            tile_rect = RoundedRectangle(corner_radius=0.15, width=4.0, height=1.1, color="#0284C7")
            tile_rect.set_fill("#082F49", opacity=0.85)
            tile_lbl = Text(tname, font_size=18, color="#BAE6FD")
            tile_grp = VGroup(tile_rect, tile_lbl).shift(RIGHT * 2.5 + UP * (1.4 - idx * 1.4))
            tiles.add(tile_grp)

        route_arrows = VGroup(*[
            Arrow(core_node.get_right(), t.get_left(), buff=0.2, color="#38BDF8", stroke_width=3)
            for t in tiles
        ])

        routing_note = Text("Direct on-chip SRAM fused kernels prevent high-latency DRAM round-trips", font_size=19, color="#E2E8F0").shift(DOWN * 3.0)

        self.play(Create(core_grp), run_time=1.5)
        self.play(LaggedStart(*[GrowArrow(a) for a in route_arrows], lag_ratio=0.3), FadeIn(tiles), run_time=2.5)
        self.play(FadeIn(routing_note), run_time=1.2)
        self.wait({max(c3 - 7.5, 5.0)})
        self.play(FadeOut(VGroup(ch3_tag, core_grp, tiles, route_arrows, routing_note)), run_time=1.0)

        # ----------------------------------------------------
        # CHAPTER 4: HARDWARE PROFILING & COMPUTE EFFICIENCY ({c4}s)
        # ----------------------------------------------------
        ch4_tag = Text("CHAPTER 4 // HARDWARE PROFILING & FLOP UTILIZATION", font_size=20, color="#F59E0B", weight=BOLD).to_corner(UL, buff=0.8)
        self.play(FadeIn(ch4_tag), run_time=1.0)

        bar_frame = RoundedRectangle(corner_radius=0.2, width=12.0, height=3.6, color="#D97706", stroke_width=2)
        bar_frame.set_fill("#1F1501", opacity=0.85).shift(UP * 0.2)

        p1_bar = RoundedRectangle(corner_radius=0.1, width=3.5, height=0.7, color="#EF4444").set_fill("#7F1D1D", opacity=0.9).shift(LEFT * 2.0 + UP * 0.9)
        p1_txt = Text("Legacy Baseline: 28% MFU (Memory Bound)", font_size=17, color="#FECACA").next_to(p1_bar, RIGHT, buff=0.3)

        p2_bar = RoundedRectangle(corner_radius=0.1, width=8.5, height=0.7, color="#10B981").set_fill("#064E3B", opacity=0.9).shift(LEFT * 0.0 + DOWN * 0.5)
        p2_txt = Text("Optimized Pipeline: 74% MFU (Compute Bound)", font_size=17, color="#D1FAE5").next_to(p2_bar, RIGHT, buff=0.3)

        hw_sub = Text("Slashing memory overhead unlocks peak Tensor Core compute throughput", font_size=19, color="#FDE68A").shift(DOWN * 2.8)

        self.play(FadeIn(bar_frame), run_time=1.0)
        self.play(FadeIn(p1_bar), Write(p1_txt), run_time=1.8)
        self.play(FadeIn(p2_bar), Write(p2_txt), run_time=2.0)
        self.play(FadeIn(hw_sub), run_time=1.2)
        self.wait({max(c4 - 8.0, 5.0)})
        self.play(FadeOut(VGroup(ch4_tag, bar_frame, p1_bar, p1_txt, p2_bar, p2_txt, hw_sub)), run_time=1.0)

        # ----------------------------------------------------
        # CHAPTER 5: BENCHMARK BREAKDOWN & PRODUCTION PLAYBOOK ({c5}s)
        # ----------------------------------------------------
        ch5_tag = Text("CHAPTER 5 // PRODUCTION BENCHMARKS & NEUBENCH", font_size=20, color="#10B981", weight=BOLD).to_corner(UL, buff=0.8)
        self.play(FadeIn(ch5_tag), run_time=1.0)

        card_rule = RoundedRectangle(corner_radius=0.25, width=13.0, height=2.8, color="#10B981", stroke_width=2)
        card_rule.set_fill("#06281E", opacity=0.92).shift(UP * 0.8)
        rule_head = Text("CRITICAL PRODUCTION ENGINEERING TAKEAWAY", font_size=22, color="#34D399", weight=BOLD).shift(UP * 1.5)
        rule_desc = Text("{pro_tip}", font_size=22, color="#ECFDF5", line_spacing=1.3).next_to(rule_head, DOWN, buff=0.4)

        link_box = RoundedRectangle(corner_radius=0.2, width=11.0, height=1.2, color="#38BDF8")
        link_box.set_fill("#0B1E3B", opacity=0.9).shift(DOWN * 1.8)
        link_txt = Text("Compare 260+ Live Model Benchmarks: https://app.neubench.workers.dev", font_size=21, color="#E0F2FE", weight=BOLD)
        link_txt.move_to(link_box.get_center())

        self.play(FadeIn(VGroup(card_rule, rule_head, rule_desc), shift=UP*0.3), run_time=2.0)
        self.play(FadeIn(VGroup(link_box, link_txt), shift=UP*0.2), run_time=1.5)
        self.wait({max(c5 - 6.5, 5.0)})
        self.play(FadeOut(VGroup(ch5_tag, card_rule, rule_head, rule_desc, link_box, link_txt)), run_time=1.0)
'''
    return code
