import socket
socket.setdefaulttimeout(10)
import feedparser
import requests
import random
import json
import re
from typing import List, Dict, Any, Optional

LINKEDIN_PILLAR_ROTATION = ["NEWS", "EXPLAINER", "DIFFERENCE", "DID_YOU_KNOW", "WHAT_IF", "BEGINNER", "SURVIVAL", "BENCHMARK"]

LINKEDIN_EVERGREEN_TOPICS: Dict[str, List[Dict[str, Any]]] = {
    "EXPLAINER": [
        {
            "title": "How retrieval augmented generation actually works",
            "summary": "A practical explanation of chunking, embedding, retrieval, reranking, and the failure modes teams hit when they ship RAG without measuring retrieval quality.",
            "category": "explainer",
        },
        {
            "title": "What an inference token really costs",
            "summary": "Input tokens, output tokens, cached tokens, and latency all carry different costs. A breakdown of where the bill comes from and which levers actually move it.",
            "category": "explainer",
        },
        {
            "title": "Why KV caching changes long context performance",
            "summary": "A plain explanation of how key value caching avoids recomputing attention, where memory pressure appears, and why long prompts can slow down before they hit a limit.",
            "category": "explainer",
        },
        {
            "title": "What quantization does to model quality",
            "summary": "FP16, INT8, and INT4 reduce memory and cost, but the quality loss is uneven across tasks. A practical guide to when quantization is safe and when it is not.",
            "category": "explainer",
        },
        {
            "title": "How rate limiting protects an API",
            "summary": "Token buckets, concurrency caps, and retry budgets explained for teams that build on top of third party AI APIs.",
            "category": "explainer",
        },
        {
            "title": "What a vector index actually stores",
            "summary": "Embeddings, distance metrics, HNSW graphs, and the tradeoffs between recall, memory, and query latency.",
            "category": "explainer",
        },
    ],
    "DIFFERENCE": [
        {
            "title": "RAG vs fine-tuning: which one to use",
            "summary": "Retrieval augmented generation keeps knowledge outside the model and fetches it at request time. Fine-tuning changes model weights. A practical comparison of cost, freshness, control, and failure modes.",
            "category": "explainer",
        },
        {
            "title": "Latency vs throughput in LLM serving",
            "summary": "Latency is how long one request takes. Throughput is how many requests a system handles per second. The two often trade off, and optimizing one can hurt the other.",
            "category": "explainer",
        },
        {
            "title": "Parameters vs tokens",
            "summary": "Parameters are learned weights inside the model. Tokens are chunks of text processed during inference. A model can have billions of parameters and still bill by tokens.",
            "category": "explainer",
        },
        {
            "title": "Prompt caching vs fine-tuning",
            "summary": "Prompt caching reuses repeated context to lower cost and latency. Fine-tuning changes behavior. They solve different problems and are often combined.",
            "category": "explainer",
        },
    ],
    "DID_YOU_KNOW": [
        {
            "title": "Did you know: attention is not memory",
            "summary": "Attention lets a model weigh other tokens while producing one token. It does not store facts permanently; weights and context do different jobs.",
            "category": "fact",
        },
        {
            "title": "Did you know: temperature changes sampling, not knowledge",
            "summary": "Temperature scales logits before sampling. It makes outputs more or less random, but it does not add facts or improve reasoning by itself.",
            "category": "fact",
        },
        {
            "title": "Did you know: a token is not a word",
            "summary": "Tokenizers split text into subword pieces. Common words may be one token, while rare words become several. This affects cost, context limits, and multilingual performance.",
            "category": "fact",
        },
        {
            "title": "Did you know: quantization can change model behavior",
            "summary": "Lower precision reduces memory and cost, but it can alter outputs unevenly across tasks. Quality should be measured on your own eval set.",
            "category": "fact",
        },
    ],
    "WHAT_IF": [
        {
            "title": "What if your RAG retriever is wrong",
            "summary": "If retrieval returns the wrong chunks, the model can still produce a fluent answer. The fix is to measure recall and precision before blaming generation.",
            "category": "scenario",
        },
        {
            "title": "What if latency matters more than accuracy",
            "summary": "Some products need fast answers more than perfect answers. Routing, caching, and smaller models can matter more than leaderboard rank.",
            "category": "scenario",
        },
        {
            "title": "What if your eval set is too easy",
            "summary": "A benchmark that never fails makes every model look good. Hard cases, edge cases, and real user traces reveal where systems break.",
            "category": "scenario",
        },
        {
            "title": "What if context windows keep growing",
            "summary": "Longer context helps, but cost, latency, and retrieval quality still matter. More tokens are not always better tokens.",
            "category": "scenario",
        },
    ],
    "EXPLAINER": [
        {
            "title": "What an API actually is",
            "summary": "An API is a contract for how software components talk to each other. It defines inputs, outputs, errors, and rules, not just a URL.",
            "category": "explainer",
        },
        {
            "title": "What a framework actually does",
            "summary": "A framework gives structure and conventions, while a library gives reusable functions. The difference is who controls the flow of the program.",
            "category": "explainer",
        },
        {
            "title": "What a database index does",
            "summary": "An index helps a database find rows faster by organizing lookup data. It speeds reads but costs storage and write overhead.",
            "category": "explainer",
        },
        {
            "title": "What JSON is and is not",
            "summary": "JSON is a text format for structured data. It is not a database, schema, or programming language, and it has no comments.",
            "category": "explainer",
        },
        {
            "title": "What an environment variable is",
            "summary": "An environment variable is configuration passed to a process from outside the code. It is useful for secrets and deployment settings, but it is not automatically secure.",
            "category": "explainer",
        },
        {
            "title": "What a webhook is",
            "summary": "A webhook is an HTTP callback triggered by an event. It lets one system notify another instead of polling repeatedly.",
            "category": "explainer",
        },
        {
            "title": "What Docker does",
            "summary": "Docker packages an application with its dependencies into a container. It makes environments more repeatable, but it does not make code correct.",
            "category": "explainer",
        },
        {
            "title": "What Git tracks",
            "summary": "Git tracks snapshots of files, not folders or empty directories. Understanding commits, branches, and remotes prevents common workflow mistakes.",
            "category": "explainer",
        },
    ],
    "DIFFERENCE": [
        {
            "title": "API vs SDK",
            "summary": "An API is the interface. An SDK is a toolkit that helps you use that interface. One defines the contract; the other speeds up implementation.",
            "category": "explainer",
        },
        {
            "title": "Library vs framework",
            "summary": "A library is called by your code. A framework calls your code. That inversion of control is the practical difference.",
            "category": "explainer",
        },
        {
            "title": "Training vs inference",
            "summary": "Training changes model weights using data. Inference uses trained weights to produce outputs. They have different costs, hardware needs, and failure modes.",
            "category": "explainer",
        },
        {
            "title": "Model vs algorithm",
            "summary": "An algorithm is the procedure. A model is the learned result of running that procedure on data. The same algorithm can produce different models.",
            "category": "explainer",
        },
        {
            "title": "Prompt vs context window",
            "summary": "A prompt is what you send. The context window is how much the model can consider at once. A long prompt can crowd out useful context.",
            "category": "explainer",
        },
        {
            "title": "CPU vs GPU for AI",
            "summary": "CPUs handle general sequential work well. GPUs handle many parallel matrix operations well. AI inference often benefits from GPU parallelism, but cost and latency still matter.",
            "category": "explainer",
        },
        {
            "title": "Batch processing vs streaming",
            "summary": "Batching waits for a full set of work and processes it together. Streaming handles items as they arrive. The choice changes latency, throughput, and complexity.",
            "category": "explainer",
        },
        {
            "title": "Cache vs memory",
            "summary": "Memory holds active data for a process. A cache keeps frequently used data closer for faster access. All caches use memory, but not all memory is a cache.",
            "category": "explainer",
        },
        {
            "title": "Git commit vs push",
            "summary": "A commit saves a snapshot locally. A push sends commits to a remote repository. You can commit many times before pushing once.",
            "category": "explainer",
        },
        {
            "title": "JSON vs schema",
            "summary": "JSON is data. A schema is the rulebook that says what that data should look like. Valid JSON can still violate a schema.",
            "category": "explainer",
        },
    ],
    "DID_YOU_KNOW": [
        {
            "title": "Did you know: an API is just a contract",
            "summary": "Behind an API can be a database, a queue, or another service. The API hides implementation details and exposes only agreed inputs and outputs.",
            "category": "fact",
        },
        {
            "title": "Did you know: frameworks are libraries with opinions",
            "summary": "Frameworks reduce decisions by enforcing structure. That can speed development, but it can also make unusual use cases harder.",
            "category": "fact",
        },
        {
            "title": "Did you know: Git does not track empty folders",
            "summary": "Git tracks files, not directories. An empty folder disappears unless it contains a file such as .gitkeep.",
            "category": "fact",
        },
        {
            "title": "Did you know: environment variables are not secrets by default",
            "summary": "Environment variables are convenient, but they can leak through logs, process listings, or child processes. Secret managers add stronger controls.",
            "category": "fact",
        },
        {
            "title": "Did you know: JSON has no comments",
            "summary": "Standard JSON does not allow comments. Some tools accept JSON5 or JSONC, but strict parsers will reject them.",
            "category": "fact",
        },
    ],
    "WHAT_IF": [
        {
            "title": "What if your API has no rate limit",
            "summary": "Without limits, one client can exhaust shared resources and make the service slow for everyone. Rate limits protect availability, not just billing.",
            "category": "scenario",
        },
        {
            "title": "What if you cache the wrong data",
            "summary": "Caching stale or user-specific data can create subtle bugs. Cache keys and invalidation rules matter as much as cache speed.",
            "category": "scenario",
        },
        {
            "title": "What if your prompt is too vague",
            "summary": "Vague prompts force the model to guess intent. Clear constraints, examples, and output formats usually improve results more than longer prompts.",
            "category": "scenario",
        },
        {
            "title": "What if your database has no index",
            "summary": "Queries may still work, but they can scan entire tables. Performance often degrades quietly until traffic grows.",
            "category": "scenario",
        },
    ],
    "BEGINNER": [
        {
            "title": "What is an API in simple terms",
            "summary": "An API is a way for two programs to talk to each other. A clear beginner explanation with a restaurant analogy and one real example.",
            "category": "beginner",
        },
        {
            "title": "What Git actually does",
            "summary": "Git saves snapshots of your code so you can undo mistakes and collaborate. A simple explanation of commits, branches, and remotes.",
            "category": "beginner",
        },
        {
            "title": "What SQL is used for",
            "summary": "SQL is how you ask questions of a database. A beginner-friendly explanation of tables, rows, columns, and simple queries.",
            "category": "beginner",
        },
        {
            "title": "What a variable is",
            "summary": "A variable is a named box that stores a value. A simple explanation for people starting to code.",
            "category": "beginner",
        },
        {
            "title": "What debugging actually means",
            "summary": "Debugging is finding why code does not behave as expected. A beginner guide to reading errors and testing one change at a time.",
            "category": "beginner",
        },
        {
            "title": "How to build your first portfolio",
            "summary": "A first portfolio needs a few small projects, clear README files, and honest explanations. Quality matters more than quantity.",
            "category": "beginner",
        },
        {
            "title": "How to prepare for your first internship",
            "summary": "A practical guide to applying, preparing projects, and talking about what you built without exaggerating.",
            "category": "beginner",
        },
        {
            "title": "How to answer 'tell me about yourself'",
            "summary": "A simple structure for interviews: background, projects, skills, and what you want next. Keep it short and specific.",
            "category": "beginner",
        },
    ],
    "SURVIVAL": [
        {
            "title": "The skills that survive AI automation in 2026",
            "summary": "A grounded look at which engineering and product skills still compound as models absorb routine work, and how to build evidence of those skills in public.",
            "category": "career",
        },
        {
            "title": "How to evaluate an AI tool before your company buys it",
            "summary": "A short evaluation framework covering accuracy on your own data, latency, cost per task, data handling, and the exit path if the vendor changes terms.",
            "category": "career",
        },
        {
            "title": "The 2026 stack for shipping AI features without a platform team",
            "summary": "A minimal stack for small teams: one model provider, one evaluation set, one logging layer, and one fallback path. No overbuilt infrastructure.",
            "category": "career",
        },
        {
            "title": "What to learn first if your role is moving toward AI",
            "summary": "A practical order of study for engineers moving into AI work: evaluation, data quality, latency and cost, then model internals.",
            "category": "career",
        },
        {
            "title": "How to build a personal benchmark for AI tools",
            "summary": "A repeatable way to test models on your own tasks instead of trusting public leaderboards. Includes a small scoring template and a review cadence.",
            "category": "career",
        },
    ],
}

NEWS_SIGNAL_TERMS = (
    "security", "breach", "hack", "cyber", "crypto", "binance", "exchange",
    "regulation", "lawsuit", "antitrust", "outage", "layoff", "hiring",
    "funding", "startup", "chip", "nvidia", "cloud", "data center", "privacy",
    "open source", "acquisition", "ipo", "revenue", "earnings",
)


class TrendHunter:
    """Discovers viral, debated, and breaking topics across the web 100% free with fast RSS & APIs."""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def get_google_trends(self, geo: str = "IN") -> List[Dict[str, Any]]:
        """Pulls top real-time trending spikes from Google Trends RSS (Default: India for explosive reach)."""
        trends = []
        for region in [geo, "US"]:
            try:
                url = f"https://trends.google.com/trending/rss?geo={region}"
                feed = feedparser.parse(url)
                for entry in feed.entries[:6]:
                    approx_traffic = getattr(entry, "ht_approx_traffic", "Trending Spike")
                    trends.append({
                        "title": entry.title,
                        "summary": getattr(entry, "summary", entry.title),
                        "source": f"Google Trends ({region})",
                        "traffic": approx_traffic,
                        "category": "breaking_news"
                    })
            except Exception as e:
                print(f"[TrendHunter] Google Trends ({region}) error: {e}")
        return trends

    def get_tech_news(self) -> List[Dict[str, Any]]:
        """Pulls top tech & AI debate stories from Hacker News."""
        news = []
        try:
            top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            res = requests.get(top_ids_url, timeout=4)
            if res.status_code == 200:
                top_ids = res.json()[:6]
                for item_id in top_ids:
                    item_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
                    item = requests.get(item_url, timeout=3).json()
                    if item and "title" in item:
                        news.append({
                            "title": item.get("title", ""),
                            "summary": item.get("title", ""),
                            "comments_count": item.get("descendants", 0),
                            "score": item.get("score", 0),
                            "url": item.get("url", ""),
                            "source": "HackerNews",
                            "category": "ai_tech"
                        })
        except Exception as e:
            print(f"[TrendHunter] HackerNews error: {e}")
        return news

    def get_breaking_rss(self) -> List[Dict[str, Any]]:
        """Pulls breaking tech and world drama from TechCrunch & BBC."""
        items = []
        feeds = [
            ("https://techcrunch.com/feed/", "TechCrunch", "ai_tech"),
            ("http://feeds.bbci.co.uk/news/rss.xml", "BBC World", "breaking_news")
        ]
        for feed_url, source_name, category in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:4]:
                    items.append({
                        "title": entry.title,
                        "summary": getattr(entry, "summary", entry.title)[:200],
                        "url": getattr(entry, "link", ""),
                        "source": source_name,
                        "traffic": "Breaking",
                        "category": category
                    })
            except Exception as e:
                print(f"[TrendHunter] RSS error on {source_name}: {e}")
        return items

    def get_neubench_stories(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Pulls breaking AI benchmark and frontier model insights directly from NeuBench."""
        curated = [
            {
                "title": "Frontier Reasoning Drift & Cost per 1M Tokens (DeepSeek vs Claude vs Gemini)",
                "summary": "NeuBench telemetry reveals significant latency and cost differences when evaluating long-horizon coding tasks across 260+ models.",
                "company": "NeuBench",
                "source": "NeuBench Live Telemetry",
                "traffic": "High Signal AI",
                "category": "ai_tech",
                "url": "https://app.neubench.workers.dev/"
            },
            {
                "title": "Real-World TTFT & Throughput Benchmarks across Major LLM Hosted Endpoints",
                "summary": "NeuBench speed testing shows real-world token throughput variances up to 40% across hosted provider APIs.",
                "company": "NeuBench",
                "source": "NeuBench Latency Radar",
                "traffic": "High Signal AI",
                "category": "ai_tech",
                "url": "https://app.neubench.workers.dev/"
            },
            {
                "title": "Quantized FP8 vs Dense Weights for Autonomous Coding Agents",
                "summary": "NeuBench evaluations analyze benchmark accuracy drop versus inference acceleration on local and cloud models.",
                "company": "NeuBench",
                "source": "NeuBench Model Index",
                "traffic": "High Signal AI",
                "category": "ai_tech",
                "url": "https://app.neubench.workers.dev/"
            },
            {
                "title": "LLM API Outage Frequency & Degradation Index",
                "summary": "NeuBench monitoring tracks endpoint reliability and error rates across top frontier intelligence providers.",
                "company": "NeuBench",
                "source": "NeuBench Reliability Index",
                "traffic": "High Signal AI",
                "category": "ai_tech",
                "url": "https://app.neubench.workers.dev/"
            }
        ]
        return curated[:limit]

    def get_huggingface_daily_papers(self, limit: int = 4) -> List[Dict[str, Any]]:
        """Pulls breaking research papers from Hugging Face Daily Papers API."""
        papers = []
        try:
            res = requests.get("https://huggingface.co/api/daily_papers", timeout=6)
            if res.status_code == 200:
                data = res.json()
                for item in data[:limit]:
                    p = item.get("paper", item)
                    title = p.get("title", "")
                    summary = p.get("summary", title)
                    if title:
                        papers.append({
                            "title": title,
                            "summary": summary[:300],
                            "source": "Hugging Face Daily Papers",
                            "traffic": "Frontier AI Research",
                            "category": "frontier_paper",
                            "url": f"https://huggingface.co/papers/{p.get('id', '')}"
                        })
        except Exception as e:
            print(f"[TrendHunter] Hugging Face Daily Papers error: {e}")
        return papers

    def get_curated_trending_topics(self) -> List[Dict[str, Any]]:
        """Combines and ranks all trends by engagement potential."""
        all_trends = []
        all_trends.extend(self.get_neubench_stories())
        all_trends.extend(self.get_huggingface_daily_papers())
        all_trends.extend(self.get_tech_news())
        all_trends.extend(self.get_breaking_rss())
        all_trends.extend(self.get_google_trends())
        
        random.shuffle(all_trends)
        return all_trends

    def get_linkedin_topics(self, pillar: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return professional LinkedIn topics, optionally filtered to one content pillar."""
        selected = (pillar or "").upper()

        if selected in LINKEDIN_EVERGREEN_TOPICS:
            items = [
                {
                    **topic,
                    "pillar": selected,
                    "source": f"AI {selected.title()} Desk",
                    "url": "",
                }
                for topic in LINKEDIN_EVERGREEN_TOPICS[selected]
            ]
            random.shuffle(items)
            return items

        if selected == "BENCHMARK":
            sources = (self.get_neubench_stories, self.get_huggingface_daily_papers)
        elif selected == "NEWS":
            sources = (self.get_tech_news, self.get_breaking_rss, self.get_neubench_stories)
        else:
            sources = (
                self.get_neubench_stories,
                self.get_huggingface_daily_papers,
                self.get_tech_news,
                self.get_breaking_rss,
            )

        all_topics = []
        for source in sources:
            try:
                all_topics.extend(source())
            except Exception:
                continue

        ai_terms = (
            "artificial intelligence", "machine learning", "deep learning",
            "large language model", "llm", "generative", "foundation model",
            "inference", "transformer", "neural", "robot", "agent",
            "openai", "anthropic", "gemini", "claude", "deepseek", "qwen",
            "mistral", "hugging face", "computer vision", "embedding", "rag",
            "diffusion", "gpu", "benchmark", "model", "token",
        )
        signal_terms = ai_terms + NEWS_SIGNAL_TERMS if selected == "NEWS" else ai_terms

        filtered = []
        seen = set()
        for topic in all_topics:
            title = (topic.get("title") or "").replace("\ufffd", "'").strip()
            summary = (topic.get("summary") or "").replace("\ufffd", "'")
            if not title or title.lower() in seen:
                continue
            haystack = f"{title} {summary}".lower()
            source_name = str(topic.get("source", "")).lower()
            has_signal = bool(re.search(r"\bai\b", haystack)) or any(term in haystack for term in signal_terms)
            trusted_source = "neubench" in source_name or "hugging face" in source_name
            if not trusted_source and not has_signal:
                continue
            seen.add(title.lower())
            filtered.append(
                {
                    **topic,
                    "title": title,
                    "summary": summary,
                    "pillar": selected or "NEWS",
                }
            )

        random.shuffle(filtered)
        return filtered

    def get_casual_topics(self) -> List[Dict[str, Any]]:
        """Return non-tech, everyday relatable, witty, and humorous topics for X and Threads (Indian & global urban lifestyle)."""
        evergreen_casual = [
            # High-Traction Desi / Indian Urban & Workplace Culture
            {"title": "Bengaluru traffic & Silk Board signals", "context": "Spending 45 minutes moving 200 meters in Bangalore traffic while watching your Swiggy delivery guy overtake you on a bicycle."},
            {"title": "The 90-day notice period trauma", "context": "Indian HR enforcing a 90-day notice period like you are an astronaut on an interplanetary mission to Mars."},
            {"title": "Swiggy/Zomato vs 'Ghar pe daal bani hai'", "context": "Carefully customizing your Swiggy cart for 20 minutes only for mom to announce 'Ghar pe daal roti bani hai'."},
            {"title": "Auto-rickshaw 'Nahi jaayega'", "context": "Auto driver looking at you, hearing your destination, and saying 'Nahi jaayega' with the supreme confidence of a billionaire declining an investment."},
            {"title": "The bag of 300 plastic bags", "context": "Every Indian household having one giant master polythene bag under the sink whose sole purpose is to store 300 other polythene bags."},
            {"title": "Mom's cookie tin betrayal", "context": "Opening a Royal Dansk butter cookies tin expecting cookies, only to find needles, buttons, and mom's sewing kit."},
            {"title": "Tatkal booking adrenaline rush at 10:00 AM", "context": "Forget bungee jumping, the real near-death experience is watching the IRCTC Tatkal timer hit 10:00:00 AM while waiting for the OTP."},
            {"title": "The Paytm sound box emotional relief", "context": "Staring intensely at the shopkeeper's QR sound box waiting for the robotic voice to confirm 'Dus rupaye praapt hue'."},
            {"title": "Wedding relatives asking 'Aage ka kya plan hai?'", "context": "A distant uncle you haven't seen in 9 years cornering you near the gulab jamun counter asking 'Aur beta, aage ka kya socha hai?'"},
            {"title": "Surviving corporate shifts on 5 cutting chais", "context": "Running an entire 9-hour corporate workday on 4 cups of cutting chai, two Parle-G biscuits, and pure spite."},
            {"title": "Free dhaniya and mirchi entitlement", "context": "Spending 800 rupees on vegetables and then refusing to leave until the bhaiya gives you free coriander and green chillies."},
            {"title": "Bangalore landlord demands", "context": "Bangalore landlord demanding 10 months security deposit, your 10th-grade board marksheet, and a LinkedIn recommendation."},
            {"title": "Salary credited vs 18th of the month", "context": "Salary credited message on the 1st: 'I will invest in real estate.' Bank balance on the 18th: 'Is tap water a meal?'"},
            {"title": "Typing 'Per my last email'", "context": "Typing 'Per my previous email' when what you really want to say is 'I already answered this, can you please read?'"},
            {"title": "Family WhatsApp 'Good Morning' GIFs", "context": "Waking up to 18 glittery animated roses with quotes like 'Life is a precious gift' in the family WhatsApp group."},
            
            # High-Engagement Conversation & Debate Bait (Massive for Threads Comments)
            {"title": "Everyday scams we normalized", "context": "What is an everyday expense that is a total and complete scam, but society just normalized it?"},
            {"title": "Unwritten public rules broken casually", "context": "What is one unwritten social rule that people break way too casually in public?"},
            {"title": "Unpopular opinion for family dinners", "context": "What is an unpopular opinion that would get you immediately disowned at a family dinner?"},
            {"title": "The age you realized adulthood is a trap", "context": "Drop the exact age you were when you realized adulthood is just being permanently exhausted and doing laundry."},
            {"title": "Overhyped social media purchases", "context": "What is something you bought that was 100% hyped by social media influencers but turned out to be completely useless?"},
            {"title": "Work habits to look busy", "context": "What is a work habit you pretend to have just so nobody gives you extra work?"},

            # Universal Everyday Quirks & Internal Monologues
            {"title": "Second iced coffee at 4 PM", "context": "Drinking cold brew late in the afternoon and then acting shocked when you can't sleep at 2 AM."},
            {"title": "The fridge inspection ritual", "context": "Opening the fridge 12 times in an evening as if new gourmet snacks spawned by magic."},
            {"title": "Canceling weekend plans", "context": "The instantaneous, unrivaled wave of relief when someone cancels the social plans you agreed to 3 weeks ago."},
            {"title": "Grocery store optimism vs reality", "context": "Buying greens with the pure intention of eating clean, only to watch them liquify in the fridge drawer."},
            {"title": "The Sunday 7 PM existential shift", "context": "When the weekend is technically not over, but emotionally you are already in Monday standup."},
            {"title": "Headphones with no music", "context": "Wearing noise-canceling headphones with nothing playing purely as social armor so nobody speaks to you."},
            {"title": "37 alarms set 2 minutes apart", "context": "The delusion that alarm 6:02 AM will wake you up gently after you ignored 5:58, 6:00, and 6:01."},
            {"title": "The post-order tracking panic", "context": "Checking package delivery status 4 minutes after checkout like the courier is going to teleport to your door."},
            {"title": "Work email exclamation marks", "context": "Typing 'Sounds great! No worries at all!' with maximum enthusiasm while looking like an emotionless statue in front of your screen."},
            {"title": "Late-night life motivation", "context": "Deciding at 11:45 PM on a Tuesday that you are going to wake up at 5 AM, run a marathon, and master French, only to hit snooze at 7:30."},
            {"title": "The unread messages spiral", "context": "Having 50 unread messages because answering just one feels like initiating a live hostage negotiation."},
            {"title": "Shopping cart abandonment therapy", "context": "Adding $600 worth of luxury items to an online cart just to feel something, then closing the tab."},
            {"title": "Camera-off telepathy", "context": "The unspoken brotherhood of turning off your camera in a group call the second you see one other person did it."},
            {"title": "Bedtime comeback formulation", "context": "Coming up with the single most devastating, articulate rebuttal to an argument that ended in 2019 while staring at your ceiling."}
        ]
        
        # Try to mix in some lighthearted Google Trends if non-tech
        try:
            spikes = self.get_google_trends(geo="US")
            for sp in spikes:
                title_lower = sp.get("title", "").lower()
                # Exclude tech/AI/politics
                if not any(k in title_lower for k in ("ai", "tech", "election", "trump", "biden", "war", "stock", "gpu", "llm")):
                    evergreen_casual.append({
                        "title": sp.get("title", ""),
                        "context": f"Current trending cultural topic: {sp.get('title')}"
                    })
        except Exception:
            pass

        random.shuffle(evergreen_casual)
        return evergreen_casual

    LAYERS = (
        "ecosystem", "bridge_flow", "merkle_tree", "vulnerability",
        "attack_injection", "fund_drain", "prevention_shield",
    )

    @staticmethod
    def _build_topic_prompt(audience: str, pillar: str, n_acts: int,
                            recent: List[str], exclude_series: List[str]) -> str:
        from src import curriculum

        style = curriculum.STYLE_GUIDE.get(audience, curriculum.STYLE_GUIDE["beginner"])
        pillar_label = curriculum.PILLAR_LABELS.get(pillar, pillar.upper())
        recent_block = "\n".join(f"- {t}" for t in recent[-40:]) or "- (none yet)"
        series_block = ", ".join(exclude_series) or "none"
        word_range = "45-65" if n_acts > 7 else "30-45"
        return (
            "You are the head of curriculum for a technology channel whose audience "
            "ranges from school students to working engineers.\n"
            f"TARGET AUDIENCE: {audience}\n"
            f"TARGET PILLAR: {pillar_label}\n"
            f"STYLE: {style}\n\n"
            "Pick ONE genuinely useful topic that belongs in this pillar and fits the audience. "
            "It may be evergreen or a recent development, but it must be accurate and explainable.\n\n"
            "STRICT ANTI-DUPLICATION: do not overlap with any of these recently used topics:\n"
            f"{recent_block}\n"
            f"Also avoid these series: {series_block}\n\n"
            "Return ONLY a raw JSON object with this exact shape:\n"
            "{\n"
            '  "title": "precise, clickable title (6-12 words)",\n'
            '  "canonical_topic": "short canonical name",\n'
            '  "series": "stable lowercase series key, e.g. caching, rag, merkle-tree",\n'
            '  "entities": ["named systems, models or concepts"],\n'
            f'  "category": "{pillar_label}",\n'
            f'  "audience": "{audience}",\n'
            f'  "pillar": "{pillar}",\n'
            '  "hook": "one sentence that makes a 12-year-old and an engineer curious",\n'
            '  "tagline": "one punchy line",\n'
            '  "summary": "2-3 sentences explaining the idea",\n'
            '  "analogy": "one concrete everyday analogy",\n'
            '  "problem": "1-2 sentences on why the naive approach fails",\n'
            '  "solution": "1-2 sentences on the mechanism that fixes it",\n'
            '  "example": "one realistic example",\n'
            '  "pro_tip": "one actionable rule",\n'
            '  "takeaway": "one sentence the viewer should remember",\n'
            f'  "acts": [ exactly {n_acts} objects with this shape ],\n'
            "}\n\n"
            "Each act object must be:\n"
            "{\n"
            '  "title": "2-5 words",\n'
            f'  "narration": "{word_range} spoken words, no markdown, no stage directions",\n'
            '  "visual_layer": "one of: ecosystem, bridge_flow, merkle_tree, vulnerability, attack_injection, fund_drain, prevention_shield",\n'
            '  "hud_badge": "2-4 uppercase words",\n'
            '  "hud_metric": "short metric or label",\n'
            '  "code_snippet": null or a short 2-5 line code/pseudocode block,\n'
            '  "viz_labels": {"exact keys listed below": "short ALL-CAPS label"},\n'
            '  "viz_counter": null or {"prefix":"$", "target":566, "suffix":"M", "decimals":0}\n'
            "}\n\n"
            "LABEL KEYS (use only the keys that belong to the act's visual_layer):\n"
            "- ecosystem: eco_label, eco_left, eco_left_fine, eco_right, eco_right_fine, "
            "eco_chip, eco_left_badge, eco_right_badge\n"
            "- bridge_flow: flow_label, flow_1, flow_1_fine, flow_2, flow_2_fine, "
            "flow_3, flow_3_fine, flow_foot\n"
            "- merkle_tree: tree_label, tree_root\n"
            "- vulnerability: vuln_label, vuln_fine\n"
            "- attack_injection: attack_label, attack_fine, attack_bad, attack_stamp\n"
            "- fund_drain: drain_label, drain_counter_text, drain_sub, drain_hub, "
            "drain_a, drain_b, drain_c\n"
            "- prevention_shield: shield_label, shield_fine, shield_1, shield_2, "
            "shield_3, shield_chip\n\n"
            "Rules:\n"
            "- CRITICAL PEDAGOGY RULE (THE BEGINNER EMPATHY PRINCIPLE): Always write as if explaining to someone with ZERO background in this tech stack, who is intensely curious.\n"
            "- NEVER start with an abstract definition, acronym, or mathematical equation.\n"
            "- The hook and analogy MUST use a vivid everyday physical metaphor (hospital triage, restaurant kitchen, traffic junction, library, postal mail).\n"
            "- Detail the concrete problem FIRST: What is slow, broken, or frustrating before this breakthrough exists?\n"
            "- Act 1 is the hook, act 2 the core idea and analogy, the middle acts the mechanism and "
            "failure modes, and the final act the fix and takeaway.\n"
            "- Vary visual_layer across acts; use fund_drain only for a measurable impact.\n"
            "- Narration must be natural speech. Never include labels like 'Act 1' or 'Visual:'.\n"
            "- Do not use the words 'delve', 'landscape', 'game-changer', 'revolutionize'.\n"
        )

    @classmethod
    def _validate_topic(cls, data: Dict[str, Any], audience: str, pillar: str,
                        n_acts: int, used_topics: List[str],
                        exclude_series: List[str]) -> Optional[Dict[str, Any]]:
        from src import curriculum, topic_memory

        if not isinstance(data, dict):
            return None
        title = str(data.get("title") or "").strip()
        if len(title) < 8:
            return None

        series = topic_memory.series_key(title, data.get("entities"), data.get("series"))
        if series and series in set(exclude_series):
            return None
        for old in used_topics:
            if topic_memory.similarity(title, old) >= topic_memory.DEFAULT_SIMILARITY:
                return None

        raw_acts = data.get("acts") if isinstance(data.get("acts"), list) else []
        clean: List[Dict[str, Any]] = []
        for act in raw_acts:
            if not isinstance(act, dict):
                continue
            narration = str(act.get("narration") or "").strip()
            if len(narration.split()) < 12:
                continue
            layer = act.get("visual_layer")
            clean.append({
                "title": str(act.get("title") or "Next")[:70],
                "narration": narration,
                "visual_layer": layer if layer in cls.LAYERS else "ecosystem",
                "hud_badge": str(act.get("hud_badge") or "")[:32],
                "hud_metric": str(act.get("hud_metric") or "")[:48],
                "viz_labels": act.get("viz_labels") if isinstance(act.get("viz_labels"), dict) else {},
                "viz_counter": act.get("viz_counter") if isinstance(act.get("viz_counter"), dict) else None,
                "code_snippet": act.get("code_snippet") if isinstance(act.get("code_snippet"), str) else None,
            })
        if len(clean) < max(5, n_acts - 2):
            return None

        result: Dict[str, Any] = {
            "title": title,
            "canonical_topic": str(data.get("canonical_topic") or title).strip(),
            "series": series,
            "entities": data.get("entities") if isinstance(data.get("entities"), list) else [],
            "category": str(data.get("category") or curriculum.PILLAR_LABELS.get(pillar, pillar)).upper(),
            "audience": audience,
            "pillar": pillar,
            "hook": str(data.get("hook") or "").strip(),
            "tagline": str(data.get("tagline") or "").strip(),
            "summary": str(data.get("summary") or "").strip(),
            "analogy": str(data.get("analogy") or "").strip(),
            "problem": str(data.get("problem") or "").strip(),
            "solution": str(data.get("solution") or "").strip(),
            "example": str(data.get("example") or "").strip(),
            "pro_tip": str(data.get("pro_tip") or "").strip(),
            "takeaway": str(data.get("takeaway") or "").strip(),
            "long_form": n_acts > 7,
        }

        if len(clean) < n_acts:
            filler = curriculum.acts_from_topic(result, n_acts)
            clean.extend(filler[len(clean):])
        result["acts"] = clean[:n_acts]
        return result

    def get_dynamic_ai_topic(self, used_topics: Optional[List[str]] = None,
                             audience: Optional[str] = None,
                             pillar: Optional[str] = None,
                             exclude_series: Optional[List[str]] = None,
                             long_form: bool = False) -> Dict[str, Any]:
        """Pick a fresh topic levelled for the audience and pillar.

        Gemini writes an act-by-act script when it is available.  The curriculum
        bank is a deterministic fallback so a rate limit never stops the channel.
        """
        used_topics = list(used_topics or [])
        exclude_series = list(exclude_series or [])
        audience = audience or "beginner"
        pillar = pillar or "foundations"
        n_acts = 12 if long_form else 7

        try:
            import config
            if getattr(config, "GEMINI_API_KEY", ""):
                from google import genai
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                model_name = getattr(config, "GEMINI_MODEL", "gemini-3.8-flash")
                prompt = self._build_topic_prompt(audience, pillar, n_acts, used_topics, exclude_series)
                res = client.models.generate_content(model=model_name, contents=prompt)
                txt = (getattr(res, "text", "") or "").strip()
                if "```json" in txt:
                    txt = txt.split("```json")[1].split("```")[0].strip()
                elif "```" in txt:
                    txt = txt.split("```")[1].split("```")[0].strip()
                data = json.loads(txt)
                validated = self._validate_topic(
                    data, audience, pillar, n_acts, used_topics, exclude_series)
                if validated:
                    print(f"[TrendHunter] Gemini wrote a fresh {audience} topic: {validated['title']}")
                    return validated
                print("[TrendHunter] Gemini topic rejected by the duplicate or quality guard.")
        except Exception as exc:
            print(f"[TrendHunter] Gemini topic generation skipped: {exc}")

        from src import curriculum
        fallback = curriculum.pick_fallback(
            audience, pillar, exclude_titles=used_topics,
            exclude_series=exclude_series, allow_repeat=True,
        )
        if fallback:
            if fallback.get("repeat_fallback"):
                print("[TrendHunter] No unused bank topic left; repeating a bank topic.")
            print(f"[TrendHunter] Curriculum fallback: {fallback['title']}")
            return fallback
        raise RuntimeError("No topic available for the requested audience")
