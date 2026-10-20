# Open-source REA Lab

A small, public lab for reproducible analysis of **published open-source artifacts**, plus tools that make that work easier. Original code is MIT licensed. No private application source or customer data is used.

The first tool, **npm Tarball Audit**, inspects an npm `.tgz` before installation. It reads the archive offline, checks its identity and structure, and never runs npm, package JavaScript, or lifecycle scripts. Extraction is not part of the audit.

## Try the tool

Python 3.11 or later, with no runtime dependencies:

```sh
PYTHONPATH=src python3 -m npm_tarball_audit example.tgz --json
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Or install into your own virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/npm-tarball-audit example.tgz --expected-name example --expected-version 1.0.0
```

Add `--integrity 'sha512-BASE64_VALUE'` to check an expected SRI token obtained from a trusted source. Add `--include-inventory --json` for paths, sizes and SHA-256 hashes of every regular file. Exit code `0` means no errors (warnings can still be present); `1` means failed checks; argument errors return `2`.

## What it checks

- Compressed size, decompressed size including tar padding/metadata, member count, individual and total payload sizes, and manifest size have independent limits.
- Rejects absolute paths, traversal, noncanonical paths, Windows-style paths, control characters, duplicate members, links, device/special members, sparse metadata and setuid/setgid bits.
- Reads gzip through its checksum/footer, including after tar's end marker.
- Validates `package/package.json`, duplicate JSON keys, expected name/version, and optional SHA-512 integrity. `--strict-semver` opts in to version syntax checks. An iterative scan bounds JSON container depth before parsing or traversing entrypoints.
- Checks exact local `bin`/`exports` targets and common `main` resolution candidates. Reports wildcard exports as unverified patterns.
- Reports license metadata/file absence and declared install/prepare hooks for review.

Defaults: 64 MiB compressed, 256 MiB decompressed stream, 32 MiB per file, 128 MiB total regular files, 1 MiB manifest, 20,000 members, and 64 nested JSON containers in the manifest. Python callers can supply `Limits(...)`.

The manifest's root object counts as depth 1; objects and arrays add levels,
while brackets, escaped quotes and backslashes inside JSON strings do not.
Over-budget input fails with `manifest_depth_exceeded` before the JSON parser
or recursive export traversal runs. This budget is independent of manifest byte
size. Invalid JSON within the depth budget still fails the ordinary JSON checks.

```python
from npm_tarball_audit import Limits, audit

report = audit("example.tgz", limits=Limits(manifest_depth=32))
```

Depth limits must be positive integers, excluding booleans. The CLI uses the
default of 64. Raising a caller's limit does not override Python's own parser
limits; inputs rejected by that parser remain failed audits.

## Parse semantic version syntax

The pure `parse_semver` API validates a supplied string using the syntax of
[SemVer 2.0.0](https://semver.org/spec/v2.0.0.html), without reading a manifest or
executing package code:

```python
from npm_tarball_audit.semver import parse_semver

version = parse_semver("2.4.1-rc.3+Build.007")
assert version == {
    "major": "2", "minor": "4", "patch": "1",
    "prerelease": ["rc", "3"], "build": ["Build", "007"],
}
```

Core numbers and identifiers remain strings, including very large numbers.
Core numbers and numeric prerelease identifiers cannot have leading zeroes;
build identifiers can. ASCII letters and hyphens are allowed in extension
identifiers. Spelling, case and order are preserved, and every result has fresh
mutable containers. Ordinary `str` subclasses are accepted without coercion.

The keyword-only `max_length=4096` budget counts Python code points and is
inclusive. It must be a positive integer, excluding booleans; callers can raise
it explicitly. The length check precedes parsing. This is an API resource
budget, not a limit imposed by SemVer. Invalid inputs, types, syntax or budgets
raise `ValueError("Invalid semantic version or length budget")` without copying
the input into the error. Inputs are not trimmed or repaired: `v` prefixes,
Unicode digits, whitespace, npm ranges and tags are rejected.

This pure API checks syntax only. It does not sort versions, evaluate
compatibility, validate npm names or establish package safety.

### Opt in to manifest version checks

Audit callers and the CLI can explicitly require a SemVer version:

```python
from npm_tarball_audit import audit

report = audit("example.tgz", strict_semver=True)
```

```sh
PYTHONPATH=src python3 -m npm_tarball_audit example.tgz --strict-semver --json
PYTHONPATH=src python3 -m npm_tarball_audit example.tgz --strict-semver --sarif
```

The default remains `False`, preserving existing audits. `strict_semver` must be
an actual boolean; other API values raise a fixed `ValueError` before archive
access. Strict mode checks the original, untrimmed manifest version with the
parser's inclusive 4,096-character budget. Invalid nonblank syntax produces the
fixed `manifest_version` error finding and exit code `1`; valid versions and
warning-only audits keep their ordinary status and exit codes. Missing,
non-string or blank versions retain the existing `manifest_identity` finding.

Expected name/version, integrity and inventory options remain independent.
Plain and JSON reports retain raw package metadata as before; SARIF uses the
existing neutral `NTA/manifest_version` rule without raw version or host paths.
`--strict-semver` takes no value and cannot be combined with `--compare`.
This is opt-in syntax enforcement, not range matching, version precedence,
compatibility, package provenance or a malware verdict.

## Parse package name syntax

The pure `parse_package_name` API splits a supplied string into scope and name using a local ASCII syntax policy, without reading files, network access or package execution:

```python
from npm_tarball_audit.names import parse_package_name

result = parse_package_name("@my-scope/my-name")
assert result == {"scope": "my-scope", "name": "my-name"}

result = parse_package_name("example")
assert result == {"scope": None, "name": "example"}
```

The local policy accepts 1-214 ASCII characters in total, including `@` and `/` when present: lowercase letters, digits, `.`, `_` and `-`, where scope and name each start with a letter or digit. Scoped form is exactly `@scope/name` with a single slash; `scope` is returned without `@` and is `None` when absent. Ordinary `str` subclasses are accepted without coercion. No trimming, spaces, Unicode or escapes are accepted. Each call returns a newly allocated plain `dict` with exactly `scope` and `name`. Invalid inputs, types, lengths or syntax raise `ValueError("Invalid package name")` without echoing the input.

This checks local syntax only. It does not validate name availability, the complete npm registry policy, safety, security, compatibility or module resolution.

## Compare inventory records

The pure Python API compares the `inventory` lists from two reports produced
with `include_inventory=True`. It reports added and removed files, paths whose
byte count or SHA-256 changed, and the number of unchanged paths:

```python
from npm_tarball_audit import audit
from npm_tarball_audit.compare import compare_inventories

before = audit("example-1.0.0.tgz", include_inventory=True)
after = audit("example-1.1.0.tgz", include_inventory=True)
# Check each report's findings/status separately before interpreting the diff.
changes = compare_inventories(before["inventory"], after["inventory"])
print(changes["added"], changes["removed"], changes["changed"])
print(changes["unchanged_count"])
```

`compare_inventories` itself reads no files and executes no package code. Each
input must be a list of records containing exactly `path`, `bytes` and `sha256`:
canonical relative `package/` paths, nonnegative integer sizes excluding
booleans, and 64 ASCII hexadecimal digest characters. Duplicate or unsafe paths
and malformed records raise `ValueError`. Digests are normalized to lowercase;
path spelling and case are preserved. The default `max_entries=20000` applies
independently to each list, including the boundary; larger inputs are rejected.
The limit must be a positive integer, excluding booleans.

Results are sorted by path and contain fresh records, without mutating either
input. Each `changed` item contains `path` and complete `before`/`after` records.
This core API compares inventory metadata only. A file diff does not determine
whether either package is safe or whether its audits passed.

### Compare saved reports

Generate reports with inventories explicitly enabled, then compare them offline:

```sh
PYTHONPATH=src python3 -m npm_tarball_audit before.tgz --include-inventory --json > before.json
PYTHONPATH=src python3 -m npm_tarball_audit after.tgz --include-inventory --json > after.json
PYTHONPATH=src python3 -m npm_tarball_audit --compare before.json after.json --json
```

Omit the final `--json` for a summary and escaped file paths. A successful
comparison returns the same four fields as `compare_inventories`. Exit code `0`
means unchanged inventory; `1` means added, removed or changed files; `2` means
invalid reports, unreadable files or arguments. A change is not an audit failure
or malware finding. Audit-only options cannot be combined with `--compare`.

Each input must be a regular, non-symlink UTF-8 file of at most 16 MiB. Reads are
bounded; directories, devices and FIFOs are refused. The loader requires schema
`npm-tarball-audit/v1`, status `pass` or `warning`, explicit false
`package_executed`/`files_extracted` flags, and an `inventory` list. Reports from
failed audits are refused because their inventories may be partial. Reports
created without `--include-inventory` are also refused. Inspect findings and
identity separately; these fields are validation, not proof of report provenance.

The whole JSON text has a default depth budget of 64 containers, with the root
object at depth 1. Bytes and depth are checked before parsing. Duplicate keys,
invalid UTF-8, nonfinite numbers, malformed entries and more than 20,000 entries
per report are rejected. Extra report metadata is accepted within these budgets
but is not returned. Invalid input produces no partial comparison or raw input
in diagnostics.

Python callers can use the pure
`npm_tarball_audit.report.parse_inventory_report(text, *, max_bytes=16777216,
max_depth=64, max_entries=20000)` API with explicitly supplied text. All budgets
are positive integers, excluding booleans. The function reads no files and
returns fresh, sorted inventory records validated by the comparator. Callers
deliberately comparing partial inventories can still use `compare_inventories`
directly; the ordinary report boundary does not silently discard a failed status.
Entrypoint-declaration comparison remains future work. Unchanged inventory does
not establish package equivalence or safety.

## Export SARIF results

Produce a SARIF 2.1.0 artifact for generic viewers or CI artifact storage:

```sh
PYTHONPATH=src python3 -m npm_tarball_audit example.tgz --sarif > audit.sarif
```

`--sarif` is an audit output format, mutually exclusive with `--json` and
unavailable with `--compare`. Ordinary expected-name/version/integrity checks
still apply. Exit codes remain `0` for pass/warning and `1` for failed audit
checks. Invalid arguments or an export that exceeds its validation budget return
`2`, without a partial SARIF document.

The pure API accepts an explicitly supplied audit report and reads no files:

```python
from npm_tarball_audit import audit
from npm_tarball_audit.sarif import to_sarif

sarif = to_sarif(audit("example.tgz"))
```

Rules have stable `NTA/<finding_code>` IDs, sorted by code. Results retain the
original finding order and severity. The converter accepts v1 pass, warning or
fail reports with explicit false execution/extraction flags; malformed inputs
raise a generic `ValueError`. The default `max_findings=20000` is inclusive and
must be a positive integer, excluding booleans. One archive member can produce
several findings, so this budget is separate from the archive member limit. Pure
callers may explicitly raise it. It is not a total input-byte budget. Results are
fresh objects and do not modify the input report.

The export intentionally uses neutral code-based messages. Original messages,
archive paths, package metadata and other extra fields are not copied: operating
system errors can include local paths. Retain the original report privately for
full details; the SARIF run sets `originalReportRequired=true`.

Member names are untrusted display text. Only canonical `package` paths may be
shown, quoted and escaped to ASCII. Unsafe paths and names over the
240-character display budget are omitted using fixed text. Unicode format
characters remain visible escapes; characters that could form HTML, links or
message placeholders are escaped too. This follows the message rules in the
[OASIS SARIF specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html).

No source snippets, physical or logical locations, artifact URIs, timestamps or
machine-specific metadata are emitted. Package members were never extracted, so
this is generic SARIF interchange, not a claim of workspace source annotations
or automatic GitHub code-scanning upload compatibility. A report does not prove
provenance or package safety. See [release notes](CHANGELOG.md).

**A passing audit is not a malware verdict or a recommendation to execute the package.** Dependency vulnerabilities, publisher authenticity, runtime behavior and a complete Node resolver are outside its scope. Optional expected integrity is only as trustworthy as the source from which you obtained it. License checks are inventory checks, not a legal assessment.

## Reproduce the first case

The target is the official npm package [`rea-agents@6.4.0`](https://www.npmjs.com/package/rea-agents/v/6.4.0), linked by the upstream [`morluto/rea`](https://github.com/morluto/rea) project. A fixed version is used so a moving `latest` release cannot silently change the case.

```sh
python3 scripts/reproduce.py
```

This downloads only the pinned public tarball from the npm registry, verifies its pinned SHA-256 and SHA-512, and writes an audit report under ignored `artifacts/`. For a static REA analysis, prepare a fresh extracted directory:

```sh
python3 scripts/reproduce.py --output artifacts/rea-static --prepare-rea --entrypoint-only
# With an existing trusted REA installation:
rea analyze-javascript-application "$PWD/artifacts/rea-static/extracted/package" --json
```

This prepares the documented two-file entrypoint slice. Drop `--entrypoint-only` only when you intentionally need the whole package; broad semantic graph construction can require substantial memory and time.

Read the [case report](analyses/rea-agents-6.4.0/README.md) for exact identity, observations, REA evidence and limitations. Vendor source, vendor archives and raw machine-specific REA dumps are deliberately not distributed here.

## Contribute useful work

See [ROADMAP.md](ROADMAP.md). Add a regression fixture with each parser fix, keep checks offline, document unsupported semantics, and make one coherent commit per tested change. An idle backlog is a reason to investigate the next useful improvement, never to fabricate commits. See [AGENTS.md](AGENTS.md) for automated contributor rules.

This lab is independent of REA and npm. Upstream REA-authored code is MIT licensed; its third-party material retains its own licenses. This repository's tool was written independently and does not embed vendor implementation code.
