"""Taxonomy classification.

Heuristic keyword classifier as the always-available baseline. When the LLM
endpoint is enabled, its labels are merged in (see pipeline/llm.py). Labels
come from the design doc's coverage taxonomy.
"""

import re

TAXONOMY_RULES: list[tuple[str, str]] = [
    (r"\bkev\b|known exploited|exploitation (observed|in the wild)|active exploitation", "offsec.vulnerability"),
    (r"\bcve-\d{4}|cvss|vulnerabilit|zero-?day|rce\b|remote code execution", "offsec.vulnerability"),
    (r"\bexploit\b|proof[- ]of[- ]concept|\bpoc\b|exploit-db|metasploit", "offsec.exploit"),
    (r"payload|shellcode|privilege escalation|lateral movement|persistence mechanism", "offsec.exploit-technique"),
    (r"\bc2\b|cobalt strike|sliver|mythic|bloodhound|impacket", "offsec.tool"),
    (r"ai-?assisted (exploit|attack|revers|phishing)|llm-?generated (malware|exploit)", "offsec.ai-assisted"),
    (r"model (release|launch)|open[- ]weights?|model card|now available.*model", "ai.model.release"),
    (r"transformer|mixture[- ]of[- ]experts|\bmoe\b|attention mechanism|architecture", "ai.model.architecture"),
    (r"\bgguf\b|safetensors|quantiz|int4|int8|fp8|4-bit|8-bit", "ai.model.quantisation"),
    (r"vllm|llama\.cpp|ollama|sglang|inference engine|tokens/sec|continuous batching", "ai.inference"),
    (r"\bagent(s|ic)?\b|tool[- ]calling|function calling|computer use", "ai.agent"),
    (r"benchmark|eval(uation)?|swe-?bench|mmlu|humanEval|leaderboard", "ai.evaluation"),
    (r"guardrail|jailbreak|red[- ]team(ing)? (ai|llm|model)|safety (eval|benchmark)", "ai.safety"),
    (r"model context protocol|\bmcp\b (spec|specification|server|client)", "mcp.specification"),
    (r"mcp (server|tool) (release|launch|registry)", "mcp.server"),
    (r"prompt injection|tool poisoning|tool shadowing|confused deputy|mcp.*(vulnerab|exploit|attack)", "mcp.security"),
    (r"deploys?|rollout|roll[s]? out|adopts?|standardizes? on|enterprise-wide", "enterprise.deployment"),
    (r"case stud|customer stor|in production at", "enterprise.case-study"),
    (r"contract|procurement|purchase agreement|enterprise agreement", "enterprise.procurement"),
    (r"integrat(e|es|ion) with|plugin|connector for", "enterprise.integration"),
    (r"governance|compliance|eu ai act|nist|iso 42001|risk management framework", "enterprise.governance"),
    (r"announc(e|es|ing).*(product|feature)|launch(es|ing)?", "vendor.product"),
    (r"partnership|partner with|collaborat(e|ion) with", "vendor.partnership"),
    (r"acqui(re|res|sition)|merger", "vendor.acquisition"),
    (r"pricing|price (cut|increase|change)|per[- ]token", "vendor.pricing"),
    (r"arxiv|preprint|proceedings|usenix|ieee s&p|ndss|\biclr\b|neurips", "research.paper"),
    (r"dataset (release|available)|hugging ?face datasets", "research.dataset"),
    (r"github\.com/.*/.* (release|commit)|we (open[- ]source|release) (the )?code", "research.code"),
]

_COMPILED = [(re.compile(pat, re.I), label) for pat, label in TAXONOMY_RULES]


def classify(text: str, existing: list[str] | None = None) -> list[str]:
    labels = {label for pat, label in _COMPILED if pat.search(text)}
    if existing:
        labels.update(existing)
    return sorted(labels)
