"""Taxonomy classification and AI-relevance detection.

Heuristic keyword classifier as the always-available baseline. When the LLM
endpoint is enabled, its labels are merged in (see pipeline/llm.py) after
being validated against ALLOWED_LABELS. Labels come from the design doc's
coverage taxonomy.

Rules are deliberately narrow: a label that fires on generic advisory prose
(review round 1, 2026-11-03: "rce\\b" matched the word "source", bare
"architecture" tagged a Brotli CVE as ai.model.architecture, "plugins"
tagged GStreamer as enterprise.integration) poisons scoring and the digest.
Tests in backend/tests/test_classify.py pin known good/bad examples.
"""

import re

TAXONOMY_RULES: list[tuple[str, str]] = [
    # --- offensive security ---
    (r"\bkev\b|known exploited|exploitation (observed|in the wild)|active(ly)? exploit", "offsec.vulnerability"),
    (r"\bcve-\d{4}-\d{4,7}\b|\bcvss\b|vulnerabilit|zero-?day|\brce\b|remote code execution|security advisory", "offsec.vulnerability"),
    (r"exploit (code|module|script|poc|chain|is (public|available)|released|published)|proof[- ]of[- ]concept|\bpoc\b|exploit-db|metasploit", "offsec.exploit"),
    (r"shellcode|privilege escalation|lateral movement|persistence mechanism|initial access|post-exploitation", "offsec.exploit-technique"),
    (r"\bc2 framework\b|cobalt strike|sliver|mythic|bloodhound|impacket|burp suite|nuclei template", "offsec.tool"),
    (r"tradecraft|\bttps\b|red[- ]team (operation|engagement|infrastructure)", "offsec.tradecraft"),
    (r"ai-?assisted (exploit|attack|revers|phishing|intrusion)|llm-?(generated|assisted) (malware|exploit|phishing)|ai-?(powered|driven) (attack|malware)", "offsec.ai-assisted"),
    # --- AI models & inference ---
    # Release-shaped verbs only — a paper *about* open-weight models is not
    # itself a model release (round-2 mislabel), and "rolling release model"
    # boilerplate is not a model release either (verb forms, no bare noun).
    (r"(releas(es|ed|ing)|launch(es|ed|ing)|unveil(ed|s|ing)|drops?|introducing) (a |an |the |new |our )?(model|llm|checkpoint|weights)\b|open[- ]weights? (release|available)|introducing (gpt|claude|gemini|llama|qwen|mistral|deepseek|gemma|phi|grok)", "ai.model.release"),
    (r"open[- ]weights?|model weights|weights (are |now )?(available|released|published)", "ai.model.weights"),
    (r"(model|transformer|neural) architecture|mixture[- ]of[- ]experts|\bmoe\b|attention mechanism|state[- ]space model", "ai.model.architecture"),
    (r"\bgguf\b|safetensors|quanti[sz]|\bint4\b|\bint8\b|\bfp8\b|4-bit|8-bit", "ai.model.quantisation"),
    (r"\bvllm\b|llama\.cpp|\bollama\b|\bsglang\b|inference (engine|server)|tokens/sec|continuous batching|kv[- ]cache", "ai.inference"),
    (r"(ai|llm|autonomous|coding) agent|agentic|tool[- ]calling|function calling|computer use|agent (framework|workspace|workflow)", "ai.agent"),
    (r"(model|llm|ai) (benchmark|eval)|swe-?bench|\bmmlu\b|humaneval|leaderboard|evaluation harness", "ai.evaluation"),
    (r"guardrail|jailbreak|red[- ]team(ing)? (ai|llm|model)|safety (eval|benchmark|training)|alignment faking|model misuse", "ai.safety"),
    # --- MCP ecosystem ---
    (r"model[- ]?context[- ]?protocol|\bmcp\b (spec|specification|protocol|client)", "mcp.specification"),
    (r"mcp (server|tool|registry)", "mcp.server"),
    (r"prompt injection|tool poisoning|tool shadowing|confused deputy|mcp[^.]{0,40}(vulnerab|exploit|attack|hijack)", "mcp.security"),
    # --- enterprise adoption (AI context required; generic IT news is noise here) ---
    (r"(deploys?|rolls? out|rolled out|adopts?|standardi[sz]es? on) (ai|llm|genai|generative ai|copilot|claude|chatgpt|gemini)|enterprise[- ]wide (ai|llm)", "enterprise.deployment"),
    (r"(ai|llm|genai) (case stud|customer stor)|in production at", "enterprise.case-study"),
    (r"(ai|llm|genai|model) (contract|procurement|purchase agreement|enterprise agreement)", "enterprise.procurement"),
    (r"integrat(es?|ion) with (ai|an? llm|claude|chatgpt|gemini|copilot)|mcp (connector|integration)", "enterprise.integration"),
    (r"(ai|llm) governance|eu ai act|iso 42001|nist ai|ai risk management framework", "enterprise.governance"),
    # --- vendor news ---
    (r"announc(e|es|ing) (a |an |new )?(model|api|agent|product|feature)|launch(es|ing)? (a |an |new )?(model|api|agent|product|feature)", "vendor.product"),
    (r"partnership|partners? with|collaborat(e|ion) with", "vendor.partnership"),
    (r"acqui(res?|sition)|merger", "vendor.acquisition"),
    (r"pricing|price (cut|increase|change)|per[- ]token", "vendor.pricing"),
    # --- research ---
    (r"\barxiv\b|preprint|proceedings|usenix|ieee s&p|\bndss\b|\biclr\b|neurips|acm ccs", "research.paper"),
    (r"(mlperf|swe-?bench|\bmmlu\b|humaneval|cyberseceval|agentharm)|benchmark (results|suite|release)", "research.benchmark"),
    (r"dataset (release|available)|hugging ?face datasets", "research.dataset"),
    (r"we (open[- ]source|release) (the )?code|code (is |now )?(available|released) (on|at) github", "research.code"),
]

_COMPILED = [(re.compile(pat, re.I), label) for pat, label in TAXONOMY_RULES]

# The one canonical label set. llm.py's prompt and ingest's merge both
# validate against this; score.py and digest.py consume only these.
ALLOWED_LABELS: frozenset[str] = frozenset(label for _pat, label in TAXONOMY_RULES) | {
    "mcp.client",
    "mcp.enterprise",
}

# AI-relevance gate. The daily digest only admits events that are about
# AI/LLM systems (the platform's mission); everything else stays searchable
# but never occupies the morning read. Matches are case-insensitive and
# word-bounded to avoid substring accidents.
_AI_TERMS = (
    r"\b(llms?|large language models?|genai|generative ai|foundation model|frontier model|"
    r"gpt-?[45o]\w*|chatgpt|openai|anthropic|claude|gemini|deepmind|copilot|"
    r"llama(\.cpp)?|ollama|vllm|sglang|llamaindex|langchain|lang graph|langgraph|"
    r"hugging ?face|transformers library|pytorch|tensorflow|\bonnx\b|litellm|mlflow|tensorrt|"
    r"mistral|qwen|deepseek|gemma|phi-\d|grok|kimi|glm-\d|"
    r"prompt injection|jailbreak|system prompt|model context protocol|mcp servers?|"
    r"ai (agent|assistant|model|chatbot|coding|pentest|red[- ]team|security)|agentic|"
    r"(coding|autonomous) agents?|machine learning|deep learning|neural network|"
    r"fine-?tun(e|ed|ing)|open[- ]weights?|inference (engine|server)|embedding model|"
    r"text-to-(image|video|speech)|diffusion model|stable diffusion|speech recognition|"
    r"stanza|spacy|whisper|comfyui|gradio|streamlit ai)\b"
)
_AI_RE = re.compile(_AI_TERMS, re.I)

# Sources whose whole remit is AI: their items are relevant by construction.
# Deliberately NOT "research": arXiv cs.CR is cryptography & security broadly
# (Android firmware, DeFi), so its papers must name an AI system or carry an
# ai.*/mcp.* label like everything else.
AI_SOURCE_TYPES = {"repository_release", "specification", "vendor_blog"}


def classify(text: str, existing: list[str] | None = None) -> list[str]:
    labels = {label for pat, label in _COMPILED if pat.search(text)}
    if existing:
        labels.update(l for l in existing if l in ALLOWED_LABELS)
    return sorted(labels)


def is_ai_relevant(text: str, taxonomy: list[str], source_type: str = "") -> bool:
    """Gate for the daily digest: is this event about AI/LLM systems?

    True when the source is AI-dedicated, the taxonomy carries an ai.*/mcp.*
    label, or the text names an AI system/topic. False means "searchable,
    not front-page" — never deletion.
    """
    if source_type in AI_SOURCE_TYPES:
        return True
    if any(t.startswith(("ai.", "mcp.")) or t == "offsec.ai-assisted" for t in taxonomy):
        return True
    return bool(_AI_RE.search(text))
