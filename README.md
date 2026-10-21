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

### Opt in to manifest name checks

Audit callers and the CLI can explicitly require the local package-name syntax:

```python
from npm_tarball_audit import audit

report = audit("example.tgz", strict_package_name=True)
```

```sh
PYTHONPATH=src python3 -m npm_tarball_audit example.tgz --strict-package-name --json
PYTHONPATH=src python3 -m npm_tarball_audit example.tgz --strict-package-name --sarif
```

The default remains `False`, preserving existing audits, including legacy names outside the local syntax. `strict_package_name` must be an actual boolean; other API values raise a fixed `ValueError` before archive access. Strict mode checks the original, untrimmed manifest name with the unchanged `parse_package_name` policy and inclusive 214-character ASCII budget: 1-214 characters total including `@` and `/`, optional exact `@scope/name` with a single slash, lowercase letters, digits, `.`, `_` and `-`, where each scope and name starts with a lowercase letter or digit. For example `example` and `@my-scope/my-name` are accepted when in budget. Invalid nonblank syntax produces the fixed `manifest_name` error finding `package.json name must follow the supported local ASCII package-name syntax` without a member field and exit code `1`; the finding is appended once after `manifest_identity` checks and before `strict_semver` checks. Missing, non-string or blank names retain only the existing `manifest_identity` finding. Expected name/version, `strict_semver`, integrity and inventory options remain literal and independent; invalid syntax may coexist with `identity_mismatch` and `manifest_version`. Plain and JSON reports retain raw package metadata as before; SARIF uses the existing neutral `NTA/manifest_name` rule without raw names or host paths. `--strict-package-name` takes no value and cannot be combined with `--compare`. This is opt-in local syntax enforcement, not complete npm registry-policy/availability validation, package equivalence, provenance, compatibility, security, legal review or a malware verdict.

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
Unchanged inventory does
not establish package equivalence or safety.

## Compare entrypoint declarations

The pure `npm_tarball_audit.entrypoints.compare_entrypoints(before, after)` API compares declared `main`/`bin`/`exports` metadata supplied explicitly by the caller. It reads no files, archives, network, or audit reports and never executes, resolves, or normalizes targets:

```python
from npm_tarball_audit.entrypoints import compare_entrypoints

before = {"main": "index.js", "bin": {"tool": "cli.js"}, "exports": {".": "./index.js"}}
after = {"main": "index.js", "bin": {"tool": "cli.js"}, "exports": {".": "./esm.js"}}
result = compare_entrypoints(before, after)
assert result == {
    "added": [],
    "removed": [],
    "changed": [{"field": "exports", "before": {".": "./index.js"}, "after": {".": "./esm.js"}}],
    "unchanged_count": 2,
}
```

Only the literal fields `main`, `bin`, and `exports` participate; other metadata is ignored and never copied. Absence differs from explicit `None`. Both arguments may be positional or named and no other options exist. Results use exactly `added`, `removed`, `changed`, and `unchanged_count`, with arrays ordered by field `main`, `bin`, `exports`. `added`/`removed` items contain exactly `field` and `value`; `changed` items contain exactly `field`, `before`, and `after`. `unchanged_count` counts selected fields present on both sides with equal declarations. Every output container is newly allocated and shares no mutable container with inputs or other occurrences.

Input limits (inclusive, checked before any comparison): each side is an exact built-in `dict` with at most 128 fields; every top-level key is an exact `str` of at most 1024 code points with no surrogates. Selected `main`/`bin`/`exports` values are bounded JSON-compatible trees using exact `dict`, `list`, `str`, `int`, `float`, `bool`, or `None`; dict keys are exact `str`. Integers must be within `-(2**53-1)..2**53-1`; floats must be finite. Every nested string and dict key is at most 1024 code points with no surrogates; control characters and non-ASCII text are retained as metadata. Per side, selected values together contain at most 4096 value nodes (each container and primitive counts one; dict keys do not count), selected containers have maximum depth 16 with a selected root container at depth 1, and the sum of string-value and nested-key lengths is at most 16384 code points (top-level field names excluded). Cycles, subclasses, unsupported types, non-finite numbers, or budget excess raise `ValueError("Invalid entrypoint metadata")` without echoing input.

Order and equality semantics: `main`/`bin` dicts are compared ignoring key order recursively and are output with lexicographically sorted keys (ordinary Python Unicode order); every object under `exports` is order-sensitive and output preserves its original insertion order. Lists are order-sensitive for all fields. Scalar types are significant, including `bool` versus `int` and `int` versus `float`; equal finite floats compare by numeric equality so `0.0` and `-0.0` are unchanged. No trimming, path normalization, wildcard expansion, browser remapping, or package-name inference is performed.

This is declarative metadata comparison only. It does not read or execute packages, resolve targets, check target existence, or conclude compatibility, provenance, security, or safety. It adds no CLI flags and changes no audit-report schema.

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


<!-- community-core:browser-remap-scan -->
### Offline browser remap enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared browser replacements and file shims from published package metadata without executing code, resolving modules or reading archives. It makes browser-field review reproducible and comparable across tarballs, surfaces ignored files for manual follow-up, and complements existing inventory hash comparison and main/bin/exports checks which cover file bytes and entrypoints only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/browser_remap_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, resolution or normalization. Input payload must be a dict with required key browser (None, str or dict) and optional positive-int budgets max_entries=200, max_length=4096 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid browser scan payload or budget without echoing input. Strings include str subclasses without coercion; every dict key and str value length <=max_length code points inclusive, dict keys must be str, dict values must be str or False (True rejected) else same fixed error. Iteration covers at most max_entries dict entries without mutating input; None gives kind absent, str gives kind replacement, dict gives kind remap including empty dict. Classification preserves spelling, case and order before sorting: remap entries with False value are ignored, entries with str value are remapped; replacement strings are returned verbatim. Returns a fresh dict with exactly kind, replacement, ignored, remapped, entry_count; kind is absent, replacement or remap, replacement is str or None, ignored is sorted code-point str list, remapped is sorted by from code-point list of fresh from/to dicts, entry_count is 0 for absent, 1 for replacement, len for remap. Inputs are never mutated and outputs share no references. This is syntax enumeration only, not Node resolution, browser-remap execution, provenance, safety, security, compatibility or legal review; entries are reported as declared patterns.

Examples (JSON input and expected output):

```json
{
  "input": {
    "browser": null
  },
  "output": {
    "entry_count": 0,
    "ignored": [],
    "kind": "absent",
    "remapped": [],
    "replacement": null
  }
}
```

```json
{
  "input": {
    "browser": "./browser.js"
  },
  "output": {
    "entry_count": 1,
    "ignored": [],
    "kind": "replacement",
    "remapped": [],
    "replacement": "./browser.js"
  }
}
```

```json
{
  "input": {
    "browser": {
      "./server.js": false,
      "fs": "./shim.js"
    }
  },
  "output": {
    "entry_count": 2,
    "ignored": [
      "./server.js"
    ],
    "kind": "remap",
    "remapped": [
      {
        "from": "fs",
        "to": "./shim.js"
      }
    ],
    "replacement": null
  }
}
```

Public regression tests: `tests/test_community_browser_remap_scan.py`.


<!-- community-core:license-identifier-scan -->
### Offline license identifier syntax checker for reproducible audits

Gives REA Lab reviewers a fast offline way to validate published package.json license strings before manual follow-up, making license-metadata review reproducible and comparable across tarballs without executing code, resolving modules, reading archives or using network. It surfaces malformed characters, lengths and shapes for manual SPDX and legal review and complements existing inventory hash comparison, name and semver syntax checks and main/bin/exports checks which cover file bytes, identity and entrypoints only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/license_identifier_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, resolution or normalization. Input payload must be a dict with required key license (None or str) and optional max_length=64 (positive int excluding bool); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid license scan payload or budget without echoing input. Str includes subclasses without coercion; code-point length must be within 1..max_length inclusive with length checked before parsing, else returns valid false for empty or over-length strings and same fixed error for budget misuse with no trimming or repair. None means absent; str must match local token syntax: ASCII letters and digits with interior '.'/'-'/' +' only, starting with letter or digit, no leading or trailing dot, hyphen or plus, no spaces, slashes, colons, Unicode, or expanded phrases; e.g. MIT, ISC and Apache-2.0 are valid when in budget. Returns fresh dict with exactly valid bool, kind absent/string, identifier None/verbatim string; absent gives valid false kind absent identifier None; valid syntax gives valid true kind string identifier verbatim input; any other string gives valid false kind string identifier None. Inputs never mutated and outputs share no references with fresh containers each call. Uses only math/re/json/unicodedata with plain functions and immutable literal constants and local mutables. Syntax check only, not SPDX validation, registry lookup, provenance, safety, security, compatibility or legal review.

Examples (JSON input and expected output):

```json
{
  "input": {
    "license": "MIT"
  },
  "output": {
    "identifier": "MIT",
    "kind": "string",
    "valid": true
  }
}
```

```json
{
  "input": {
    "license": "Apache-2.0"
  },
  "output": {
    "identifier": "Apache-2.0",
    "kind": "string",
    "valid": true
  }
}
```

```json
{
  "input": {
    "license": null
  },
  "output": {
    "identifier": null,
    "kind": "absent",
    "valid": false
  }
}
```

Public regression tests: `tests/test_community_license_identifier_scan.py`.


<!-- community-core:integrity-token-scan -->
### Offline SRI token syntax checker for reproducible audits

Gives REA Lab reviewers a fast offline way to validate expected sha512 SRI tokens obtained from a trusted source before running tarball audits, making integrity review reproducible and comparable across published artifacts without executing code, reading archives, resolving modules or using network. It surfaces malformed prefixes, alphabets, lengths and budgets for manual follow-up and complements existing inventory hash comparison, name and semver syntax checks and main bin exports checks which cover file bytes, identity and entrypoints only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/integrity_token_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, resolution or normalization. Input payload must be a dict with required key integrity set to None or str and optional positive-int budget max_length with default 128 where bools are rejected; any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid integrity scan payload or budget without echoing input. Strings include str subclasses without coercion; code-point length is checked before parsing and must be within 1 to max_length inclusive, else empty or over-length strings return valid false without error, with no trimming or repair. None denotes absent. A string is valid only when it equals prefix sha512- followed by exactly 88 base64 characters where the first 86 are ASCII letters digits plus and slash and the final two are equals equals, for a total of 95 characters; other algorithms, spaces, missing prefix or padding, wrong length, wrong alphabet or Unicode are invalid. Returns a fresh dict with exactly valid, kind, token; absent gives valid false kind absent token None; valid syntax gives valid true kind string token verbatim input; any other string gives valid false kind string token None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math re json unicodedata with plain functions and immutable literal constants and local mutable containers. This is syntax check only, not digest verification, registry lookup, provenance, safety, security, compatibility or legal review; tokens are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "integrity": "sha512-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/ABCDEFGHIJKLMNOPQRSTUV=="
  },
  "output": {
    "kind": "string",
    "token": "sha512-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/ABCDEFGHIJKLMNOPQRSTUV==",
    "valid": true
  }
}
```

```json
{
  "input": {
    "integrity": "sha384-abc"
  },
  "output": {
    "kind": "string",
    "token": null,
    "valid": false
  }
}
```

```json
{
  "input": {
    "integrity": null
  },
  "output": {
    "kind": "absent",
    "token": null,
    "valid": false
  }
}
```

Public regression tests: `tests/test_community_integrity_token_scan.py`.


<!-- community-core:dependency-declaration-scan -->
### Offline dependency declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared runtime dependencies from published package.json metadata without executing code, installing packages, reading archives, resolving modules or using network. It makes dependency review reproducible and comparable across tarballs, surfaces declared names and specifiers for manual follow-up, and complements existing inventory hash comparison, name and semver syntax checks, main/bin/exports checks, license and integrity syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/dependency_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, resolution or normalization. Input payload must be a dict with required key dependencies and optional positive-int budgets max_entries=128 and max_length=1024 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid dependency scan payload or budget without echoing input. dependencies must be None or dict; None denotes absent. Strings include str subclasses without coercion; every dict key and every dict value must be str with code-point length 1..max_length inclusive, else same fixed error, with no trimming, normalization, name validation, range evaluation or repair. If dict size exceeds max_entries same fixed error. Returns fresh dict with exactly dependencies and count; dependencies is code-point sorted by name list of fresh name/spec dicts preserving verbatim spelling, case and specifier text, count is len. None gives empty list and zero count. Inputs never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math/re/json/unicodedata with plain functions and immutable literal constants and local mutable containers. Declaration enumeration only, not resolution, installation, provenance, safety, security, compatibility or legal review; entries reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "dependencies": {
      "lodash": "^4.17.21",
      "react": "18.2.0"
    }
  },
  "output": {
    "count": 2,
    "dependencies": [
      {
        "name": "lodash",
        "spec": "^4.17.21"
      },
      {
        "name": "react",
        "spec": "18.2.0"
      }
    ]
  }
}
```

```json
{
  "input": {
    "dependencies": null
  },
  "output": {
    "count": 0,
    "dependencies": []
  }
}
```

```json
{
  "input": {
    "dependencies": {
      "left-pad": "1.3.0"
    }
  },
  "output": {
    "count": 1,
    "dependencies": [
      {
        "name": "left-pad",
        "spec": "1.3.0"
      }
    ]
  }
}
```

Public regression tests: `tests/test_community_dependency_declaration_scan.py`.


<!-- community-core:files-allowlist-scan -->
### Offline files allowlist enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared files allowlist entries from published package.json metadata without executing code, installing packages, reading archives, resolving globs or using network. It makes packing intent reproducible and comparable across tarballs, surfaces declared include patterns for manual follow-up against actual inventory hashes, and complements existing inventory hash comparison, name and semver syntax checks, main/bin/exports checks, and license, integrity, browser and dependency syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/files_allowlist_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, resolution, glob evaluation or normalization. Input payload must be a dict with required key files and optional positive-int budgets max_entries=128 and max_length=1024 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid files scan payload or budget without echoing input. files must be None or list; None denotes absent. Strings include str subclasses without coercion; every list element must be str with code-point length 1..max_length inclusive, else same fixed error, with no trimming, normalization, pattern validation, glob evaluation or repair. If list size exceeds max_entries same fixed error. Returns fresh dict with exactly files and count; files is code-point sorted list preserving verbatim spelling, case and pattern text including duplicates in sorted order, count is len. None gives empty list and zero count. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math/re/json/unicodedata with plain functions and immutable literal module constants with local mutable containers. This is declaration enumeration only, not execution, resolution, packing enforcement, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "files": [
      "dist/",
      "README.md"
    ]
  },
  "output": {
    "count": 2,
    "files": [
      "README.md",
      "dist/"
    ]
  }
}
```

```json
{
  "input": {
    "files": null
  },
  "output": {
    "count": 0,
    "files": []
  }
}
```

```json
{
  "input": {
    "files": [
      "lib/index.js"
    ],
    "max_entries": 128,
    "max_length": 1024
  },
  "output": {
    "count": 1,
    "files": [
      "lib/index.js"
    ]
  }
}
```

Public regression tests: `tests/test_community_files_allowlist_scan.py`.


<!-- community-core:platform-declaration-scan -->
### Offline os/cpu declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared os and cpu constraints from published package.json metadata without executing code, installing packages, reading archives, resolving platforms or using network. It makes platform intent reproducible and comparable across tarballs, surfaces exact allow and negate tokens for manual follow-up against inventory hashes, and complements existing inventory hash comparison, name and semver syntax checks, main/bin/exports checks, and license, integrity, browser, dependency and files syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/platform_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, platform resolution or installation. Input payload must be a dict with required keys os and cpu and optional positive-int budgets max_entries=32 and max_length=64 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid platform scan payload or budget without echoing input. os and cpu must each be None or list; None denotes absent. Strings include str subclasses without coercion; every list element must be str with code-point length 1..max_length inclusive, else same fixed error, with no trimming, case change, negation evaluation, platform resolution or repair. If either list size exceeds max_entries same fixed error. Returns fresh dict with exactly os, cpu and count; os and cpu are code-point sorted lists of fresh verbatim strings preserving spelling, case and duplicates including leading-bang tokens, None gives empty list, count is len os plus len cpu. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math/re/json/unicodedata with plain functions and immutable literal module constants with local mutable containers. This is declaration enumeration only, not execution, resolution, installation, compatibility assessment, provenance, safety, security or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "cpu": [
      "x64"
    ],
    "os": [
      "linux",
      "darwin"
    ]
  },
  "output": {
    "count": 3,
    "cpu": [
      "x64"
    ],
    "os": [
      "darwin",
      "linux"
    ]
  }
}
```

```json
{
  "input": {
    "cpu": [
      "arm64",
      "!x32"
    ],
    "os": null
  },
  "output": {
    "count": 2,
    "cpu": [
      "!x32",
      "arm64"
    ],
    "os": []
  }
}
```

Public regression tests: `tests/test_community_platform_declaration_scan.py`.
