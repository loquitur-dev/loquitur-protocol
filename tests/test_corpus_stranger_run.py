"""tools/check_corpus_stranger_run.py runs the commands of conformance-testing.md sections 1 and 2 in an
empty directory, and fails when one of them fails."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from conftest import tool

ROOT = Path(__file__).resolve().parents[1]
stranger = tool("check_corpus_stranger_run")
IGNORED = stranger.IGNORED


def test_the_commands_are_read_from_sections_1_and_2() -> None:
    listed = stranger.commands((ROOT / stranger.DOCUMENT).read_text(encoding="utf-8"))
    assert len(listed) == 3
    assert listed[0].startswith("python -c ") and "CONFORMANCE_LOCK.json" in listed[0]
    assert "extractall('../corpus')" in listed[1]
    assert listed[2] == "python tools/validate_corpus.py ../corpus/loquitur-conformance"


def test_the_documented_commands_pass_in_an_empty_directory(capsys: pytest.CaptureFixture[str]) -> None:
    assert stranger.main([]) == 0
    output = capsys.readouterr().out
    assert "stranger run: 3 of 3 commands passed" in output
    assert "corpus OK" in output


def _with_section_2(tmp_path: Path, block: str) -> Path:
    root = tmp_path / "loquitur-protocol"
    shutil.copytree(ROOT, root, ignore=IGNORED)
    document = root / stranger.DOCUMENT
    text = document.read_text(encoding="utf-8")
    start = text.index("\n## 2. ")
    end = text.index("\n## 3. ")
    document.write_text(
        text[:start] + "\n## 2. Extract it\n\n```bash\n" + block + "\n```\n" + text[end:], encoding="utf-8"
    )
    return root


def test_a_failing_command_fails_the_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _with_section_2(tmp_path, "python tools/validate_corpus.py ../corpus/absent")
    assert stranger.main(["--root", str(root)]) == 1
    assert "FAIL  python tools/validate_corpus.py ../corpus/absent" in capsys.readouterr().out


def test_a_command_that_is_not_python_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _with_section_2(tmp_path, "unzip conformance/x.zip")
    assert stranger.main(["--root", str(root)]) == 1
    assert "REFUSED  unzip conformance/x.zip" in capsys.readouterr().out


def test_a_document_without_the_sections_is_a_usage_error(tmp_path: Path) -> None:
    root = tmp_path / "loquitur-protocol"
    (root / "docs/specification").mkdir(parents=True)
    (root / stranger.DOCUMENT).write_text("# nothing\n", encoding="utf-8")
    assert stranger.main(["--root", str(root)]) == 2
