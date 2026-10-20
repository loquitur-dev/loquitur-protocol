"""The reason-code register in docs/specification/reason-codes.md is generated, and must stay so.

tools/render_reason_codes.py renders the register and the affirmative-code table from the
catalog, and refuses to render when the catalog and the two schema enums disagree. Its
docstring says the register is "GENERATED, never typed", and this module is what runs the
tool: without it an edit to the document, or to the catalog without re-rendering, would leave
every gate green, and the one guarantee the tool exists to give would be kept only by whoever
remembered to run it.

The first test runs the tool over this repository in its verify mode. The others run it over
a scratch copy of the four files it reads, after one change of the kind that has to fail: a
hand edit inside the generated block, and a catalog severity changed without re-rendering.
A scratch copy, because the tool resolves every path from its own location and the real
documents must not be touched.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = "tools/render_reason_codes.py"
INPUTS = (
    "docs/specification/reason-codes/v2.0/catalog.json",
    "docs/specification/reason-codes/schema.json",
    "docs/specification/schemas/verification_summary.schema.json",
    "docs/specification/schemas/registry_entry.schema.json",
    "docs/specification/schemas/verification_receipt.schema.json",
    "docs/specification/reason-codes.md",
)


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, TOOL],
        cwd=root,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        encoding="utf-8",
        check=False,
    )


def _scratch(tmp_path: Path) -> Path:
    for rel in (TOOL, *INPUTS):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, tmp_path / rel)
    return tmp_path


def test_the_committed_register_matches_the_catalog() -> None:
    result = _run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "document block matches" in result.stdout


def test_the_scratch_copy_is_faithful(tmp_path: Path) -> None:
    # Without this, the two failure tests below would pass for any reason the copy is
    # broken: a missing input fails the tool too.
    result = _run(_scratch(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_hand_edit_inside_the_generated_register_fails(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    document = root / "docs/specification/reason-codes.md"
    text = document.read_text(encoding="utf-8")
    begin = text.index("<!-- BEGIN GENERATED REGISTER -->")
    end = text.index("<!-- END GENERATED REGISTER -->")
    assert "**57 codes across 11 categories**" in text[begin:end]
    edited = text[:begin] + text[begin:end].replace("**57 codes", "**56 codes", 1) + text[end:]
    document.write_bytes(edited.encode("utf-8"))
    result = _run(root)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "do not match the catalog" in result.stderr


def test_a_catalog_change_that_was_not_rendered_fails(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    catalog_path = root / "docs/specification/reason-codes/v2.0/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    code, entry = next((code, entry) for code, entry in catalog["entries"].items() if entry["severity"] == "fail")
    entry["severity"] = "review"
    catalog_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    result = _run(root)
    assert result.returncode == 1, f"{code} changed severity and the register still verified:\n{result.stdout}"


def test_a_receipt_enum_that_drifts_from_the_catalog_fails(tmp_path: Path) -> None:
    """The third copy of the vocabulary, on the verification receipt, is guarded like the other two."""
    root = _scratch(tmp_path)
    schema_path = root / "docs/specification/schemas/verification_receipt.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    enum = schema["properties"]["reason_codes"]["items"]["enum"]
    dropped = enum.pop()
    schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    result = _run(root)
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"verification_receipt.reason_codes enum omits catalog code(s): [{dropped!r}]" in result.stderr


def test_the_vocabulary_codes_are_in_their_category_and_no_code_is_about_a_chain() -> None:
    """The two codes of registered vocabularies, and the reserved anchoring category.

    VOCABULARY_VALUE_UNKNOWN is a question (review) and VOCABULARY_VALUE_INVALID a producer
    defect (fail). No code of this version is about an anchoring record: the category name
    anchoring is reserved and the meta-schema does not admit it, and the category chain is gone.
    """
    catalog = json.loads((ROOT / INPUTS[0]).read_text(encoding="utf-8"))["entries"]
    assert {code: (entry["category"], entry["severity"]) for code, entry in catalog.items() if code.startswith("VOCABULARY_")} == {
        "VOCABULARY_VALUE_UNKNOWN": ("vocabulary", "review"),
        "VOCABULARY_VALUE_INVALID": ("vocabulary", "fail"),
    }
    categories = json.loads((ROOT / INPUTS[1]).read_text(encoding="utf-8"))["$defs"]["CatalogEntry"]["properties"]["category"]["enum"]
    assert categories[-1] == "vocabulary"
    assert "chain" not in categories and "anchoring" not in categories
    assert not [code for code, entry in catalog.items() if "CHAIN" in code or entry["category"] in ("chain", "anchoring")]
    register = (ROOT / INPUTS[-1]).read_text(encoding="utf-8")
    assert "### 2.8 `anchoring` — reserved" in register and "### 2.12 `vocabulary` — 2 codes" in register
