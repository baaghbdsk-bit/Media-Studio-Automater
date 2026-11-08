"""Audience-aware curriculum bank and act scaffolding.

The channel serves viewers from school students to working engineers, so every
topic carries an audience level and a pillar.  Gemini writes the detailed acts
when it is available; this bank guarantees that the pipeline still produces a
coherent, correctly levelled script when the model is rate-limited or offline.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

try:
    from src import topic_memory
except Exception:  # pragma: no cover
    import topic_memory

AUDIENCES = ("beginner", "intermediate", "advanced")
PILLARS = ("foundations", "engineering", "ai_systems", "security", "career")

PILLAR_LABELS = {
    "foundations": "FOUNDATIONS",
    "engineering": "ENGINEERING",
    "ai_systems": "AI SYSTEMS",
    "security": "SECURITY",
    "career": "CAREER & CRAFT",
}

STYLE_GUIDE = {
    "beginner": (
        "Explain to a curious 12-15 year old. Use one concrete everyday analogy. "
        "Short sentences. Define every technical term the first time. No assumed background."
    ),
    "intermediate": (
        "Explain to a computer-science student or junior developer. Define key terms once, "
        "then explain the mechanism, a realistic example and one common mistake."
    ),
    "advanced": (
        "Explain to a working engineer. Focus on the mechanism, tradeoffs, failure modes "
        "and concrete numbers. Skip basic definitions unless they are subtle."
    ),
}

FIELDS = (
    "title", "audience", "pillar", "hook", "summary", "analogy", "problem",
    "solution", "example", "pro_tip", "takeaway", "entities",
)

_RAW = [
    (
        "What is an API?", "beginner", "foundations",
        "An API is the plug that lets two programs talk without knowing each other's code.",
        "An API is a contract: one program asks for something in a defined format, and another program answers. The caller never needs to know how the work is done.",
        "Think of a restaurant menu. You do not walk into the kitchen; you order from a menu, and the kitchen returns a dish.",
        "Without a contract, every app would need a custom integration, and one small change would break everyone downstream.",
        "An API hides the implementation behind stable inputs and outputs, so teams can upgrade the kitchen without changing the menu.",
        "When you tap Pay in a shopping app, the app calls a payment API instead of talking to the bank directly.",
        "Design APIs around use cases, version them, and never leak internal implementation details into the response.",
        "An API is a promise: stable inputs, predictable outputs, and freedom to change what happens behind it.",
        ["api"],
    ),
    (
        "How the internet works", "beginner", "foundations",
        "The internet is a postal system for data packets, not a cloud in the sky.",
        "Your device splits data into packets, routers forward each packet toward a destination address, and the receiving device reassembles them in order.",
        "It is like mailing a book one page at a time, with every envelope numbered so the reader can rebuild the book.",
        "Packets get lost, arrive out of order, or take different routes, so the network needs rules to recover.",
        "Protocols such as IP, TCP and DNS handle addressing, ordering and retransmission so apps see a reliable stream.",
        "When you open a website, DNS turns the name into an IP address and TCP delivers the page across many hops.",
        "Measure real latency and packet loss instead of assuming the network is reliable; design for retries and timeouts.",
        "The internet is best-effort delivery plus smart rules on the edges, not a single reliable wire.",
        ["internet", "tcp", "dns"],
    ),
    (
        "What is a database?", "beginner", "foundations",
        "A database is a careful notebook that many programs can read and write at the same time.",
        "A database stores structured data, enforces rules about valid values, and lets many users read and update it without corrupting each other's work.",
        "Think of a shared spreadsheet with rules, locks and an undo log, so two people cannot overwrite the same cell by accident.",
        "Without structure and concurrency control, updates collide and the data slowly becomes untrustworthy.",
        "Transactions group changes into all-or-nothing units, indexes make lookups fast, and constraints reject bad data at the door.",
        "A banking app uses a transaction to move money between two accounts so one side can never be debited without the other being credited.",
        "Start with a relational database and a clear schema; add caches or NoSQL stores only when you can name the access pattern they solve.",
        "A database is not just storage; it is the set of rules that keeps shared data correct.",
        ["database"],
    ),
    (
        "How GPS works", "beginner", "foundations",
        "GPS is a timing system: your phone measures how long signals take to arrive from satellites.",
        "Each satellite broadcasts its position and a precise timestamp. Your receiver compares the arrival time with the broadcast time to estimate distance, then solves for its own position.",
        "It is like hearing four clocks chime from known locations and using the delays to work out where you are standing.",
        "Clocks drift and signals bounce off buildings, so a naive distance estimate can be off by many metres.",
        "Receivers correct for clock error, atmospheric delay and multipath, and combine at least four satellites to solve position and time.",
        "Navigation apps use GPS plus cell towers and Wi-Fi to keep the blue dot stable in cities and tunnels.",
        "Always treat GPS as one noisy sensor; fuse it with other signals and expose accuracy instead of pretending it is perfect.",
        "GPS is precise timing turned into position through geometry and correction, not magic.",
        ["gps", "satellite"],
    ),
    (
        "What is encryption?", "beginner", "foundations",
        "Encryption scrambles data so only someone with the right key can read it.",
        "Encryption turns readable data into ciphertext using a key. Decryption reverses it. Modern systems separate the public key used to agree on a secret from the private key that stays on your device.",
        "Think of a locked box: anyone can snap the lock shut, but only the key holder can open it.",
        "Sending secrets over a network is unsafe because anyone on the path can copy the bytes.",
        "TLS combines asymmetric key exchange with fast symmetric encryption, then authenticates the server with certificates.",
        "The padlock in your browser means the connection is encrypted and the site proved it owns the certificate.",
        "Use established libraries and protocols; never invent your own encryption or reuse a nonce.",
        "Encryption protects confidentiality, but it does not replace authentication, integrity checks or good key management.",
        ["encryption", "tls"],
    ),
    (
        "How caching works", "intermediate", "engineering",
        "A cache trades memory for speed by keeping the answer to a recent question close at hand.",
        "A cache stores a copy of expensive data in a faster tier. A request checks the cache first; a hit returns immediately, while a miss fetches the source and stores the result.",
        "It is like keeping the salt on the counter instead of walking to the pantry every time you cook.",
        "Caches go stale, and a thundering herd of misses can hit the database all at once.",
        "Time-to-live rules, write-through or write-behind policies, and request coalescing keep cached data fresh without stampeding the source.",
        "A product page caches its rendered HTML for a few seconds so a traffic spike does not reach the database.",
        "Add a cache only after measuring the bottleneck, and always know the maximum staleness your product can tolerate.",
        "A cache is a bet about reuse; measure the hit rate and design the miss path before celebrating the speedup.",
        ["caching"],
    ),
    (
        "What a load balancer does", "intermediate", "engineering",
        "A load balancer spreads traffic across many servers so no single machine takes the whole hit.",
        "It accepts connections, applies a routing policy such as round-robin or least-connections, and forwards each request to a healthy backend.",
        "Think of a supermarket opening more checkout lanes as the queue grows, with an usher sending each shopper to the shortest lane.",
        "A naive balancer can pin a slow request to a healthy server or keep sending traffic to a dead one.",
        "Health checks, connection draining and consistent hashing keep traffic on healthy nodes and preserve cache locality.",
        "During a flash sale, the balancer adds backends and drains old ones without dropping in-flight requests.",
        "Make backends stateless where possible, and test what happens when a node dies mid-request.",
        "A load balancer buys scale and resilience only when health checks and graceful draining are part of the design.",
        ["load-balancing"],
    ),
    (
        "What a message queue is", "intermediate", "engineering",
        "A message queue lets a producer hand work to a consumer without waiting for it to finish.",
        "The producer writes a message to a durable queue; one or more consumers read it later. This decouples request latency from background work and absorbs bursts.",
        "It is like a restaurant ticket rail: the waiter clips the order and keeps serving, while the kitchen works through tickets at its own pace.",
        "Queues can grow without bound, messages can be processed twice, and ordering is not free.",
        "Visibility timeouts, idempotent consumers, dead-letter queues and partition keys make delivery reliable and ordered where it matters.",
        "An image upload returns immediately while a worker queue generates thumbnails and sends notifications.",
        "Design every consumer to be idempotent, monitor queue depth, and alert on age rather than just length.",
        "A queue is a buffer and a contract; it moves failure from the user's request into a system you can observe and retry.",
        ["message-queue"],
    ),
    (
        "What a database index does", "intermediate", "engineering",
        "An index is a shortcut that lets the database find rows without scanning the whole table.",
        "Most indexes are balanced trees that map a key to a location. Lookups become logarithmic instead of linear, at the cost of extra storage and slower writes.",
        "It is like the index at the back of a textbook: you jump to the right page instead of reading every page.",
        "Too many indexes slow down inserts and updates, and a poorly chosen index is ignored by the planner.",
        "Composite indexes follow the leftmost-prefix rule, and covering indexes can answer a query without touching the table.",
        "A user lookup by email becomes instant after adding an index on the email column.",
        "Index the columns your real queries filter and sort on, then verify with the query plan instead of guessing.",
        "An index is a write-time cost paid for read-time speed; measure both sides before adding another one.",
        ["database-index"],
    ),
    (
        "HTTP vs HTTPS", "intermediate", "engineering",
        "HTTPS is HTTP carried inside an encrypted, authenticated tunnel.",
        "HTTP defines the request and response format. HTTPS wraps that traffic in TLS, which encrypts the bytes and proves the server's identity with a certificate.",
        "It is like sending a postcard versus a sealed, tamper-evident envelope with a verified return address.",
        "Plain HTTP lets anyone on the path read or modify passwords, cookies and page content.",
        "TLS handshakes agree on keys, certificates chain to a trusted authority, and modern versions remove weak ciphers.",
        "Every browser padlock and every secure login form depends on HTTPS, and search engines rank HTTP sites lower.",
        "Terminate TLS at the edge, redirect HTTP to HTTPS, and enable HSTS so browsers refuse to fall back.",
        "HTTPS protects data in transit; it says nothing about whether the server stores or handles that data safely.",
        ["http"],
    ),
    (
        "Mixture of Experts (MoE)", "advanced", "ai_systems",
        "MoE activates only a small slice of a huge model for each token, so quality scales without paying the full compute bill.",
        "A lightweight router sends each token to the top-k expert sub-networks. The model keeps many parameters in memory but only runs a fraction of them per token.",
        "Think of a large hospital: a triage desk sends each patient to the right specialist instead of making every doctor see every patient.",
        "Dense models run every weight for every token, so scaling parameters scales compute and latency linearly.",
        "Sparse routing cuts active compute while preserving capacity, but it shifts the bottleneck to memory bandwidth and load balancing across experts.",
        "Frontier models use MoE to reach hundreds of billions of parameters while keeping per-token cost closer to a much smaller dense model.",
        "Monitor expert load and token drop rates; a hot expert or an imbalanced router silently wastes capacity.",
        "MoE trades compute for memory and routing complexity; measure active parameters, not total parameters.",
        ["mixture-of-experts", "moe"],
    ),
    (
        "FlashAttention", "advanced", "ai_systems",
        "FlashAttention makes attention faster by moving less data between GPU memory and on-chip cache.",
        "It tiles the query, key and value matrices so each block is computed inside fast SRAM, avoiding repeated round-trips to high-bandwidth memory.",
        "It is like cooking from a small countertop instead of walking to the pantry for every ingredient.",
        "Attention is memory-bound: the math is cheap, but repeatedly reading and writing large matrices dominates latency.",
        "Tiling and online softmax keep intermediate state on chip, producing mathematically identical results with far less memory traffic.",
        "Long-context models rely on FlashAttention-style kernels to keep time and memory linear enough to be usable.",
        "Verify the kernel is enabled in your serving stack and benchmark real sequence lengths; not every shape benefits equally.",
        "FlashAttention is an I/O optimization, not an approximation; the win comes from data movement, not fewer operations.",
        ["flashattention"],
    ),
    (
        "Quantization: FP16 vs INT8 vs INT4", "advanced", "ai_systems",
        "Quantization stores model weights in fewer bits so large models fit on smaller, cheaper hardware.",
        "Weights are mapped from 16-bit floats to 8-bit or 4-bit integers with scaling factors. The compute stays similar; the memory footprint and bandwidth drop sharply.",
        "It is like compressing a high-resolution photo into a smaller file that looks almost the same at normal viewing size.",
        "A 70B model in FP16 needs roughly 140 GB, which prices out most single-machine deployments.",
        "INT8 roughly halves memory with little quality loss; INT4 can cut it by 75 percent when outliers and salient weights are protected.",
        "A 70B model quantized to INT4 can fit on two 24 GB GPUs and still produce useful answers.",
        "Benchmark quality on your own evaluation set; quantization can change reasoning and long-context behavior in subtle ways.",
        "Quantization buys memory and bandwidth, not free accuracy; validate the task, not just perplexity.",
        ["quantization"],
    ),
    (
        "LoRA (Low-Rank Adaptation)", "advanced", "ai_systems",
        "LoRA fine-tunes a huge model by training tiny adapter matrices instead of every weight.",
        "The base model is frozen, and two low-rank matrices are inserted into selected layers. Only those adapters are trained, cutting trainable parameters by more than 99 percent.",
        "It is like adding a small set of sticky notes to a textbook instead of rewriting the whole book.",
        "Full fine-tuning requires optimizer states and memory for every parameter, which is out of reach for most teams.",
        "Low-rank updates capture task-specific behavior while keeping the base model reusable and the adapters easy to swap.",
        "A support team can ship a LoRA adapter for its domain and switch adapters at runtime without duplicating the base model.",
        "Tune rank and target modules deliberately, and evaluate on held-out tasks; a higher rank is not automatically better.",
        "LoRA makes adaptation cheap and portable; it does not remove the need for clean data and honest evaluation.",
        ["lora"],
    ),
    (
        "Retrieval-Augmented Generation (RAG)", "advanced", "ai_systems",
        "RAG gives a language model an open book instead of relying only on what it memorised during training.",
        "Documents are chunked and embedded into vectors. At query time, the system retrieves the most relevant chunks and inserts them into the prompt so the model answers from evidence.",
        "It is like an exam where the student can bring the right pages of the textbook into the room.",
        "Models hallucinate when they lack context, and retraining them every time a document changes is slow and expensive.",
        "Retrieval grounds answers in current, private sources, and citations make the answer auditable.",
        "A company assistant retrieves the latest policy paragraph before answering an HR question.",
        "Combine keyword and vector search, add a reranker, and evaluate retrieval separately from generation.",
        "RAG fails at retrieval far more often than at generation; measure recall before blaming the model.",
        ["rag"],
    ),
    (
        "KV cache optimization", "advanced", "ai_systems",
        "The KV cache is why chat responses slow down and eat memory as the conversation grows.",
        "Autoregressive generation reuses past attention keys and values instead of recomputing them. Caching them turns each new token into a much cheaper step, but the cache grows with context length and concurrency.",
        "It is like keeping a growing notebook of what was already said so you do not re-read the whole conversation every time.",
        "Without a cache, token N requires recomputing attention for all previous tokens, which is quadratic and slow.",
        "Grouped-query attention, paged allocation and quantization shrink the cache and reduce memory fragmentation.",
        "A long-context chatbot can serve many concurrent users only when the cache is paged and bounded.",
        "Watch cache memory per request, cap context length, and choose architectures with grouped-query attention for high concurrency.",
        "KV caching trades memory for latency; the engineering problem is managing that memory under concurrency.",
        ["kv-cache"],
    ),
    (
        "Speculative decoding", "advanced", "ai_systems",
        "Speculative decoding uses a small draft model to guess several tokens, then lets the large model verify them in one pass.",
        "The draft model proposes a short continuation. The target model scores those tokens in parallel, accepts the matching prefix and corrects the first mismatch.",
        "It is like a junior writer drafting sentences and a senior editor approving or fixing them in one review.",
        "Large models generate one token at a time and leave GPU compute underused during memory-bound decoding.",
        "Parallel verification turns idle compute into extra accepted tokens, often doubling or tripling throughput without changing the output distribution.",
        "Code assistants benefit because code is predictable and draft models guess syntax well.",
        "Measure acceptance rate on your workload; speculative decoding helps most when the draft model is well aligned and the task is predictable.",
        "Speculative decoding accelerates generation by spending spare compute to reduce sequential steps.",
        ["speculative-decoding"],
    ),
    (
        "Vector embeddings", "advanced", "ai_systems",
        "Embeddings turn meaning into coordinates so a computer can compare ideas mathematically.",
        "An embedding model maps text, images or code into a dense vector. Items with similar meaning end up close together, and cosine similarity measures that closeness.",
        "It is like plotting every word on a giant map where synonyms live in the same neighbourhood.",
        "Keyword search misses paraphrases because it compares characters, not meaning.",
        "Embeddings enable semantic search, clustering and recommendation by representing meaning as geometry.",
        "Searching for car repair can find a document about automobile maintenance even without the exact words.",
        "Evaluate embedding models on your domain, chunk documents carefully, and combine vector search with keyword search.",
        "Embeddings capture similarity, not truth; retrieval quality depends on the model, the chunks and the evaluation set.",
        ["embeddings"],
    ),
    (
        "Phishing: how it really works", "beginner", "security",
        "Phishing is social engineering: the attacker tricks you into handing over access, not hacking the computer directly.",
        "A convincing message creates urgency and sends you to a fake login page or a malicious attachment. The goal is credentials, a session cookie or a payment.",
        "It is like a forged letter that looks like it came from your bank, asking you to confirm your PIN.",
        "Technical defences cannot fully stop a person who is rushed and trusts the sender.",
        "Verify the sender through a second channel, use passkeys, and never enter credentials from a link in a message.",
        "A fake invoice email asks an employee to log in and approve a payment before the boss notices.",
        "Slow down on urgency, hover over links, and confirm unusual requests using a channel you already trust.",
        "Phishing targets trust and time pressure; the best defence is a habit, not just a filter.",
        ["phishing"],
    ),
    (
        "Passkeys vs passwords and 2FA", "intermediate", "security",
        "Passkeys replace shared secrets with a cryptographic key that never leaves your device.",
        "The site stores a public key; your device keeps the private key and signs a challenge. There is no password to phish or reuse across sites.",
        "It is like a key that only works for one lock and never leaves your pocket.",
        "Passwords are reused, phished and leaked, and one-time codes can be intercepted in real time.",
        "Passkeys bind authentication to the site's origin, resist phishing and remove the shared secret from the server.",
        "Signing in with a fingerprint or face unlock on a phone is a passkey flow, not a password typed into a box.",
        "Roll out passkeys alongside existing methods, keep a recovery path, and require phishing-resistant 2FA for administrators.",
        "Passkeys are a big upgrade because they remove the secret attackers love to steal.",
        ["passkeys"],
    ),
    (
        "Zero trust architecture", "advanced", "security",
        "Zero trust stops assuming that being inside the network makes a request safe.",
        "Every request is authenticated, authorised and evaluated against policy, regardless of where it comes from. Identity, device posture and least privilege replace the old perimeter.",
        "It is like a building where every door checks your badge, not just the front gate.",
        "Flat internal networks let one stolen credential move laterally across the whole estate.",
        "Strong identity, short-lived credentials, micro-segmentation and continuous verification limit blast radius.",
        "A compromised laptop cannot reach the payroll database without a fresh, scoped authorisation.",
        "Start with identity and least privilege, then segment the highest-value systems; do not buy a product and call it zero trust.",
        "Zero trust is an architecture of continuous verification and least privilege, not a single appliance.",
        ["zero-trust"],
    ),
    (
        "Supply chain attacks", "advanced", "security",
        "A supply chain attack compromises the tools you trust so your own build ships the attacker's code.",
        "Attackers target dependencies, build systems, package registries or update channels. The malicious change arrives signed and trusted by your normal process.",
        "It is like someone tampering with the flour supplier instead of breaking into the bakery.",
        "Most teams trust hundreds of transitive dependencies they have never reviewed.",
        "Lockfiles, pinned versions, provenance attestations, reproducible builds and least-privilege CI reduce the attack surface.",
        "A popular package adds a malicious install script that steals environment secrets during CI.",
        "Pin dependencies, verify signatures, isolate build secrets, and review what install scripts are allowed to run.",
        "Assume dependencies and build tools are part of your attack surface; verify provenance, not just version numbers.",
        ["supply-chain"],
    ),
    (
        "Merkle trees", "advanced", "security",
        "A Merkle tree compresses a large set of data into one root hash that can verify any item cheaply.",
        "Each leaf is hashed, pairs are hashed together, and the process repeats until a single root remains. A proof needs only the sibling hashes along one path.",
        "It is like a tamper-evident summary where changing one page changes the final fingerprint.",
        "Verifying every item against a full dataset is expensive, especially across untrusted networks.",
        "Merkle proofs let a verifier check inclusion in logarithmic time, and the root binds the whole dataset.",
        "Blockchains and distributed databases use Merkle roots to prove that a transaction is included without downloading everything.",
        "Anchor every proof to a trusted root; a valid-looking proof is meaningless if the root itself is attacker-controlled.",
        "Merkle trees make integrity cheap, but only the trusted root makes the proof meaningful.",
        ["merkle-tree"],
    ),
    (
        "SQL injection", "intermediate", "security",
        "SQL injection happens when user input is treated as code instead of data.",
        "If an application builds a query by concatenating strings, an attacker can change the query's structure and read or modify data they should never see.",
        "It is like a form where writing a special phrase in the name field rewrites the instructions on the form.",
        "String-built queries blur the line between the query and the values, so a quote can escape the intended field.",
        "Parameterised queries keep the query structure fixed and pass values separately, so input can never become SQL syntax.",
        "A login form that concatenates the username lets an attacker bypass the password check entirely.",
        "Use parameterised queries or an ORM, validate input, and give the application the least database privilege it needs.",
        "SQL injection is a data-versus-code bug; parameters are the fix, not escaping quotes by hand.",
        ["sql-injection"],
    ),
    (
        "Latency vs throughput", "intermediate", "career",
        "Latency is how long one request takes; throughput is how many requests the system finishes per second.",
        "You can improve throughput by batching or adding parallelism, but that often increases the latency of an individual request. The right tradeoff depends on the product.",
        "It is like a bus: carrying more passengers per trip raises throughput, but each passenger may wait longer to arrive.",
        "Teams optimise the wrong metric and make the user experience worse while the dashboard looks better.",
        "Measure p50, p95 and p99 latency alongside throughput, and set explicit budgets for each user journey.",
        "A video export service batches jobs to raise throughput, but interactive users need a separate low-latency path.",
        "Define the user-facing SLO first, then choose batching, concurrency and queueing to meet it.",
        "Latency and throughput trade off; optimise the one your user actually feels, and measure the tail.",
        ["latency-throughput"],
    ),
    (
        "Build vs buy", "intermediate", "career",
        "Build vs buy is a decision about where your team's scarce attention creates the most advantage.",
        "Buying gives you a mature solution and a vendor relationship; building gives you control and a closer fit, but you own maintenance forever.",
        "It is like cooking dinner versus ordering it: cooking can be cheaper and better, but only if you count the shopping, cleanup and skill.",
        "Teams underestimate the long-term cost of owning a system and overestimate how unique their requirement really is.",
        "Compare total cost of ownership, time to value, lock-in, compliance and the team's ability to operate the system for years.",
        "A startup buys email delivery and builds its recommendation engine because one is commodity and the other is the product.",
        "Write down the exit plan and the maintenance owner before choosing to build.",
        "Build only what differentiates you; buy the commodity and spend the saved attention on the product.",
        ["build-vs-buy"],
    ),
    (
        "Observability", "intermediate", "career",
        "Observability is the ability to ask new questions about a running system without shipping new code.",
        "Logs, metrics and traces describe what happened, how much and where. Together they let you debug unknown failures, not just the ones you predicted.",
        "It is like a flight recorder plus cockpit instruments: one tells you the story after an incident, the others show the live state.",
        "Monitoring known dashboards catches expected failures but misses novel ones.",
        "Structured logs, high-cardinality traces and service-level indicators make unfamiliar failures diagnosable.",
        "A checkout error is traced across five services to the one dependency that started timing out.",
        "Instrument the user journey, propagate trace IDs, and alert on symptoms users feel rather than every internal metric.",
        "Observability is a design property; you cannot bolt it on after the incident.",
        ["observability"],
    ),
    (
        "Technical debt", "advanced", "career",
        "Technical debt is a future cost you accept today in exchange for speed or scope.",
        "Shortcuts in design, tests or documentation make later changes slower. Like financial debt, a little can be strategic; too much becomes compounding interest.",
        "It is like borrowing to renovate a shop: useful if it increases revenue, dangerous if you keep borrowing for snacks.",
        "Debt is invisible in the backlog, so it grows until every feature takes twice as long.",
        "Name the debt, estimate its interest, and pay it down deliberately with a budget rather than heroics.",
        "A team ships a hard-coded workaround to hit a launch date, then schedules the general solution before the next customer segment arrives.",
        "Track debt items with the same rigour as features and pay the highest-interest items first.",
        "Technical debt is a tool, not a moral failure; the problem is unmanaged debt, not borrowing itself.",
        ["tech-debt"],
    ),
    (
        "System design interviews", "advanced", "career",
        "A system design interview tests how you reason about tradeoffs, not whether you memorise one architecture.",
        "You clarify requirements, estimate scale, sketch the data flow, choose components, and then discuss bottlenecks, failure modes and tradeoffs.",
        "It is like planning a city: you start with how many people and what they need, then decide on roads, utilities and emergency capacity.",
        "Candidates jump to a favourite stack before understanding the workload, then cannot defend their choices.",
        "Driving the conversation with requirements and numbers lets you justify every component and adapt when the interviewer changes a constraint.",
        "Designing a URL shortener starts with read/write ratio and retention, which determine the storage and caching strategy.",
        "State assumptions, do rough arithmetic, and name the tradeoff behind each decision.",
        "Interviewers hire for structured reasoning and tradeoff awareness, not for a perfect diagram.",
        ["system-design"],
    ),
    (
        "What is artificial intelligence?", "beginner", "ai_systems",
        "AI is a machine learning from examples instead of being told exact rules.",
        "Artificial intelligence means programs that improve at a task by learning patterns from data, rather than following hand-written rules.",
        "Think of teaching a child to recognise cats by showing thousands of photos, not by writing a rulebook about whiskers.",
        "Hand-written rules fail on edge cases and cannot adapt to new data without a human rewrite.",
        "Machine learning trains a model on examples so it generalises to new inputs on its own.",
        "A spam filter learns from emails you mark as spam instead of relying on a fixed keyword list.",
        "Start with the simplest model that works, measure it on real data, and only add complexity when the numbers demand it.",
        "AI learns patterns from examples; it does not understand the world the way people do.",
        ["ai", "machine-learning"],
    ),
    (
        "What is ChatGPT?", "beginner", "ai_systems",
        "ChatGPT is a text predictor trained on a huge pile of writing.",
        "ChatGPT is a language model that predicts the next word in a conversation, trained on vast amounts of text so the predictions feel helpful.",
        "It is like autocomplete on your phone, except the phone read most of the internet first.",
        "Without training data the model has no idea what a sensible reply looks like.",
        "Training on billions of words builds a statistical map of language, and fine-tuning on conversations makes it behave like an assistant.",
        "You ask it to explain a topic and it continues the conversation in a useful direction.",
        "Treat its answers as a starting point: verify facts, especially numbers, dates and citations.",
        "ChatGPT predicts plausible text; it does not know truth from fiction.",
        ["chatgpt", "llm"],
    ),
    (
        "How a neural network learns", "intermediate", "ai_systems",
        "A neural network adjusts millions of tiny weights until its mistakes shrink.",
        "A neural network is layers of numbers that transform inputs into outputs; training nudges each weight so the output matches the right answer more often.",
        "Picture a mixing desk with thousands of knobs: training slowly turns each knob until the sound is right.",
        "Random weights produce nonsense, so the network needs feedback and many small adjustments to become useful.",
        "Backpropagation computes how each weight contributed to the error, then gradient descent updates them in the helpful direction.",
        "An image classifier starts by guessing randomly and, after training, confidently labels a cat.",
        "Always split data into train and test sets, and watch for overfitting when accuracy on train data keeps rising but test data stalls.",
        "Learning is just repeated error correction across millions of parameters.",
        ["neural-network", "backpropagation"],
    ),
    (
        "What is an embedding?", "intermediate", "ai_systems",
        "An embedding turns meaning into a list of numbers a computer can compare.",
        "An embedding maps text, images or other data into a vector of numbers so that similar items end up close together in that space.",
        "Think of plotting words on a map where synonyms sit next door to each other.",
        "Raw text cannot be compared mathematically, so search and recommendation need a numeric representation.",
        "A model learns to place related items near each other, letting distance in vector space stand in for similarity.",
        "Searching 'cheap laptop' can surface 'budget notebook' because their embeddings are close.",
        "Normalise and deduplicate your corpus before embedding; garbage in means garbage vectors.",
        "Embeddings encode similarity as distance, not meaning as a human understands it.",
        ["embeddings", "vectors"],
    ),
    (
        "How a recommendation system works", "beginner", "ai_systems",
        "Recommendations are guesses about what you will like, based on what you and others did before.",
        "A recommendation system predicts items you will enjoy by combining your past behaviour with patterns across many users.",
        "It is like a friend who remembers what you liked and what people like you enjoyed.",
        "With no history the system has nothing to personalise, so it falls back to popular items.",
        "Collaborative filtering finds users with similar tastes, while content-based filtering matches item features to your preferences.",
        "A streaming service suggests a show because viewers with your history also watched it.",
        "Blend personalisation with diversity so users discover new things instead of being trapped in a filter bubble.",
        "Recommendations optimise for engagement, which is not the same as what is best for you.",
        ["recommendations", "collaborative-filtering"],
    ),
    (
        "What is a token?", "beginner", "ai_systems",
        "A token is the chunk of text an AI reads and prices.",
        "A token is a piece of text, roughly three quarters of a word, that a language model reads, generates and bills for.",
        "Think of tokens as syllables the model eats one at a time.",
        "Counting in words instead of tokens makes costs and limits impossible to predict.",
        "The model splits text into tokens, processes them in parallel, and charges per token consumed and produced.",
        "The sentence 'Hello, world!' is three tokens, not two words.",
        "Estimate tokens as words times 1.3, and always set a max output limit to control cost.",
        "Tokens are the currency of language models, not words.",
        ["tokens", "llm"],
    ),
    (
        "What is a prompt?", "beginner", "ai_systems",
        "A prompt is the instruction you give an AI, and wording changes everything.",
        "A prompt is the text you send to a model; its clarity, context and constraints shape the answer more than the model choice.",
        "It is like giving directions: 'turn left at the shop' beats 'go somewhere nearby'.",
        "Vague prompts force the model to guess your intent, producing generic or wrong answers.",
        "Good prompts state the role, the task, the format and the constraints, then give examples.",
        "Asking 'summarise this in three bullets for a manager' beats asking 'summarise this'.",
        "Iterate prompts like code: version them, test them, and measure the outputs.",
        "A prompt is a program written in natural language.",
        ["prompt", "prompt-engineering"],
    ),
    (
        "What is hallucination in AI?", "intermediate", "ai_systems",
        "Hallucination is when an AI states something false with full confidence.",
        "Hallucination is when a model generates plausible but fabricated facts, because it predicts likely text rather than verified truth.",
        "It is like a confident student who fills gaps in memory with invented details.",
        "Models have no built-in fact checker, so gaps get filled with statistically likely but possibly wrong text.",
        "Grounding answers in retrieved documents, citations and verification steps reduces hallucination.",
        "A model may invent a citation that looks real but does not exist.",
        "Never ship AI output to users without a verification step for facts, numbers and links.",
        "Confidence is not accuracy; always verify.",
        ["hallucination", "grounding"],
    ),
    (
        "What is a context window?", "intermediate", "ai_systems",
        "The context window is how much text an AI can hold in its head at once.",
        "The context window is the maximum number of tokens a model can consider in one request, covering both your input and its reply.",
        "It is like a desk: only so many papers fit before you must clear space.",
        "Exceed the window and the model forgets the beginning of your conversation.",
        "Longer windows cost more and slow down, so put the most important information near the end.",
        "A 128k window can hold a short book, but reasoning degrades well before the limit.",
        "Keep prompts focused and summarise long histories instead of dumping everything in.",
        "The window is a budget; spend it on what matters.",
        ["context-window", "tokens"],
    ),
    (
        "What is temperature in AI?", "beginner", "ai_systems",
        "Temperature controls how creative or predictable an AI's answer is.",
        "Temperature is a setting from zero to two that controls randomness: low means focused and repeatable, high means creative and varied.",
        "Think of it as a spice dial for the model's imagination.",
        "At temperature zero the model always picks the most likely next word, which can be dull or stuck.",
        "Higher temperature samples less likely words, increasing variety but also hallucination risk.",
        "Use 0.2 for code and facts, 0.7 for chat, 1.2 for brainstorming.",
        "Match temperature to the task, and never tune it without measuring output quality.",
        "Temperature shapes style, not knowledge.",
        ["temperature", "sampling"],
    ),
    (
        "What are AI agents?", "intermediate", "ai_systems",
        "An agent is an AI that can take actions, not just answer questions.",
        "An AI agent is a model that plans, calls tools and observes results in a loop until it completes a task.",
        "It is like an assistant who can use a calculator, search the web and write files, not just talk.",
        "A plain model can only reply; an agent can act, which means it can also make mistakes with real consequences.",
        "The loop is plan, act, observe, repeat, with guardrails on which tools it may call.",
        "An agent can book a meeting by checking your calendar and sending an invite.",
        "Give agents the least privilege possible and require confirmation for irreversible actions.",
        "Agents turn language into action; the risk scales with the tools.",
        ["agents", "tools"],
    ),
    (
        "What is fine-tuning?", "intermediate", "ai_systems",
        "Fine-tuning teaches a general model your specific style and facts.",
        "Fine-tuning takes a pre-trained model and trains it further on your own data so it adopts your tone, format or domain.",
        "It is like hiring a generalist and training them for your company.",
        "Training from scratch is impossible for most teams; fine-tuning reuses the base model's knowledge.",
        "You provide input-output pairs, and the model adjusts its weights to match your examples.",
        "A support bot fine-tuned on your help articles answers in your brand voice.",
        "Fine-tune for format and tone; use retrieval for facts that change.",
        "Fine-tuning bakes in style, not live knowledge.",
        ["fine-tuning", "training"],
    ),
    (
        "What is RAG?", "intermediate", "ai_systems",
        "RAG lets an AI look up facts before answering instead of guessing.",
        "Retrieval-Augmented Generation searches a knowledge base for relevant documents, then feeds them to the model as context for its answer.",
        "It is like an open-book exam instead of a closed-book one.",
        "A model alone cannot know your private or recent data, so it hallucinates or refuses.",
        "Retrieve top matching chunks, inject them into the prompt, and ask the model to answer from them.",
        "A company chatbot answers policy questions from the actual handbook.",
        "Chunk documents sensibly, rank by relevance, and cite sources so users can verify.",
        "RAG grounds answers in documents, but retrieval quality decides everything.",
        ["rag", "retrieval"],
    ),
    (
        "What is a system prompt?", "beginner", "ai_systems",
        "The system prompt sets the rules an AI follows for the whole conversation.",
        "A system prompt is hidden instructions given to the model before the user speaks, defining its role, tone and limits.",
        "It is like the briefing a manager gives before a meeting starts.",
        "Without it the model defaults to a generic assistant with no guardrails.",
        "It sets persona, safety rules, output format and what topics to avoid.",
        "A coding assistant's system prompt says to write clean code and refuse harmful requests.",
        "Keep system prompts short and test them against adversarial inputs.",
        "The system prompt is the constitution; user messages are the cases.",
        ["system-prompt", "prompt"],
    ),
    (
        "AI vs machine learning vs deep learning", "beginner", "ai_systems",
        "AI is the goal, machine learning is one way to reach it, deep learning is a powerful subset.",
        "Artificial intelligence is the broad idea of machines doing smart tasks; machine learning is learning from data; deep learning is machine learning with neural networks.",
        "Think of AI as transport, machine learning as engines, deep learning as electric motors.",
        "Confusing the three leads to wrong tool choices and unrealistic expectations.",
        "Each layer narrows the method while increasing power and data needs.",
        "A spam filter is machine learning; ChatGPT is deep learning; both are AI.",
        "Pick the simplest layer that solves the problem; do not default to deep learning.",
        "The terms nest: all deep learning is machine learning, all machine learning is AI.",
        ["ai", "machine-learning", "deep-learning"],
    ),
]


TOPIC_BANK: List[Dict[str, Any]] = [dict(zip(FIELDS, row)) for row in _RAW]


def _sentence(text: Any, fallback: str) -> str:
    value = str(text or "").strip()
    if not value:
        value = fallback
    if value and value[-1] not in ".!?":
        value += "."
    return value


def _narrate(topic: Dict[str, Any], raw: str, fallback: str) -> str:
    audience = topic.get("audience", "beginner")
    text = _sentence(raw, fallback)
    if audience == "beginner":
        return text
    if audience == "intermediate":
        return text
    return text


def acts_from_topic(topic: Dict[str, Any], n: int = 7) -> List[Dict[str, Any]]:
    title = topic.get("title", "this idea")
    hook = _sentence(topic.get("hook"), f"Here is the one idea behind {title}")
    summary = _sentence(topic.get("summary"), f"{title} is worth understanding")
    analogy = _sentence(topic.get("analogy"), "A useful analogy makes the mechanism easier to hold in your head")
    problem = _sentence(topic.get("problem"), "The naive approach breaks under real conditions")
    solution = _sentence(topic.get("solution"), "The fix is a deliberate design choice")
    example = _sentence(topic.get("example"), "This shows up in real systems every day")
    pro_tip = _sentence(topic.get("pro_tip"), "Measure before you optimise")
    takeaway = _sentence(topic.get("takeaway"), f"The takeaway is simple: understand the tradeoff behind {title}")

    seven = [
        ("ecosystem", "THE BIG IDEA", f"{hook} This is {title}, explained without unnecessary jargon.", "BIG PICTURE"),
        ("bridge_flow", "THE CORE IDEA", f"At its core, {summary} {analogy}", "CORE MECHANISM"),
        ("merkle_tree", "HOW IT WORKS", f"Here is the mechanism. {solution}", "MECHANISM"),
        ("vulnerability", "THE HARD PART", f"But there is a catch. {problem}", "WEAK POINT"),
        ("fund_drain", "WHY IT MATTERS", f"In practice, {example} When this goes wrong, the cost is real.", "REAL IMPACT"),
        ("prevention_shield", "THE FIX", f"The practical fix is simple to state. {pro_tip}", "BEST PRACTICE"),
        ("ecosystem", "THE TAKEAWAY", f"So remember this: {takeaway}", "SUMMARY"),
    ]
    long = [
        ("ecosystem", "THE HOOK", f"{hook} This is {title}.", "BIG PICTURE"),
        ("bridge_flow", "WHY IT MATTERS", f"Here is why this matters. {example}", "MOTIVATION"),
        ("merkle_tree", "THE CORE IDEA", f"At its core, {summary}", "CORE MECHANISM"),
        ("bridge_flow", "THE ANALOGY", f"A useful way to picture it: {analogy}", "MENTAL MODEL"),
        ("merkle_tree", "HOW IT WORKS I", f"Here is the first part of the mechanism. {solution}", "MECHANISM"),
        ("vulnerability", "THE TRADEOFF", f"The important tradeoff is this. {problem}", "TRADEOFF"),
        ("attack_injection", "WHERE IT BREAKS", f"When the assumptions fail, this is what goes wrong. {problem}", "FAILURE MODE"),
        ("fund_drain", "A REAL FAILURE", f"A realistic failure looks like this. {example}", "FAILURE CASE"),
        ("fund_drain", "THE IMPACT", f"The impact is concrete. {example}", "IMPACT"),
        ("prevention_shield", "THE FIX", f"The fix is a design habit. {pro_tip}", "BEST PRACTICE"),
        ("prevention_shield", "COMMON MISTAKES", f"Teams often get this wrong by skipping the fundamentals. {pro_tip}", "PITFALLS"),
        ("ecosystem", "THE TAKEAWAY", f"If you remember one thing, remember this. {takeaway}", "SUMMARY"),
    ]
    spec = long if n > 7 else seven
    spec = spec[:n]
    acts: List[Dict[str, Any]] = []
    for layer, badge, narration, metric in spec:
        acts.append({
            "title": badge.title(),
            "narration": narration,
            "visual_layer": layer,
            "hud_badge": badge,
            "hud_metric": metric,
            "code_snippet": None,
        })
    return acts


def pick_fallback(audience: Optional[str], pillar: Optional[str],
                  exclude_titles: Optional[List[str]] = None,
                  exclude_series: Optional[List[str]] = None,
                  allow_repeat: bool = True) -> Optional[Dict[str, Any]]:
    excluded_titles = list(exclude_titles or [])
    excluded_series = set(exclude_series or [])

    def fresh(topic: Dict[str, Any]) -> bool:
        series = topic_memory.series_key(topic.get("title", ""), topic.get("entities"), topic.get("series"))
        if series and series in excluded_series:
            return False
        return not any(topic_memory.similarity(topic["title"], old) >= topic_memory.DEFAULT_SIMILARITY
                       for old in excluded_titles)

    tiers = [
        lambda t: t.get("audience") == audience and t.get("pillar") == pillar,
        lambda t: t.get("pillar") == pillar,
        lambda t: t.get("audience") == audience,
        lambda t: True,
    ]
    for match in tiers:
        pool = [t for t in TOPIC_BANK if match(t) and fresh(t)]
        if pool:
            chosen = random.choice(pool)
            result = dict(chosen)
            result["series"] = topic_memory.series_key(
                result.get("title", ""), result.get("entities"), result.get("series"))
            result["audience"] = result.get("audience") or audience or "beginner"
            result["pillar"] = result.get("pillar") or pillar or "foundations"
            result["acts"] = acts_from_topic(result, 7)
            return result
    if not allow_repeat:
        return None

    pool = [t for t in TOPIC_BANK if not audience or t.get("audience") == audience]
    if not pool:
        pool = list(TOPIC_BANK)
    chosen = random.choice(pool)
    result = dict(chosen)
    result["series"] = topic_memory.series_key(
        result.get("title", ""), result.get("entities"), result.get("series"))
    result["audience"] = result.get("audience") or audience or "beginner"
    result["pillar"] = result.get("pillar") or pillar or "foundations"
    result["acts"] = acts_from_topic(result, 7)
    result["repeat_fallback"] = True
    return result
