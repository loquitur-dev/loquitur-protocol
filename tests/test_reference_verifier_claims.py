"""A normative document may not credit the reference verifiers with what they do not do.

This repository is read alone: the reader it is written for is an outside developer writing a
conforming verifier from it and nothing else. So a sentence here that describes the
reference implementations is a claim that reader cannot check, and a stale one sends them
looking for an option that does not exist.

A document that credits them with a migration-only path for legacy v1 signatures, or a
schema that says verifiers reject such a signature `by default`, asserts a path on which they
accept. No needle matches either wording, and a document compared only with other documents
can be uniformly wrong.

What is checked here is therefore two-sided. The documents must deny the option, and the
reference command line must genuinely not offer it. Either side flipping alone fails, so
the denial cannot quietly become false and the option cannot quietly come back.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPECIFICATION = ROOT / "docs" / "specification"

# An option for that purpose would be spelled with these.
LEGACY_OPTION_WORDS = ("legacy", "migration", "v1")


def _prose(text: str) -> str:
    """The document without its fenced code blocks.

    A worked example is not a claim about the reference verifiers, and a block of Python
    has no sentence ends, so leaving one in makes a single unsplittable sentence out of
    everything around it.
    """
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    assert not fenced, "a fenced code block is never closed"
    return "\n".join(out)


def _sentences(text: str) -> list[str]:
    """Split on sentence ends, keeping the text otherwise intact."""

    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", _prose(text)) if s.strip()]


def _normative_documents() -> list[Path]:
    documents = sorted(SPECIFICATION.glob("*.md"))
    assert documents, f"no normative documents found under {SPECIFICATION}"
    return documents


def test_no_normative_document_credits_the_reference_verifiers_with_an_option() -> None:
    """Where a document names the reference verifiers and an option, it must deny it.

    The protocol allows a verifier to offer an out-of-conformance option for evidence
    recovery, and says so. What it may not do is state that the reference verifiers are
    such a verifier, because they are not.
    """
    offenders: list[str] = []
    for document in _normative_documents():
        for sentence in _sentences(document.read_text(encoding="utf-8")):
            flat = " ".join(sentence.split())
            lowered = flat.lower()
            if "reference verifier" not in lowered or "option" not in lowered:
                continue
            if "no such option" in lowered or "no option" in lowered:
                continue
            offenders.append(f"{document.relative_to(ROOT).as_posix()}: {flat}")

    assert not offenders, (
        "a normative document credits the reference verifiers with an option instead of "
        "denying it; the wording used elsewhere is 'The reference verifiers offer no such "
        "option':\n  " + "\n  ".join(offenders)
    )


def test_no_normative_schema_says_a_legacy_signature_is_rejected_only_by_default() -> None:
    """`reject by default` names a default, and so asserts the other path exists.

    A conforming verifier rejects a v1 signature on every path. A description that hedges
    the rejection tells a schema reader the opposite of what the signing envelope
    specification tells a prose reader.
    """
    def descriptions(node: object) -> list[str]:
        """Every `description` string anywhere in a schema, at any depth."""

        found: list[str] = []
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "description" and isinstance(value, str):
                    found.append(value)
                else:
                    found.extend(descriptions(value))
        elif isinstance(node, list):
            for value in node:
                found.extend(descriptions(value))
        return found

    offenders: list[str] = []
    schemas = sorted((SPECIFICATION / "schemas").glob("*.json"))
    assert schemas, f"no normative schemas found under {SPECIFICATION / 'schemas'}"
    for schema in schemas:
        for description in descriptions(json.loads(schema.read_text(encoding="utf-8"))):
            lowered = description.lower()
            if "reject" not in lowered:
                continue
            if "by default" in lowered or "unless" in lowered:
                offenders.append(f"{schema.relative_to(ROOT).as_posix()}: {description}")

    assert not offenders, (
        "a normative schema describes a rejection as conditional, which asserts a path on "
        "which the value is accepted:\n  " + "\n  ".join(offenders)
    )


def test_the_reference_command_line_offers_no_legacy_option() -> None:
    """The anchor outside the documents.

    Without this, the two checks above only hold the documents against each other, and a
    denial that has become false reads exactly like one that is still true. The reference
    command line is the thing the denial is about, so it is what the denial is measured
    against.
    """
    cli = ROOT.parent / "loquitur-verify-py" / "src" / "loquitur" / "verify" / "cli.py"
    if not cli.is_file():
        message = f"loquitur-verify-py is not checked out beside this repository at {cli}"
        if os.environ.get("LOQUITUR_REQUIRE_SIBLINGS", "").strip().lower() in {"1", "true", "yes", "on"}:
            pytest.fail(message)
        pytest.skip(message)

    options = sorted(set(re.findall(r'"(--[a-z0-9-]+)"', cli.read_text(encoding="utf-8"))))
    assert options, f"no long options found in {cli}; the extraction has stopped working"

    offering = [
        option
        for option in options
        if any(word in option for word in LEGACY_OPTION_WORDS)
    ]
    assert not offering, (
        "the reference command line offers an option this repository's documents say it "
        f"does not: {offering}. Either the option is unintended, or every document that "
        "denies it is wrong and changes with it."
    )


def test_the_documents_and_the_anchor_are_about_the_same_thing() -> None:
    """Guard the pair above against drifting apart into two unrelated checks.

    The denial these documents make is specifically about verifying the legacy v1 signing
    payload. If that subject ever leaves the specification, the anchor is measuring
    nothing and should be retired rather than left passing.
    """
    envelope = SPECIFICATION / "signing-envelope-v2.md"
    text = envelope.read_text(encoding="utf-8")
    assert "Legacy migration policy" in text, (
        f"{envelope.relative_to(ROOT).as_posix()} does not state the legacy migration "
        "policy, so the checks in this module have lost their subject"
    )
    assert "offer no such option" in text, (
        f"{envelope.relative_to(ROOT).as_posix()} does not deny the option, so the "
        "anchor is bound to a claim the repository has stopped making"
    )


def test_the_prose_digests_cover_the_documents_these_checks_read() -> None:
    """A sentence these checks read cannot change without its digest changing."""

    digests = json.loads((SPECIFICATION / "PROSE_DIGESTS.json").read_text(encoding="utf-8"))
    listed = {entry["path"] for entry in digests["files"]}
    for document in _normative_documents():
        relative = document.relative_to(ROOT).as_posix()
        assert relative in listed, (
            f"{relative} is read by these checks but is not bound by PROSE_DIGESTS.json"
        )
