"""
Local Production Script: Technical Explainer Engine.
Topic: How Binance Bridge Got Hacked for $566M
Visual Direction: Dark Navy, Cyan, Electric Blue, 7-Scene Narrative Visual Storytelling.
NO git push - local verification only.
"""
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.technical_explainer import TechnicalExplainerStudio

def run_local_explainer_render():
    print("=" * 70, flush=True)
    print("STARTING LOCAL TECHNICAL EXPLAINER PRODUCTION TEST", flush=True)
    print("Topic: How Binance Bridge Got Hacked for $566M", flush=True)
    print("Visual Direction: Premium 3D Technical Explainer (7-Scene Narrative)", flush=True)
    print("=" * 70, flush=True)

    topic_data = {
        "title": "How Binance Bridge Got Hacked for $566M",
        "category": "CRYPTO SECURITY",
        "summary": "In October 2022, an attacker forged Merkle cryptographic proofs to siphon 2 million BNB ($566M) from the Binance cross-chain bridge.",
        "problem": "The BSC Token Hub precompile verified that leaf hashes combined properly into inner nodes, but failed to assert that intermediate branch paths matched the canonical root in state.",
        "solution": "Binance halted the chain, executed BSC hard-fork v1.1.15 to enforce canonical path validation, and installed decentralized multi-signature threshold gates.",
        "pro_tip": "Never deploy custom cryptographic verification precompiles without formal verification and decentralized multi-signature threshold gates."
    }

    start_time = time.time()
    studio = TechnicalExplainerStudio(fps=24)
    result = studio.generate_explainer_video(topic_data, custom_slug="binance_technical_explainer")
    elapsed = time.time() - start_time

    print("\n" + "=" * 70, flush=True)
    print(f"LOCAL EXPLAINER RENDER COMPLETE IN {elapsed:.1f} SECONDS!", flush=True)
    print(f"Video File:  {result['video_path']}", flush=True)
    print(f"Duration:    {result['duration']:.1f}s ({result['frames']} frames @ {result['fps']} fps)", flush=True)
    print(f"File Size:   {result['file_size_mb']} MB", flush=True)
    print(f"Subtitles:   {result['srt_path']}", flush=True)
    print(f"Scenes:      {result['scenes_count']} sequential narrative scenes", flush=True)
    print("=" * 70, flush=True)

    return result

if __name__ == "__main__":
    run_local_explainer_render()
