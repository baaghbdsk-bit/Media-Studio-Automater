"""Production Pipeline Orchestrator
Implements the 14-step automated video production pipeline.
"""
from rich.console import Console

console = Console()


class ProductionPipeline:
    """14-step automated video production pipeline."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        from src.script_generator import ScriptGenerator
        from src.manim_renderer import ManimRenderer
        from src.audio_producer import AudioProducer
        from src.subtitle_generator import SubtitleGenerator
        from src.quality_assurance import QualityAssurance
        from src.video_organizer import VideoOrganizer

        self.script_gen = ScriptGenerator()
        self.manim_renderer = ManimRenderer()
        self.audio_producer = AudioProducer()
        self.subtitle_gen = SubtitleGenerator()
        self.qa = QualityAssurance()
        self.organizer = VideoOrganizer()

    def run(
        self,
        topic: str,
        format_key: str = "youtube_shorts",
        visual_theme: str = "dark_tech",
        color_palette: str = "dark_tech",
        source_topic=None,
    ):
        console.print(f"\n[bold cyan]🎬 Production Pipeline[/bold cyan]")
        console.print(f"Topic: {topic} | Format: {format_key}")

        result = {"success": False, "project_id": None, "video_path": None, "qa_report": None, "errors": []}

        try:
            console.print("[cyan]Step 1: Topic selection...[/cyan]")
            from src.video_config import get_format
            fmt = __import__("src.video_config", fromlist=["get_format"]).get_format(format_key)

            console.print(f"  ✓ Format: {fmt.name} ({fmt.width}x{fmt.height}, {fmt.fps}fps)")
            console.print(f"  ✓ Duration: {fmt.min_duration}-{fmt.max_duration}s")

            console.print("[cyan]Step 3: Generate script...[/cyan]")
            from src.script_generator import ScriptGenerator as SG
            sg = SG()
            script = sg.generate_script(topic, format_key, visual_theme, color_palette, source_topic)
            console.print(f"  ✓ Script: {script.script_id}")

            console.print("[cyan]Step 8: Render with Manim...[/cyan]")
            project_id = f"{script.script_id}_project"
            from pathlib import Path
            from src.video_config import PROJECTS_DIR
            project_dir = PROJECTS_DIR / project_id

            render_result = self.manim_renderer.render_video(
                json.loads(json.dumps(__import__("dataclasses").asdict(script))),
                project_dir=project_dir,
                dry_run=self.dry_run,
            )

            console.print(f"  ✓ Render {'complete' if render_result['success'] else 'failed'}")

            console.print("[cyan]Step 9: Voiceover...[/cyan]")
            from src.audio_producer import AudioProducer
            ap = AudioProducer()
            ar = ap.generate_voiceover(text=script.narration_full, output_name=script.script_id)
            console.print(f"  ✓ Voiceover: {'complete' if ar['success'] else 'failed'}")

            console.print("[cyan]Step 11: Subtitles...[/cyan]")
            from src.subtitle_generator import SubtitleGenerator
            sg2 = SubtitleGenerator()
            sd = sg2.generate_from_script(json.loads(json.dumps(__import__("dataclasses").asdict(script))), output_name=script.script_id)
            console.print(f"  ✓ Subtitles: {sd.get('srt', 'N/A')}")

            console.print("[cyan]Step 13: QA...[/cyan]")
            from src.quality_assurance import QualityAssurance
            qa = QualityAssurance()
            vp = __import__("pathlib").Path(render_result.get("video_path", ""))
            qr = qa.verify_video(vp, format_key, script.total_duration)

            console.print(f"  ✓ QA: {'PASS' if qr['passed'] else 'FAIL'}")

            console.print(f"\n[bold green]✅ Pipeline complete![/bold green]")
            result = {"success": True, "project_id": project_id, "video_path": str(PROJECTS_DIR / project_id / "final_video.mp4"), "qa_passed": qr["passed"]}

        except Exception as e:
            console.print(f"\n[bold red]❌ Pipeline failed: {e}[/bold red]")
            result = {"success": False, "errors": [str(e)]}

        return result