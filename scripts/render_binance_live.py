"""
Live Production Test: Binance Bridge Exploit 3D Animated Video Generation.
Topic: How Binance Bridge Got Hacked for $566M
Presenter: Nova (3D Humanoid)
Demo: Cryptographic Merkle Tree Verification Exploit
"""
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.presenter_3d import Presenter3DStudio

def run_binance_production_test():
    print("=" * 65)
    print("STARTING LIVE 3D PRESENTER PRODUCTION TEST")
    print("Topic: How Binance Bridge Got Hacked for $566M")
    print("=" * 65)

    topic_data = {
        "title": "How Binance Bridge Got Hacked for $566M",
        "category": "CRYPTO SECURITY",
        "summary": "In October 2022, an attacker forged Merkle cryptographic proofs to drain 2 million BNB ($566M) from the Binance cross-chain bridge.",
        "problem": "The BSC Token Hub bridge precompile failed to validate that intermediate branch hash paths matched the canonical root, allowing the attacker to inject arbitrary leaf nodes.",
        "solution": "Binance halted the chain, hard-forked BSC, and upgraded the IAVL precompile to enforce strict root-path validation and decentralized multi-signature validator gates.",
        "pro_tip": "Never deploy custom cryptographic verification precompiles without formal verification and strict multi-sig time locks."
    }

    start_time = time.time()
    studio = Presenter3DStudio(fps=24)
    result = studio.generate_presenter_video(topic_data, custom_slug="binance_hack_live")
    total_elapsed = time.time() - start_time

    print("\n" + "=" * 65)
    print("PRODUCTION TEST COMPLETED IN", round(total_elapsed, 1), "SECONDS!")
    print("Video File:   ", result["video_path"])
    print("Duration:     ", round(result["duration"], 1), "seconds")
    print("File Size:    ", result["file_size_mb"], "MB")
    print("Subtitles:    ", result["srt_path"])
    print("Visual Demo:  ", result["visual_demo"])
    print("=" * 65)

    return result

if __name__ == "__main__":
    run_binance_production_test()
