"""Deterministic identifier + entity extraction.

LLMs never do this part — CVE/GHSA/CWE/arXiv IDs, repository paths, URLs,
versions and hashes are all regular-structure data. Deterministic extraction
is exact, auditable and free.
"""

import re
from typing import Any

CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)
GHSA_RE = re.compile(r"\bGHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}\b", re.I)
CWE_RE = re.compile(r"\bCWE-\d{1,5}\b", re.I)
ARXIV_RE = re.compile(r"\barXiv:(\d{4}\.\d{4,5})(v\d+)?\b", re.I)
GITHUB_REPO_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")
SEMVER_RE = re.compile(r"\bv?(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?)\b")

# Heuristic model-name detector: Vendor-Name-7B / Name-3x7B-Instruct etc.
MODEL_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*-(?:\d+(?:\.\d+)?[x×]?\d*[BbMm])(?:-[A-Za-z0-9]+)*)\b"
)


def extract_identifiers(text: str, existing: dict[str, Any] | None = None) -> dict[str, list[str]]:
    ids: dict[str, list[str]] = {
        "cve": sorted({m.upper() for m in CVE_RE.findall(text)}),
        "ghsa": sorted({m.upper() for m in GHSA_RE.findall(text)}),
        "cwe": sorted({m.upper() for m in CWE_RE.findall(text)}),
        "repository": sorted({r.strip("/") for r in GITHUB_REPO_RE.findall(text)}),
        "model": sorted(set(MODEL_RE.findall(text))),
        "arxiv": sorted({m[0] for m in ARXIV_RE.findall(text)}),
    }
    if existing:
        for key, values in ids.items():
            merged = set(values) | set((existing or {}).get(key) or [])
            ids[key] = sorted(merged)
        if existing.get("other"):
            ids["other"] = existing["other"]
    return ids


def identifiers_to_entities(ids: dict[str, list[str]]) -> list[dict[str, str]]:
    entities: list[dict[str, str]] = []
    for cve in ids.get("cve", []):
        entities.append({"type": "cve", "name": cve})
    for ghsa in ids.get("ghsa", []):
        entities.append({"type": "ghsa", "name": ghsa})
    for cwe in ids.get("cwe", []):
        entities.append({"type": "cwe", "name": cwe})
    for repo in ids.get("repository", []):
        entities.append({"type": "repository", "name": repo})
    for model in ids.get("model", []):
        entities.append({"type": "model", "name": model})
    for paper in ids.get("arxiv", []):
        entities.append({"type": "paper", "name": f"arXiv:{paper}"})
    return entities
