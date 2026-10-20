# Test ownership

This repository owns tests for its own surface only. A test that needs another repository
names it and looks for it beside this one.

## What this repository owns

- public specification boundary tests;
- public spec manifest checks;
- governance/status limitation checks;
- the requirements inventory checks (`tests/test_requirements_inventory.py`);
- the release workflow and the files it builds (`tests/test_release_workflow.py`).

## What this repository does not own

- service runtime tests;
- package internals;
- documentation-site, website and user-interface application tests.

## Local check commands

[`testing.md`](testing.md) gives the commands and says what each check covers.

## Other repositories

Sibling repositories may be installed or referenced for integration checks, but this repository
remains the owner of only the surfaces listed above. A test brought in from another repository
must preserve public/private boundary discipline and must not introduce production, audit,
legal truth, valuation correctness, compliance, chain finality, or oracle claims.
