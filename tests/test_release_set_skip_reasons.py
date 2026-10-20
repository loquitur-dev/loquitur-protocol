"""What test_release_set_verifier.py prints in a published layout must follow the verifier's rule.

The verifier names no unpublished repository in a published subset, and its tests assert
that of the verifier's output. The test module is a second path to the same reader:
`pytest -rs` prints every skip reason, and the skips fire precisely in the layouts that do
not hold every repository: a release workspace, or a single clone. A reason that names an
absent unpublished repository tells whoever runs the suite there what is not published,
which is the leak the verifier's rule closes.

So this runs that module the way such a reader would: in a scratch workspace holding only
the layout, as a separate pytest process, and reads what it printed. Asserting on the reason
strings in-process would pass vacuously for any reason built at run time.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
POINTER = "RELEASE_SET_POINTER.json"
MODULE = "tests/test_release_set_verifier.py"
REQUIRE_SIBLINGS_ENV = "LOQUITUR_REQUIRE_SIBLINGS"


def _load_verifier_tests():
    spec = importlib.util.spec_from_file_location("_release_set_verifier_tests", ROOT / MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_TESTS = _load_verifier_tests()
PUBLISHED: list[str] = _TESTS.PUBLISHED
UNPUBLISHED: list[str] = _TESTS.UNPUBLISHED

LAYOUTS = {
    # What a contributor or a single-repository CI job gets.
    "isolated": ["loquitur-protocol"],
    # What a release workspace holds.
    "published": PUBLISHED,
}


def _layout(tmp_path: Path, names: list[str]) -> Path:
    protocol = tmp_path / "ws" / "loquitur-protocol"
    (protocol / "tests").mkdir(parents=True)
    shutil.copytree(ROOT / "tools", protocol / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / MODULE, protocol / MODULE)
    for rel in ("pyproject.toml", "release-set.json", POINTER):
        shutil.copy2(ROOT / rel, protocol / rel)
    for name in names:
        if name == "loquitur-protocol":
            continue
        (protocol.parent / name).mkdir()
        shutil.copy2(WORKSPACE / name / POINTER, protocol.parent / name / POINTER)
    return protocol


@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_skip_reasons_in_a_published_layout_name_nothing_unpublished(tmp_path: Path, layout: str) -> None:
    names = LAYOUTS[layout]
    absent = [name for name in names if name != "loquitur-protocol" and not (WORKSPACE / name / POINTER).is_file()]
    if absent:
        message = f"published repositories not checked out beside this one: {absent}"
        if os.environ.get(REQUIRE_SIBLINGS_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
            pytest.fail(f"{REQUIRE_SIBLINGS_ENV} is set, but {message}")
        pytest.skip(message)
    protocol = _layout(tmp_path, names)

    environment = dict(os.environ)
    environment.pop("PYTEST_ADDOPTS", None)
    # The layout is incomplete on purpose: it is what a reader has, and that reader has not
    # set the variable. Inherited from a complete workspace, it would turn the skips this
    # test reads into failures.
    environment.pop(REQUIRE_SIBLINGS_ENV, None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", MODULE],
        cwd=protocol,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**environment, "PYTHONIOENCODING": "utf-8"},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    # Non-vacuity: the layout must actually produce skip reasons, or there is nothing to read.
    assert "SKIPPED" in output, output
    leaked = [name for name in UNPUBLISHED if name in output]
    assert not leaked, f"the {layout} layout's test output names unpublished repositories {leaked}:\n{output}"
