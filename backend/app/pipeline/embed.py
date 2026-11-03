"""Embeddings. OpenAI-compatible /embeddings endpoint (Ollama, vLLM, TEI or a
cloud provider). Falls back to a deterministic hash-based pseudo-embedding so
the pipeline and hybrid search stay functional with no model available —
vector recall will be meaningless in that mode, lexical search still works.
"""

import hashlib
import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)


def _pseudo_embedding(text: str) -> list[float]:
    dim = settings.embed_dim
    vec = [0.0] * dim
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


async def embed_text(text: str) -> tuple[list[float], str]:
    """Returns (vector, model_label)."""
    if not settings.llm_enabled:
        return _pseudo_embedding(text), "pseudo-hash"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.llm_base_url.rstrip('/')}/embeddings",
                json={"model": settings.embed_model, "input": text[:8000]},
                headers=_auth(),
            )
            resp.raise_for_status()
            vec = resp.json()["data"][0]["embedding"]
            if len(vec) != settings.embed_dim:
                log.warning("embedding dim %s != configured %s; using pseudo-embedding", len(vec), settings.embed_dim)
                return _pseudo_embedding(text), "pseudo-hash"
            return vec, settings.embed_model
    except Exception as exc:  # endpoint down, model missing, etc.
        log.warning("embedding endpoint unavailable (%s); using pseudo-embedding", exc)
        return _pseudo_embedding(text), "pseudo-hash"


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}
