"""Regression tests for the round-1 classifier bugs: rules that fired on
generic advisory prose ("source" -> rce, bare "architecture", "plugins")
tagged non-AI CVEs as AI content and poisoned the digest."""

from app.pipeline.classify import classify, is_ai_relevant


def test_source_does_not_match_rce():
    labels = classify("Ashby is hiring. We are an open source company.")
    assert "offsec.vulnerability" not in labels


def test_brotli_cve_not_tagged_as_ai_architecture():
    text = (
        "CVE-2026-28372: A vulnerability in the Brotli decompression architecture "
        "of .NET allows remote code execution via a crafted archive."
    )
    labels = classify(text)
    assert "offsec.vulnerability" in labels
    assert "ai.model.architecture" not in labels
    assert not is_ai_relevant(text, labels, "security_advisory")


def test_gstreamer_plugins_not_enterprise_integration():
    text = "CVE-2026-11223: GStreamer FLV plugin heap overflow via crafted plugins."
    labels = classify(text)
    assert "enterprise.integration" not in labels
    assert not is_ai_relevant(text, labels, "vulnerability_record")


def test_bare_exploit_word_does_not_tag():
    labels = classify("The analyst exploits market inefficiencies for profit.")
    assert "offsec.exploit" not in labels


def test_publication_shaped_exploit_tags():
    labels = classify("Public exploit code released for CVE-2026-9999; proof-of-concept on exploit-db.")
    assert "offsec.exploit" in labels


def test_uk_quantisation_spelling():
    assert "ai.model.quantisation" in classify("New GGUF quantisation builds are out.")
    assert "ai.model.quantisation" in classify("New GGUF quantization builds are out.")


def test_inference_engine_is_ai_relevant():
    text = "llama.cpp release b12077: improved KV cache handling for vLLM users."
    labels = classify(text)
    assert "ai.inference" in labels
    assert is_ai_relevant(text, labels, "repository_release")


def test_ai_package_vuln_is_relevant():
    text = "Stanza pickle deserialization allows remote code execution in the NLP pipeline."
    labels = classify(text)
    assert "offsec.vulnerability" in labels
    assert is_ai_relevant(text, labels, "security_advisory")


def test_mcp_spec_labels_and_relevance():
    text = "Model Context Protocol specification updated with new tool calling rules."
    labels = classify(text)
    assert "mcp.specification" in labels
    assert is_ai_relevant(text, labels, "specification")


def test_unknown_labels_filtered_from_existing():
    labels = classify("plain text", existing=["ai.inference", "made.up.label"])
    assert "ai.inference" in labels
    assert "made.up.label" not in labels


def test_rolling_release_model_boilerplate_is_not_a_model_release():
    # VulDB advisory boilerplate — round-2 tagged a PHP classroom CVE as AI.
    text = (
        "A vulnerability was identified in CloudClassroom-PHP-Project. "
        "The exploit has been released to the public. This product uses a "
        "rolling release model to deliver continuous updates."
    )
    labels = classify(text)
    assert "ai.model.release" not in labels
    assert not is_ai_relevant(text, labels, "security_advisory")


def test_real_model_release_still_tags():
    labels = classify("We are releasing a new model today: open weights available.")
    assert "ai.model.release" in labels
