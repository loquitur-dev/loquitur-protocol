import json
import shutil
import subprocess
import sys
from pathlib import Path

USAGE = "usage: compare_verify_vectors.py [--process-exit] [--summaries] --intake archive|directory_only CORPUS COMMAND..."
arguments = sys.argv[1:]
flags = set()
while arguments[:1] in (["--process-exit"], ["--summaries"]) and arguments[0] not in flags:
    flags.add(arguments.pop(0))
process_exit, summaries = "--process-exit" in flags, "--summaries" in flags
if len(arguments) < 4 or arguments[0] != "--intake" or arguments[1] not in ("archive", "directory_only"):
    sys.exit(USAGE)
intake, corpus, command = arguments[1], Path(arguments[2]), arguments[3:]
program = shutil.which(command[0])
if program is None:
    sys.exit(f"{command[0]} is not on PATH")
command = [program, *command[1:]]
vectors = corpus / "vectors"
COMPARED = ("status", "verdict", "exit_code", "reason", "errors", "checks_requested",
            "checks_established", "review_reasons", "evaluation_time", "unsupported_version")
STATUSES = ("authorization_status", "signature_status", "trust_registry_root_signature_status")


def declared_runs():
    """Every run of the three files section 6 item 1 binds, under the name it is reported by."""
    yield from json.loads((vectors / "verify.json").read_text(encoding="utf-8")).items()
    for rel in ("additional-negatives/expected.json", "bundles/manifest.json"):
        for case in json.loads((vectors / rel).read_text(encoding="utf-8"))["cases"]:
            yield f"{rel}#{case['id']}", case
    if summaries:
        rel = "summary-checks/expected.json"
        for case in json.loads((vectors / rel).read_text(encoding="utf-8"))["cases"]:
            yield f"{rel}#{case['id']}", case


def surface(report):
    """The members of a report that section 6 item 1 compares."""
    outcome = report.get("outcome") or {}
    errors = report.get("errors") or []
    gate = next((error for error in errors if error.get("code") == "unsupported_version"), None)
    registry = report.get("trust_registry")
    return {
        "status": report.get("status"),
        "verdict": report.get("verdict"),
        "exit_code": report.get("exit_code"),
        "reason": outcome.get("reason"),
        "errors": [error.get("code") for error in errors],
        "checks_requested": report.get("checks_requested"),
        "checks_established": report.get("checks_established"),
        "review_reasons": report.get("review_reasons"),
        "evaluation_time": report.get("evaluation_time"),
        "unsupported_version": None if gate is None else {"object": gate.get("object"), "version": gate.get("version")},
        "trust_registry": registry if registry is None else {status: registry.get(status) for status in STATUSES},
    }


def differences(expected, actual):
    """Every member the run declares and the report does not reproduce."""
    out = [
        f"{member} is {actual[member]!r}, declared {expected[member]!r}"
        for member in COMPARED
        if member in expected and actual[member] != expected[member]
    ]
    if "trust_registry" in expected:
        declared, found = expected["trust_registry"], actual["trust_registry"]
        if declared is None or found is None:
            # A declared null is compared too: a report that evaluated a registry does not agree with it.
            if declared != found:
                out.append(f"trust_registry is {found!r}, declared {declared!r}")
        else:
            out += [
                f"trust_registry.{status} is {found.get(status)!r}, declared {value!r}"
                for status, value in declared.items()
                if found.get(status) != value
            ]
    return out


runs = list(declared_runs())
disagreements = 0
for name, run in runs:
    if run.get("surface", "verify") == "summary":
        # A summary run checks one verification summary: the declaration is the rules it violates.
        result = subprocess.run([*command, "--summary", str(vectors / run["summary"])], capture_output=True, encoding="utf-8")
        try:
            found = json.loads(result.stdout).get("violated_rules")
        except (json.JSONDecodeError, AttributeError):
            found = f"no result; the command exited {result.returncode}: {result.stderr.strip()[-300:]}"
        if found != run["expected"]["violated_rules"]:
            disagreements += 1
            print(f"{name}: violated_rules is {found!r}, declared {run['expected']['violated_rules']!r}")
        continue
    # A run names a bundle directory, or an input whose reading is itself the question.
    target = vectors / "bundles" / run["bundle"] if "bundle" in run else vectors / run["input"]
    argv = [*command, "--bundle", str(target)]
    for option, member in (
        ("--registry-entry", "registry_entry"),
        ("--trust-registry", "trust_registry"),
        ("--trust-root", "trust_root"),
    ):
        if member in run:
            argv += [option, str(vectors / run[member])]
    if "evaluation_time" in run:
        argv += ["--evaluation-time", run["evaluation_time"]]
    # The vocabulary a run names for a kind, else the corpus's baseline for it (section 4.1).
    named = run.get("vocabularies", {})
    for kind in ("asset_type", "workflow", "anchoring_method"):
        document = vectors / named[kind] if kind in named else vectors / "vocabularies" / "baseline" / f"{kind}.json"
        if kind in named or document.is_file():
            argv += [f"--{kind.replace('_', '-')}-vocabulary", str(document)]
    result = subprocess.run(argv, capture_output=True, encoding="utf-8")

    # A run whose outcome depends on the reader declares one outcome per intake. The verifier's
    # intake is a property of the verifier, so the same declared intake is compared on every run.
    expected = run["expected"] if "expected" in run else run["expected_by_intake"][intake]
    if process_exit and "expected_command_line" in run:
        # A command line answers some invocations differently from a library (section 4.1).
        expected = run["expected_command_line"]
    if expected.get("report", False) is None:
        # A refused invocation reads no evidence, so there is no report and no reason surface to
        # compare: the declaration is the exit code and the silence. A command that writes a report
        # and then exits with that code has not refused.
        if result.stdout.strip() or result.returncode != expected["exit_code"]:
            disagreements += 1
            print(f"{name}: declared a refusal with exit {expected['exit_code']}; the command exited"
                  f" {result.returncode} and wrote {len(result.stdout)} characters")
        continue
    try:
        found = differences(expected, surface(json.loads(result.stdout)))
    except (json.JSONDecodeError, AttributeError, TypeError):
        # Output that is not JSON, or JSON that is not a report object (null, an array, error
        # codes as plain strings), is no report.
        disagreements += 1
        print(f"{name}: no report; the command exited {result.returncode}: {result.stderr.strip()[-300:]}")
        continue
    if process_exit and result.returncode != expected["exit_code"]:
        found.append(f"the process exited {result.returncode}, declared {expected['exit_code']}")
    for difference in found:
        disagreements += 1
        print(f"{name}: {difference}")
print(f"{len(runs)} runs, {disagreements} disagreements on the reason surface")
sys.exit(1 if disagreements else 0)
