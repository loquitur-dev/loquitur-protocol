"""The release workflow does only what docs/maintainers/releasing.md says it does.

`.github/workflows/release.yml` builds the release files from a tag and opens a draft release. What
makes it safe to leave running is a handful of properties of its text, each held here:

* it starts only on a push of a tag vX.Y.Z, or by hand;
* every action it runs is pinned by a full commit SHA, with the release that SHA is in a comment,
  and an action pinned in both workflows is pinned to the same commit;
* no job has a permission it is not named for: writing the repository's contents only where the
  draft release is created, the identity token and the attestations only where files are attested;
* the job that attests checks out nothing and installs nothing, and attests only files it has
  checked against the names the verify job gave and against SHA256SUMS; the build, which installs
  packages, holds no token that could sign anything;
* nothing publishes: the one release command creates a draft from an existing tag, no step uploads
  to a package index, and the workflow reads no secret.

`tools/release_files.py` builds the files the workflow attaches, and is held below to its own
description: the archive and the comparison script byte for byte, the specification tar.gz with
exactly the files it names, and a SHA256SUMS that `sha256sum -c` accepts.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
import yaml
from conftest import release_files

TOOL = release_files()
ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE = WORKFLOWS / "release.yml"
TAG_PATTERN = "v[0-9]+.[0-9]+.[0-9]+"
PINNED = re.compile(
    r"^\s*(?:-\s+)?uses:\s+(?P<action>[\w.-]+/[\w./-]+)@(?P<sha>[0-9a-f]{40}) # (?P<tag>v\d+\.\d+\.\d+)$"
)
LOCAL = re.compile(r"^\s*(?:-\s+)?uses:\s+\./\.github/workflows/[\w.-]+\.yml$")
ATTESTING = ("actions/attest",)
# Every job of release.yml, with exactly the permissions it is named for: writing the repository's
# contents only where the draft release is created, the identity token and the attestations only
# where the files are attested.
PERMISSIONS = {
    "ci": {"contents": "read"},
    "verify": {"contents": "read"},
    "build": {"contents": "read"},
    "attest": {"id-token": "write", "attestations": "write"},
    "release": {"contents": "write"},
}


# The dry-run notice of the attest job, the same step in the four repositories: the last step of
# the job, after both attestations, under the opposite of their condition.
DRY_RUN_NOTICE = {
    "name": "Say that this dry run attested nothing",
    "if": "github.event_name != 'push' && github.event.repository.private",
    "run": 'echo "::notice::private repository, so this dry run built, summed and described the files and attested none"',
}

# The two reads of GitHub's API in the tag check. Each answer is kept in a variable, so that a
# failed call stops the run with its own error, and only then split at the tabs: bash checks the
# status of a command substitution and not that of a process substitution, so
# `read < <(gh api ...)` would take a failed call for an empty answer.
API_READ = re.compile(r"""^ *if ! (\w+)="\$\(gh api "([^"]+)" --jq '\[([^\]]+)\] \| @tsv'\)"; then$""", re.M)
API_READS = [
    ("ref", "repos/$GITHUB_REPOSITORY/git/ref/tags/$TAG", ".object.type, .object.sha"),
    (
        "tag",
        "repos/$GITHUB_REPOSITORY/git/tags/$tag_sha",
        ".object.type, .object.sha, .verification.verified, .verification.reason",
    ),
]
SPLITS = [
    "IFS=$'\\t' read -r ref_type tag_sha <<< \"$ref\"",
    "IFS=$'\\t' read -r target_type target_sha verified reason <<< \"$tag\"",
]

# `gh` and `git` as GitHub and the clone answer them: gh from STUB_REF and STUB_TAG (`fail` fails
# as gh does on a 404), git's default-branch question from STUB_ON_BRANCH.
TAG_STUBS = """
gh() {
  case "$2" in */git/ref/tags/*) answer="$STUB_REF" ;; *) answer="$STUB_TAG" ;; esac
  if [ "$answer" = fail ]; then echo "gh: Not Found (HTTP 404)" >&2; return 1; fi
  printf '%s\\n' "$answer"
}
git() { [ "$1" = merge-base ] && [ "$STUB_ON_BRANCH" = yes ]; }
"""
TAGGED = "c" * 40
RELEASABLE_TAG = {
    "TAG": "v0.1.0",
    "DEFAULT_BRANCH": "main",
    "GITHUB_REPOSITORY": "owner/repo",
    "GITHUB_SHA": TAGGED,
    "STUB_REF": "tag\t" + "a" * 40,
    "STUB_TAG": f"commit\t{TAGGED}\ttrue\tvalid",
    "STUB_ON_BRANCH": "yes",
}
TAG_REFUSALS = {
    "the ref cannot be read": ({"STUB_REF": "fail"}, "no answer for the ref of tag v0.1.0"),
    "a lightweight tag": ({"STUB_REF": f"commit\t{TAGGED}"}, "tag v0.1.0 is lightweight"),
    "a ref with no tag object": ({"STUB_REF": "\t"}, "names no tag object"),
    "the tag object cannot be read": ({"STUB_TAG": "fail"}, "no answer for the tag object"),
    "a tag of another commit": ({"STUB_TAG": f"commit\t{'d' * 40}\ttrue\tvalid"}, "not the commit this run builds"),
    "a tag of a tag": ({"STUB_TAG": f"tag\t{TAGGED}\ttrue\tvalid"}, "not the commit this run builds"),
    "an unverified signature": (
        {"STUB_TAG": f"commit\t{TAGGED}\tfalse\tunsigned"},
        "no signature GitHub verifies (unsigned)",
    ),
    "a commit off the default branch": ({"STUB_ON_BRANCH": "no"}, "not on main"),
}


@functools.cache
def _workflow(path: Path = RELEASE) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    # YAML 1.1 reads the key `on` as the boolean true.
    return workflow.get("on", workflow.get(True))


def _runs(workflow: dict) -> list[str]:
    return [step["run"] for job in workflow["jobs"].values() for step in job.get("steps", []) if "run" in step]


def test_the_workflow_starts_only_on_a_version_tag_or_by_hand() -> None:
    triggers = _triggers(_workflow())
    assert set(triggers) == {"push", "workflow_dispatch"}, triggers
    assert triggers["push"] == {"tags": [TAG_PATTERN]}, triggers["push"]
    assert not triggers["workflow_dispatch"], "a manual run takes no input"
    assert re.fullmatch(TAG_PATTERN, "v0.1.0") and not re.fullmatch(TAG_PATTERN, "v0.1.0-rc1")


def _uses(workflow: dict) -> list[str]:
    """Every `uses` of a workflow, of a job or of a step, read from the parsed YAML."""
    found = []
    for job in workflow["jobs"].values():
        if "uses" in job:
            found.append(job["uses"])
        found.extend(step["uses"] for step in job.get("steps", []) if "uses" in step)
    return found


@pytest.mark.parametrize("name", ["ci.yml", "release.yml"])
def test_every_action_is_pinned_by_a_full_commit_sha_with_its_release_named(name: str) -> None:
    path = WORKFLOWS / name
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if re.match(r"^\s*(?:-\s+)?uses:", line)]
    assert len(lines) >= 5, f"only {len(lines)} uses: lines found in {name}; the check is thin"
    loose = [line.strip() for line in lines if not (PINNED.match(line) or LOCAL.match(line))]
    assert not loose, f"not pinned by a 40-hex SHA and a release comment: {loose}"
    # The parsed YAML sees every `uses`, a step written as a flow mapping included, which the line
    # check above does not: each one is local or pinned, and each one is on a line checked above.
    uses = _uses(_workflow(path))
    unpinned = [
        use
        for use in uses
        if not re.fullmatch(r"\./\.github/workflows/[\w.-]+\.yml|[\w.-]+/[\w./-]+@[0-9a-f]{40}", use)
    ]
    assert not unpinned, f"{name} runs an action not pinned by a full commit SHA: {unpinned}"
    assert len(uses) == len(lines), f"{name} has a `uses` the line check does not read, such as a flow mapping"


def test_the_pin_check_reads_a_step_written_as_a_flow_mapping() -> None:
    workflow = yaml.safe_load("jobs:\n  a:\n    steps:\n      - { uses: actions/cache@v4, with: { path: x } }\n")
    assert _uses(workflow) == ["actions/cache@v4"]


def test_an_action_pinned_in_two_workflows_is_pinned_to_one_commit() -> None:
    pins: dict[str, set[tuple[str, str]]] = {}
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = PINNED.match(line)
            if match:
                pins.setdefault(match["action"], set()).add((match["sha"], match["tag"]))
    assert {"actions/checkout", "actions/setup-python", *ATTESTING} <= set(pins), sorted(pins)
    drift = {action: sorted(found) for action, found in pins.items() if len(found) != 1}
    assert not drift, f"one action pinned to different commits: {drift}"


def test_each_job_has_only_the_permissions_it_is_named_for() -> None:
    workflow = _workflow()
    assert workflow["permissions"] == {}, "the workflow grants nothing by default"
    text = RELEASE.read_text(encoding="utf-8")
    assert "write-all" not in text and "read-all" not in text
    jobs = workflow["jobs"]
    assert {name: job.get("permissions") for name, job in jobs.items()} == PERMISSIONS
    # The reusable workflow is this repository's own file, read at the commit being released.
    assert jobs["ci"]["uses"] == "./.github/workflows/ci.yml"


def test_the_called_checks_ask_for_no_more_than_the_caller_grants() -> None:
    ci = _workflow(WORKFLOWS / "ci.yml")
    triggers = _triggers(ci)
    assert "workflow_call" in triggers, "release.yml calls ci.yml, which must accept the call"
    # Pushes to main, and every tag but a release tag: a release tag runs the checks once, through
    # release.yml, and not a second time directly. A branch is checked through its pull request.
    # The tags are a `tags` filter, every tag and then not the release ones: beside `branches`, a
    # `tags-ignore` alone is not a filter GitHub documents as letting the other tags through.
    assert triggers["push"] == {"branches": ["main"], "tags": ["**", "!" + TAG_PATTERN]}, triggers["push"]
    assert "pull_request" in triggers
    assert ci["permissions"] == {"contents": "read"}
    assert all("permissions" not in job for job in ci["jobs"].values())


def test_the_vocabularies_are_compared_with_a_commit_the_checked_one_contains() -> None:
    # Called by release.yml on a tag, the checks must not compare the tagged commit with the tip
    # of the default branch: a registration merged there after the tag would read as a removal.
    [step] = [
        step
        for step in _workflow(WORKFLOWS / "ci.yml")["jobs"]["test"]["steps"]
        if "registered_vocabularies.py" in step.get("run", "")
    ]
    assert 'base="$(git merge-base HEAD FETCH_HEAD)"' in step["run"]
    assert 'registered_vocabularies.py --base "$base"' in step["run"]
    assert "--depth" not in step["run"]
    [checkout] = [
        step
        for step in _workflow(WORKFLOWS / "ci.yml")["jobs"]["test"]["steps"]
        if step.get("uses", "").startswith("actions/checkout@")
    ]
    assert checkout["with"] == {"fetch-depth": 0}, "a merge base needs the history"


def test_a_release_run_and_a_push_run_never_cancel_each_others_checks() -> None:
    # A called workflow reads its concurrency group in the caller's context, where github.workflow
    # is the caller's name: the event keeps a release run and a run of another event apart.
    ci = _workflow(WORKFLOWS / "ci.yml")
    assert ci["concurrency"] == {
        "group": "ci-${{ github.workflow }}-${{ github.ref }}-${{ github.event_name }}",
        "cancel-in-progress": True,
    }
    # The caller sets no group of its own, which the called checks would wait on.
    assert "concurrency" not in _workflow()


def test_nothing_is_published() -> None:
    workflow = _workflow()
    text = RELEASE.read_text(encoding="utf-8")
    runs = _runs(workflow)
    commands = [line.strip() for run in runs for line in run.replace("\\\n", " ").splitlines()]
    releases = [command for command in commands if "gh release" in command]
    assert len(releases) == 1, releases
    [create] = releases
    assert create.startswith("gh release create ") and " --draft " in create and " --verify-tag " in create, create
    for needle in ("npm publish", "twine", "pypi", "registry-url", "--draft=false", "gh release edit", "git push"):
        assert needle not in text.lower(), f"release.yml carries {needle!r}"
    assert "secrets." not in text, "the workflow reads no secret; the token GitHub gives the run is enough"
    release = workflow["jobs"]["release"]
    assert release["needs"] == "attest"
    assert release["if"] == "github.event_name == 'push'"


@pytest.mark.parametrize("name", ["ci.yml", "release.yml"])
def test_no_script_interpolates_an_expression(name: str) -> None:
    # ci.yml is also the workflow release.yml calls, so its scripts are held to the same rule: a
    # value of the event, such as a ref name, reaches a script through env, never pasted into it.
    runs = _runs(_workflow(WORKFLOWS / name))
    assert len(runs) >= 5, f"only {len(runs)} run scripts in {name}; the check is thin"
    for run in runs:
        assert "${{" not in run, f"a run script of {name} interpolates an expression instead of reading env: {run[:80]}"


def test_no_checkout_of_the_release_keeps_its_token() -> None:
    workflow = _workflow()
    checkouts = [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if step.get("uses", "").startswith("actions/checkout@")
    ]
    assert checkouts and all(step.get("with", {}).get("persist-credentials") is False for step in checkouts)
    assert "pull_request_target" not in RELEASE.read_text(encoding="utf-8")


def _step(steps: list[dict], action: str) -> dict:
    [step] = [step for step in steps if step.get("uses", "").startswith(f"actions/{action}@")]
    return step


def test_the_attesting_job_runs_no_code_of_the_repository_or_of_a_package() -> None:
    jobs = _workflow()["jobs"]
    attest = jobs["attest"]
    used = {step["uses"].split("@")[0] for step in attest["steps"] if "uses" in step}
    assert used == {"actions/download-artifact", *ATTESTING}, sorted(used)
    runs = "\n".join(step.get("run", "") for step in attest["steps"])
    # The shell and coreutils only: no interpreter, package manager, network client or checked-out file.
    ran = re.findall(r"\b(?:python3?|pip3?|npm|npx|node|git|gh|curl|wget|make|bash|sh)\b|\./", runs)
    assert not ran, f"the attest job runs {sorted(set(ran))}"
    # The identity token and the attestations are this job's alone; the build runs pip and holds none.
    holders = [name for name, job in jobs.items() if "id-token" in job.get("permissions", {})]
    assert holders == ["attest"], holders
    assert sorted(attest["needs"]) == ["build", "verify"]


def test_every_file_uploaded_is_checked_then_attested() -> None:
    jobs = _workflow()["jobs"]
    build, attest = jobs["build"]["steps"], jobs["attest"]["steps"]
    upload = _step(build, "upload-artifact")
    assert upload["with"]["name"] == "release-files"
    built = upload["with"]["path"].rstrip("/")
    # The SBOM is written into the directory uploaded, and the sums last, over everything in it.
    build_step = next(i for i, step in enumerate(build) if "release_files.py build" in step.get("run", ""))
    sbom_step = next(i for i, step in enumerate(build) if "release_files.py sbom" in step.get("run", ""))
    sums_step = next(i for i, step in enumerate(build) if "release_files.py sums" in step.get("run", ""))
    assert build[sbom_step]["run"] == 'python tools/release_files.py sbom "$RUNNER_TEMP/release"'
    assert built == "${{ runner.temp }}/release"
    assert build_step < sbom_step < sums_step < build.index(upload)

    download = _step(attest, "download-artifact")
    assert download["with"] == {"name": "release-files", "path": built}
    directory = download["with"]["path"]
    [check] = [step for step in attest if "sha256sum" in step.get("run", "")]
    assert check["working-directory"] == directory
    assert check["env"] == {
        "FILES": "${{ needs.verify.outputs.files }}",
        "SBOM": "${{ needs.verify.outputs.sbom }}",
    }
    assert 'grep -vx -e SHA256SUMS -e "$SBOM"' in check["run"]
    for needle in ("sha256sum --strict -c SHA256SUMS", '[ "$found" != "$expected" ]', "! -type f", "exit 1"):
        assert needle in check["run"], needle
    # One action makes both attestations: the step given an SBOM attests it, the other the provenance.
    attesting = [step for step in attest if step.get("uses", "").startswith("actions/attest@")]
    [sbom] = [step for step in attesting if "sbom-path" in step["with"]]
    [provenance] = [step for step in attesting if "sbom-path" not in step["with"]]
    assert provenance["with"] == {"subject-path": f"{directory}/*"}
    assert sbom["with"] == {
        "subject-path": "${{ runner.temp }}/sbom-subjects/*",
        "sbom-path": f"{directory}/${{{{ needs.verify.outputs.sbom }}}}",
    }
    assert attest.index(download) < attest.index(check) < attest.index(sbom) < attest.index(provenance)
    # The release uploads the files of the same artifact, checked against the same sums.
    release = jobs["release"]["steps"]
    assert _step(release, "download-artifact")["with"] == download["with"]
    assert any(step.get("run") == "sha256sum --strict -c SHA256SUMS" for step in release)


def test_verify_names_the_files_the_attest_job_expects() -> None:
    verify = _workflow()["jobs"]["verify"]
    assert verify["outputs"] == {
        "version": "${{ steps.names.outputs.version }}",
        "files": "${{ steps.names.outputs.files }}",
        "sbom": "${{ steps.names.outputs.sbom }}",
    }
    [names] = [step for step in verify["steps"] if step.get("id") == "names"]
    for command in ("names |", "version)", "sbom-name)"):
        assert f"release_files.py {command}" in names["run"], command
    # The SBOM's name has one source, sbom_name() in the tool: the workflow never spells it.
    assert ".cdx.json" not in RELEASE.read_text(encoding="utf-8")
    assert all(
        "uses" not in step or step["uses"].startswith(("actions/checkout@", "actions/setup-python@"))
        for step in verify["steps"]
    )


def test_the_tag_check_runs_before_anything_is_built() -> None:
    jobs = _workflow()["jobs"]
    assert jobs["ci"]["needs"] == "verify"
    assert sorted(jobs["build"]["needs"]) == ["ci", "verify"]
    # Every later job takes the version verify read; none reads it again.
    build = "\n".join(step.get("run", "") for step in jobs["build"]["steps"])
    assert "release_files.py version" not in build and "import json" not in build
    runs = "\n".join(step.get("run", "") for step in jobs["verify"]["steps"])
    assert 'release_files.py check --tag "$TAG"' in runs
    assert "git/ref/tags/$TAG" in runs and ".verification.verified" in runs


def test_a_manual_run_on_a_tag_is_refused_before_anything_else() -> None:
    # A manual run skips the tag checks, which only a push runs; started on a tag, it would still
    # attest files under refs/tags/vX.Y.Z. A dry run runs on a branch.
    [first, *_] = _workflow()["jobs"]["verify"]["steps"]
    assert first["if"] == "github.event_name != 'push' && github.ref_type == 'tag'"
    assert "::error::" in first["run"] and first["run"].rstrip().endswith("exit 1")


def test_the_tag_check_reads_the_tag_from_github_and_requires_the_default_branch() -> None:
    verify = _workflow()["jobs"]["verify"]["steps"]
    [tag] = [step for step in verify if "git/ref/tags/$TAG" in step.get("run", "")]
    assert tag["if"] == "github.event_name == 'push'"
    assert tag["env"]["DEFAULT_BRANCH"] == "${{ github.event.repository.default_branch }}"
    run = tag["run"]
    # The commit the tag names compared with the one this run builds.
    assert '[ "$target_sha" != "$GITHUB_SHA" ]' in run
    assert 'git merge-base --is-ancestor "$GITHUB_SHA" "refs/remotes/origin/$DEFAULT_BRANCH"' in run
    assert _step(verify, "checkout")["with"] == {"fetch-depth": 0, "persist-credentials": False}


def _tag_check() -> dict:
    [tag] = [step for step in _workflow()["jobs"]["verify"]["steps"] if "git/ref/tags/$TAG" in step.get("run", "")]
    return tag


def _attest_steps() -> list[dict]:
    return _workflow()["jobs"]["attest"]["steps"]


def test_the_tag_check_keeps_each_api_answer_before_it_reads_it() -> None:
    run = _tag_check()["run"]
    assert API_READ.findall(run) == API_READS
    code = [line for line in run.splitlines() if not line.lstrip().startswith("#")]
    assert sum(line.count("gh api") for line in code) == 2 and not [line for line in code if "< <(" in line]
    for split in SPLITS:
        assert split in run, split


def _bash() -> str:
    # On Windows the first bash on the PATH can be WSL's launcher, which runs no script of ours.
    found = shutil.which("bash")
    if found is None or (sys.platform == "win32" and Path(found).parent.name.lower() in {"windowsapps", "system32"}):
        pytest.skip("no POSIX bash on this host to run the tag check with")
    return found


def _run_tag_check(env: dict[str, str], where: Path) -> subprocess.CompletedProcess[str]:
    """The tag check run after TAG_STUBS, which stand in for gh and git; the rest is bash's own."""
    bash = _bash()
    script = where / "tag-check.sh"
    script.write_text(TAG_STUBS + _tag_check()["run"], encoding="utf-8", newline="\n")
    return subprocess.run(
        [bash, "--noprofile", "--norc", "-eo", "pipefail", script.as_posix()],
        cwd=where,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_tag_check_passes_a_releasable_tag(tmp_path: Path) -> None:
    run = _run_tag_check(RELEASABLE_TAG, tmp_path)
    assert run.returncode == 0, (run.stdout, run.stderr)
    assert "::error::" not in run.stdout and "annotated, signed and verified" in run.stdout


@pytest.mark.parametrize("case", sorted(TAG_REFUSALS))
def test_the_tag_check_ends_every_refusal_with_its_own_error(case: str, tmp_path: Path) -> None:
    change, refusal = TAG_REFUSALS[case]
    run = _run_tag_check({**RELEASABLE_TAG, **change}, tmp_path)
    assert run.returncode == 1, (case, run.stdout, run.stderr)
    assert run.stdout.startswith("::error::") and refusal in run.stdout, (case, run.stdout)


def test_a_dry_run_that_attests_nothing_says_so_in_its_last_step() -> None:
    steps = _attest_steps()
    guard = "github.event_name == 'push' || !github.event.repository.private"
    assert [step.get("if") for step in steps[-3:-1]] == [guard, guard]
    assert all(step["uses"].startswith("actions/attest@") for step in steps[-3:-1])
    assert steps[-1] == DRY_RUN_NOTICE


# tools/release_files.py


def test_the_tree_passes_the_release_check_under_its_own_tag() -> None:
    current = TOOL.version()
    assert re.fullmatch(r"\d+\.\d+\.\d+", current)
    assert TOOL.problems(ROOT, f"v{current}") == []


def _scratch(root: Path) -> Path:
    for name in (
        "PROTOCOL_RELEASE.json",
        "CHANGELOG.md",
        "CONFORMANCE_LOCK.json",
        "tools/compare_verify_vectors.py",
        "docs/specification/conformance-testing.md",
        LOCK["artifact"],
    ):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, root / name)
    return root


def test_the_check_refuses_any_other_tag(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    current = TOOL.version(root)
    major, minor, patch = current.split(".")
    other = f"v{major}.{minor}.{int(patch) + 1}"
    assert TOOL.problems(root, other) == [
        f"tag {other} does not name the version PROTOCOL_RELEASE.json gives, {current}"
    ]
    # One comparison with the version, which has no leading zero, holds the tag to its form.
    for tag in (current, f"v{major}.{minor}.0{patch}", f"v{current}-rc.1", f"V{current}"):
        assert TOOL.problems(root, tag) == [
            f"tag {tag} does not name the version PROTOCOL_RELEASE.json gives, {current}"
        ]


@pytest.mark.parametrize(
    ("heading", "found"),
    [
        ("## [1.2.3]", True),
        ("## [1.2.3] - 2026-10-17", True),
        ("## [1.2.3]rc", False),
        ("## [1.2.3] \u2014 2026-10-17", False),
        ("## [1.2.30]", False),
        # A date in other digits than ASCII ones: Arabic-Indic, then full-width.
        ("## [1.2.3] - \u0662\u0660\u0662\u0666-\u0661\u0660-\u0661\u0667", False),
        ("## [1.2.3] - \uff12\uff10\uff12\uff16-\uff11\uff10-\uff11\uff17", False),
    ],
)
def test_the_changelog_section_has_the_one_heading_form(heading: str, found: bool) -> None:
    changelog = f"# Changelog\n\n{heading}\n\nThe changes.\n"
    assert TOOL.has_changelog_section(changelog, "1.2.3") is found


@pytest.mark.parametrize(
    ("changelog", "found"),
    [
        ("## [1.2.3]\n\n## [1.2.2]\n\nThe changes of 1.2.2.\n", False),
        ("# Changelog\n\n## [1.2.3] - 2026-10-17\n\n\n", False),
        ("## [1.2.3]\n", False),
        ("## [1.2.3]\n\n### Fixed\n\n- A fix.\n\n## [1.2.2]\n\nOlder.\n", True),
        ("## [1.2.3]\nOne line.\n", True),
    ],
)
def test_the_changelog_section_has_text_in_it(changelog: str, found: bool) -> None:
    assert TOOL.has_changelog_section(changelog, "1.2.3") is found


def test_each_failure_the_check_names_is_reported(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    assert TOOL.problems(root) == []
    current = TOOL.version(root)
    changelog = root / "CHANGELOG.md"
    changelog.write_text(changelog.read_text(encoding="utf-8").replace(f"## [{current}]", "## [0.0.0]"), "utf-8")
    script = root / "tools/compare_verify_vectors.py"
    script.write_bytes(script.read_bytes() + b"# changed\n")
    (root / "CONFORMANCE_LOCK.json").write_text("{}", encoding="utf-8")
    found = TOOL.problems(root)
    assert found[0] == f"CHANGELOG.md has no section ## [{current}] with text in it"
    assert found[1].startswith("CONFORMANCE_LOCK.json holds exactly the keys ")
    assert found[2:] == [
        "tools/compare_verify_vectors.py is not the script of section 7 of docs/specification/conformance-testing.md",
    ]


def test_the_check_refuses_an_archive_the_lock_does_not_describe(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    archive = root / LOCK["artifact"]
    archive.write_bytes(archive.read_bytes() + b"\0")
    assert TOOL.problems(root) == [
        "the pinned archive's size is not the size the lock declares",
        "the pinned archive's SHA-256 is not the digest the lock declares",
        "the pinned archive's corpus id is not derived from its bytes",
    ]
    with pytest.raises(ValueError, match="does not pass the release check"):
        TOOL.build(root, tmp_path / "out")
    archive.unlink()
    assert TOOL.problems(root) == [f"the pinned archive {LOCK['artifact']} is not a regular file"]


def test_a_heading_line_inside_a_fenced_block_does_not_split_a_section() -> None:
    document = (
        "## 6. Before\n\n```text\n## 7. not a heading\n```\n\n"
        "## 7. The script\n\n```python\nprint(1)\n## a comment at column 0\nprint(2)\n```\n\n"
        "## 8. After\n"
    )
    assert TOOL.blocks(document, "7", "python") == ["print(1)\n## a comment at column 0\nprint(2)\n"]
    assert TOOL.blocks(document, "6", "text") == ["## 7. not a heading\n"]
    with pytest.raises(ValueError, match="has no section 9"):
        TOOL.section(document, "9")


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> tuple[Path, Path]:
    first, second = tmp_path_factory.mktemp("first") / "out", tmp_path_factory.mktemp("second") / "out"
    for out in (first, second):
        TOOL.build(ROOT, out)
        TOOL.sbom(ROOT, out)
    # Summed once: SHA256SUMS is a function of the other files, which the second build must equal.
    TOOL.sums(first)
    return first, second


def test_the_build_writes_the_release_files_and_twice_the_same_bytes(built: tuple[Path, Path]) -> None:
    first, second = built
    artifact = LOCK["artifact"]
    archive = Path(artifact).name
    tarball = f"loquitur-protocol-specification-{TOOL.version()}.tar.gz"
    sbom = TOOL.sbom_name(TOOL.version())
    names = sorted(p.name for p in first.iterdir())
    assert names == sorted([*TOOL.LICENSES, "SHA256SUMS", "compare_verify_vectors.py", archive, tarball, sbom])
    # The names the attest job expects.
    assert TOOL.names() == names
    copies = {archive: artifact, "compare_verify_vectors.py": "tools/compare_verify_vectors.py"}
    for name, source in {**copies, **{name: name for name in TOOL.LICENSES}}.items():
        assert (first / name).read_bytes() == (ROOT / source).read_bytes(), name
    assert {p.name: p.read_bytes() for p in first.iterdir() if p.name != "SHA256SUMS"} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    with pytest.raises(ValueError, match="is not empty"):
        TOOL.build(ROOT, first)


def test_the_sbom_describes_the_release_files_and_nothing_else(built: tuple[Path, Path]) -> None:
    out, _ = built
    current = TOOL.version()
    document = json.loads((out / TOOL.sbom_name(current)).read_text(encoding="utf-8"))
    assert document["bomFormat"] == "CycloneDX" and document["specVersion"] == "1.6"
    # The attestation action accepts a CycloneDX document only with a serial number, and the same
    # files must give the same one.
    assert re.fullmatch(
        r"urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", document["serialNumber"]
    )
    assert TOOL.sbom_document(out, current)["serialNumber"] == document["serialNumber"]
    assert document["metadata"]["component"]["name"] == "loquitur-protocol"
    assert document["metadata"]["component"]["version"] == current
    # No dependency: the release files are documents, data and a standard-library script.
    assert "dependencies" not in document
    # The components are the files the SBOM attestation names as its subjects: every file but
    # the SBOM and SHA256SUMS, each with the sha256 of its bytes.
    subjects = [name for name in TOOL.names() if name not in ("SHA256SUMS", TOOL.sbom_name(current))]
    components = document["components"]
    assert [component["name"] for component in components] == subjects
    for component in components:
        assert component["type"] == "file" and component["bom-ref"] == component["name"]
        digest = hashlib.sha256((out / component["name"]).read_bytes()).hexdigest()
        assert component["hashes"] == [{"alg": "SHA-256", "content": digest}]
    licences = {component["name"]: component.get("licenses") for component in components}
    assert licences[f"loquitur-protocol-specification-{current}.tar.gz"] == [
        {"expression": "CC-BY-4.0 AND (MIT OR Apache-2.0)"}
    ]
    for name in ("LICENSE-APACHE", "LICENSE-MIT", "LICENSE-docs"):
        assert licences[name] is None, name
    for name in (Path(LOCK["artifact"]).name, "compare_verify_vectors.py", "NOTICE"):
        assert licences[name] == [{"expression": "MIT OR Apache-2.0"}], name
    with pytest.raises(ValueError, match="already exists"):
        TOOL.sbom(ROOT, out)


def test_the_sums_are_the_format_sha256sum_checks(built: tuple[Path, Path]) -> None:
    out, _ = built
    lines = (out / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    listed = {}
    for line in lines:
        match = re.fullmatch(r"(?P<digest>[0-9a-f]{64})  (?P<name>[^/\\]+)", line)
        assert match, line
        listed[match["name"]] = match["digest"]
    assert [line.split("  ", 1)[1] for line in lines] == sorted(listed)
    # The archive is the pinned one byte for byte, so its digest is the one the lock records; the
    # sums are the one place this module hashes it.
    archive = Path(LOCK["artifact"]).name
    others = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in out.iterdir()
        if p.name not in ("SHA256SUMS", archive)
    }
    assert listed == {**others, archive: LOCK["sha256"]}
    if shutil.which("sha256sum"):
        result = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=out, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr


def test_the_specification_tarball_holds_the_specification_and_its_licenses(built: tuple[Path, Path]) -> None:
    out, _ = built
    prefix = f"loquitur-protocol-specification-{TOOL.version()}"
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", *TOOL.SPECIFICATION],
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout
    expected = sorted([name for name in listing.split("\0") if name] + list(TOOL.LICENSES))
    assert len(expected) > 30, f"only {len(expected)} files expected; the check is thin"
    with tarfile.open(out / f"{prefix}.tar.gz", mode="r:gz") as tar:
        members = tar.getmembers()
        files = {m.name.removeprefix(prefix + "/"): tar.extractfile(m).read() for m in members if m.isfile()}
        assert all(m.name == prefix or m.name.startswith(prefix + "/") for m in members)
        assert all(m.uid == 0 and m.gid == 0 and not m.uname and not m.gname for m in members)
        assert all(m.isfile() or m.isdir() for m in members), "the tarball holds files and directories only"
    assert sorted(files) == expected
    assert all(files[name] == (ROOT / name).read_bytes() for name in expected)
    # The tar.gz can check its own digest list: every file PROSE_DIGESTS.json binds is in it.
    digests = json.loads(files["docs/specification/PROSE_DIGESTS.json"])
    bound = [entry["path"] for entry in digests["files"]]
    assert bound and not [path for path in bound if path not in files]
    # Every relative link of a document in it resolves inside it.
    broken = []
    for name, data in files.items():
        if not name.endswith(".md"):
            continue
        for target in re.findall(r"\]\(([^)\s]+)\)", data.decode("utf-8")):
            path = target.split("#", 1)[0]
            if not path or re.match(r"[a-z][a-z0-9+.-]*:", path):
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), path))
            if resolved not in files and not any(member.startswith(resolved + "/") for member in files):
                broken.append(f"{name} -> {target}")
    assert not broken, f"links the tar.gz cannot follow: {broken}"


def test_the_tool_reports_a_failed_check_by_its_exit_status(tmp_path: Path) -> None:
    root = _scratch(tmp_path)

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        argv = [sys.executable, str(ROOT / "tools/release_files.py"), "--root", str(root), *args]
        return subprocess.run(argv, capture_output=True, encoding="utf-8", check=False)

    current = TOOL.version()
    assert run("version").stdout == f"{current}\n"
    assert run("artifact").stdout == f"{LOCK['artifact']}\n"
    assert run("check", "--tag", f"v{current}").returncode == 0
    failed = run("check", "--tag", "v0.0.0")
    assert failed.returncode == 1 and "does not name the version" in failed.stdout
    assert run("frobnicate").returncode == 2
    assert run("check").stdout == f"release check ok: {current}\n"


def test_the_documented_sbom_check_covers_exactly_the_files_the_sbom_attestation_names() -> None:
    """releasing.md checks the SBOM attestation over the files release.yml attests it for."""
    import fnmatch

    text = (ROOT / "docs" / "maintainers" / "releasing.md").read_text(encoding="utf-8")
    blocks = re.findall(r"^```bash\n(.*?)^```$", text, re.M | re.S)
    loops = [block for block in blocks if "for file in *" in block and "gh attestation verify" in block]
    predicate = "--predicate-type https://cyclonedx.org/bom"
    [sbom_loop] = [block for block in loops if predicate in block]
    [provenance_loop] = [block for block in loops if predicate not in block]
    assert "continue" not in provenance_loop
    [skipped] = re.findall(r'case "\$file" in ([^)]+)\) continue ;; esac', sbom_loop)
    patterns = [pattern.strip() for pattern in skipped.split("|")]
    current = TOOL.version()
    carried = TOOL.names()
    left_out = {name for name in carried if any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)}
    # release.yml attests the SBOM for every file but the SBOM and SHA256SUMS.
    assert left_out == {"SHA256SUMS", TOOL.sbom_name(current)}
    assert "checked the same way" not in text


def test_every_documented_attestation_check_refuses_a_self_hosted_build() -> None:
    """Each `gh attestation verify` command in releasing.md, line continuations joined, refuses a
    build that ran on a self-hosted runner."""

    text = (ROOT / "docs" / "maintainers" / "releasing.md").read_text(encoding="utf-8")
    joined = re.sub(r"\\\r?\n\s*", " ", text)
    commands = [line for line in joined.splitlines() if line.lstrip().startswith("gh attestation verify")]
    assert commands, "releasing.md shows no attestation check"
    for command in commands:
        assert re.search(r"\s--deny-self-hosted-runners(?:\s|$)", command), command


# `git` as GitHub answers the sibling probe: STUB_PROBE holds one `status|message` answer per
# attempt, separated by `;`, the last one repeated, and the file `attempts` counts the calls;
# `sleep` returns at once. Bash builtins only, so no tool beside bash is needed.
PROBE_STUBS = """
git() {
  local count=0 answers line
  if [ -f attempts ]; then read -r count < attempts; fi
  echo $((count + 1)) > attempts
  IFS=';' read -ra answers <<< "$STUB_PROBE"
  line="${answers[count < ${#answers[@]} ? count : ${#answers[@]} - 1]}"
  echo "${line#*|}" >&2
  return "${line%%|*}"
}
sleep() { :; }
"""
PROBE_READABLE = "0|"
PROBE_PRIVATE = "128|fatal: could not read Username for 'https://github.com': terminal prompts disabled"
PROBE_ABSENT = "128|remote: Repository not found.\nfatal: repository 'https://github.com/o/r.git/' not found"
PROBE_UNREACHABLE = {
    "no-name-resolution": "128|fatal: unable to access 'https://github.com/o/r.git/': Could not resolve host: github.com",
    "server-error": "128|fatal: unable to access 'https://github.com/o/r.git/': The requested URL returned error: 503",
    "rate-limited": "128|fatal: unable to access 'https://github.com/o/r.git/': The requested URL returned error: 403",
}


def _probe() -> dict:
    [probe] = [
        step for step in _workflow(WORKFLOWS / "ci.yml")["jobs"]["siblings"]["steps"] if step.get("id") == "probe"
    ]
    return probe


def _probed_siblings() -> list[str]:
    found = re.search(r"^ *for repo in ([a-z -]+); do$", _probe()["run"], re.M)
    assert found, "the probe names no sibling"
    return found[1].split()


def _run_probe(answers: str, ref_type: str, where: Path) -> tuple[subprocess.CompletedProcess[str], str, int]:
    """The probe step, run with git answering ``answers``: the run, its outputs and the attempts made."""
    output = where / "output"
    output.write_text("", encoding="utf-8")
    env = {"OWNER": "owner", "REF_TYPE": ref_type, "STUB_PROBE": answers, "GITHUB_OUTPUT": str(output)}
    script = where / "probe.sh"
    script.write_text(PROBE_STUBS + _probe()["run"], encoding="utf-8", newline="\n")
    run = subprocess.run(
        [_bash(), "--noprofile", "--norc", "-eo", "pipefail", script.as_posix()],
        cwd=where,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    attempts = where / "attempts"
    count = int(attempts.read_text(encoding="utf-8")) if attempts.is_file() else 0
    return run, output.read_text(encoding="utf-8"), count


def test_the_probe_passes_the_ref_type_through_env() -> None:
    assert _probe()["env"]["REF_TYPE"] == "${{ github.ref_type }}"


@pytest.mark.parametrize("ref_type", ["branch", "tag"])
def test_the_probe_checks_out_every_readable_sibling(ref_type: str, tmp_path: Path) -> None:
    run, output, attempts = _run_probe(PROBE_READABLE, ref_type, tmp_path)
    assert run.returncode == 0, (run.stdout, run.stderr)
    assert f"published={' '.join(_probed_siblings())}" in output.splitlines()
    assert attempts == len(_probed_siblings())


@pytest.mark.parametrize("answer", [PROBE_PRIVATE, PROBE_ABSENT, "2|"], ids=["private", "absent", "no-head"])
@pytest.mark.parametrize("ref_type", ["branch", "tag"])
def test_a_sibling_that_is_not_found_is_skipped_at_once_even_on_a_tag(
    ref_type: str, answer: str, tmp_path: Path
) -> None:
    run, output, attempts = _run_probe(answer, ref_type, tmp_path)
    assert run.returncode == 0, (run.stdout, run.stderr)
    assert "published=" in output.splitlines() and "::" not in run.stdout
    assert attempts == len(_probed_siblings())


@pytest.mark.parametrize("answer", sorted(PROBE_UNREACHABLE.values()), ids=sorted(PROBE_UNREACHABLE))
def test_a_probe_failure_that_is_not_a_not_found_fails_a_run_on_a_tag(answer: str, tmp_path: Path) -> None:
    run, output, attempts = _run_probe(answer, "tag", tmp_path)
    assert run.returncode == 1, (run.stdout, run.stderr)
    assert f"::error::{_probed_siblings()[0]} could not be probed" in run.stdout
    assert attempts == 4 and output == ""


@pytest.mark.parametrize("answer", sorted(PROBE_UNREACHABLE.values()), ids=sorted(PROBE_UNREACHABLE))
def test_a_probe_failure_on_a_branch_warns_and_skips_the_sibling(answer: str, tmp_path: Path) -> None:
    run, output, attempts = _run_probe(answer, "branch", tmp_path)
    assert run.returncode == 0, (run.stdout, run.stderr)
    assert run.stdout.count("::warning::") == len(_probed_siblings())
    assert "published=" in output.splitlines() and attempts == 4 * len(_probed_siblings())


def test_a_transient_probe_failure_is_asked_again(tmp_path: Path) -> None:
    run, output, attempts = _run_probe(PROBE_UNREACHABLE["server-error"] + ";" + PROBE_READABLE, "tag", tmp_path)
    assert run.returncode == 0, (run.stdout, run.stderr)
    assert f"published={' '.join(_probed_siblings())}" in output.splitlines()
    assert attempts == len(_probed_siblings()) + 1
