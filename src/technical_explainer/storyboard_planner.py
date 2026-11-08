"""
Technical Explainer Storyboard & Visual Narrative Planner.
Plans comprehensive, multi-scene technical narratives with:
- Synchronized technical script
- 3D spatial object coordination
- Cinematic camera movements and exploded views
- Scene-specific telemetry, HUD badges, and code snippets
"""
import copy
import re
from typing import Dict, Any, List


class ExplainerStoryboardPlanner:
    def __init__(self):
        pass

    def plan_storyboard(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a 7-act cinematic technical storyboard with deep visual storytelling.
        """
        title = topic_data.get("title", "Technical Architecture Breakdown")
        title_lower = title.lower()

        # Check for crypto bridge hack topic
        if any(w in title_lower for w in ["bridge", "hack", "exploit", "binance", "bnb", "merkle"]):
            return self._plan_binance_bridge_hack(topic_data)
        else:
            return self._plan_generic_systems_explainer(topic_data)

    def _plan_binance_bridge_hack(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        7-Scene Cinematic Storyboard: The Binance Bridge $566M Exploit.
        Follows the exact visual narrative:
        1. Blockchain Ecosystem (BNB Beacon Chain + BSC Smart Chain)
        2. Normal Cross-Chain Asset Transfer (Lock, Relay, Mint)
        3. Smart Contract Architecture Zoom (Cosmos IAVL Merkle Tree)
        4. The Vulnerability Exposed (Unchecked Inner Node Paths)
        5. The Attack Step-by-Step (Forged Proof Injection)
        6. Fund Flow & Drainage ($566M Siphoned Across DeFi)
        7. Security Failure Analysis & Prevention (Canonical Anchoring + Multi-Sig Gates)
        """
        scenes = [
            {
                "scene_id": "scene_1_ecosystem",
                "act_number": 1,
                "act_tag": "ACT 01 // CROSS-CHAIN ECOSYSTEM",
                "title": "Dual-Chain Architecture",
                "caption": "Billions of dollars relied on a single cross-chain bridge: the BSC Token Hub.",
                "fraction": 0.14,
                "camera_pos": [0.0, 2.3, 5.8],
                "camera_target": [0.0, 1.2, 0.0],
                "active_layer": "ecosystem",
                "lighting_mode": "normal_cyan",
                "hud_badge": "CHAIN TOPOLOGY",
                "hud_metric": "Beacon Chain (Gov) <--> Smart Chain (EVM)",
                "code_snippet": None,
                "narration_segment": (
                    "Cross-chain bridges are the financial conduits connecting independent blockchains. "
                    "In the BNB ecosystem, the Beacon Chain handled governance, while the Smart Chain executed EVM smart contracts. "
                    "To move assets between them, billions of dollars relied on a single native module called the BSC Token Hub."
                )
            },
            {
                "scene_id": "scene_2_normal_flow",
                "act_number": 2,
                "act_tag": "ACT 02 // NORMAL ASSET TRANSFER",
                "title": "Lock, Verify & Mint Protocol",
                "caption": "Under normal operation, assets are locked on Chain A and synthetic tokens minted on Chain B.",
                "fraction": 0.14,
                "camera_pos": [0.0, 1.8, 4.4],
                "camera_target": [0.0, 1.0, 0.0],
                "active_layer": "bridge_flow",
                "lighting_mode": "normal_cyan",
                "hud_badge": "TRANSFER PROTOCOL",
                "hud_metric": "Lock Vault A -> Relay Packet -> Mint Hub B",
                "code_snippet": None,
                "narration_segment": (
                    "Under normal operation, when a user transfers funds, tokens are locked in a vault contract on Chain A. "
                    "A relayer passes a cryptographic packet across the bridge conduit to the Token Hub contract on Chain B. "
                    "The bridge verifies a cryptographic signature from consensus validators, and only then mints the synthetic tokens."
                )
            },
            {
                "scene_id": "scene_3_contract_zoom",
                "act_number": 3,
                "act_tag": "ACT 03 // SMART CONTRACT CORE",
                "title": "Cosmos IAVL Merkle Tree",
                "caption": "The bridge contract executes an IAVL precompile to verify cryptographic leaf membership.",
                "fraction": 0.15,
                "camera_pos": [0.0, 1.9, 3.8],
                "camera_target": [0.0, 1.2, 0.0],
                "active_layer": "merkle_tree",
                "lighting_mode": "focus_blue",
                "hud_badge": "CRYPTOGRAPHIC VERIFICATION",
                "hud_metric": "Canonical Root: 0x9e4b... | Tree Depth: 16",
                "code_snippet": (
                    "// Cosmos IAVL Precompile Verification\n"
                    "bool isValid = verifyMerkleProof(\n"
                    "    bytes32 canonicalRoot,\n"
                    "    bytes32 leafHash,\n"
                    "    ProofPath[] path\n"
                    ");"
                ),
                "narration_segment": (
                    "To verify that transactions really happened without trust, the bridge used Cosmos IAVL Merkle Trees. "
                    "A Merkle Tree aggregates thousands of transaction hashes into a single root hash. "
                    "When a withdrawal request arrives, the bridge contract executes a built-in precompile to mathematically prove that the user's transaction leaf belongs to the canonical root."
                )
            },
            {
                "scene_id": "scene_4_vulnerability",
                "act_number": 4,
                "act_tag": "ACT 04 // THE ARCHITECTURAL FLAW",
                "title": "Unchecked Inner Node Paths",
                "caption": "The precompile checked hash combinations but failed to anchor intermediate branches to canonical root state.",
                "fraction": 0.15,
                "camera_pos": [0.25, 1.6, 3.0],
                "camera_target": [0.1, 1.3, 0.0],
                "active_layer": "vulnerability",
                "lighting_mode": "alert_amber",
                "hud_badge": "CRITICAL FLAW DETECTED",
                "hud_metric": "Missing Canonical Path Root Assertion",
                "code_snippet": (
                    "// VULNERABILITY IN PRECOMPILE:\n"
                    "// Computes parent hash but never asserts:\n"
                    "// assert(inner_branch.root == canonical_state_root)\n"
                    "return computeInnerHash(left, right) == intermediate;"
                ),
                "narration_segment": (
                    "Here was the fatal flaw. In the BSC Token Hub's IAVL verification precompile, the algorithm checked that leaf hashes combined properly into inner nodes, "
                    "but it failed to enforce that intermediate branch paths were anchored to the canonical block header root. "
                    "If an attacker could inject an arbitrary leaf, the math would never check whether that leaf actually existed in state."
                )
            },
            {
                "scene_id": "scene_5_the_attack",
                "act_number": 5,
                "act_tag": "ACT 05 // EXPLOIT EXECUTION",
                "title": "Forged Merkle Proof Injected",
                "caption": "The attacker crafted synthetic hash padding, bypassing verification and approving 2M BNB.",
                "fraction": 0.15,
                "camera_pos": [0.0, 1.4, 3.2],
                "camera_target": [0.0, 1.25, 0.0],
                "active_layer": "attack_injection",
                "lighting_mode": "danger_red",
                "hud_badge": "EXPLOIT INJECTED",
                "hud_metric": "Forged Leaf Hash Accepted -> Status: TRUE",
                "code_snippet": (
                    "// ATTACK PAYLOAD INJECTION:\n"
                    "forgeProof(forgedLeaf, customHashPadding);\n"
                    "-> Precompile returns: VALID\n"
                    "-> Mint: 2,000,000 BNB ($566M)"
                ),
                "narration_segment": (
                    "On October 6, 2022, the attacker struck. They crafted a completely synthetic transaction leaf requesting two million BNB. "
                    "By adding custom mathematical padding to an intermediate branch, they generated a hash that matched the bridge's flawed verification rules. "
                    "The precompile executed, believed the forged leaf was valid, and approved the transaction."
                )
            },
            {
                "scene_id": "scene_6_drain_funds",
                "act_number": 6,
                "act_tag": "ACT 06 // CAPITAL FLIGHT & IMPACT",
                "title": "$566M Drained Across DeFi",
                "caption": "Funds siphoned into Venus and Uniswap before Binance coordinated an emergency validator halt.",
                "fraction": 0.14,
                "camera_pos": [0.0, 2.1, 4.8],
                "camera_target": [0.0, 1.1, 0.0],
                "active_layer": "fund_drain",
                "lighting_mode": "danger_red",
                "hud_badge": "CAPITAL IMPACT",
                "hud_metric": "Total Siphoned: $566,000,000 | 2,000,000 BNB",
                "code_snippet": None,
                "narration_segment": (
                    "Instantly, two million BNB—worth over 566 million dollars—was minted directly to the hacker's wallet. "
                    "The attacker immediately deposited 100 million dollars into lending protocols like Venus to borrow stablecoins and siphon value across multiple chains. "
                    "Within hours, Binance coordinated with validators to halt the entire blockchain, containing over 400 million dollars."
                )
            },
            {
                "scene_id": "scene_7_prevention",
                "act_number": 7,
                "act_tag": "ACT 07 // ARCHITECTURAL PREVENTION",
                "title": "Canonical Anchors & Multi-Sig",
                "caption": "The permanent fix: canonical root validation and decentralized threshold validator gates.",
                "fraction": 0.13,
                "camera_pos": [0.0, 1.8, 4.2],
                "camera_target": [0.0, 1.2, 0.0],
                "active_layer": "prevention_shield",
                "lighting_mode": "secure_emerald",
                "hud_badge": "SYSTEM HARDENING",
                "hud_metric": "BSC v1.1.15 Hard Fork | Multi-Sig Gate 3-of-5",
                "code_snippet": (
                    "// PRODUCTION PREVENTION ARCHITECTURE:\n"
                    "1. Canonical Root Path Anchoring (Strict Enforced)\n"
                    "2. Threshold Validator Quorum (3-of-5 Gate)\n"
                    "3. Time-locked Emergency Circuit Breaker"
                ),
                "narration_segment": (
                    "The fix required two fundamental architectural upgrades: "
                    "First, hard-forking the BSC client to enforce strict canonical root validation on every inner node path. "
                    "Second, eliminating single-contract authority by installing decentralized multi-signature threshold gates. "
                    "For developers building cross-chain systems, never trust custom precompiles without formal verification and time-locked emergency pauses."
                )
            }
        ]

        full_narration = " ".join(sc["narration_segment"] for sc in scenes)

        return {
            "title": topic_data.get("title", "How Binance Bridge Got Hacked for $566M"),
            "category": "CRYPTO SECURITY",
            "topic_type": "CRYPTO_BRIDGE_HACK",
            "narration": full_narration,
            "scenes": scenes,
            "pro_tip": "Never deploy custom cryptographic verification precompiles without formal verification and decentralized multi-signature threshold gates."
        }

    def _plan_generic_systems_explainer(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic fallback for other systems/AI topics with clean 7-act breakdown."""
        title = topic_data.get("title", "Systems Breakthrough")
        summary = topic_data.get("summary", "")
        problem = topic_data.get("problem", "")
        solution = topic_data.get("solution", "")
        pro_tip = topic_data.get("pro_tip", "Validate real-world throughput in production.")

        scenes = [
            {
                "scene_id": "scene_1_ecosystem",
                "act_number": 1,
                "act_tag": "ACT 01 // SYSTEM OVERVIEW",
                "title": title[:30],
                "caption": summary[:70],
                "fraction": 0.14,
                "camera_pos": [0.0, 2.2, 5.5],
                "camera_target": [0.0, 1.2, 0.0],
                "active_layer": "ecosystem",
                "lighting_mode": "normal_cyan",
                "hud_badge": "SYSTEM TOPOLOGY",
                "hud_metric": "Frontier Architecture",
                "code_snippet": None,
                "narration_segment": f"Welcome to this technical breakdown of {title}. {summary}"
            },
            {
                "scene_id": "scene_2_normal_flow",
                "act_number": 2,
                "act_tag": "ACT 02 // NORMAL PIPELINE",
                "title": "Baseline Execution Flow",
                "caption": "How the conventional architecture routes computation and data.",
                "fraction": 0.14,
                "camera_pos": [0.0, 1.8, 4.4],
                "camera_target": [0.0, 1.0, 0.0],
                "active_layer": "bridge_flow",
                "lighting_mode": "normal_cyan",
                "hud_badge": "DATA PIPELINE",
                "hud_metric": "Baseline Latency & Throughput",
                "code_snippet": None,
                "narration_segment": "Under conventional operating pipelines, data flows sequentially through memory hierarchies and processing stages before reaching state convergence."
            },
            {
                "scene_id": "scene_3_contract_zoom",
                "act_number": 3,
                "act_tag": "ACT 03 // ARCHITECTURE ZOOM",
                "title": "Internal Engine Core",
                "caption": "Inspecting the low-level algorithmic structures and access patterns.",
                "fraction": 0.15,
                "camera_pos": [0.0, 1.9, 3.8],
                "camera_target": [0.0, 1.2, 0.0],
                "active_layer": "merkle_tree",
                "lighting_mode": "focus_blue",
                "hud_badge": "INTERNAL ENGINE",
                "hud_metric": "Kernel Layer Execution",
                "code_snippet": None,
                "narration_segment": "Zooming into the core engine reveals how operations are serialized and coordinated across distributed nodes and memory registers."
            },
            {
                "scene_id": "scene_4_vulnerability",
                "act_number": 4,
                "act_tag": "ACT 04 // THE CORE BOTTLENECK",
                "title": "System Failure Mode",
                "caption": problem[:70],
                "fraction": 0.15,
                "camera_pos": [0.25, 1.6, 3.0],
                "camera_target": [0.1, 1.3, 0.0],
                "active_layer": "vulnerability",
                "lighting_mode": "alert_amber",
                "hud_badge": "CRITICAL BOTTLENECK",
                "hud_metric": "Contention & State Stall",
                "code_snippet": None,
                "narration_segment": f"Here is the core bottleneck: {problem} This creates severe latency penalties that throttle scalability."
            },
            {
                "scene_id": "scene_5_the_attack",
                "act_number": 5,
                "act_tag": "ACT 05 // SYSTEM IMPACT",
                "title": "Failure Under Load",
                "caption": "Under peak stress, the bottleneck cascades across downstream dependencies.",
                "fraction": 0.15,
                "camera_pos": [0.0, 1.4, 3.2],
                "camera_target": [0.0, 1.25, 0.0],
                "active_layer": "attack_injection",
                "lighting_mode": "danger_red",
                "hud_badge": "STRESS CASSCADE",
                "hud_metric": "P99 Tail Latency Spike",
                "code_snippet": None,
                "narration_segment": "Under peak load or adversarial traffic, intermediate queues saturate, creating resource exhaustion across dependent clusters."
            },
            {
                "scene_id": "scene_6_drain_funds",
                "act_number": 6,
                "act_tag": "ACT 06 // THE UNLOCK",
                "title": "Breakthrough Solution",
                "caption": solution[:70],
                "fraction": 0.14,
                "camera_pos": [0.0, 2.1, 4.8],
                "camera_target": [0.0, 1.1, 0.0],
                "active_layer": "fund_drain",
                "lighting_mode": "focus_blue",
                "hud_badge": "ARCHITECTURAL UNLOCK",
                "hud_metric": "Zero-Copy Data Transfer",
                "code_snippet": None,
                "narration_segment": f"This breakthrough re-engineers the paradigm: {solution} By eliminating redundant round-trips, throughput scales dramatically."
            },
            {
                "scene_id": "scene_7_prevention",
                "act_number": 7,
                "act_tag": "ACT 07 // PRODUCTION RULE",
                "title": "Engineering Guardrails",
                "caption": pro_tip[:70],
                "fraction": 0.13,
                "camera_pos": [0.0, 1.8, 4.2],
                "camera_target": [0.0, 1.2, 0.0],
                "active_layer": "prevention_shield",
                "lighting_mode": "secure_emerald",
                "hud_badge": "PRODUCTION RULE",
                "hud_metric": "Benchmarked on NeuBench Labs",
                "code_snippet": None,
                "narration_segment": f"When deploying these architectures in production, keep this critical rule in mind: {pro_tip} To inspect live benchmarks across 260 frontier AI models, explore NeuBench."
            }
        ]

        full_narration = " ".join(sc["narration_segment"] for sc in scenes)
        return {
            "title": title,
            "category": topic_data.get("category", "SYSTEMS ENGINEERING"),
            "topic_type": "GENERIC_SYSTEMS",
            "narration": full_narration,
            "scenes": scenes,
            "pro_tip": pro_tip
        }

    # ================================================================== long
    def plan_long_storyboard(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds a 12-act long-form (4-5 minute) storyboard for 16:9 YouTube.
        Reuses the same seven visual beats but interleaves deeper analysis so the
        pacing stays varied over a longer runtime.
        """
        title = topic_data.get("title", "Technical Architecture Breakdown")
        title_lower = title.lower()
        if any(w in title_lower for w in ["bridge", "hack", "exploit", "binance", "bnb", "merkle"]):
            return self._plan_binance_long(topic_data)
        return self._plan_generic_long(topic_data)

    @staticmethod
    def _variant(base: Dict[str, Any], **overrides) -> Dict[str, Any]:
        sc = copy.deepcopy(base)
        sc.update(overrides)
        return sc

    def _plan_binance_long(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        base = self._plan_binance_bridge_hack(topic_data)
        s = base["scenes"]
        scenes = [
            self._variant(s[0]),
            self._variant(s[1]),
            self._variant(s[2]),
            self._variant(
                s[2],
                scene_id="scene_4_proof_path",
                act_number=4,
                act_tag="ACT 04 // WALKING THE PROOF PATH",
                title="Leaf to Root",
                caption="Each sibling hash is combined level by level until the root is rebuilt.",
                hud_badge="PROOF PATH // LEAF TO ROOT",
                hud_metric="depth 16 | siblings combined per level",
                code_snippet=(
                    "// PROOF WALK\n"
                    "node = hash(leaf)\n"
                    "for sibling in path:\n"
                    "    node = hash(node, sibling)\n"
                    "assert(node == canonicalRoot)"
                ),
                narration_segment=(
                    "Each proof climbs from the transaction leaf toward the root. "
                    "At every level the verifier hashes two siblings and compares the parent. "
                    "If the final hash matches the root in the block header, the transaction is authentic. "
                    "Security depends on every intermediate comparison being anchored to canonical state."
                ),
            ),
            self._variant(s[3]),
            self._variant(s[4]),
            self._variant(
                s[4],
                scene_id="scene_7_omission",
                act_number=7,
                act_tag="ACT 07 // ROOT CAUSE ANALYSIS",
                title="An Omission, Not a Break",
                caption="Attacker-supplied siblings let a forged leaf match an arbitrary node.",
                hud_badge="ROOT CAUSE // MISSING ANCHOR",
                hud_metric="attacker-controlled sibling hashes",
                code_snippet=(
                    "// NO CIPHER WAS BROKEN:\n"
                    "// sibling hashes were attacker-controlled\n"
                    "// parent matched an arbitrary node\n"
                    "// no check against the real state root"
                ),
                narration_segment=(
                    "The exploit used an omission, not a broken cipher. "
                    "Because the precompile trusted attacker supplied sibling hashes, a fabricated leaf could be padded until its parent matched an arbitrary node. "
                    "No key was stolen. The logic simply never confirmed that the path ended at the real state root."
                ),
            ),
            self._variant(s[5]),
            self._variant(
                s[5],
                scene_id="scene_9_laundering",
                act_number=9,
                act_tag="ACT 09 // ON-CHAIN FUND FLOW",
                title="Laundering at Machine Speed",
                caption="Collateral, swaps and bridges moved value before validators could react.",
                hud_badge="FUND FLOW // $100M TO VENUS",
                hud_metric="Venus collateral -> stablecoin loans -> bridge out",
                code_snippet=(
                    "// ATTACKER FUND FLOW:\n"
                    "mint 2,000,000 BNB\n"
                    "-> deposit 100M USD to Venus\n"
                    "-> borrow stablecoins\n"
                    "-> swap + bridge toward Ethereum"
                ),
                narration_segment=(
                    "The freshly minted BNB moved instantly. "
                    "About one hundred million dollars entered Venus as collateral for stablecoin loans, while other portions were swapped across decentralized exchanges and bridged toward Ethereum. "
                    "Settlement is irreversible, so speed mattered more than stealth. An emergency validator halt became the final circuit breaker."
                ),
            ),
            self._variant(s[6]),
            self._variant(
                s[1],
                scene_id="scene_11_defense_depth",
                act_number=11,
                act_tag="ACT 11 // DEFENSE IN DEPTH",
                title="Layered Trust Boundaries",
                caption="Canonical anchoring, independent attestations, rate limits and pauses.",
                hud_badge="HARDENING // LAYERED GATES",
                hud_metric="validate -> attest -> rate-limit -> pause",
                code_snippet=(
                    "// DEFENSE IN DEPTH:\n"
                    "1. canonical root anchoring\n"
                    "2. independent relayer attestation\n"
                    "3. mint rate limits\n"
                    "4. time-locked emergency pause"
                ),
                narration_segment=(
                    "A hardened bridge treats every proof as untrusted until it anchors to finalized consensus state. "
                    "Modern designs combine strict canonical root validation, independent relayer attestations, mint rate limits, and time locked emergency pauses. "
                    "No single contract should hold unilateral authority to release funds, however elegant its cryptography looks."
                ),
            ),
            self._variant(
                s[0],
                scene_id="scene_12_lesson",
                act_number=12,
                act_tag="ACT 12 // POST-MORTEM",
                title="The Lasting Lesson",
                caption="Verification depth matters more than cryptographic sophistication.",
                hud_badge="POST-MORTEM // AUDIT TRACE",
                hud_metric="trace every value to the canonical root",
                code_snippet=(
                    "// AUDITOR CHECKLIST:\n"
                    "trace every value to canonical root\n"
                    "treat unchecked state as hostile\n"
                    "assume forged proofs are possible"
                ),
                narration_segment=(
                    "The BNB bridge remains a textbook lesson in verification depth. "
                    "The mathematics worked, the signatures were valid, and yet two million BNB were created from nothing because one assertion was missing. "
                    "When auditing cross chain systems, trace every value to the canonical root and treat unchecked intermediate state as an invitation."
                ),
            ),
        ]
        for i, sc in enumerate(scenes):
            sc["fraction"] = 1.0 / len(scenes)
            sc["act_number"] = i + 1
        return {
            "title": base["title"],
            "category": base["category"],
            "topic_type": base["topic_type"],
            "narration": " ".join(sc["narration_segment"] for sc in scenes),
            "scenes": scenes,
            "pro_tip": base["pro_tip"],
            "long_form": True,
        }

    def _plan_generic_long(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        base = self._plan_generic_systems_explainer(topic_data)
        s = base["scenes"]
        title = base["title"]
        summary = topic_data.get("summary", "")
        problem = topic_data.get("problem", "")
        solution = topic_data.get("solution", "")
        pro_tip = base["pro_tip"]

        scenes = [
            self._variant(s[0]),
            self._variant(s[1]),
            self._variant(s[2]),
            self._variant(
                s[2],
                scene_id="scene_4_commitment",
                act_number=4,
                act_tag="ACT 04 // STATE COMMITMENT",
                title="Committing State Safely",
                caption="Authenticated data structures bind every update to a verifiable root.",
                hud_badge="STATE INTEGRITY",
                hud_metric="append -> hash -> commit -> verify",
                code_snippet=(
                    "// STATE COMMITMENT\n"
                    "update = apply(op, state)\n"
                    "root = commit(update)\n"
                    "assert(root == expected_root)"
                ),
                narration_segment=(
                    "Reliable systems commit every state transition to an authenticated structure. "
                    "Each operation produces a new root that downstream services can verify independently. "
                    "If the commitment does not match, the update is rejected before it can corrupt shared state."
                ),
            ),
            self._variant(s[3]),
            self._variant(s[4]),
            self._variant(
                s[5],
                scene_id="scene_7_impact",
                act_number=7,
                act_tag="ACT 07 // MEASURED IMPACT",
                title="Quantifying the Cost",
                caption="Latency, throughput and error budgets reveal the real bottleneck.",
                hud_badge="IMPACT ANALYSIS",
                hud_metric="tail latency | throughput | error budget",
                code_snippet=None,
                narration_segment=(
                    "Before optimizing, quantify the cost. "
                    "Tail latency, sustained throughput, and error budgets expose which stage actually limits the system. "
                    "Measurements beat intuition, and they turn architectural debates into concrete engineering targets."
                ),
            ),
            self._variant(
                s[6],
                scene_id="scene_8_unlock",
                act_number=8,
                act_tag="ACT 08 // THE ARCHITECTURAL UNLOCK",
                title="The Architectural Unlock",
                caption=solution[:70] if solution else "The design change that removes the bottleneck.",
                hud_badge="BREAKTHROUGH",
                hud_metric="decouple -> route -> verify",
                code_snippet=None,
                narration_segment=(
                    f"The unlock is architectural rather than incremental. {solution} "
                    "By decoupling the critical path and routing work more intelligently, the system removes the structural penalty instead of hiding it."
                ),
            ),
            self._variant(
                s[1],
                scene_id="scene_9_pipeline",
                act_number=9,
                act_tag="ACT 09 // OPTIMIZED DATA FLOW",
                title="A Leaner Data Path",
                caption="Fewer round-trips, tighter queues and predictable latency.",
                hud_badge="PIPELINE",
                hud_metric="fewer hops | bounded queues",
                code_snippet=None,
                narration_segment=(
                    "With the new design, data takes a shorter path. "
                    "Fewer hops mean lower latency, and bounded queues keep behavior predictable under load. "
                    "The result is a pipeline that scales by design rather than by over-provisioning."
                ),
            ),
            self._variant(
                s[2],
                scene_id="scene_10_correctness",
                act_number=10,
                act_tag="ACT 10 // CORRECTNESS UNDER LOAD",
                title="Correctness Under Load",
                caption="Every optimization must preserve verifiable invariants.",
                hud_badge="INVARIANTS",
                hud_metric="verify -> commit -> observe",
                code_snippet=None,
                narration_segment=(
                    "Speed is worthless if correctness drifts. "
                    "Every optimization must preserve the invariants the system depends on. "
                    "Verification gates and continuous observation keep the fast path trustworthy under real traffic."
                ),
            ),
            self._variant(
                s[3],
                scene_id="scene_11_hardening",
                act_number=11,
                act_tag="ACT 11 // HARDENING & GUARDRAILS",
                title="Designed for Failure",
                caption="Rate limits, isolation and graceful degradation contain faults.",
                hud_badge="HARDENING",
                hud_metric="isolate | limit | degrade",
                code_snippet=None,
                narration_segment=(
                    "Production systems assume components will fail. "
                    "Isolation, rate limits, and graceful degradation keep a local fault from becoming a global outage. "
                    "Designing for failure is what makes high availability credible."
                ),
            ),
            self._variant(
                s[0],
                scene_id="scene_12_outro",
                act_number=12,
                act_tag="ACT 12 // PRODUCTION RULE",
                title="The Production Rule",
                caption=pro_tip[:70],
                hud_badge="PRODUCTION RULE",
                hud_metric="benchmark real workloads",
                code_snippet=None,
                narration_segment=(
                    f"When deploying {title}, keep one rule in mind: {pro_tip} "
                    "Validate real-world throughput, latency distributions, and cost under peak concurrency. "
                    "Explore live benchmarks across 260 frontier models on NeuBench."
                ),
            ),
        ]
        for i, sc in enumerate(scenes):
            sc["fraction"] = 1.0 / len(scenes)
            sc["act_number"] = i + 1
        return {
            "title": title,
            "category": base["category"],
            "topic_type": base["topic_type"],
            "narration": " ".join(sc["narration_segment"] for sc in scenes),
            "scenes": scenes,
            "pro_tip": pro_tip,
            "long_form": True,
        }
