"""Verify the release set: each repository's pointer against the `release-set.json` manifest.

The rules are the profile `loquitur.release_set_verifier.v1`, and loquitur-protocol (governance)
owns them. The release set is declared by the RELEASE_SET_POINTER.json file of each repository.

What this verifier DOES check:
  * every manifest member that is present agrees with the manifest (absent members are
    reported, never verified; see PUBLISHED_MEMBERS for how, and --require-every-member to
    make absence a failure); a repository carrying a pointer that the manifest does not list
    is not a member, and is counted, never verified and never named;
    (NOT that every workspace repository carries a pointer: members are discovered by
    looking for directories that already contain one, so a repository missing its pointer
    is invisible here rather than reported;)
  * all pointers agree on release_set_id, parent_release_set_id, branch_id,
    schema_version and the release_manifest block;
  * each pointer's `repository` field matches the directory it lives in;
  * each pointer file hashes to the sha256 recorded in the manifest;
  * every declared branch_input artifact that IS present matches its recorded
    bytes and sha256.

A pointer may declare a branch input or none. A pointer that declares none has no branch
input to verify, and is reported as such only under --require-branch-inputs, which requires one.

What this verifier does NOT and CANNOT claim:
  * that a branch whose inputs a pointer declares was completed or certified.
    Branch-input artifacts that are declared and absent from the workspace are reported as
    UNVERIFIABLE, never as verified. Use --require-branch-inputs to make their
    absence a hard failure.

Exit codes: 0 verified, 1 verification failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Collection
from pathlib import Path

PROFILE_ID = "loquitur.release_set_verifier.v1"
MANIFEST_NAME = "release-set.json"
POINTER_NAME = "RELEASE_SET_POINTER.json"
MANIFEST_SCHEMA = "loquitur.release_set_manifest.v1"
AGREEMENT_KEYS = ("release_set_id", "parent_release_set_id", "branch_id", "schema_version")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def discover_repositories(workspace: Path) -> list[Path]:
    return sorted(
        (p for p in workspace.iterdir() if p.is_dir() and (p / POINTER_NAME).is_file()),
        key=lambda p: p.name,
    )


# Membership is the manifest's decision, and only the manifest's. A repository whose directory
# carries a pointer but which `release-set.json` does not list is not a member: it is not
# verified, it is not named, and its presence is not an error. A run counts such repositories,
# as it counts absent members that are not published, so that a pointer left in a repository
# that is not a member is visible without a published file having to name it. No list of
# non-members is kept here: such a list is one a published file would have to spell out, and
# the manifest already says which repositories are in the release set.
#
# Leaving the release set is removing the member from the manifest. Joining it is adding one,
# with --write-manifest --add-member NAME, because a regeneration refreshes the members the
# manifest lists and admits no repository merely for carrying a pointer.
# The members that are published: the repositories README.md lists for publication that
# carry a pointer, which are the ones a publication's workspace holds. "Published" names the
# layout a publication produces, which is the layout this rule has to hold in.
# loquitur-verify-ts is published with loquitur-verify-py, in the same release, so it is one of
# them: leaving it out would make the verifier hide, in a published workspace, the absence of a
# repository that is published.
#
# A release workspace holds a SUBSET of the members: the published repositories side by side,
# with two or more pointers. Reporting every member it does not hold as an error would fail
# every publishable layout and print, to whoever ran it, the names of repositories that are
# not published.
#
# The rule, stated once:
#   * a member that is present is verified in full, published or not, and a broken one fails;
#   * a member that is absent is not verified and is never reported as verified;
#   * an absent PUBLISHED member is named in a warning, since its name is public by definition;
#   * absent members that are NOT published are counted, never named, and do not fail the run.
# The manifest already says this about itself: "records-only-the-repositories-present-when-
# checked". A private workspace that must be complete passes --require-every-member,
# which turns absence into an error without changing what is named.
PUBLISHED_MEMBERS = frozenset({"loquitur-protocol", "loquitur-schemas", "loquitur-verify-py", "loquitur-verify-ts"})


def load_pointers(workspace: Path, members: Collection[str]) -> tuple[dict[str, dict], list[str], int]:
    """The pointers of the manifest's members that are present, the errors, and how many others.

    A directory carrying a pointer that is not a member is counted and not read.
    """
    errors: list[str] = []
    pointers: dict[str, dict] = {}
    outside = 0
    for repo in discover_repositories(workspace):
        if repo.name not in members:
            outside += 1
            continue
        raw = (repo / POINTER_NAME).read_bytes()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{repo.name}: pointer is not valid JSON: {exc}")
            continue
        data["_sha256"] = sha256_bytes(raw)
        if data.get("repository") != repo.name:
            errors.append(f"{repo.name}: pointer declares repository={data.get('repository')!r}")
        pointers[repo.name] = data
    if not pointers:
        errors.append(f"no {POINTER_NAME} of a manifest member found under {workspace}")
    return pointers, errors, outside


def load_manifest(workspace: Path) -> tuple[dict | None, list[str]]:
    manifest_path = workspace / "loquitur-protocol" / MANIFEST_NAME
    if not manifest_path.is_file():
        return None, [f"release manifest missing: {manifest_path}"]
    return json.loads(manifest_path.read_text(encoding="utf-8")), []


def outside_warning(outside: int) -> list[str]:
    if not outside:
        return []
    return [
        f"{outside} repository(ies) in this workspace carry a release-set pointer and are not "
        "manifest members - NOT CHECKED"
    ]


def check_agreement(pointers: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    for key in AGREEMENT_KEYS:
        values = {name: p.get(key) for name, p in pointers.items()}
        distinct = set(values.values())
        if len(distinct) > 1:
            errors.append(f"pointers disagree on {key}: {json.dumps(values, sort_keys=True)}")
    manifests = {name: json.dumps(p.get("release_manifest"), sort_keys=True) for name, p in pointers.items()}
    if len(set(manifests.values())) > 1:
        errors.append("pointers disagree on release_manifest block")
    profiles = {p.get("release_manifest", {}).get("verification_profile_id") for p in pointers.values()}
    if profiles != {PROFILE_ID}:
        errors.append(f"pointers declare verification_profile_id {profiles}, expected {{{PROFILE_ID!r}}}")
    return errors


def branch_input_state(workspace: Path, repo: str, pointer: dict) -> dict:
    """Locate a declared branch-input artifact and report present/verified/unverifiable."""
    declared = pointer.get("branch_input") or {}
    artifact = declared.get("artifact")
    state = {
        "artifact": artifact,
        "kind": declared.get("kind"),
        "declared_bytes": declared.get("bytes"),
        "declared_sha256": declared.get("sha256"),
        "status": "unverifiable_artifact_absent",
    }
    if not artifact:
        state["status"] = "not_declared"
        return state
    # Search under the repository this state is about, not the whole workspace: a search of
    # every repository could let an artifact belonging to one repository mark another's branch
    # input "verified". Two matches is an ambiguity, not a choice to make silently.
    search_root = workspace / repo
    if not search_root.is_dir():
        return state
    matches = sorted(p for p in search_root.rglob(artifact) if p.is_file())
    if not matches:
        return state
    if len(matches) > 1:
        state["status"] = "ambiguous"
        state["candidates"] = [m.relative_to(workspace).as_posix() for m in matches]
        return state
    found = matches[0]
    raw = found.read_bytes()
    state["located_at"] = found.relative_to(workspace).as_posix()
    state["actual_bytes"] = len(raw)
    state["actual_sha256"] = sha256_bytes(raw)
    ok = state["actual_sha256"] == declared.get("sha256") and (
        declared.get("bytes") is None or state["actual_bytes"] == declared.get("bytes")
    )
    state["status"] = "verified" if ok else "mismatch"
    return state


def build_manifest(workspace: Path, pointers: dict[str, dict]) -> dict:
    any_pointer = next(iter(pointers.values()))
    members = {}
    unverifiable = []
    declared = 0
    for name in sorted(pointers):
        st = branch_input_state(workspace, name, pointers[name])
        members[name] = {
            "pointer_sha256": pointers[name]["_sha256"],
            "repository_role": pointers[name].get("repository_role"),
            "branch_input_artifact": st.get("artifact"),
            "branch_input_status": st["status"],
        }
        # A pointer that declares no branch input has nothing to verify and nothing unverifiable.
        # `branch_inputs_present` is true only when at least one input is declared and every
        # declared input was checked and held, so it is never true having verified nothing.
        if st["status"] == "not_declared":
            continue
        declared += 1
        if st["status"] != "verified":
            unverifiable.append(f"{name}:{st.get('artifact')}")
    return {
        "schema_version": MANIFEST_SCHEMA,
        "verification_profile_id": PROFILE_ID,
        "owner": "loquitur-protocol-governance",
        "release_set_id": any_pointer.get("release_set_id"),
        "parent_release_set_id": any_pointer.get("parent_release_set_id"),
        "branch_id": any_pointer.get("branch_id"),
        "members": members,
        "branch_inputs_declared": declared,
        "branch_inputs_present": declared > 0 and not unverifiable,
        "unverifiable_branch_inputs": sorted(unverifiable),
        "non_claims": [
            "not-a-certification-of-an-earlier-release-set",
            "not-a-claim-that-a-branch-input-was-completed-or-verified",
            "not-a-release-approval",
            "not-a-partner-readiness-claim",
            "records-only-the-repositories-present-when-checked",
        ],
    }


def verify(
    workspace: Path, require_branch_inputs: bool, require_every_member: bool = False
) -> tuple[list[str], list[str]]:
    manifest, errors = load_manifest(workspace)
    if manifest is None:
        return errors, []
    members = manifest.get("members") or {}
    pointers, errors, outside = load_pointers(workspace, members)
    if errors:
        return errors, []
    errors += check_agreement(pointers)

    if manifest.get("verification_profile_id") != PROFILE_ID:
        errors.append(f"manifest verification_profile_id != {PROFILE_ID}")
    for key in ("release_set_id", "parent_release_set_id", "branch_id"):
        expected = next(iter(pointers.values())).get(key)
        if manifest.get(key) != expected:
            errors.append(f"manifest {key}={manifest.get(key)!r} but pointers say {expected!r}")

    absent = sorted(set(members) - set(pointers))

    warnings: list[str] = outside_warning(outside)
    # Absent members: see PUBLISHED_MEMBERS. Published ones by name, the rest by count only.
    absence = errors if require_every_member else warnings
    for name in absent:
        if name in PUBLISHED_MEMBERS:
            absence.append(f"{name}: manifest member is not present in this workspace - NOT CHECKED")
    unpublished_absent = sum(1 for name in absent if name not in PUBLISHED_MEMBERS)
    if unpublished_absent:
        absence.append(
            f"{unpublished_absent} manifest member(s) that are not published are not present in this "
            "workspace - NOT CHECKED"
        )
    for name in sorted(set(pointers) & set(members)):
        recorded = members[name].get("pointer_sha256")
        actual = pointers[name]["_sha256"]
        if recorded != actual:
            errors.append(f"{name}: pointer sha256 {actual} does not match manifest {recorded}")
        st = branch_input_state(workspace, name, pointers[name])
        if st["status"] == "mismatch":
            errors.append(
                f"{name}: branch input {st['artifact']} present but hash/size mismatch "
                f"(declared {st['declared_sha256']}, actual {st.get('actual_sha256')})"
            )
        elif st["status"] == "ambiguous":
            errors.append(
                f"{name}: branch input {st['artifact']} matches more than one file "
                f"({', '.join(st.get('candidates', []))})"
            )
        elif st["status"] == "unverifiable_artifact_absent":
            message = f"{name}: branch input {st['artifact']} is absent - UNVERIFIABLE"
            (errors if require_branch_inputs else warnings).append(message)
        elif st["status"] == "not_declared" and require_branch_inputs:
            # A flag that requires branch inputs must not pass a pointer that declares none.
            errors.append(f"{name}: pointer declares no branch_input - NOTHING TO VERIFY")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="workspace root containing the repositories (default: parent of loquitur-protocol)",
    )
    parser.add_argument(
        "--require-branch-inputs",
        action="store_true",
        help="treat absent branch-input artifacts as a failure instead of a warning",
    )
    parser.add_argument(
        "--require-every-member",
        action="store_true",
        help="treat a manifest member absent from the workspace as a failure instead of a warning",
    )
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        help="regenerate release-set.json for the members it lists, from the current workspace state",
    )
    parser.add_argument(
        "--add-member",
        action="append",
        default=[],
        metavar="NAME",
        help="with --write-manifest: admit the repository NAME, which carries a pointer, as a new member",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        print(f"workspace not found: {workspace}", file=sys.stderr)
        return 2

    # A public clone has no siblings. `--workspace` defaults to the directory ABOVE the
    # checkout, which for `git clone loquitur-protocol` is wherever the user happened to
    # run git. One line per manifest member it could not find would be a failure the reader
    # cannot act on, and a list of repositories they are not meant to learn about. Say what
    # the tool needs, once, and name nothing.
    # Keyed on the number of pointers, not on the manifest. A workspace that has the
    # repositories but is missing the manifest is a real failure this tool must report by
    # name; a directory that simply is not a workspace is a usage problem, and the two
    # deserve different answers.
    if sum(1 for p in workspace.iterdir() if p.is_dir() and (p / POINTER_NAME).is_file()) < 2:
        print(
            "this verifier compares release-set pointers ACROSS the workspace repositories, "
            "and fewer than two of them are present here.",
            file=sys.stderr,
        )
        print(f"point --workspace at the directory that holds them (currently {workspace}).", file=sys.stderr)
        return 2

    if args.add_member and not args.write_manifest:
        parser.error("--add-member only applies with --write-manifest")
    if args.write_manifest:
        manifest, errors = load_manifest(workspace)
        if manifest is None and args.add_member:
            errors = []  # a first manifest, for the members named on the command line
        members = set(args.add_member)
        if manifest is not None:
            members |= set(manifest.get("members") or {})
        pointers, more, _outside = load_pointers(workspace, members)
        errors += more
        unknown = sorted(set(args.add_member) - set(pointers))
        errors += [f"{name}: --add-member names no repository carrying a pointer here" for name in unknown]
        if errors:
            for e in errors:
                print(f"ERROR {e}", file=sys.stderr)
            return 1
        manifest = build_manifest(workspace, pointers)
        target = workspace / "loquitur-protocol" / MANIFEST_NAME
        target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="")
        print(f"wrote {target.relative_to(workspace).as_posix()}")
        # Regenerating and then verifying is verifying a file against itself: a manifest
        # rebuilt around an altered pointer agrees with it. A run that writes the manifest
        # therefore reports no success, because no check has been performed.
        print("not verifying: this run regenerated the manifest, so comparing against it proves nothing.")
        print("re-run without --write-manifest to verify.")
        return 0

    errors, warnings = verify(workspace, args.require_branch_inputs, args.require_every_member)
    if args.json:
        print(
            json.dumps(
                {"profile": PROFILE_ID, "errors": errors, "warnings": warnings, "status": "FAIL" if errors else "OK"},
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for w in warnings:
            print(f"WARN  {w}")
        for e in errors:
            print(f"ERROR {e}", file=sys.stderr)
        if not errors:
            note = f" ({len(warnings)} warning(s))" if warnings else ""
            print(f"release set pointer coherence OK: {PROFILE_ID}{note}")
            print("note: this verifies pointer/manifest coherence only; it certifies no earlier release set.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
