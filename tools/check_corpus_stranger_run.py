"""Run the commands of conformance-testing.md sections 1 and 2 where a stranger would run them.

A reader of this repository checks, extracts and validates the pinned corpus with the commands
`docs/specification/conformance-testing.md` gives in sections 1 and 2. This check copies the
files of this repository into an empty temporary directory, with no sibling repository beside
it, and runs every command of those two sections' fenced `bash` blocks there, read from the
document rather than written here. Each command must exit 0, and the check in section 1 must
print `True`.

Only commands whose program is `python` are run, with the interpreter given by `--python` (by
default the one running this check); a command naming any other program is refused, because the
check could not then say it ran the document's commands. LOQUITUR_REQUIRE_SIBLINGS and PYTHONPATH
are removed from the environment, since a stranger has neither.

Exit codes: 0 every command passed, 1 a command failed, 2 the commands cannot be found.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = "docs/specification/conformance-testing.md"
SECTIONS = ("## 1. ", "## 2. ")
# The caches and the virtual environments .gitignore names: a reader's .venv is not part of the
# repository a stranger receives, and copying it costs time and proves nothing.
IGNORED = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "venv")


def commands(text: str) -> list[str]:
    """The commands of the fenced ``bash`` blocks of sections 1 and 2, in order."""
    found: list[str] = []
    for heading in SECTIONS:
        start = text.find("\n" + heading)
        if start == -1:
            raise ValueError(f"{DOCUMENT} has no section starting {heading.strip()!r}")
        end = text.find("\n## ", start + 1)
        section = text[start : end if end != -1 else len(text)]
        for block in re.findall(r"```bash\n(.*?)```", section, re.S):
            found += [line.strip() for line in block.splitlines() if line.strip()]
    if not found:
        raise ValueError(f"sections 1 and 2 of {DOCUMENT} name no command")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="the loquitur-protocol checkout copied into the empty directory (default: the one this tool is in)",
    )
    parser.add_argument("--python", default=sys.executable, help="the interpreter `python` names")
    parser.add_argument("--timeout", type=float, default=1800.0, help="seconds each command may take")
    args = parser.parse_args(argv)
    try:
        listed = commands((args.root / DOCUMENT).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2
    env = {key: value for key, value in os.environ.items() if key not in {"LOQUITUR_REQUIRE_SIBLINGS", "PYTHONPATH"}}
    env["PYTHONIOENCODING"] = "utf-8"
    failures = 0
    with tempfile.TemporaryDirectory(prefix="stranger-") as scratch:
        checkout = Path(scratch) / "loquitur-protocol"
        shutil.copytree(args.root, checkout, ignore=IGNORED)
        for command in listed:
            words = shlex.split(command)
            if words[0] != "python":
                print(f"REFUSED  {command}: the program is not python")
                failures += 1
                continue
            try:
                result = subprocess.run(
                    [args.python, *words[1:]],
                    cwd=checkout,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=args.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                print(f"FAIL  {command}: still running after {args.timeout:.0f} s")
                failures += 1
                continue
            output = (result.stdout + result.stderr).strip()
            ok = result.returncode == 0 and ("print(" not in command or result.stdout.strip() == "True")
            print(f"{'PASS' if ok else 'FAIL'}  {command}  (exit {result.returncode})")
            if output:
                print("      " + output.replace("\n", "\n      "))
            failures += not ok
    print(f"stranger run: {len(listed) - failures} of {len(listed)} commands passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
