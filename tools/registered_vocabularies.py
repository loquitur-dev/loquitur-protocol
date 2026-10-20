"""Check the registered vocabularies under vocabularies/, and that a change to one only adds.

    python tools/registered_vocabularies.py [--base REVISION]

Each file `vocabularies/<kind>.json` is one version of the registered vocabulary of that kind
(docs/specification/verification-vocabularies.md sections 5 to 10). Three things are checked:

  * CONTRACT: the file satisfies docs/specification/registered-vocabularies/schema.json, and the
    two rules the schema cannot state (section 6): no value's `since` is later than the
    document's `version`, and `asset_types` is present on a value exactly when `kind` is
    `workflow`. Its free strings are not empty under the whitespace set W of bundle-objects.md.
  * COVERAGE: there is exactly one file per kind the meta-schema closes `kind` to, named after it,
    and every workflow's `asset_types` names a value of the asset_type vocabulary.
  * APPEND-ONLY, with --base: each file is compared with its own bytes at REVISION, read with
    `git show`. No value is removed, no `since` changes, a status only moves from `active` to
    `deprecated`, a value's `asset_types` never changes, `version` grows by the component the
    change calls for (a minor version for an added or deprecated value, a patch for a title or a
    profile), and every added value carries `since` equal to the new `version` (section 9). A file
    that does not exist at REVISION is new, and only its contract is checked.

Exit codes: 0 verified, 1 a check failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META_SCHEMA = "docs/specification/registered-vocabularies/schema.json"
DIRECTORY = "vocabularies"
VERSION = re.compile(r"(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})")

# The whitespace set W of bundle-objects.md: a free string made only of these code points is empty.
_W = frozenset(
    [*range(0x09, 0x0E), *range(0x1C, 0x20), 0x20, 0x85, 0xA0, 0x1680, *range(0x2000, 0x200B)]
    + [0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF]
)


def empty_under_w(value: str) -> bool:
    return all(ord(character) in _W for character in value)


def version_tuple(value: str) -> tuple[int, int, int]:
    match = VERSION.fullmatch(value)
    if match is None:
        raise ValueError(f"not a vocabulary version: {value!r}")
    return int(match[1]), int(match[2]), int(match[3])


def _strict(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate member {key!r}")
        result[key] = value
    return result


def parse(data: bytes) -> object:
    """A vocabulary document's bytes, read as strict UTF-8 JSON with no duplicate member."""
    return json.loads(data.decode("utf-8"), object_pairs_hook=_strict)


def meta_schema(root: Path = ROOT) -> dict:
    return json.loads((root / META_SCHEMA).read_text(encoding="utf-8"))


def kinds(root: Path = ROOT) -> list[str]:
    return list(meta_schema(root)["properties"]["kind"]["enum"])


def contract_errors(document: object, root: Path = ROOT) -> list[str]:
    """Every way ``document`` breaks the meta-schema or the rules of section 6."""
    import jsonschema

    validator = jsonschema.Draft202012Validator(meta_schema(root))
    errors = [
        f"{'/'.join(str(part) for part in error.absolute_path) or '(document)'}: {error.message}"
        for error in sorted(validator.iter_errors(document), key=lambda e: list(map(str, e.absolute_path)))
    ]
    if errors or not isinstance(document, dict):
        return errors or ["the document is not an object"]
    return prose_errors(document)


def prose_errors(document: dict) -> list[str]:
    """The rules of section 6 that no keyword of the meta-schema states."""
    errors: list[str] = []
    version = version_tuple(document["version"])
    for value, entry in document["values"].items():
        if version_tuple(entry["since"]) > version:
            errors.append(f"values/{value}: since {entry['since']} is later than the version {document['version']}")
        if ("asset_types" in entry) != (document["kind"] == "workflow"):
            errors.append(f"values/{value}: asset_types is present exactly when kind is workflow")
        for member in ("title", "profile"):
            text = entry.get(member)
            if isinstance(text, str) and empty_under_w(text):
                errors.append(f"values/{value}/{member} is empty under W")
    return errors


def append_only_errors(old: dict, new: dict) -> list[str]:
    """Every way ``new`` is not a later version of ``old`` under section 9."""
    errors: list[str] = []
    if old["kind"] != new["kind"]:
        return [f"kind changed from {old['kind']} to {new['kind']}"]
    minor = patch = False
    for value, before in old["values"].items():
        after = new["values"].get(value)
        if after is None:
            errors.append(f"values/{value} was removed")
            continue
        if after["since"] != before["since"]:
            errors.append(f"values/{value}: since changed from {before['since']} to {after['since']}")
        if after["status"] != before["status"]:
            if (before["status"], after["status"]) == ("active", "deprecated"):
                minor = True
            else:
                errors.append(f"values/{value}: status moved from {before['status']} to {after['status']}")
        if after.get("asset_types") != before.get("asset_types"):
            errors.append(f"values/{value}: asset_types changed")
        if after["title"] != before["title"] or after["profile"] != before["profile"]:
            patch = True
    added = sorted(set(new["values"]) - set(old["values"]))
    for value in added:
        minor = True
        if new["values"][value]["since"] != new["version"]:
            errors.append(f"values/{value} is added with since {new['values'][value]['since']}, not {new['version']}")
    before_version, after_version = version_tuple(old["version"]), version_tuple(new["version"])
    if minor:
        expected = (before_version[0], before_version[1] + 1, 0)
    elif patch:
        expected = (before_version[0], before_version[1], before_version[2] + 1)
    else:
        expected = before_version
    if after_version != expected:
        errors.append(
            f"version {new['version']} after {old['version']}: the change calls for "
            + ".".join(str(part) for part in expected)
        )
    return errors


def check(root: Path = ROOT, base: str | None = None) -> list[str]:
    errors: list[str] = []
    expected = kinds(root)
    present = sorted(path.stem for path in (root / DIRECTORY).glob("*.json"))
    if present != sorted(expected):
        errors.append(f"{DIRECTORY}/ holds {present}, the kinds are {sorted(expected)}")
    documents: dict[str, dict] = {}
    for kind in expected:
        path = root / DIRECTORY / f"{kind}.json"
        if not path.is_file():
            continue
        try:
            document = parse(path.read_bytes())
        except (UnicodeDecodeError, ValueError) as exc:
            errors.append(f"{DIRECTORY}/{kind}.json is not strict JSON ({exc})")
            continue
        found = contract_errors(document, root)
        errors.extend(f"{DIRECTORY}/{kind}.json: {error}" for error in found)
        if found:
            continue
        if document["kind"] != kind:
            errors.append(f"{DIRECTORY}/{kind}.json registers the kind {document['kind']}")
            continue
        documents[kind] = document
        if base is not None:
            errors.extend(f"{DIRECTORY}/{kind}.json: {error}" for error in _against_base(root, base, kind, document))
    if "workflow" in documents and "asset_type" in documents:
        asset_types = set(documents["asset_type"]["values"])
        for value, entry in documents["workflow"]["values"].items():
            unknown = sorted(set(entry["asset_types"]) - asset_types)
            if unknown:
                errors.append(f"{DIRECTORY}/workflow.json: values/{value} names asset types not registered: {unknown}")
    return errors


def _against_base(root: Path, base: str, kind: str, document: dict) -> list[str]:
    shown = subprocess.run(
        ["git", "-C", str(root), "show", f"{base}:{DIRECTORY}/{kind}.json"], capture_output=True, check=False
    )
    if shown.returncode != 0:
        listed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
            capture_output=True,
            check=False,
        )
        if listed.returncode != 0:
            return [f"the base revision {base} cannot be read"]
        return []  # new at this revision: only its contract applies
    try:
        old = parse(shown.stdout)
    except (UnicodeDecodeError, ValueError) as exc:
        return [f"the copy at {base} is not strict JSON ({exc})"]
    if contract_errors(old, root):
        return [f"the copy at {base} breaks the contract, so nothing can be compared with it"]
    return append_only_errors(old, document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="a git revision to compare each vocabulary with")
    args = parser.parse_args(argv)
    errors = check(ROOT, args.base)
    if errors:
        for error in errors:
            print("ERROR " + error, file=sys.stderr)
        return 1
    summary = ", ".join(
        f"{kind} {json.loads((ROOT / DIRECTORY / f'{kind}.json').read_text(encoding='utf-8'))['version']}"
        for kind in kinds()
    )
    print(f"registered vocabularies OK: {summary}" + (f"; append-only against {args.base}" if args.base else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
