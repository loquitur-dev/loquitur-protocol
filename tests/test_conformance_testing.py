"""conformance-testing.md describes the pinned archive as it is, and its commands do what it says.

The document tells a third implementation how to check and extract the conformance archive, what
each vector file declares, how the reference adapters are called and what counts as conforming.
Every one of those statements is about bytes this repository carries, so each is checked against
them here rather than trusted:

* the commands of §1 and §2 are read out of the document and run, and the extraction they perform
  is what the other checks read;
* the layout table of §3 covers every member of the archive it describes, and names nothing the
  archive does not hold;
* the table of §4 lists exactly the declaration files under `vectors/`, with the profiles
  `conformance-manifest.json` gives them, the number of cases each holds, and the classification
  of §6, which is pinned below;
* the table of §4.1 counts every run of `verify.json` at the outermost check its inputs request;
* the commands of §5 and §7 run against loquitur-verify-py beside this repository, print what the
  document says they print, and the §7 script reports a disagreement when a declared outcome is
  changed, compares a command that exits with the report's exit code as it compares the adapter,
  compares the process exit under --process-exit, and counts a command that writes no report as a
  disagreement. That half skips without the
  sibling and fails instead under LOQUITUR_REQUIRE_SIBLINGS.

Each §7 comparison starts one process per declared run, so the six comparisons below are started
together by one fixture, none reading another's output, and each test waits for the ones it
asserts on.

Every command runs as the document writes it. Its first word is looked up on PATH, as the shell a
reader types it into looks it up, with this interpreter's directory first on PATH, as an activated
virtual environment puts it; nothing in it is replaced. The words after the first are passed as
written, the bare `python` the §7 command hands to the script included, so the script's own lookup
of that word is what is tested: a program name handed straight to CreateProcess on Windows is
looked up beside the running interpreter first, which for a virtual environment is the base
interpreter without loquitur-verify-py.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import pytest
from conftest import release_files

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/specification/conformance-testing.md"
LOCK = json.loads((ROOT / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))
VERIFY = ROOT.parent / "loquitur-verify-py"
# The reader of sections and their code blocks that tools/release_files.py checks the section 7
# script with: the release and these tests read the document alike.
TOOL = release_files()

# §6: what a third implementation must reproduce. `vectors/additional-negatives/expected.json` and
# `vectors/bundles/manifest.json` are binding because the corpus gate executes their cases as runs,
# through the same loop and against the same declared surface as `vectors/verify.json`.
CLASSIFICATION = {
    "vectors/verify.json": "binding",
    "vectors/schema-valid/expected.json": "binding",
    "vectors/schema-negative/manifest.json": "binding",
    "vectors/canonicalization.json": "binding",
    "vectors/canonicalization_unicode.json": "binding",
    "vectors/jcs-numeric.json": "binding",
    "vectors/signature.json": "binding",
    "vectors/signature_payload_version.json": "binding",
    "vectors/anchor-methods.json": "binding",
    "vectors/additional-negatives/expected.json": "binding",
    "vectors/bundles/manifest.json": "binding",
    "vectors/summary-checks/expected.json": "binding",
    "vectors/cryptographic_capabilities.json": "not binding",
    "vectors/report-invariants.json": "not binding",
    "vectors/subject-ref-hash.json": "not binding",
}


def _text() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


def _numeric(spelling: str) -> bool:
    """Whether a reject entry is a JSON number; the non-finite spellings are not."""
    try:
        return isinstance(json.loads(spelling), (int, float)) and not isinstance(json.loads(spelling), bool)
    except ValueError:
        return False


def _section(number: str) -> str:
    return TOOL.section(_text(), number)


def _blocks(number: str, language: str) -> list[str]:
    return TOOL.blocks(_text(), number, language)


def _table(section: str) -> list[list[str]]:
    rows = [line for line in section.splitlines() if line.startswith("| ")]
    return [[cell.strip() for cell in row.strip("|").split(" | ")] for row in rows[2:]]


def _environment(**extra: str) -> dict[str, str]:
    """This environment, with this interpreter's directory first on PATH.

    User site-packages are off, so that another interpreter reached by mistake cannot stand in for
    this one through packages installed for the user: a virtual environment does not see them either.
    """
    environment = {**os.environ, "PYTHONNOUSERSITE": "1", **extra}
    environment["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), environment.get("PATH", "")])
    return environment


def _shell_argv(command: str, environment: dict[str, str]) -> list[str]:
    """The words of ``command``, its first looked up on PATH as a shell looks it up, the rest as written."""
    argv = shlex.split(command)
    assert argv[0] == "python", command
    program = shutil.which(argv[0], path=environment["PATH"])
    assert program, f"{argv[0]} is not on PATH"
    return [program, *argv[1:]]


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    """The archive extracted by the command of §2, from a checkout laid out as §1 assumes."""
    base = tmp_path_factory.mktemp("conformance-testing")
    checkout = base / "checkout"
    (checkout / "conformance").mkdir(parents=True)
    shutil.copy2(ROOT / LOCK["artifact"], checkout / LOCK["artifact"])
    shutil.copy2(ROOT / "CONFORMANCE_LOCK.json", checkout / "CONFORMANCE_LOCK.json")
    command = _blocks("2", "bash")[0]
    environment = _environment()
    subprocess.run(_shell_argv(command.strip(), environment), cwd=checkout, env=environment, check=True)
    root = base / "corpus" / "loquitur-conformance"
    assert (root / "conformance-manifest.json").is_file()
    return root


def _members(corpus: Path) -> list[str]:
    return sorted(p.relative_to(corpus).as_posix() for p in corpus.rglob("*") if p.is_file())


def test_the_pin_command_accepts_the_pinned_archive() -> None:
    [command] = _blocks("1", "bash")
    environment = _environment()
    result = subprocess.run(
        _shell_argv(command.strip(), environment),
        cwd=ROOT,
        env={**environment, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert (result.returncode, result.stdout) == (0, "True\n"), result.stderr


def test_the_extraction_holds_exactly_the_archive(corpus: Path) -> None:
    with zipfile.ZipFile(ROOT / LOCK["artifact"]) as archive:
        names = sorted(n.split("/", 1)[1] for n in archive.namelist() if not n.endswith("/"))
    assert _members(corpus) == names
    assert all(n.startswith("loquitur-conformance/") for n in zipfile.ZipFile(ROOT / LOCK["artifact"]).namelist())


def test_the_layout_table_covers_the_archive_and_names_nothing_else(corpus: Path) -> None:
    patterns = []
    for path_cell, _ in _table(_section("3")):
        patterns.extend(re.findall(r"`([^`]+)`", path_cell))
    members = _members(corpus)

    def matches(pattern: str, member: str) -> bool:
        return member.startswith(pattern) if pattern.endswith("/") else fnmatch.fnmatchcase(member, pattern)

    unmatched_patterns = [p for p in patterns if not any(matches(p, m) for m in members)]
    assert not unmatched_patterns, f"the layout names what the archive does not hold: {unmatched_patterns}"
    uncovered = [m for m in members if "/" in m and not any(matches(p, m) for p in patterns)]
    assert not uncovered, f"members in a directory the layout does not describe: {uncovered}"
    assert "conformance-manifest.json" in patterns


# The four kinds of input a run names under `input`, as `_input_kinds` measures them, and the words
# each place that lists those kinds uses for each: §3's `vectors/inputs/` row and §4.1's sentence
# on what a run names. Every kind the runs name must be named in both places.
INPUT_KIND_WORDS = {
    "3": {
        "archive": "archives, one of them clean and each of the rest that archive with the entries or bytes one "
        "reading of",
        "container": "directories that contain a bundle",
        "respelled": "a directory that holds a bundle's members with its manifest stored under another spelling",
        "other": "a regular file that is no archive at all",
    },
    "4.1": {
        "archive": "an archive",
        "container": "a directory containing a bundle",
        "respelled": "a directory whose manifest is stored under another spelling of its name",
        "other": "a regular file that is no archive at all",
    },
}


def _input_kinds(corpus: Path) -> tuple[dict[str, str], dict[str, set[str]]]:
    """Each input the runs of `verify.json` name, sorted by kind, with the run that names it.

    An archive; a directory that contains a bundle one level down; a directory that holds a
    bundle's members at its own top level with the manifest stored under another spelling, which
    asks whether a host that ignores letter case decides the bundle root (`bundle-objects.md` §1);
    and a regular file that is no archive at all, which is how the corpus asks for `invalid_zip`.
    Anything else is an input of a kind no sentence describes, and fails here.
    """
    runs = json.loads((corpus / "vectors/verify.json").read_text(encoding="utf-8"))
    # A run whose input names nothing lists it under not_a_regular_file, and §4.1 describes it there.
    named = {
        run["input"]: name
        for name, run in runs.items()
        if "input" in run and "input" not in run.get("not_a_regular_file", [])
    }
    kinds: dict[str, set[str]] = {kind: set() for kind in INPUT_KIND_WORDS["3"]}
    for member in named:
        target = corpus / "vectors" / member
        if target.is_dir():
            listing = os.listdir(target)
            if "manifest.json" not in listing and any(name.lower() == "manifest.json" for name in listing):
                kinds["respelled"].add(member)
            elif any("manifest.json" in os.listdir(target / name) for name in listing if (target / name).is_dir()):
                kinds["container"].add(member)
            else:
                raise AssertionError(f"{member}: a directory input of a kind no sentence describes: {listing}")
        elif zipfile.is_zipfile(target):
            kinds["archive"].add(member)
        elif target.is_file():
            kinds["other"].add(member)
        else:
            raise AssertionError(f"{member}: an input that is neither a directory nor a regular file")
    return named, kinds


def test_the_inputs_row_names_every_kind_of_input_a_run_supplies(corpus: Path) -> None:
    """§3's `vectors/inputs/` row names every kind of input the runs name, and each is measured here.

    The two kinds of directory are measured apart, so that the row cannot name one and pass for
    both. The archives are one clean, being the run that shows the archive intake accepting one,
    and the rest that archive with what one reading of `bundle-objects.md` §5 turns on. Several of
    the rest break no rule: they are refused while extracting, or verify with an extra file, so the
    row cannot say that each breaks one.
    """
    runs = json.loads((corpus / "vectors/verify.json").read_text(encoding="utf-8"))
    named, kinds = _input_kinds(corpus)
    assert named, "no run names an input; the row would describe nothing"
    assert all(kinds.values()), kinds

    def declared(member: str) -> list[dict]:
        run = runs[named[member]]
        return [run["expected"]] if "expected" in run else list(run["expected_by_intake"].values())

    clean = {m for m in kinds["archive"] if any(d["exit_code"] == 0 for d in declared(m))}
    assert clean, "the row says one archive is clean and no archive run declares exit 0"
    assert kinds["archive"] - clean, "the row says the rest differ from the clean one and every archive is clean"

    [row] = [cell for path_cell, cell in _table(_section("3")) if "`vectors/inputs/`" in path_cell]
    for kind in kinds:
        assert INPUT_KIND_WORDS["3"][kind] in row, (kind, row)


def test_the_declared_runs_name_every_kind_of_input_a_run_supplies(corpus: Path) -> None:
    """§4.1's sentence on what a run names lists every kind of input the runs name under `input`.

    The kinds are an archive, two kinds of directory and, in the run `regular_file_not_a_zip`, a
    regular file that is no archive at all. The test above holds the §3 row to the same kinds.
    """
    named, kinds = _input_kinds(corpus)
    assert named and all(kinds.values()), kinds
    sentence = re.search(r"^A run names its input, (.*?\.)\s+It optionally names", _section("4.1"), re.M | re.S)
    assert sentence, "§4.1 does not say what a run names"
    words = " ".join(sentence.group(1).split())
    for kind in kinds:
        assert INPUT_KIND_WORDS["4.1"][kind] in words, (kind, words)


def _cases(corpus: Path, name: str) -> int:
    document = json.loads((corpus / name).read_text(encoding="utf-8"))
    counts = {
        "vectors/verify.json": lambda d: len(d),
        "vectors/canonicalization.json": lambda d: len(d["canonicalize_ok"]) + len(d["canonicalize_reject"]),
        "vectors/canonicalization_unicode.json": lambda d: len(d),
        "vectors/jcs-numeric.json": lambda d: len(d["cases"]) + len(d["reject"]),
        "vectors/signature.json": lambda d: 1,
        "vectors/signature_payload_version.json": lambda d: len([k for k in d if k.endswith("_entry")]),
        "vectors/cryptographic_capabilities.json": lambda d: len(d["positive_cases"]) + len(d["negative_cases"]),
        "vectors/report-invariants.json": lambda d: len(d["invariants"]),
    }
    return counts.get(name, lambda d: len(d["cases"]))(document)


def test_the_vector_table_lists_every_declaration_with_its_profiles_cases_and_classification(corpus: Path) -> None:
    runs = json.loads((corpus / "vectors/verify.json").read_text(encoding="utf-8"))
    inputs = {f"vectors/{run[k]}" for run in runs.values() for k in ("registry_entry", "trust_registry") if k in run}
    declarations = {m for m in _members(corpus) if re.fullmatch(r"vectors/[^/]+\.json", m) and m not in inputs}
    declarations |= {
        "vectors/schema-valid/expected.json",
        "vectors/schema-negative/manifest.json",
        "vectors/additional-negatives/expected.json",
        "vectors/bundles/manifest.json",
        "vectors/summary-checks/expected.json",
    }
    manifest = json.loads((corpus / "conformance-manifest.json").read_text(encoding="utf-8"))
    profiles: dict[str, set[str]] = {}
    for profile in manifest["profiles"]:
        for vector in profile["files"]:
            profiles.setdefault(vector, set()).add(profile["id"])

    table = {}
    for file_cell, profile_cell, cases_cell, class_cell in _table(_section("4")):
        [name] = re.findall(r"`([^`]+)`", file_cell)
        table[name] = (set(re.findall(r"`([^`]+)`", profile_cell)), int(cases_cell), class_cell)
    assert set(table) == declarations
    problems = []
    for name, (listed_profiles, cases, classification) in sorted(table.items()):
        if listed_profiles != profiles.get(name, set()):
            problems.append(f"{name}: profiles {sorted(listed_profiles)}, manifest {sorted(profiles.get(name, set()))}")
        if cases != _cases(corpus, name):
            problems.append(f"{name}: {cases} cases listed, {_cases(corpus, name)} in the archive")
        if classification != CLASSIFICATION[name]:
            problems.append(f"{name}: classified {classification!r}, pinned here as {CLASSIFICATION[name]!r}")
    assert not problems, "\n".join(problems)


def test_section_6_lists_as_not_binding_exactly_the_files_the_table_does() -> None:
    section = _section("6")
    listed = section.split("These files are not binding in this corpus:", 1)[1].split("\n\n", 2)[1]
    named = set(re.findall(r"^- `([^`]+)`", listed, re.M))
    assert named == {name for name, value in CLASSIFICATION.items() if value == "not binding"}
    assert "the corpus `CONFORMANCE_LOCK.json` pins" in section


def test_no_jcs_numeric_case_declares_a_serialization_input_strictness_rule_2_refuses(corpus: Path) -> None:
    """§6 item 4 excepts nothing, so the corpus must give it nothing to except.

    Rule 2 of "Input strictness" in `canonicalization-and-hashing.md` makes an integer-valued
    number beyond 2^53 - 1 invalid, and the corpus declares such numbers refused. What has to hold
    is that no case declares a serialization of one, the reject list exercises the rule, and the
    item names no case to except.
    """
    document = json.loads((corpus / "vectors/jcs-numeric.json").read_text(encoding="utf-8"))

    def beyond(value: object) -> bool:
        return float(value).is_integer() and abs(float(value)) > 2**53 - 1

    assert not [case["id"] for case in document["cases"] if "value" in case and beyond(case["value"])]
    assert [spelling for spelling in document["reject"] if _numeric(spelling) and beyond(json.loads(spelling))]

    item = re.search(r"^4\. \*\*Canonicalization\.\*\*(.*?)^5\. ", _section("6"), re.M | re.S)
    assert item, "§6 has no canonicalization item"
    named = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", item.group(1))) - {"canonicalization-and-hashing"}
    assert not named, f"§6 item 4 excepts cases: {sorted(named)}"


def test_the_checks_table_counts_every_run_at_the_outermost_check_of_its_inputs(corpus: Path) -> None:
    """The table gives one count per outermost check, the runs being far too many to name.

    Naming six hundred runs would be a list nobody reads and a pin that moves on every vector; the
    count is the property a reader checks the corpus against.
    """
    runs = json.loads((corpus / "vectors/verify.json").read_text(encoding="utf-8"))
    # Every run of the three files section 6 item 1 binds, as the section 7 script runs them.
    declared = _declared_runs(corpus)
    expected = {"integrity": 0, "link": 0, "authorization": 0}
    for _, run in declared:
        expected[
            "authorization" if "trust_registry" in run else "link" if "registry_entry" in run else "integrity"
        ] += 1
    listed = {}
    for check_cell, count_cell in _table(_section("4.1")):
        listed[re.match(r"`([a-z]+)`", check_cell).group(1)] = int(count_cell)
    assert listed == expected
    assert sum(listed.values()) == len(declared)
    assert len(declared) > len(runs), "the other two files hold runs, so counting verify.json alone would differ"

    # The outermost check is decided by the trust registry, and the row says so. The runs that supply a
    # trust registry with no registry entry are named in the sentence under the table, so that a
    # reader recomputing the table from the row's own words lands on its count.
    flat = " ".join(_section("4.1").split())
    entry_less = {name for name, run in runs.items() if "trust_registry" in run and "registry_entry" not in run}
    sentence = re.search(
        r"((?:`[a-z0-9_]+`, )*`[a-z0-9_]+` and `[a-z0-9_]+`) are the three authorization runs\s*that supply a trust registry"
        r" with no registry entry",
        flat,
    )
    assert sentence, "§4.1 does not name the runs that supply a trust registry with no registry entry"
    assert set(re.findall(r"`([a-z0-9_]+)`", sentence.group(1))) == entry_less
    assert len(entry_less) == 3, entry_less
    # report-contract.md §4: the error comes after every error the bundle gives, and is the only
    # error when the bundle gives none. One run pairs it with a bundle error, so the order is pinned.
    paired = 0
    for name in entry_less:
        declared = runs[name]["expected"]
        assert declared["errors"][-1] == "trust_registry_requires_registry_entry", declared
        assert declared["reason"] == declared["errors"][0], declared
        paired += len(declared["errors"]) > 1
    assert paired == 1, "§4.1 names one run that pairs a bundle error with the trust registry's"
    assert "`trust_registry_requires_registry_entry`, the answer a library interface gives, after every error" in flat


def test_the_authorization_outcome_sentence_is_a_ceiling_every_run_respects(corpus: Path) -> None:
    """§4.1's sentence on what an authorization run reaches, measured over the runs rather than read.

    The rule of `trust-root.md` §2 is a ceiling, not an outcome: most authorization runs that pin no trust
    root fail a check first and reach `OFFLINE_FAIL`, and the sentence states the ceiling. Here it
    is executed: no run without a trust root declares better than `OFFLINE_REVIEW`, and no run
    declares `OFFLINE_OK` without one, nor without an evaluation time
    (`trust-registry-authorization.md` §2).
    """
    runs = json.loads((corpus / "vectors/verify.json").read_text(encoding="utf-8"))
    declarations = {
        name: declared
        for name, run in runs.items()
        for declared in ([run["expected"]] if "expected" in run else run["expected_by_intake"].values())
        if declared.get("report", False) is not None
    }
    authorization_runs = {name: runs[name] for name in declarations if "trust_registry" in runs[name]}
    assert authorization_runs, "no authorization run declares an outcome; the rule below would hold over nothing"

    without = {name for name in authorization_runs if "trust_root" not in runs[name]}
    reached = {declarations[name]["status"] for name in without}
    # A version gate stops a run before any evidence outcome, and a run refused as a whole reaches
    # HOST_FAILURE; the sentence after the ceiling says both.
    assert reached - {"UNSUPPORTED_VERSION", "HOST_FAILURE"} <= {"OFFLINE_REVIEW", "OFFLINE_FAIL"}, sorted(reached)
    assert "OFFLINE_REVIEW" in reached, "no run pins the ceiling itself; the rule holds vacuously"

    ok = {name for name in authorization_runs if declarations[name]["status"] == "OFFLINE_OK"}
    assert ok, "no authorization run reaches OFFLINE_OK; the second half of the sentence holds over nothing"
    assert all("trust_root" in runs[name] for name in ok), sorted(ok - without)
    assert all("evaluation_time" in runs[name] for name in ok), sorted(ok)

    flat = " ".join(_section("4.1").split())
    assert "`OFFLINE_REVIEW` is the most an authorization run reaches" in flat
    assert "A run that a version gate stops reaches `UNSUPPORTED_VERSION`" in flat
    assert (
        "a run refused as a whole, such as one whose trust registry path names nothing, reaches `HOST_FAILURE`" in flat
    )
    assert "An authorization run reaches `OFFLINE_OK` with exit 0 only where a trust root is supplied" in flat
    assert "and an evaluation time is supplied" in flat


def _sibling_verifier() -> dict[str, str]:
    if not (VERIFY / "src/loquitur/verify/runner.py").is_file():
        message = f"loquitur-verify-py is not checked out beside this repository ({VERIFY})"
        if os.environ.get("LOQUITUR_REQUIRE_SIBLINGS", "").strip().lower() in {"1", "true", "yes", "on"}:
            pytest.fail(f"LOQUITUR_REQUIRE_SIBLINGS is set, but {message}")
        pytest.skip(message)
    return _environment(PYTHONPATH=str(VERIFY / "src"))


def _place_the_adapter(corpus: Path) -> None:
    """The sibling loquitur-verify-py's adapter, where §5 and §7 name it: beside the checkout."""
    target = corpus.parents[1] / "loquitur-verify-py" / "tools" / "conformance_adapter.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(VERIFY / "tools/conformance_adapter.py", target)


def test_the_python_adapter_command_prints_the_report_the_document_describes(corpus: Path) -> None:
    environment = _sibling_verifier()
    _place_the_adapter(corpus)
    [command] = _blocks("5", "bash")
    result = subprocess.run(
        _shell_argv(command.strip(), environment),
        cwd=corpus.parents[1] / "checkout",
        capture_output=True,
        encoding="utf-8",
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert len(result.stdout.splitlines()) == 1
    report = json.loads(result.stdout)
    assert list(report) == sorted(report)
    declared = json.loads((corpus / "vectors/verify.json").read_text(encoding="utf-8"))[
        "authorization_evaluated_inside_the_registry_window"
    ]["expected"]
    assert {k: report[k] for k in ("status", "verdict", "exit_code")} == {
        k: declared[k] for k in ("status", "verdict", "exit_code")
    }
    sentence = (
        f"`status` is `{report['status']}`, `verdict` `{report['verdict']}`, `exit_code` `{report['exit_code']}` and\n"
        f"`outcome.reason` `{report['outcome']['reason']}`"
    )
    assert sentence in _section("5"), f"§5 does not describe the report the command prints:\n{sentence}"


def test_section_5_counts_the_refusals_both_adapters_reproduce(corpus: Path) -> None:
    """§5's claim about the two adapters' refusals, bound to the runs the corpus declares refused.

    The two adapters do not refuse the same inputs. The Python adapter is a command line and
    refuses a trust root or an evaluation time supplied without a trust registry as well
    (`report-contract.md` §4); the TypeScript adapter is a library and refuses only the two
    refusals that section gives a library interface. What both refuse alike is every run this
    corpus declares refused, each of which supplies a trust registry and either a trust-root
    document `trust-root.md` §3 rejects or an evaluation time that is no calendar instant. The
    number in the sentence is therefore the corpus's own.
    """
    runs = json.loads((corpus / "vectors/verify.json").read_text(encoding="utf-8"))
    refused = {name: run for name, run in runs.items() if (run.get("expected") or {}).get("report", False) is None}
    assert refused, "no run declares a refusal; the sentence would hold over nothing"
    # A run refused for a registered vocabulary document names it under `vocabularies`; every other
    # refused run supplies a trust registry and a trust-root document or an evaluation time.
    trust = {name: run for name, run in refused.items() if "vocabularies" not in run}
    assert all("trust_root" in run or "evaluation_time" in run for run in trust.values()), sorted(trust)
    assert any("trust_root" not in run for run in trust.values()), "no refused evaluation time"
    assert all("trust_registry" in run for run in trust.values()), sorted(trust)
    flat = " ".join(_section("5").split())
    assert f"both adapters refuse the same {len(refused)}" in flat, flat[-400:]


def _declared_runs(corpus: Path) -> list[tuple[str, dict]]:
    """Every run of the three files §6 item 1 binds, named as the §7 script names them."""
    vectors = corpus / "vectors"
    runs = list(json.loads((vectors / "verify.json").read_text(encoding="utf-8")).items())
    for rel in ("additional-negatives/expected.json", "bundles/manifest.json"):
        cases = json.loads((vectors / rel).read_text(encoding="utf-8"))["cases"]
        runs += [(f"{rel}#{case['id']}", case) for case in cases]
    return runs


def _archive_declaration(run: dict) -> dict:
    """The declaration the §7 script compares for a verifier whose intake is `archive`."""
    return run["expected"] if "expected" in run else run["expected_by_intake"]["archive"]


def _run_in(checkout: Path, argv: list[str], environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=checkout, capture_output=True, encoding="utf-8", env=environment, check=False)


def _compare(
    corpus: Path, environment: dict[str, str], *command: str, process_exit: bool = False
) -> subprocess.CompletedProcess[str]:
    """The §7 script, as the comparisons fixture placed it in the checkout, over ``corpus`` with ``command``."""
    program = shutil.which("python", path=environment["PATH"])
    options = ["--process-exit"] if process_exit else []
    argv = [program, "compare_verify_vectors.py", *options, "--intake", "archive", str(corpus), *command]
    return _run_in(corpus.parents[1] / "checkout", argv, environment)


def _changed_outcome(corpus: Path, argv: list[str], environment: dict[str, str]):
    """The documented command over a copy of the corpus whose `link_valid` run declares exit code 2."""
    changed = corpus.parents[1] / "changed" / "loquitur-conformance"
    shutil.copytree(corpus, changed)
    runs_path = changed / "vectors/verify.json"
    runs = json.loads(runs_path.read_text(encoding="utf-8"))
    runs["link_valid"]["expected"]["exit_code"] = 2
    runs_path.write_text(json.dumps(runs), encoding="utf-8")
    argv = list(argv)
    argv[argv.index(next(a for a in argv if a.endswith("corpus/loquitur-conformance")))] = str(changed)
    return runs, _run_in(corpus.parents[1] / "checkout", argv, environment)


def _exit_code_command(corpus: Path, environment: dict[str, str], directory: Path):
    """§7: a command line that follows report-contract.md §4 is compared as the adapter is."""
    adapter = VERIFY / "tools/conformance_adapter.py"
    command_line = directory / "command_line.py"
    command_line.write_text(
        "import json, subprocess, sys\n"
        f"done = subprocess.run([sys.executable, {str(adapter)!r}, *sys.argv[1:]], capture_output=True, text=True)\n"
        "sys.stdout.write(done.stdout)\n"
        # A refused invocation writes no report, so there is no exit_code to exit with and the
        # command line exits with the refusal of its own. report-contract.md §4 gives the
        # report's code to a run that produced a report, which is the other branch.
        "sys.exit(done.returncode if not done.stdout.strip() else json.loads(done.stdout)['exit_code'])\n",
        encoding="utf-8",
    )
    return _compare(corpus, environment, "python", str(command_line), process_exit=True)


def _refusing_command(corpus: Path, environment: dict[str, str], directory: Path):
    """The command line above, refusing what report-contract.md §4 requires a command line to refuse."""
    adapter = VERIFY / "tools/conformance_adapter.py"
    refusing = directory / "refusing_command_line.py"
    refusing.write_text(
        "import json, subprocess, sys\n"
        "argv = sys.argv[1:]\n"
        # The refusal report-contract.md §4 requires of a command line, and nothing else: the
        # invocation is refused before any evidence is read, so there is no report to write.
        "if '--trust-registry' in argv and '--registry-entry' not in argv:\n"
        "    sys.exit(64)\n"
        f"done = subprocess.run([sys.executable, {str(adapter)!r}, *argv], capture_output=True, text=True)\n"
        "sys.stdout.write(done.stdout)\n"
        "sys.exit(done.returncode if not done.stdout.strip() else json.loads(done.stdout)['exit_code'])\n",
        encoding="utf-8",
    )
    return _compare(corpus, environment, "python", str(refusing), process_exit=True)


def _adapter_under_process_exit(corpus: Path, environment: dict[str, str], directory: Path):
    """The adapter, which exits 0 after any report, compared as a command line: every non-zero run disagrees."""
    return _compare(corpus, environment, "python", str(VERIFY / "tools/conformance_adapter.py"), process_exit=True)


def _silent_command(corpus: Path, environment: dict[str, str], directory: Path):
    """A command that writes no report for any run, and exits 3."""
    silent = directory / "silent.py"
    silent.write_text("import sys\nsys.stderr.write('crashed')\nsys.exit(3)\n", encoding="utf-8")
    return _compare(corpus, environment, "python", str(silent))


@pytest.fixture(scope="module")
def comparisons(corpus: Path, tmp_path_factory) -> Iterator[dict[str, object]]:
    """The six §7 comparisons the tests below assert on, started at once.

    The script and the adapter are placed once, before any comparison starts, so no comparison
    reads a file another is writing. Each comparison is prepared inside its own task, so a failure
    to prepare one fails the test that reads it and no other.
    """
    environment = _sibling_verifier()
    _place_the_adapter(corpus)
    [script] = _blocks("7", "python")
    [command] = _blocks("7", "bash")
    checkout = corpus.parents[1] / "checkout"
    (checkout / "compare_verify_vectors.py").write_text(script, encoding="utf-8")
    documented = _shell_argv(command.strip(), environment)
    directory = tmp_path_factory.mktemp("commands")
    with ThreadPoolExecutor(max_workers=6) as pool:
        started: dict[str, Future] = {
            "documented": pool.submit(_run_in, checkout, documented, environment),
            "changed": pool.submit(_changed_outcome, corpus, documented, environment),
            "exit_code": pool.submit(_exit_code_command, corpus, environment, directory),
            "refusing": pool.submit(_refusing_command, corpus, environment, directory),
            "adapter_exit": pool.submit(_adapter_under_process_exit, corpus, environment, directory),
            "silent": pool.submit(_silent_command, corpus, environment, directory),
        }
        yield {"argv": documented, **started}


def test_the_comparison_script_agrees_with_the_corpus_and_reports_a_changed_outcome(
    corpus: Path, comparisons: dict[str, object]
) -> None:
    argv = comparisons["argv"]
    assert argv[2:5] == ["--summaries", "--intake", "archive"], (
        "the documented command compares the summary runs and declares the adapter's intake"
    )
    assert argv[6] == "python", "the documented command hands the script a bare python"

    result = comparisons["documented"].result()
    printed = re.search(r"It prints `([^`]+)` and exits 0", _section("7"))
    assert printed, "§7 does not say what the script prints"
    assert (result.returncode, result.stdout) == (0, printed.group(1) + "\n"), result.stderr

    _, result = comparisons["changed"].result()
    summaries = json.loads((corpus / "vectors/summary-checks/expected.json").read_text(encoding="utf-8"))["cases"]
    total = len(_declared_runs(corpus)) + len(summaries)
    assert result.returncode == 1
    assert "link_valid: exit_code is 0, declared 2" in result.stdout
    assert result.stdout.endswith(f"{total} runs, 1 disagreements on the reason surface\n")


def test_the_comparison_script_takes_a_command_that_exits_with_the_report_exit_code(
    corpus: Path, comparisons: dict[str, object]
) -> None:
    """§7: a command line that follows report-contract.md §4 is compared as the adapter is."""
    # Read as a sentence, not as two lines: where the paragraph wraps is not the property, and an
    # assertion that depends on it fails on a reflow while the document still says what it must.
    assert "exits with the report's `exit_code`, so either kind of command can be compared" in " ".join(
        _section("7").split()
    )
    result = comparisons["exit_code"].result()
    runs = json.loads((corpus / "vectors/verify.json").read_text(encoding="utf-8"))
    total = len(_declared_runs(corpus))
    entry_less = sorted(name for name, run in runs.items() if "trust_registry" in run and "registry_entry" not in run)
    assert result.returncode == 1
    assert result.stdout.endswith(f"{total} runs, {len(entry_less)} disagreements on the reason surface\n"), (
        result.stdout + result.stderr
    )
    # Not every run declares one `expected`: a run whose outcome depends on the intake declares one
    # per branch, and `expected` is not read on those.
    codes = {
        declared["exit_code"]
        for run in runs.values()
        for declared in ([run["expected"]] if "expected" in run else run["expected_by_intake"].values())
    }
    assert codes >= {0, 1, 2}, "the check needs runs that exit 1 and 2"
    assert 64 in codes, "the check needs a run whose invocation is refused"

    # The one place a conforming command line cannot agree, executed rather than left to prose.
    # report-contract.md §4 requires a command line to refuse a trust registry supplied with no
    # registry entry (exit 64, no report), while the corpus declares the report a library
    # returns for that same invocation. §7 says this script reports those runs as disagreements
    # for such a command and that the command is conforming; the count and the names are
    # measured here. The command line above refuses nothing and is the other half of the pair.
    assert len(entry_less) == 3, entry_less
    for name in entry_less:
        assert runs[name]["expected_command_line"] == {"exit_code": 64, "report": None}, name
    result = comparisons["refusing"].result()
    assert (result.returncode, result.stdout) == (0, f"{total} runs, 0 disagreements on the reason surface\n"), (
        result.stdout[-400:]
    )
    flat = " ".join(_section("7").split())
    assert "so a command line that refuses them agrees" in flat

    # --process-exit is what compares a process exit: the adapter exits 0 after every report, so
    # under it every run that declares a report with a non-zero exit code disagrees, and no other.
    result = comparisons["adapter_exit"].result()
    non_zero = [
        (name, declared["exit_code"])
        for name, run in _declared_runs(corpus)
        # Under --process-exit a run declaring the command line's answer is compared with it.
        for declared in [run.get("expected_command_line") or _archive_declaration(run)]
        if declared.get("report", False) is not None and declared["exit_code"] != 0
    ]
    assert non_zero, "no run declares a non-zero exit; the comparison would hold over nothing"
    assert result.returncode == 1
    for name, code in non_zero:
        assert f"{name}: the process exited 0, declared {code}" in result.stdout, name
    # The adapter writes a report where a command line refuses (section 4.1), so each run that
    # declares the command line's refusal disagrees too.
    refused = [
        name
        for name, run in _declared_runs(corpus)
        if (run.get("expected_command_line") or {}).get("report", False) is None
    ]
    assert len(refused) == 3, refused
    for name in refused:
        assert f"{name}: declared a refusal with exit 64; the command exited 0" in result.stdout, name
    assert result.stdout.endswith(f"{total} runs, {len(non_zero) + len(refused)} disagreements on the reason surface\n")
    assert "`--process-exit` is given" in flat


def test_the_comparison_script_counts_a_command_that_writes_no_report(
    corpus: Path, comparisons: dict[str, object]
) -> None:
    """Every run is a disagreement, by one of the script's two ways of writing no report down.

    A run declaring an outcome is compared against a report, so silence is "no report". A run
    declaring a refusal is compared against silence AND an exit code, so a command that is silent
    with the wrong code disagrees for the code. Both counts are asserted, because a script that
    stopped reading one of the two shapes would still report every run.
    """
    result = comparisons["silent"].result()
    runs = _declared_runs(corpus)
    refusals = [name for name, run in runs if _archive_declaration(run).get("report", False) is None]
    stated = re.search(r"both adapters refuse the same ([0-9]+)", " ".join(_section("5").split()))
    assert stated, "§5 does not state how many runs both adapters refuse"
    assert result.returncode == 1
    # Every run that is not a declared refusal, counted from the corpus rather than written as a
    # literal that a new vector would make false.
    assert result.stdout.count("no report; the command exited 3: crashed") == len(runs) - len(refusals)
    assert result.stdout.count("declared a refusal with exit") == len(refusals) == int(stated.group(1))
    assert result.stdout.endswith(f"{len(runs)} runs, {len(runs)} disagreements on the reason surface\n")


def test_the_normative_members_are_the_ones_a_conformance_comparison_reads() -> None:
    """report-contract.md §2: its table's normative members, and nothing else, are what a comparison reads.

    The table classes each member; the paragraph under it says what a conformance comparison
    compares; conformance-testing.md §6 item 1 says what reproducing a declared run produces. The
    three must name the same members, so a member moved from one class to the other in the table,
    or dropped from the comparison, fails here.
    """
    contract = (ROOT / "docs/specification/report-contract.md").read_text(encoding="utf-8")
    section = contract.split("## 2. Normative and informative members", 1)[1].split("\n## ", 1)[0]
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in section.splitlines()]
    rows = [row for row in rows if len(row) == 3 and row[0].startswith("`")]
    normative = {row[0].strip("`") for row in rows if row[2].startswith("normative")}
    assert all(row[2].startswith(("normative", "informative")) for row in rows), rows
    statuses = {member for member in normative if member.startswith("trust_registry.")}
    assert len(statuses) == 3, statuses

    flat = " ".join(section.split())
    compared = re.search(
        r"A conformance comparison of runs over the same inputs compares exactly these: (.*?)\. ", flat
    )
    assert compared, "report-contract.md §2 does not say what a conformance comparison compares"
    named = set(re.findall(r"`([^`]+)`", compared.group(1)))
    named = {"errors" if member == "errors[].code" else member for member in named}
    assert "the three statuses of §5.4" in compared.group(1)
    assert named | statuses == normative, (sorted(named | statuses), sorted(normative))

    item = " ".join(_section("6").split("\n2. ", 1)[0].split())
    assert "produces the declared `status`, `verdict`, `exit_code`, `reason`, error codes" in item
    assert "checks requested and established, review reasons and evaluation time" in item
    assert "and the three trust-registry statuses" in item
    report_members = {"checks_requested", "checks_established", "review_reasons", "evaluation_time"}
    assert {"status", "verdict", "exit_code", "outcome.reason", "errors"} | report_members | statuses == normative


def _synthetic_corpus(base: Path, runs: dict, summaries: list | None = None) -> Path:
    """A corpus tree holding only the declarations the section 7 script reads, and no bundle bytes.

    The commands below decide from their arguments alone, so the runs need no input on disk.
    """
    vectors = base / "loquitur-conformance" / "vectors"
    (vectors / "additional-negatives").mkdir(parents=True)
    (vectors / "bundles").mkdir()
    (vectors / "verify.json").write_text(json.dumps(runs), encoding="utf-8")
    for rel in ("additional-negatives/expected.json", "bundles/manifest.json"):
        (vectors / rel).write_text(json.dumps({"cases": []}), encoding="utf-8")
    if summaries is not None:
        (vectors / "summary-checks").mkdir()
        (vectors / "summary-checks/expected.json").write_text(json.dumps({"cases": summaries}), encoding="utf-8")
    return vectors.parent


def _run_script(base: Path, corpus: Path, command: Path, *options: str) -> subprocess.CompletedProcess[str]:
    [script] = _blocks("7", "python")
    path = base / "compare_verify_vectors.py"
    path.write_text(script, encoding="utf-8")
    argv = [sys.executable, str(path), *options, "--intake", "archive", str(corpus), sys.executable, str(command)]
    return subprocess.run(argv, capture_output=True, encoding="utf-8", check=False)


def test_a_command_line_is_compared_with_the_answer_a_run_declares_for_a_command_line(tmp_path: Path) -> None:
    """section 4.1 and 7: under --process-exit a declared expected_command_line replaces expected.

    The command refuses a trust registry supplied with no registry entry, as report-contract.md
    section 4 requires of a command line. Declared with the library's answer alone, the run is a
    disagreement; declared with the command line's answer as well, it agrees, and the adapter
    comparison, which gives no --process-exit, still reads expected.
    """
    command = tmp_path / "refusing.py"
    command.write_text(
        "import sys\n"
        "argv = sys.argv[1:]\n"
        "sys.exit(64 if '--trust-registry' in argv and '--registry-entry' not in argv else 3)\n",
        encoding="utf-8",
    )
    library = {
        "status": "OFFLINE_FAIL",
        "verdict": "FAIL",
        "exit_code": 1,
        "reason": "trust_registry_requires_registry_entry",
        "errors": ["trust_registry_requires_registry_entry"],
    }
    run = {"bundle": "b", "trust_registry": "t.json", "intake": "any", "expected": library}
    without = _synthetic_corpus(tmp_path / "without", {"entry_less": run})
    result = _run_script(tmp_path, without, command, "--process-exit")
    assert result.stdout.endswith("1 runs, 1 disagreements on the reason surface\n"), result.stdout + result.stderr
    declared = {**run, "expected_command_line": {"exit_code": 64, "report": None}}
    with_member = _synthetic_corpus(tmp_path / "with", {"entry_less": declared})
    result = _run_script(tmp_path, with_member, command, "--process-exit")
    assert (result.returncode, result.stdout) == (0, "1 runs, 0 disagreements on the reason surface\n"), result.stderr
    result = _run_script(tmp_path, with_member, command)
    assert "entry_less: no report; the command exited 64" in result.stdout, result.stdout


@pytest.mark.parametrize("output", ["null", "[]", '{"errors": ["x"]}', '{"errors": 5}', '{"outcome": "x"}'])
def test_json_that_is_not_a_report_object_is_counted_as_no_report(tmp_path: Path, output: str) -> None:
    """section 7: valid JSON that is not a report object is a disagreement, and the count still ends.

    Two runs, so that the first one's output stopping the script would leave the second uncompared
    and the closing count unprinted.
    """
    command = tmp_path / "not_a_report.py"
    command.write_text(f"print({output!r})\n", encoding="utf-8")
    declared = {"status": "OFFLINE_PASS", "verdict": "PASS", "exit_code": 0}
    runs = {name: {"bundle": "b", "intake": "any", "expected": declared} for name in ("first", "second")}
    result = _run_script(tmp_path, _synthetic_corpus(tmp_path / "c", runs), command)
    assert result.returncode == 1, result.stderr
    assert "Traceback" not in result.stderr, result.stderr
    assert result.stdout.count(": no report; the command exited 0") == 2, result.stdout
    assert result.stdout.endswith("2 runs, 2 disagreements on the reason surface\n"), result.stdout


def test_summary_runs_are_compared_only_under_summaries(tmp_path: Path) -> None:
    """section 4.1 and 7: a summary run hands the command --summary and compares violated_rules."""
    command = tmp_path / "summary_checker.py"
    command.write_text(
        "import json, sys\n"
        "argv = sys.argv[1:]\n"
        "assert argv[0] == '--summary', argv\n"
        "document = json.loads(open(argv[1], encoding='utf-8').read())\n"
        "print(json.dumps({'violated_rules': document['rules_this_fake_reports']}))\n",
        encoding="utf-8",
    )
    cases = [
        {
            "id": "holds",
            "surface": "summary",
            "summary": "summary-checks/holds.json",
            "expected": {"violated_rules": []},
        },
        {
            "id": "no_key_checks",
            "surface": "summary",
            "summary": "summary-checks/no_key_checks.json",
            "expected": {"violated_rules": ["VG-5"]},
        },
    ]
    corpus = _synthetic_corpus(tmp_path / "c", {}, cases)
    (corpus / "vectors/summary-checks/holds.json").write_text('{"rules_this_fake_reports": []}', encoding="utf-8")
    (corpus / "vectors/summary-checks/no_key_checks.json").write_text(
        '{"rules_this_fake_reports": ["VG-6"]}', encoding="utf-8"
    )
    result = _run_script(tmp_path, corpus, command)
    assert (result.returncode, result.stdout) == (0, "0 runs, 0 disagreements on the reason surface\n"), result.stderr
    result = _run_script(tmp_path, corpus, command, "--summaries")
    assert result.returncode == 1
    assert "summary-checks/expected.json#no_key_checks: violated_rules is ['VG-6'], declared ['VG-5']" in result.stdout
    assert result.stdout.endswith("2 runs, 1 disagreements on the reason surface\n"), result.stdout
