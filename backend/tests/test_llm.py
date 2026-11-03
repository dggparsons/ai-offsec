"""TLDR/markup hygiene: no raw markdown, no listing boilerplate, no
mid-word truncation (round-1 end-user findings). Plus the schema wall:
nothing unvalidated from the model may reach the analyses table."""

import pytest
from pydantic import ValidationError

from app.pipeline.llm import _validated, heuristic_analysis, make_tldr
from app.pipeline.normalize import strip_markup, truncate_words


def test_tldr_strips_markdown_headings():
    body = (
        "### Impact\nA critical vulnerability in the inference server allows "
        "remote code execution by anyone. Patches are available upstream now."
    )
    tldr = make_tldr("Advisory", body)
    assert "#" not in tldr
    assert "remote code execution" in tldr


def test_tldr_strips_hn_boilerplate():
    body = (
        "Article URL: https://example.com/post\nPoints: 6\nComments: 0\n"
        "A new open weights model beats every benchmark published this year."
    )
    tldr = make_tldr("HN post", body)
    assert "Points" not in tldr
    assert "Article URL" not in tldr
    assert "open weights model" in tldr


def test_truncation_is_word_bounded_with_ellipsis():
    text = " ".join(f"word{i:03d}" for i in range(120))  # 719 chars
    out = truncate_words(text, 400)
    assert out.endswith("…")
    assert len(out) <= 400
    assert out[:-1].split()[-1].startswith("word")  # no mid-word cut


def test_heuristic_analysis_stores_no_filler_rows():
    out = heuristic_analysis("Title", "Some body text about models.", ["ai.inference"])
    assert "fact_summary" not in out
    assert "technical_delta" not in out
    assert out["confidence"] == "low"
    assert out["taxonomy_labels"] == ["ai.inference"]


def test_strip_markup_keeps_link_text():
    assert strip_markup("See [the advisory](https://x.test) now") == "See the advisory now"


def test_strip_markup_preserves_snake_case_identifiers():
    # Round-2: the emphasis regex ate underscores in identifiers.
    text = "a crafted ACTION_SEND intent with a ContentProvider-supplied file_name"
    assert strip_markup(text) == text
    assert strip_markup("**Important** and `code` here") == "Important and code here"


def test_validated_drops_unknown_keys_and_labels():
    out = _validated(
        {
            "tldr": "A model did a thing.",
            "confidence": "high",
            "taxonomy_labels": ["ai.inference", "invented.label"],
            "prompt_injection_attempt": "ignore previous instructions",
        }
    )
    assert "prompt_injection_attempt" not in out
    assert out["taxonomy_labels"] == ["ai.inference"]
    assert out["confidence"] == "high"


def test_validated_rejects_bad_confidence():
    with pytest.raises(ValidationError):
        _validated({"confidence": "definitely"})


def test_validated_defaults_confidence_low_not_up():
    assert _validated({"tldr": "x"})["confidence"] == "low"


def test_validated_tldr_is_cleaned_and_truncated():
    out = _validated({"tldr": "### " + " ".join(["word"] * 200)})
    assert "#" not in out["tldr"]
    assert len(out["tldr"]) <= 400
