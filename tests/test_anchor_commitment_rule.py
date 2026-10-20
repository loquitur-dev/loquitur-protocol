"""The rule of anchor-commitment.md section 1 is the same rule whatever the anchoring method.

Registering anchoring methods (verification-vocabularies.md section 5) generalizes what carries an
anchor, and must not touch what an anchor commits to: `H`, the SHA-256 of the registry entry's v2
signing message. Section 1 is therefore held byte for byte: the bytes from its heading up to the
next `## ` heading have the digest they had when the anchoring methods were introduced. Any change
to them, wording included, is a change to the rule and fails here, where it has to be argued as one.
The corpus vector vectors/anchor-methods.json holds the other half: one signed entry has one `H`
with no anchor and under an anchor of each method.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/specification/anchor-commitment.md"
SECTION_1_SHA256 = "2505360e9f297bae8e93c4868262cec8f73dfa2b012560e7feab2e3e166f1a3c"


def section_1() -> bytes:
    text = DOCUMENT.read_bytes()
    start = text.index(b"## 1. The rule\n")
    end = text.index(b"\n## ", start) + 1
    return text[start:end]


def test_section_1_is_byte_identical_to_the_rule_as_pinned() -> None:
    assert hashlib.sha256(section_1()).hexdigest() == SECTION_1_SHA256


def test_section_1_states_the_commitment_to_h() -> None:
    rule = section_1().decode("utf-8")
    assert "MUST commit to `H`" in rule
    assert "Nothing else may be committed." in rule


def test_the_anchoring_methods_section_defers_to_section_1() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")
    assert "## 6. Anchoring methods" in text
    methods = text.split("## 6. Anchoring methods", 1)[1]
    for method in ("blockchain_transaction", "rfc3161_timestamp", "transparency_log_checkpoint"):
        assert f"`{method}`" in methods, method
    assert "§1 binds" in methods or "section 1 binds" in methods
