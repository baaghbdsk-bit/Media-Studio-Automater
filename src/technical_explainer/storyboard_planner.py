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

    LAYERS = (
        "ecosystem", "bridge_flow", "merkle_tree", "vulnerability",
        "attack_injection", "fund_drain", "prevention_shield",
    )

    def plan_storyboard(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a 7-act storyboard driven by the topic's own acts.

        The old keyword router sent anything containing "hack" or "merkle" to a
        hard-coded crypto story.  Templates are now explicit, so a topic about
        Merkle trees or security is explained with its own narration.
        """
        if topic_data.get("template") == "binance_bridge_hack":
            return self._plan_binance_bridge_hack(topic_data)
        acts = topic_data.get("acts")
        if isinstance(acts, list) and len(acts) >= 5:
            return self._plan_from_acts(topic_data, acts, long_form=False)
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
        """Fallback plan built from the topic's own fields (no boilerplate acts)."""
        from .. import curriculum

        topic = dict(topic_data)
        topic.setdefault("audience", "beginner")
        topic.setdefault("pillar", "foundations")
        acts = topic.get("acts")
        if not isinstance(acts, list) or len(acts) < 5:
            acts = curriculum.acts_from_topic(topic, 7)
        return self._plan_from_acts(topic, acts, long_form=False)

    def _plan_from_acts(self, topic_data: Dict[str, Any], acts: List[Dict[str, Any]],
                        long_form: bool = False) -> Dict[str, Any]:
        from .. import curriculum

        total = 12 if long_form else 7
        acts = [a for a in (acts or []) if isinstance(a, dict)]
        if len(acts) < total:
            filler = curriculum.acts_from_topic(topic_data, total)
            acts = acts + filler[len(acts):]
        acts = acts[:total]

        title = topic_data.get("title", "Technology Explained")
        audience = str(topic_data.get("audience", "beginner")).lower()
        pillar = str(topic_data.get("pillar", "foundations")).lower()
        scenes: List[Dict[str, Any]] = []

        for i, act in enumerate(acts):
            layer = act.get("visual_layer")
            if layer not in self.LAYERS:
                layer = self.LAYERS[i % len(self.LAYERS)]
            narration = str(act.get("narration") or "").strip() or f"Here is the next part of {title}."
            hud_badge = str(act.get("hud_badge") or "").strip()[:32] or f"PART {i + 1:02d}"
            hud_metric = str(act.get("hud_metric") or "").strip()[:48]
            scene_title = str(act.get("title") or "").strip()[:46] or f"Part {i + 1}"

            # Scene-level prosody: a brighter hook, a sober failure act, a
            # confident fix. The narration builder applies these per clip.
            if i == 0:
                rate, pitch, pause_after = "+4%", "+2Hz", 0.5
            elif layer in ("vulnerability", "attack_injection", "fund_drain"):
                rate, pitch, pause_after = "+0%", "-2Hz", 0.34
            elif layer == "prevention_shield":
                rate, pitch, pause_after = "+4%", "+1Hz", 0.5
            elif i == total - 1:
                rate, pitch, pause_after = "+2%", "+0Hz", 0.8
            else:
                rate, pitch, pause_after = "+2%", "+0Hz", 0.34

            scenes.append({
                "scene_id": f"scene_{i + 1}_{layer}",
                "act_number": i + 1,
                "act_tag": f"ACT {i + 1:02d} // {hud_badge.upper()}",
                "title": scene_title,
                "caption": self._caption_from(narration, 78),
                "fraction": 1.0 / total,
                "camera_pos": [0.0, 1.8, 4.4],
                "camera_target": [0.0, 1.2, 0.0],
                "active_layer": layer,
                "lighting_mode": self._lighting_for(layer),
                "hud_badge": hud_badge.upper(),
                "hud_metric": hud_metric,
                "code_snippet": act.get("code_snippet"),
                "narration_segment": narration,
                "viz_labels": self._viz_labels(layer, topic_data, act),
                "viz_counter": act.get("viz_counter"),
                "rate": rate,
                "pitch": pitch,
                "pause_after": pause_after,
            })

        return {
            "title": title,
            "category": str(topic_data.get("category") or pillar).upper(),
            "topic_type": "CURRICULUM",
            "audience": audience,
            "pillar": pillar,
            "narration": " ".join(sc["narration_segment"] for sc in scenes),
            "scenes": scenes,
            "pro_tip": topic_data.get("pro_tip", ""),
            "long_form": bool(long_form),
        }

    @staticmethod
    def _caption_from(text: str, limit: int = 78) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text:
            return ""
        first = re.split(r"(?<=[.!?])\s+", text)[0]
        if len(first) <= limit:
            return first
        return first[: limit - 1].rstrip() + "…"

    @staticmethod
    def _lighting_for(layer: str) -> str:
        return {
            "ecosystem": "normal_cyan",
            "bridge_flow": "normal_cyan",
            "merkle_tree": "focus_blue",
            "vulnerability": "alert_amber",
            "attack_injection": "danger_red",
            "fund_drain": "alert_amber",
            "prevention_shield": "secure_emerald",
        }.get(layer, "normal_cyan")

    @staticmethod
    def _viz_labels(layer: str, topic: Dict[str, Any], act: Dict[str, Any]) -> Dict[str, str]:
        badge = (act.get("hud_badge") or act.get("title") or topic.get("title", "")).upper()
        metric = (act.get("hud_metric") or topic.get("tagline") or "").upper()
        defaults: Dict[str, Dict[str, str]] = {
            "ecosystem": {
                "eco_label": badge, "eco_left": "INPUT", "eco_left_fine": "STAGE ONE",
                "eco_right": "OUTPUT", "eco_right_fine": "STAGE TWO",
                "eco_chip": metric, "eco_left_badge": "A", "eco_right_badge": "B",
            },
            "bridge_flow": {
                "flow_label": badge, "flow_1": "STEP 1", "flow_1_fine": "INPUT",
                "flow_2": "STEP 2", "flow_2_fine": "PROCESS",
                "flow_3": "STEP 3", "flow_3_fine": "OUTPUT", "flow_foot": metric,
            },
            "merkle_tree": {"tree_label": badge, "tree_root": "ROOT"},
            "vulnerability": {"vuln_label": badge, "vuln_fine": "WEAK LINK"},
            "attack_injection": {
                "attack_label": badge, "attack_fine": "UNTREATED INPUT",
                "attack_bad": "BAD INPUT", "attack_stamp": "ACCEPTED (WRONG)",
            },
            "fund_drain": {
                "drain_label": badge, "drain_counter_text": metric or "IMPACT",
                "drain_sub": "COST / RISK", "drain_hub": "CORE",
                "drain_a": "TEAM A", "drain_b": "TEAM B", "drain_c": "USERS",
            },
            "prevention_shield": {
                "shield_label": badge, "shield_fine": "GUARDRAILS ENFORCED",
                "shield_1": "CHECK 1", "shield_2": "CHECK 2", "shield_3": "CHECK 3",
                "shield_chip": "SAFE BY DEFAULT",
            },
        }
        labels = dict(defaults.get(layer, {}))
        overrides = act.get("viz_labels") if isinstance(act.get("viz_labels"), dict) else {}
        for key, value in overrides.items():
            if value is not None and str(value).strip():
                labels[str(key)] = str(value).upper()[:40]
        return labels

    # ================================================================== long
    def plan_long_storyboard(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a 12-act 16:9 storyboard from the topic's own acts."""
        if topic_data.get("template") == "binance_bridge_hack":
            return self._plan_binance_long(topic_data)
        from .. import curriculum

        acts = topic_data.get("acts")
        if not isinstance(acts, list) or len(acts) < 12:
            acts = curriculum.acts_from_topic(topic_data, 12)
        return self._plan_from_acts(topic_data, acts, long_form=True)

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
        from .. import curriculum

        acts = topic_data.get("acts")
        if not isinstance(acts, list) or len(acts) < 12:
            acts = curriculum.acts_from_topic(topic_data, 12)
        return self._plan_from_acts(topic_data, acts, long_form=True)
