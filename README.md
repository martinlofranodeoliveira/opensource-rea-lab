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


<!-- community-core:repository-declaration-scan -->
### Offline repository declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared repository references from published package.json metadata without executing code, installing packages, reading archives, fetching URLs or using network. It makes source-link intent reproducible and comparable across tarballs, surfaces exact type, URL and directory strings for manual follow-up against inventory hashes, and complements existing inventory hash comparison, name and semver syntax checks, main/bin/exports checks, and license, integrity, browser, dependency, files, platform and engines syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/repository_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, URL fetching or validation. Input payload must be a dict with required key repository and optional positive-int budget max_length=512 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid repository scan payload or budget without echoing input. repository must be None or str or dict; None denotes absent. Strings include str subclasses without coercion; every examined string must have code-point length 1..max_length inclusive with no trimming, normalization, URL validation, fetching or repair, else same fixed error. A str entry denotes a repository reference verbatim. A dict entry must contain required url str in budget and optional type and directory str in budget with no other keys; missing url, extra key or bad value raises same fixed error. Returns fresh dict with exactly repository and count; None gives repository None and count 0, otherwise repository is fresh dict with exactly type, url and directory preserving verbatim spelling and case with absent optionals as None and count 1. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers. This is declaration enumeration only, not execution, resolution, installation, fetching, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "repository": null
  },
  "output": {
    "count": 0,
    "repository": null
  }
}
```

```json
{
  "input": {
    "repository": "github:user/repo"
  },
  "output": {
    "count": 1,
    "repository": {
      "directory": null,
      "type": null,
      "url": "github:user/repo"
    }
  }
}
```

```json
{
  "input": {
    "repository": {
      "type": "git",
      "url": "https://github.com/user/repo.git"
    }
  },
  "output": {
    "count": 1,
    "repository": {
      "directory": null,
      "type": "git",
      "url": "https://github.com/user/repo.git"
    }
  }
}
```

Public regression tests: `tests/test_community_repository_declaration_scan.py`.


<!-- community-core:scripts-declaration-scan -->
### Offline scripts declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared scripts commands from published package.json metadata without executing code, installing packages, reading archives, running lifecycle hooks or using network. It makes install/test intent reproducible and comparable across tarballs, surfaces exact script names and command strings for manual follow-up against inventory hashes, and complements existing inventory hash comparison, name and semver syntax checks, main/bin/exports checks, and license, integrity, browser, dependency, files, platform and repository syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/scripts_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or hook execution. Input payload must be a dict with required key scripts and optional positive-int budgets max_entries=32 and max_length=1024 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid scripts scan payload or budget without echoing input. scripts must be None or dict; None denotes absent. Strings include str subclasses without coercion; every dict key and value must be str with code-point length 1..max_length inclusive, else same fixed error, with no trimming, case change, normalization, execution, resolution or repair. If dict size exceeds max_entries same fixed error. Returns fresh dict with exactly scripts and count; scripts is code-point sorted by name list of fresh name and command dicts preserving verbatim spelling, case and whitespace, None gives empty list, count is len of scripts list. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math/re/json/unicodedata with plain functions and immutable literal module constants with local mutable containers. This is declaration enumeration only, not execution, installation, resolution, compatibility assessment, provenance, safety, security or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "scripts": {
      "prepare": "husky install",
      "test": "node test.js"
    }
  },
  "output": {
    "count": 2,
    "scripts": [
      {
        "command": "husky install",
        "name": "prepare"
      },
      {
        "command": "node test.js",
        "name": "test"
      }
    ]
  }
}
```

```json
{
  "input": {
    "scripts": null
  },
  "output": {
    "count": 0,
    "scripts": []
  }
}
```

```json
{
  "input": {
    "max_entries": 32,
    "max_length": 1024,
    "scripts": {
      "start": "node server.js"
    }
  },
  "output": {
    "count": 1,
    "scripts": [
      {
        "command": "node server.js",
        "name": "start"
      }
    ]
  }
}
```

Public regression tests: `tests/test_community_scripts_declaration_scan.py`.


<!-- community-core:author-contributors-scan -->
### Offline author and contributors declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared author and contributors persons from published package.json metadata without executing code, installing packages, reading archives, contacting addresses or using network. It makes authorship intent reproducible and comparable across tarballs, surfaces exact name, email and url strings for manual follow-up against inventory hashes, and complements existing inventory hash comparison, name and semver syntax checks, main/bin/exports checks, and license, integrity, browser, dependency, files, platform, repository and scripts syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/author_contributors_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or hook execution. Input payload must be a dict with required keys author and contributors and optional positive-int budgets max_entries=32 and max_length=512 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid author scan payload or budget without echoing input. author must be None or str or dict; None denotes absent. contributors must be None or list; None or empty list denotes absent. Strings include str subclasses without coercion; every examined string must have code-point length 1..max_length inclusive with no trimming, case change, normalization, fetching, validation or repair, else same fixed error. A str person denotes a verbatim name with absent email and url. A dict person must contain required name str in budget and may contain optional email str in budget and optional url str in budget with no other keys; missing name, extra key or bad value raises same fixed error. A contributors list must contain only str or dict items under the same per-item rules with no nesting beyond one level; if list size exceeds max_entries same fixed error. Returns fresh dict with exactly persons and count; persons is list of fresh dicts with exactly name, email, url and source preserving verbatim spelling, case and whitespace with absent email or url as None and source as author or contributors, code-point sorted by source then name then email then url with None as empty string, None or empty inputs give empty list, count is len of persons list. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math/re/json/unicodedata with plain functions and immutable literal module constants with local mutable containers. This is declaration enumeration only, not execution, installation, resolution, fetching, contact, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "author": "Jane Doe",
    "contributors": null
  },
  "output": {
    "count": 1,
    "persons": [
      {
        "email": null,
        "name": "Jane Doe",
        "source": "author",
        "url": null
      }
    ]
  }
}
```

```json
{
  "input": {
    "author": {
      "email": "jane@example.com",
      "name": "Jane Doe"
    },
    "contributors": [
      {
        "name": "John Smith",
        "url": "https://example.com/john"
      }
    ]
  },
  "output": {
    "count": 2,
    "persons": [
      {
        "email": "jane@example.com",
        "name": "Jane Doe",
        "source": "author",
        "url": null
      },
      {
        "email": null,
        "name": "John Smith",
        "source": "contributors",
        "url": "https://example.com/john"
      }
    ]
  }
}
```

```json
{
  "input": {
    "author": null,
    "contributors": []
  },
  "output": {
    "count": 0,
    "persons": []
  }
}
```

Public regression tests: `tests/test_community_author_contributors_scan.py`.


<!-- community-core:engines-declaration-scan -->
### Offline engines declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared runtime engines from published package.json metadata without executing code, installing packages, reading archives or using network. It makes engine intent reproducible and comparable across tarballs, surfaces exact engine names and range strings for manual follow-up against inventory hashes, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, dependency, files, integrity, license, platform, repository and scripts syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/engines_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or resolution. Input payload must be a dict with required key engines and optional positive-int budgets max_entries=16 and max_length=256 with bools rejected; any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid engines scan payload or budget without echoing input. engines must be None or dict; None or empty dict denotes absent. Keys and values include str subclasses without coercion; every name and range must be str with code-point length 1 to max_length inclusive with no trimming, case change, normalization, range evaluation or repair, else same fixed error. If dict size exceeds max_entries same fixed error. Returns fresh dict with exactly engines and count; engines is code-point sorted list by name then range of fresh dicts with exactly name and range preserving verbatim spelling, case and whitespace, None or empty dict gives empty list, count is len of engines list. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers. This is declaration enumeration only, not execution, installation, resolution, range satisfaction, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "engines": {
      "node": ">=18",
      "npm": ">=9"
    }
  },
  "output": {
    "count": 2,
    "engines": [
      {
        "name": "node",
        "range": ">=18"
      },
      {
        "name": "npm",
        "range": ">=9"
      }
    ]
  }
}
```

```json
{
  "input": {
    "engines": null
  },
  "output": {
    "count": 0,
    "engines": []
  }
}
```

```json
{
  "input": {
    "engines": {},
    "max_entries": 16,
    "max_length": 256
  },
  "output": {
    "count": 0,
    "engines": []
  }
}
```

Public regression tests: `tests/test_community_engines_declaration_scan.py`.


<!-- community-core:type-declaration-scan -->
### Offline package type declaration checker for reproducible audits

Gives REA Lab reviewers a fast offline way to surface the declared package type from published package.json metadata without executing code, installing packages, reading archives or using network. It makes module-system intent reproducible and comparable across tarballs, surfaces exact commonjs or module strings for manual follow-up against inventory hashes and entrypoint targets, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, dependency, engines, files, integrity, license, platform, repository and scripts syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/type_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or resolution. Input payload must be a dict with required key type and optional positive-int budget max_length=32 with bools rejected; any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid type scan payload or budget without echoing input. type must be None or str; None denotes absent. Str values include str subclasses without coercion; every examined string must have code-point length 1 to max_length inclusive with no trimming, case change, normalization or repair and must equal exactly commonjs or module case-sensitively, else same fixed error. Returns fresh dict with exactly type and declared; type is None when absent else fresh verbatim string, declared is True when present else False. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers. This is declaration enumeration only, not execution, installation, resolution, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "type": "module"
  },
  "output": {
    "declared": true,
    "type": "module"
  }
}
```

```json
{
  "input": {
    "type": null
  },
  "output": {
    "declared": false,
    "type": null
  }
}
```

```json
{
  "input": {
    "max_length": 32,
    "type": "commonjs"
  },
  "output": {
    "declared": true,
    "type": "commonjs"
  }
}
```

Public regression tests: `tests/test_community_type_declaration_scan.py`.


<!-- community-core:description-declaration-scan -->
### Offline description declaration checker for reproducible audits

Gives REA Lab reviewers a fast offline way to surface the declared package description from published package.json metadata without executing code, installing packages, reading archives or using network. It makes short intent statements reproducible and comparable across tarballs, surfaces exact description text for manual follow-up against inventory hashes, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, dependency, engines, files, integrity, license, platform, repository, scripts and type syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/description_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or resolution. Input payload must be a dict with required key description and optional positive-int budget max_length=512 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid description scan payload or budget without echoing input. description must be None or str; None denotes absent. Str values include str subclasses without coercion; every examined string must have code-point length 1..max_length inclusive with no trimming, case change, normalization, validation or repair, else same fixed error. Returns fresh dict with exactly description and declared; description is None when absent else fresh verbatim string preserving spelling, case and whitespace, declared is True when present else False. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers. This is declaration enumeration only, not execution, installation, resolution, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "description": "Small audit helper"
  },
  "output": {
    "declared": true,
    "description": "Small audit helper"
  }
}
```

```json
{
  "input": {
    "description": null
  },
  "output": {
    "declared": false,
    "description": null
  }
}
```

```json
{
  "input": {
    "description": "Hi",
    "max_length": 4
  },
  "output": {
    "declared": true,
    "description": "Hi"
  }
}
```

Public regression tests: `tests/test_community_description_declaration_scan.py`.


<!-- community-core:homepage-declaration-scan -->
### Offline homepage declaration checker for reproducible audits

Gives REA Lab reviewers a fast offline way to surface the declared homepage string from published package.json metadata without executing code, installing packages, reading archives or using network. It makes project-link intent reproducible and comparable across tarballs, surfaces exact homepage text for manual follow-up against inventory hashes and repository/description declarations, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, dependency, engines, files, integrity, license, platform, repository, scripts and type syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/homepage_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or resolution. Input payload must be a dict with required key homepage and optional positive-int budget max_length=512 with bools rejected; any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid homepage scan payload or budget without echoing input. homepage must be None or str; None denotes absent. Str values include str subclasses without coercion; every examined string must have code-point length 1 to max_length inclusive with no trimming, case change, normalization, fetching, validation or repair, else same fixed error. Returns fresh dict with exactly homepage and declared; homepage is None when absent else fresh verbatim string preserving spelling, case and whitespace, declared is True when present else False. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers. This is declaration enumeration only, not execution, installation, resolution, fetching, ranking, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "homepage": "https://example.com/project"
  },
  "output": {
    "declared": true,
    "homepage": "https://example.com/project"
  }
}
```

```json
{
  "input": {
    "homepage": null
  },
  "output": {
    "declared": false,
    "homepage": null
  }
}
```

```json
{
  "input": {
    "homepage": "https://example.com/docs",
    "max_length": 512
  },
  "output": {
    "declared": true,
    "homepage": "https://example.com/docs"
  }
}
```

Public regression tests: `tests/test_community_homepage_declaration_scan.py`.


<!-- community-core:funding-declaration-scan -->
### Offline funding declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared funding support pointers from published package.json metadata without executing code, installing packages, reading archives or using network. It makes sponsorship-contact intent reproducible and comparable across tarballs, surfaces exact type and url strings for manual follow-up against inventory hashes, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, engines, files, homepage, integrity, keywords, license, platform, repository, scripts and type syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/funding_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or hook execution. Input payload must be a dict with required key funding and optional positive-int budgets max_entries=16 and max_length=512 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid funding scan payload or budget without echoing input. funding must be None or str or dict or list; None denotes absent. Str values include str subclasses without coercion and denote shorthand url with type absent. Dict values denote single entry with 1 to 2 keys drawn only from type and url with at least one present. List values denote array with 1..max_entries entries each str or dict as above; empty list denotes absent. Every examined string must have code-point length 1..max_length inclusive with no trimming, case change, normalization, fetching, validation or repair, else same fixed error. List size exceeding max_entries raises same fixed error. Returns fresh dict with exactly entries and count; entries is list of fresh dicts each with exactly type and url where absent maps to None and present maps to fresh verbatim string preserving spelling, case and whitespace, in input order for single or array form with shorthand str mapping to type None, count is len of entries list, None or empty list gives empty list and zero. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, ranking, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "funding": null
  },
  "output": {
    "count": 0,
    "entries": []
  }
}
```

```json
{
  "input": {
    "funding": "https://example.com/sponsor"
  },
  "output": {
    "count": 1,
    "entries": [
      {
        "type": null,
        "url": "https://example.com/sponsor"
      }
    ]
  }
}
```

```json
{
  "input": {
    "funding": [
      {
        "type": "github",
        "url": "https://example.com/fund"
      },
      {
        "url": "https://example.com/other"
      }
    ]
  },
  "output": {
    "count": 2,
    "entries": [
      {
        "type": "github",
        "url": "https://example.com/fund"
      },
      {
        "type": null,
        "url": "https://example.com/other"
      }
    ]
  }
}
```

Public regression tests: `tests/test_community_funding_declaration_scan.py`.


<!-- community-core:keywords-declaration-scan -->
### Offline keywords declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to list declared keywords from published package.json metadata without executing code, installing packages, reading archives or using network. It makes discovery intent reproducible and comparable across tarballs, surfaces exact keyword strings for manual follow-up against inventory hashes and description homepage and repository declarations, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, dependency, description, engines, files, funding, homepage, integrity, license, platform, repository, scripts and type syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/keywords_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or resolution. Input payload must be a dict with required key keywords and optional positive-int budgets max_entries=64 and max_length=256 with bools rejected; any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid keywords scan payload or budget without echoing input. keywords must be None or list; None denotes absent. List values denote keyword array with 0 to max_entries str entries; empty list denotes absent. Str values include str subclasses without coercion. Every examined string must have code-point length 1 to max_length inclusive with no trimming, case change, normalization, fetching, validation or repair, else same fixed error. List size exceeding max_entries raises same fixed error. Returns fresh dict with exactly keywords, count and declared; keywords is list of fresh verbatim strings preserving spelling, case and whitespace in input order, empty when absent, count is len of keywords list, declared is True when non-empty list present else False. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, ranking, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "keywords": null
  },
  "output": {
    "count": 0,
    "declared": false,
    "keywords": []
  }
}
```

```json
{
  "input": {
    "keywords": [
      "audit",
      "reproducible"
    ]
  },
  "output": {
    "count": 2,
    "declared": true,
    "keywords": [
      "audit",
      "reproducible"
    ]
  }
}
```

```json
{
  "input": {
    "keywords": [
      "  Search  ",
      "Node.js"
    ],
    "max_entries": 64,
    "max_length": 256
  },
  "output": {
    "count": 2,
    "declared": true,
    "keywords": [
      "  Search  ",
      "Node.js"
    ]
  }
}
```

Public regression tests: `tests/test_community_keywords_declaration_scan.py`.


<!-- community-core:bugs-declaration-scan -->
### Offline bugs declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared bugs tracker and contact pointers from published package.json metadata without executing code, installing packages, reading archives or using network. It makes issue-report intent reproducible and comparable across tarballs, surfaces exact url and email strings for manual follow-up against inventory hashes, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, dependency, description, engines, files, funding, homepage, integrity, keywords, license, platform, repository, scripts and type syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/bugs_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or hook execution. Input payload must be a dict with required key bugs and optional positive-int budget max_length=512 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid bugs scan payload or budget without echoing input. bugs must be None or str or dict; None denotes absent. Str values include str subclasses without coercion and denote shorthand url with email absent. Dict values denote object with 1 to 2 keys drawn only from url and email with at least one present; empty dict or unknown keys raise same fixed error. Every examined string must have code-point length 1..max_length inclusive with no trimming, case change, normalization, fetching, validation or repair, else same fixed error. Returns fresh dict with exactly url, email and declared; url maps to fresh verbatim url string or None when absent, email maps to fresh verbatim email string or None when absent, declared is True when str or valid dict present else False when None, preserving spelling, case and whitespace. Shorthand str maps to url set and email None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, ranking, provenance, safety, security, compatibility or legal review; entries are reported as declared strings.

Examples (JSON input and expected output):

```json
{
  "input": {
    "bugs": null
  },
  "output": {
    "declared": false,
    "email": null,
    "url": null
  }
}
```

```json
{
  "input": {
    "bugs": "https://example.com/issues"
  },
  "output": {
    "declared": true,
    "email": null,
    "url": "https://example.com/issues"
  }
}
```

```json
{
  "input": {
    "bugs": {
      "email": "bugs@example.com",
      "url": "https://example.com/issues"
    }
  },
  "output": {
    "declared": true,
    "email": "bugs@example.com",
    "url": "https://example.com/issues"
  }
}
```

Public regression tests: `tests/test_community_bugs_declaration_scan.py`.


<!-- community-core:sideeffects-declaration-scan -->
### Offline sideEffects declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared sideEffects intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes bundler-relevant flags and path patterns reproducible and comparable across tarballs, surfaces exact verbatim booleans and patterns for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, engines, files, funding, homepage, integrity, keywords, license, platform, repository, scripts and type syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/sideeffects_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or resolution. Input payload must be a dict with required key sideEffects and optional positive-int budgets max_entries=32 and max_length=512 (bools rejected); any missing key, extra key, wrong type or non-positive budget raises ValueError with fixed text Invalid sideEffects scan payload or budget without echoing input. sideEffects must be None or exact bool where type(value) is bool or str or list; None denotes absent, bool denotes flag, str denotes single pattern, list denotes pattern list; integers including 0 and 1, dicts or other types raise same fixed error. Str form must be str including str subclasses without coercion with code-point length 1 to max_length inclusive with no trimming, case change, normalization, fetching, validation or repair else same fixed error. List form must contain 0 to max_entries items; each item must be str including str subclasses without coercion with code-point length 1 to max_length inclusive with same verbatim handling else same fixed error. Exact bools need no length check. Returns fresh dict with exactly flag, entries and declared; flag is input bool or None, entries is None for None/bool else fresh list of fresh verbatim strings preserving order spelling case and whitespace with single string input mapped to single-element list, declared is True when bool/str/list present else False when None. Empty list yields entries [] with declared True and flag None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, existence check, glob matching, provenance, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "sideEffects": null
  },
  "output": {
    "declared": false,
    "entries": null,
    "flag": null
  }
}
```

```json
{
  "input": {
    "sideEffects": false
  },
  "output": {
    "declared": true,
    "entries": null,
    "flag": false
  }
}
```

```json
{
  "input": {
    "sideEffects": [
      "./src/*.js",
      "./styles.css"
    ]
  },
  "output": {
    "declared": true,
    "entries": [
      "./src/*.js",
      "./styles.css"
    ],
    "flag": null
  }
}
```

Public regression tests: `tests/test_community_sideeffects_declaration_scan.py`.


<!-- community-core:types-declaration-scan -->
### Offline types declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared TypeScript declaration entry strings from published package.json metadata without executing code, installing packages, reading archives or using network. It makes exact verbatim types and typings strings reproducible and comparable across tarballs, surfaces present versus absent for manual follow-up against inventory hashes and main bin exports checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, engines, files, funding, homepage, integrity, keywords, license, platform, repository, scripts, sideEffects and type syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/types_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, resolution or hook execution. Input payload must be a dict with required keys types and typings and optional positive-int budget max_length=512 (bools rejected); any non-dict payload, missing key, extra key, wrong budget type or non-positive budget raises ValueError with fixed text Invalid types scan payload or budget without echoing input. types and typings must each be None or str including str subclasses without coercion; None denotes absent, str denotes present declaration; integers including 0 and 1, bools, lists, dicts or other types raise the same fixed error. No trimming, coercion, fetching, validation, normalization or repair is performed. Each present string must have code-point length 1 to max_length inclusive with spelling, case and whitespace preserved verbatim else the same fixed error. Returns a fresh dict with exactly keys types, typings and declared; types is the verbatim string content or None when absent, typings is the verbatim string content or None when absent, declared is True when either string is present else False when both are None. Both None yields types None with typings None and declared False. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This covers plural types and typings declaration strings only, not singular type module flag, and is declaration enumeration only, not execution, installation, resolution, existence check, fetching, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "types": "./dist/index.d.ts",
    "typings": null
  },
  "output": {
    "declared": true,
    "types": "./dist/index.d.ts",
    "typings": null
  }
}
```

```json
{
  "input": {
    "types": null,
    "typings": null
  },
  "output": {
    "declared": false,
    "types": null,
    "typings": null
  }
}
```

```json
{
  "input": {
    "types": null,
    "typings": "./lib/main.d.ts"
  },
  "output": {
    "declared": true,
    "types": null,
    "typings": "./lib/main.d.ts"
  }
}
```

Public regression tests: `tests/test_community_types_declaration_scan.py`.


<!-- community-core:publishconfig-declaration-scan -->
### Offline publishConfig declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared publishConfig intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes exact verbatim registry access tag entries reproducible and comparable across tarballs, surfaces present versus absent for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, engines, files, funding, homepage, integrity, keywords, license, platform, repository, scripts, sideEffects, type and types syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/publishconfig_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or resolution. Input payload must be a dict with required key publishConfig and optional positive-int budgets max_entries=32 and max_length=512 (bools rejected); any non-dict payload, missing key, extra key, wrong budget type or non-positive budget raises ValueError with fixed text Invalid publishConfig scan payload or budget without echoing input. publishConfig must be None or dict; None denotes absent, dict denotes present map; strings, integers including 0 and 1, bools, lists or other types raise the same fixed error with no coercion, trimming, fetching, normalization or repair. Dict form must contain 0 to max_entries entries inclusive; each key and each value must be str including str subclasses without coercion with code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching, validation, existence check or repair else the same fixed error. Returns a fresh dict with exactly entries and declared; entries is None when publishConfig is None else a fresh sorted list of fresh dicts each with exactly key and value; dict input maps to entries sorted ascending by key code points with verbatim key and value; empty dict yields entries [] with declared True; declared is True when dict present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, existence check, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "publishConfig": null
  },
  "output": {
    "declared": false,
    "entries": null
  }
}
```

```json
{
  "input": {
    "publishConfig": {}
  },
  "output": {
    "declared": true,
    "entries": []
  }
}
```

```json
{
  "input": {
    "publishConfig": {
      "access": "public",
      "registry": "https://registry.npmjs.org/"
    }
  },
  "output": {
    "declared": true,
    "entries": [
      {
        "key": "access",
        "value": "public"
      },
      {
        "key": "registry",
        "value": "https://registry.npmjs.org/"
      }
    ]
  }
}
```

Public regression tests: `tests/test_community_publishconfig_declaration_scan.py`.


<!-- community-core:man-declaration-scan -->
### Offline man declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared man-page intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes exact verbatim single-file and array targets reproducible and comparable across tarballs, surfaces present versus absent for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, engines, files, funding, homepage, integrity, keywords, license, platform, publishConfig, repository, scripts, sideEffects, type and types syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/man_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or resolution. Input payload must be a dict with required key man and optional positive-int budgets max_entries=32 and max_length=512 (bools rejected); any non-dict payload, missing key, extra key, wrong budget type or non-positive budget raises ValueError with fixed text Invalid man scan payload or budget without echoing input. man must be None or str including str subclasses without coercion or list; None denotes absent, str denotes single man target, list denotes man target array; integers including 0 and 1, bools, dicts or other types raise the same fixed error. Str form must have code-point length 1 to max_length inclusive with spelling, case and whitespace preserved verbatim else the same fixed error. List form must contain 0 to max_entries entries inclusive; each element must be str including str subclasses without coercion with code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching, validation, existence check or repair; duplicate elements, non-string elements or out-of-budget lengths raise the same fixed error. Returns a fresh dict with exactly entries and declared; entries is None when man is None else a fresh sorted list of verbatim targets sorted ascending by code points; str input maps to single-element list; list input maps to sorted list; empty list yields entries [] with declared True; declared is True when str or list present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, existence check, glob matching, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "man": null
  },
  "output": {
    "declared": false,
    "entries": null
  }
}
```

```json
{
  "input": {
    "man": "man/foo.1"
  },
  "output": {
    "declared": true,
    "entries": [
      "man/foo.1"
    ]
  }
}
```

```json
{
  "input": {
    "man": [
      "man/b.1",
      "man/a.1"
    ]
  },
  "output": {
    "declared": true,
    "entries": [
      "man/a.1",
      "man/b.1"
    ]
  }
}
```

Public regression tests: `tests/test_community_man_declaration_scan.py`.


<!-- community-core:directories-declaration-scan -->
### Offline directories declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared directories layout intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes exact verbatim lib, bin, man, doc, example and test targets reproducible and comparable across tarballs, surfaces present versus absent for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, engines, files, funding, homepage, integrity, keywords, license, man, platform, publishConfig, repository, scripts, sideEffects, type and types syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/directories_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, resolution or hook execution. Input payload must be a dict with required key directories and optional positive-int budgets max_entries=8 and max_length=512 (bools rejected); any non-dict payload, missing key, extra key, wrong budget type or non-positive budget raises ValueError with fixed text Invalid directories scan payload or budget without echoing input. directories must be None or dict; None denotes absent, dict denotes present layout map; strings, integers including 0 and 1, bools, lists or other types raise the same fixed error with no coercion, trimming, fetching, normalization or repair. Dict form must contain 0 to max_entries entries inclusive; each key must be str including str subclasses without coercion exactly one of lib, bin, man, doc, example or test preserved verbatim case-sensitively; each value must be str including str subclasses without coercion with code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching, validation, existence check or repair; unknown keys, non-string keys or values, empty values or out-of-budget counts or lengths raise the same fixed error. Returns a fresh dict with exactly entries and declared; entries is None when directories is None else a fresh sorted list of fresh dicts each with exactly key and value; dict input maps to entries sorted ascending by key code points with verbatim key and value; empty dict yields entries [] with declared True; declared is True when dict present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, existence check, glob matching, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "directories": null
  },
  "output": {
    "declared": false,
    "entries": null
  }
}
```

```json
{
  "input": {
    "directories": {}
  },
  "output": {
    "declared": true,
    "entries": []
  }
}
```

```json
{
  "input": {
    "directories": {
      "doc": "docs",
      "lib": "lib"
    }
  },
  "output": {
    "declared": true,
    "entries": [
      {
        "key": "doc",
        "value": "docs"
      },
      {
        "key": "lib",
        "value": "lib"
      }
    ]
  }
}
```

Public regression tests: `tests/test_community_directories_declaration_scan.py`.


<!-- community-core:packagemanager-declaration-scan -->
### Offline packageManager declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared packageManager intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes exact verbatim manager strings reproducible and comparable across tarballs, surfaces present versus absent for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, directories, engines, files, funding, homepage, integrity, keywords, license, man, platform, publishConfig, repository, scripts, sideEffects, type and types syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/packagemanager_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation or resolution. Input payload must be a dict with required key packageManager and optional positive-int budget max_length=256 (bools rejected, allowed 1 to 4096 inclusive); any non-dict payload, missing key, extra key, wrong budget type or out-of-range budget raises ValueError with fixed text Invalid packageManager scan payload or budget without echoing input. packageManager must be None for absent or str including str subclasses without coercion for present; integers including 0 and 1, bools, lists, dicts or other types raise the same fixed error with no coercion, trimming, fetching, normalization or repair. Str form must have code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching, validation or repair and without C0 control characters except LF CR TAB and without unpaired surrogates; out-of-budget lengths or disallowed characters raise the same fixed error. Returns a fresh dict with exactly declared and value; value is None when packageManager is None else verbatim string content; declared is True when str present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "packageManager": "npm@10.8.2"
  },
  "output": {
    "declared": true,
    "value": "npm@10.8.2"
  }
}
```

```json
{
  "input": {
    "packageManager": null
  },
  "output": {
    "declared": false,
    "value": null
  }
}
```

```json
{
  "input": {
    "max_length": 256,
    "packageManager": "pnpm@9.1.0"
  },
  "output": {
    "declared": true,
    "value": "pnpm@9.1.0"
  }
}
```

Public regression tests: `tests/test_community_packagemanager_declaration_scan.py`.


<!-- community-core:workspaces-declaration-scan -->
### Offline workspaces declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared workspaces intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes exact verbatim workspace patterns reproducible and comparable across tarballs, surfaces present versus absent for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, directories, engines, files, funding, homepage, integrity, keywords, license, man, packageManager, platform, publishConfig, repository, scripts, sideEffects, type and types syntax checks which cover file bytes, identity, entrypoints and token shapes only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/workspaces_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, resolution or hook execution. Input payload must be a dict with required key workspaces and optional positive-int budgets max_entries=32 and max_length=256 (bools rejected, max_entries 1 to 256 inclusive, max_length 1 to 1024 inclusive); any non-dict payload, missing key, extra key, wrong budget type or out-of-range budget raises ValueError with fixed text Invalid workspaces scan payload or budget without echoing input. workspaces must be None for absent or list for present; strings, integers including 0 and 1, bools, dicts or other types raise the same fixed error with no coercion, trimming, fetching, normalization or repair. List form must contain 0 to max_entries items inclusive; each item must be str including str subclasses without coercion with code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching or repair and without C0 control characters except LF CR TAB and without unpaired surrogates; empty strings, wrong types, disallowed characters, out-of-budget counts or lengths raise the same fixed error. Returns a fresh dict with exactly entries and declared; entries is None when workspaces is None else a fresh sorted list by code points of verbatim strings; empty list yields entries [] with declared True; declared is True when list present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, existence check, glob expansion, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "workspaces": null
  },
  "output": {
    "declared": false,
    "entries": null
  }
}
```

```json
{
  "input": {
    "workspaces": [
      "packages/*",
      "apps/web"
    ]
  },
  "output": {
    "declared": true,
    "entries": [
      "apps/web",
      "packages/*"
    ]
  }
}
```

```json
{
  "input": {
    "workspaces": []
  },
  "output": {
    "declared": true,
    "entries": []
  }
}
```

Public regression tests: `tests/test_community_workspaces_declaration_scan.py`.


<!-- community-core:overrides-declaration-scan -->
### Offline npm overrides declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared npm overrides intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes present-versus-absent overrides and exact verbatim spec strings reproducible and comparable across tarballs for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, directories, engines, files, funding, homepage, integrity, keywords, license, man, packageManager, platform, publishConfig, repository, scripts, sideEffects, type, types and workspaces syntax checks which cover file bytes, identity, entrypoints and other declarations only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/overrides_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, resolution or hook execution. Input payload must be a dict with required key overrides and optional positive-int budgets max_entries=32 and max_length=256 (bools rejected, max_entries 1 to 64 inclusive, max_length 1 to 1024 inclusive); any non-dict payload, missing key, extra key, wrong budget type or out-of-range budget raises ValueError with fixed text Invalid overrides scan payload or budget without echoing input. overrides must be None for absent or dict for present; strings, integers including 0 and 1, bools, lists or other types raise the same fixed error with no coercion, trimming, fetching, normalization or repair. Dict form must contain 0 to max_entries keys inclusive; each top key must be str including str subclasses without coercion with code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching or repair and without C0 control characters except LF CR TAB and without unpaired surrogates; each top value must be either such a str version spec with length 1 to max_length under the same character rules preserved verbatim or a nested dict with 1 to max_entries keys inclusive mapping override target to such a str version spec; each nested key follows the same str length and character rules preserved verbatim; empty strings, wrong types, disallowed characters, empty nested dicts, arrays, deeper nesting beyond one level, out-of-budget counts or lengths raise the same fixed error. Returns a fresh dict with exactly declared and entries; entries is None when overrides is None else a fresh sorted list by code points of fresh key and value dicts with verbatim strings, where nested dict values are fresh dicts with code-point-sorted insertion order and verbatim strings; empty dict yields entries [] with declared True; declared is True when dict present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, existence check, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "overrides": null
  },
  "output": {
    "declared": false,
    "entries": null
  }
}
```

```json
{
  "input": {
    "overrides": {
      "lodash": "4.17.21"
    }
  },
  "output": {
    "declared": true,
    "entries": [
      {
        "key": "lodash",
        "value": "4.17.21"
      }
    ]
  }
}
```

```json
{
  "input": {
    "overrides": {
      "aaa": "1.0.0",
      "foo@2": {
        "bar": "3.0.0"
      }
    }
  },
  "output": {
    "declared": true,
    "entries": [
      {
        "key": "aaa",
        "value": "1.0.0"
      },
      {
        "key": "foo@2",
        "value": {
          "bar": "3.0.0"
        }
      }
    ]
  }
}
```

Public regression tests: `tests/test_community_overrides_declaration_scan.py`.


<!-- community-core:bundled-deps-declaration-scan -->
### Offline bundled dependencies declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared bundledDependencies intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes present-versus-absent lists and exact verbatim entry strings reproducible and comparable across tarballs for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, dependency, description, directories, engines, files, funding, homepage, integrity, keywords, license, man, overrides, packageManager, platform, publishConfig, repository, scripts, sideEffects, type, types and workspaces syntax checks which cover file bytes, identity, entrypoints and other declarations only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/bundled_deps_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, resolution or hook execution. Input payload must be a dict with required key bundled and optional positive-int budgets max_entries=64 and max_length=214 (bools rejected, max_entries 1 to 128 inclusive, max_length 1 to 214 inclusive); any non-dict payload, missing key, extra key, wrong budget type or out-of-range budget raises ValueError with fixed text Invalid bundled dependencies scan payload or budget without echoing input. bundled must be None for absent or list for present; strings, integers including 0 and 1, bools, dicts or other types raise the same fixed error with no coercion, trimming, fetching, normalization or repair. List form must contain 0 to max_entries items inclusive; each item must be str including str subclasses without coercion with code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching or repair and without C0 control characters except LF CR TAB and without unpaired surrogates; empty strings, wrong types, disallowed characters, duplicates, out-of-budget counts or lengths raise the same fixed error. Returns a fresh dict with exactly declared and entries; entries is None when bundled is None else a fresh list sorted by code points with verbatim strings; empty list yields entries [] with declared True; declared is True when list present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, existence check, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "bundled": [
      "react",
      "@scope/pkg"
    ]
  },
  "output": {
    "declared": true,
    "entries": [
      "@scope/pkg",
      "react"
    ]
  }
}
```

```json
{
  "input": {
    "bundled": null
  },
  "output": {
    "declared": false,
    "entries": null
  }
}
```

```json
{
  "input": {
    "bundled": []
  },
  "output": {
    "declared": true,
    "entries": []
  }
}
```

Public regression tests: `tests/test_community_bundled_deps_declaration_scan.py`.


<!-- community-core:peer-meta-declaration-scan -->
### Offline peerDependenciesMeta declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared peerDependenciesMeta optional-peer intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes present-versus-absent declarations and exact verbatim optional flags reproducible and comparable across tarballs for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, bundled, dependency, description, directories, engines, files, funding, homepage, integrity, keywords, license, man, overrides, packageManager, platform, publishConfig, repository, scripts, sideEffects, type, types and workspaces syntax checks which cover file bytes, identity, entrypoints and other declarations only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/peer_meta_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, resolution or hook execution. Input payload must be a dict with required key peerDependenciesMeta and optional positive-int budgets max_entries=32 (bools rejected, allowed 1 to 64 inclusive) and max_length=214 (bools rejected, allowed 1 to 214 inclusive); any non-dict payload, missing key, extra key, wrong budget type or out-of-range budget raises ValueError with fixed text Invalid peer metadata scan payload or budget without echoing input. peerDependenciesMeta must be None for absent or dict for present; strings, integers including 0 and 1, bools, lists or other types raise the same fixed error with no coercion, trimming, fetching, normalization or repair. Dict form must contain 0 to max_entries keys inclusive; each key must be str including str subclasses without coercion with code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching or repair; each value must be a dict with 0 to 1 keys inclusive; when present the single key must be exactly optional with value type(value) is bool preserved verbatim; empty inner dict means no flag; strings, lists, None, extra inner keys, wrong types or out-of-budget counts or lengths raise the same fixed error. Returns a fresh dict with exactly declared and entries; entries is None when peerDependenciesMeta is None else a fresh sorted list by code points of fresh name and optional dicts where optional is verbatim bool or None for empty inner dict; empty dict yields entries [] with declared True; declared is True when dict present else False when None. Entries sorted by name code points. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "peerDependenciesMeta": null
  },
  "output": {
    "declared": false,
    "entries": null
  }
}
```

```json
{
  "input": {
    "peerDependenciesMeta": {}
  },
  "output": {
    "declared": true,
    "entries": []
  }
}
```

```json
{
  "input": {
    "peerDependenciesMeta": {
      "lodash": {},
      "react": {
        "optional": true
      }
    }
  },
  "output": {
    "declared": true,
    "entries": [
      {
        "name": "lodash",
        "optional": null
      },
      {
        "name": "react",
        "optional": true
      }
    ]
  }
}
```

Public regression tests: `tests/test_community_peer_meta_declaration_scan.py`.


<!-- community-core:typesversions-declaration-scan -->
### Offline typesVersions declaration enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared TypeScript typesVersions version-redirect intent from published package.json metadata without executing code, installing packages, reading archives or using network. It makes present-versus-absent maps and exact verbatim version selectors, subpath patterns and ordered fallback path lists reproducible and comparable across tarballs for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, bundled, dependency, description, directories, engines, files, funding, homepage, integrity, keywords, license, man, overrides, packageManager, peer meta, platform, publishConfig, repository, scripts, sideEffects, type, types and workspaces syntax checks which cover file bytes, identity, entrypoints and other declarations only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/typesversions_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, resolution or hook execution. Input payload must be a dict with required key typesVersions and optional positive-int budgets max_entries=32 with bools rejected and allowed 1 to 64 inclusive and max_length=256 with bools rejected and allowed 1 to 512 inclusive; any non-dict payload, missing key, extra key, wrong budget type or out-of-range budget raises ValueError with fixed text Invalid typesVersions scan payload or budget without echoing input. typesVersions must be None for absent or dict for present; strings, integers including 0 and 1, bools, floats, lists or other types raise the same fixed error with no coercion, trimming, fetching, normalization, resolution or repair. Dict form must contain 0 to max_entries keys inclusive; each selector key must be str including str subclasses without coercion with code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching, resolution or repair and without C0 control characters except LF CR TAB and without unpaired surrogates; each selector value must be dict with 1 to max_entries pattern keys inclusive; each pattern key must be str including subclasses with code-point length 1 to max_length inclusive with same character and verbatim rules; each pattern value must be list with 1 to max_entries items inclusive each item str including subclasses with code-point length 1 to max_length inclusive with same character and verbatim rules; empty maps, empty lists, empty strings, wrong types, disallowed characters or out-of-budget counts or lengths raise the same fixed error. Returns a fresh dict with exactly declared and entries; entries is None when typesVersions is None else a fresh list sorted by selector code points of fresh selector and mappings pairs where mappings is a fresh list sorted by pattern code points of fresh pattern and targets pairs where targets is a fresh list preserving declared order of fresh verbatim copies; empty dict yields entries empty list with declared True; declared is True when dict present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, type-checking, existence check, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "typesVersions": null
  },
  "output": {
    "declared": false,
    "entries": null
  }
}
```

```json
{
  "input": {
    "typesVersions": {}
  },
  "output": {
    "declared": true,
    "entries": []
  }
}
```

```json
{
  "input": {
    "typesVersions": {
      ">=3.0": {
        "*": [
          "types-3/*",
          "types/*"
        ]
      },
      ">=4.0": {
        "*": [
          "types-4/*"
        ]
      }
    }
  },
  "output": {
    "declared": true,
    "entries": [
      {
        "mappings": [
          {
            "pattern": "*",
            "targets": [
              "types-3/*",
              "types/*"
            ]
          }
        ],
        "selector": ">=3.0"
      },
      {
        "mappings": [
          {
            "pattern": "*",
            "targets": [
              "types-4/*"
            ]
          }
        ],
        "selector": ">=4.0"
      }
    ]
  }
}
```

Public regression tests: `tests/test_community_typesversions_declaration_scan.py`.


<!-- community-core:resolutions-declaration-scan -->
### Offline resolutions pin enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface declared Yarn resolutions version pins from published package.json metadata without executing code, installing packages, reading archives or using network. It makes present-versus-absent maps and exact verbatim selector-to-pin entries reproducible and comparable across tarballs for manual follow-up against inventory hashes and entrypoint checks, and complements existing inventory hash comparison, name and semver syntax checks, main bin exports checks, and author, browser, bugs, bundled, dependency, description, directories, engines, files, funding, homepage, integrity, keywords, license, man, overrides, packageManager, peer meta, platform, publishConfig, repository, scripts, sideEffects, type, types, typesVersions and workspaces syntax checks which cover file bytes, identity, entrypoints and other declarations only, with npm overrides distinct from Yarn resolutions selectors.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/resolutions_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, resolution or hook execution. Input payload must be a dict with required key resolutions and optional positive-int budgets max_entries=64 with bools rejected and allowed 1 to 128 inclusive and max_length=256 with bools rejected and allowed 1 to 512 inclusive; any non-dict payload, missing key, extra key, wrong budget type or out-of-range budget raises ValueError with fixed text Invalid resolutions scan payload or budget without echoing input. resolutions must be None for absent or dict for present; strings, integers including 0 and 1, bools, floats, lists or other types raise the same fixed error with no coercion, trimming, fetching, normalization, resolution or repair. Dict form must contain 0 to max_entries keys inclusive; each selector key must be str including str subclasses without coercion with code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching, resolution or repair and without C0 control characters except LF CR TAB and without unpaired surrogates; each pin value must be str including subclasses with same length and character and verbatim rules; empty strings, wrong types, disallowed characters or out-of-budget counts or lengths raise the same fixed error. Returns a fresh dict with exactly declared and entries; entries is None when resolutions is None else a fresh list sorted by selector code points of fresh selector and pin pairs where pin is a fresh verbatim copy; empty dict yields entries empty list with declared True; declared is True when dict present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, existence check, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "resolutions": null
  },
  "output": {
    "declared": false,
    "entries": null
  }
}
```

```json
{
  "input": {
    "resolutions": {
      "lodash": "4.17.21"
    }
  },
  "output": {
    "declared": true,
    "entries": [
      {
        "pin": "4.17.21",
        "selector": "lodash"
      }
    ]
  }
}
```

```json
{
  "input": {
    "resolutions": {
      "**/lodash": "4.17.21",
      "react": "18.2.0"
    }
  },
  "output": {
    "declared": true,
    "entries": [
      {
        "pin": "4.17.21",
        "selector": "**/lodash"
      },
      {
        "pin": "18.2.0",
        "selector": "react"
      }
    ]
  }
}
```

Public regression tests: `tests/test_community_resolutions_declaration_scan.py`.


<!-- community-core:module-entry-declaration-scan -->
### Offline module entry enumerator for reproducible audits

Gives REA Lab reviewers a fast offline way to surface the declared module ESM entry string from published package.json metadata without executing code, installing packages, reading archives or using network. It makes present-versus-absent entries and exact verbatim values reproducible and comparable across tarballs for manual follow-up against inventory hashes and main/bin/exports checks, and complements existing inventory hash comparison, name and semver syntax checks, main/bin/exports checks, and author, browser, bugs, bundled, dependency, description, directories, engines, files, funding, homepage, integrity, keywords, license, man, overrides, packageManager, peer meta, platform, publishConfig, repository, resolutions, scripts, sideEffects, type, types, typesVersions and workspaces checks which cover file bytes, identity, entrypoints and other declarations only.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/module_entry_declaration_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, resolution or hook execution. Input payload must be a dict with required key module and optional positive-int budget max_length=512 with bools rejected and allowed 1 to 1024 inclusive; any non-dict payload, missing key, extra key, wrong budget type or out-of-range budget raises ValueError with fixed text Invalid module entry scan payload or budget without echoing input. module must be None for absent or str for present; strings include str subclasses without coercion; integers including 0 and 1, bools, floats, lists, dicts or other types raise the same fixed error with no coercion, trimming, fetching, normalization, resolution or repair. Str form must have code-point length 1 to max_length inclusive preserved verbatim with no trimming, case change, normalization, fetching, resolution or repair; empty strings or out-of-budget lengths raise the same fixed error. Returns a fresh dict with exactly declared and value; value is None when module is None else a fresh verbatim plain-str copy; declared is True when str present else False when None. Inputs are never mutated and outputs share no mutable references with fresh containers each call. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults. This is declaration enumeration only, not execution, installation, resolution, fetching, existence check, provenance verification, safety, security, compatibility or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "module": null
  },
  "output": {
    "declared": false,
    "value": null
  }
}
```

```json
{
  "input": {
    "module": "dist/esm/index.js"
  },
  "output": {
    "declared": true,
    "value": "dist/esm/index.js"
  }
}
```

```json
{
  "input": {
    "max_length": 512,
    "module": "lib/module.js"
  },
  "output": {
    "declared": true,
    "value": "lib/module.js"
  }
}
```

Public regression tests: `tests/test_community_module_entry_declaration_scan.py`.


<!-- community-core:inventory-composition-summary -->
### Offline inventory composition summary for reproducible audits

Gives REA Lab reviewers a fast offline way to summarize a published tarball inventory by file extension without reading archives, network, execution or installation. It aggregates validated path, size and hash records into totals and per-extension counts and bytes for triage and reproducible notes. It complements compare_inventories hash diffing, entrypoint verbatim comparison, name and SemVer syntax checks and manifest declaration scans which do not aggregate composition.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/inventory_composition_summary.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, extraction, resolution or hook execution. Input payload must be a dict with required key inventory and optional key max_entries default 20000 and no other keys; any non-dict payload, missing inventory key or extra key raises ValueError with fixed text Invalid inventory summary payload or budget without echoing input. The max_entries budget when present must be an exact int excluding bools in range 1 to 20000 inclusive; floats, bools, strings including subclasses, lists, dicts, None or out-of-range ints raise the same fixed payload error with no coercion, trimming, fetching, normalization, resolution or repair. The inventory value must be a list with length 0 to max_entries inclusive; longer lists raise the same fixed payload error. Each record must be a dict with exactly path, bytes and sha256 and no other keys; missing, extra or non-dict records raise ValueError with fixed text Invalid inventory record without echoing input. The path value must be str including subclasses accepted without coercion as plain str copy; other types raise the same fixed record error. Valid paths start with package/ prefix, length 9 to 256 inclusive, contain only printable ASCII without backslash, contain no empty segment, single dot, double dot, double slash, dot slash or dot dot slash sequences, do not end with slash, and are unique case-sensitively within the list; violations raise the same fixed record error with no normalization or fetching. The bytes value must be an exact int excluding bools in range 0 to 33554432 inclusive; other types or out-of-range values raise the same fixed record error. The sha256 value must be str including subclasses accepted without coercion as plain str copy with exactly 64 ASCII hexadecimal characters; other types, lengths or alphabets raise the same fixed record error, with ASCII case-insensitive validation and no coercion or fetching. No tar parsing, extraction, manifest fetching, range matching or resolution is performed. Aggregation is deterministic over validated records: total_files is list length, total_bytes is exact integer sum, and by_extension groups by lowercased ASCII suffix after the final dot in the basename, using empty string when the basename has no dot or only a leading dot, where basename is the substring after the final slash and lowercasing maps ASCII uppercase to lowercase only. Groups are sorted by extension ASCII code-point order. Returns a fresh dict with exactly total_files, total_bytes and by_extension in fixed order; total_files and total_bytes are ints, by_extension is a fresh sorted list of fresh dicts each with exactly extension, count and bytes in fixed order, where extension is fresh plain str, count is group length and bytes is group byte sum. Inputs are never mutated and outputs share no mutable references with fresh containers each call and deterministic ordering. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults, and API run_feature(payload) preserves input. This is composition enumeration only, not compatibility, provenance verification, safety, security or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "inventory": [
      {
        "bytes": 100,
        "path": "package/index.js",
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      },
      {
        "bytes": 50,
        "path": "package/README.md",
        "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
      }
    ]
  },
  "output": {
    "by_extension": [
      {
        "bytes": 100,
        "count": 1,
        "extension": "js"
      },
      {
        "bytes": 50,
        "count": 1,
        "extension": "md"
      }
    ],
    "total_bytes": 150,
    "total_files": 2
  }
}
```

```json
{
  "input": {
    "inventory": []
  },
  "output": {
    "by_extension": [],
    "total_bytes": 0,
    "total_files": 0
  }
}
```

```json
{
  "input": {
    "inventory": [
      {
        "bytes": 10,
        "path": "package/.npmignore",
        "sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
      },
      {
        "bytes": 20,
        "path": "package/lib/Tool.JS",
        "sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
      }
    ]
  },
  "output": {
    "by_extension": [
      {
        "bytes": 10,
        "count": 1,
        "extension": ""
      },
      {
        "bytes": 20,
        "count": 1,
        "extension": "js"
      }
    ],
    "total_bytes": 30,
    "total_files": 2
  }
}
```

Public regression tests: `tests/test_community_inventory_composition_summary.py`.


<!-- community-core:findings-tally-scan -->
### Offline audit findings tally for reproducible triage

Gives REA Lab reviewers a fast offline way to tally published npm-tarball audit findings by severity and code without re-reading archives, network, execution or installation. It aggregates validated error and warning records into totals and per-code counts for reproducible notes and triage follow-up against identity, integrity, inventory hash comparison, entrypoint comparison, name and SemVer syntax checks and manifest declaration scans which do not summarize finding severity. It complements file diffing and verbatim declaration comparison with findings-level counting distinct as severity totals and ASCII-sorted per-code grouping over caller-supplied records.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/findings_tally_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, extraction, resolution or hook execution. Input payload must be a dict with required key findings and optional key max_entries default 256 and no other keys; any non-dict payload, missing findings key or extra key raises ValueError with fixed text Invalid findings payload or budget without echoing input. The max_entries budget when present must be an exact int excluding bools in range 1 to 500 inclusive; floats, bools, strings including subclasses, lists, dicts, None or out-of-range ints raise the same fixed payload error with no coercion, trimming, fetching, normalization, resolution or repair. The findings value must be a list with length 0 to max_entries inclusive; longer lists raise the same fixed payload error. Each record must be a dict with exactly code and severity and no other keys; missing, extra or non-dict records raise ValueError with fixed text Invalid finding record without echoing input. The code value must be str including subclasses accepted without coercion as plain str copy with length 1 to 64 inclusive matching [A-Za-z0-9_/-]+ with no leading, trailing or doubled slash; other types, lengths or alphabets raise the same fixed record error with no coercion, trimming or fetching. The severity value must be exact str error or warning case-sensitive; other types or values raise the same fixed record error. No tar parsing, extraction, manifest fetching, range matching, resolution or normalization is performed. Aggregation is deterministic over validated records: total is list length, errors is count with severity error, warnings is count with severity warning, and by_code groups by code sorted ASCII code-point order. Returns a fresh dict with exactly total, errors, warnings and by_code in fixed order; total, errors and warnings are ints, by_code is a fresh sorted list of fresh dicts each with exactly code, count, errors and warnings in fixed order, where code is fresh plain str, count is group length, errors is group error count and warnings is group warning count. Inputs are never mutated and outputs share no mutable references with fresh containers each call and deterministic ordering. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults, and API run_feature(payload) preserves input. This is findings enumeration only, not compatibility, provenance verification, safety, security or legal review; values are reported as declared.

Examples (JSON input and expected output):

```json
{
  "input": {
    "findings": []
  },
  "output": {
    "by_code": [],
    "errors": 0,
    "total": 0,
    "warnings": 0
  }
}
```

```json
{
  "input": {
    "findings": [
      {
        "code": "manifest_identity",
        "severity": "error"
      },
      {
        "code": "manifest_identity",
        "severity": "warning"
      }
    ]
  },
  "output": {
    "by_code": [
      {
        "code": "manifest_identity",
        "count": 2,
        "errors": 1,
        "warnings": 1
      }
    ],
    "errors": 1,
    "total": 2,
    "warnings": 1
  }
}
```

```json
{
  "input": {
    "findings": [
      {
        "code": "manifest_version",
        "severity": "error"
      },
      {
        "code": "identity_mismatch",
        "severity": "warning"
      },
      {
        "code": "manifest_identity",
        "severity": "error"
      }
    ],
    "max_entries": 256
  },
  "output": {
    "by_code": [
      {
        "code": "identity_mismatch",
        "count": 1,
        "errors": 0,
        "warnings": 1
      },
      {
        "code": "manifest_identity",
        "count": 1,
        "errors": 1,
        "warnings": 0
      },
      {
        "code": "manifest_version",
        "count": 1,
        "errors": 1,
        "warnings": 0
      }
    ],
    "errors": 2,
    "total": 3,
    "warnings": 1
  }
}
```

Public regression tests: `tests/test_community_findings_tally_scan.py`.


<!-- community-core:exports-wildcard-scan -->
### Offline exports wildcard-pattern classifier for reproducible audits

Gives REA Lab reviewers a fast offline way to classify declared npm exports subpath keys and string targets into exact entries versus asterisk wildcard patterns without reading archives, network, execution, installation, extraction, resolution or normalization. It supports triage of the audit unverified-pattern reports by enumerating which declared keys and targets contain literal * for manual follow-up, complementing inventory hash diffing, verbatim entrypoint comparison, name and SemVer syntax checks, manifest declaration scans and findings tallies which do not flag wildcard semantics.

Reusable deterministic JSON core: `src/npm_tarball_audit/features/exports_wildcard_scan.py`, API `run_feature(payload)`. This module is independently tested; application/UI integration is outside this change.

Exposes run_feature(payload) as a pure deterministic JSON core with no I/O, filesystem, network, processes, time, randomness, callbacks, dependencies, or package-code execution, installation, extraction, resolution, normalization or hook execution. Input payload must be a dict with required key exports and optional keys max_entries default 64, max_length default 256, max_depth default 8 and no other keys; any non-dict payload, missing exports key or extra key raises ValueError with fixed text Invalid exports payload or budget without echoing input. The max_entries budget when present must be an exact int excluding bools in range 1 to 256 inclusive; the max_length budget when present must be an exact int excluding bools in range 1 to 1024 inclusive; the max_depth budget when present must be an exact int excluding bools in range 1 to 16 inclusive; floats, bools, strings including subclasses, lists, dicts, None or out-of-range ints raise the same fixed payload error with no coercion, trimming, fetching, normalization, resolution or repair. The exports value may be None, str including subclasses accepted without coercion as plain str copy, list, or dict; other types raise ValueError with fixed text Invalid exports declaration without echoing input. None at top level means absent. A str top level is a single target. A list must contain only str, list, dict or None elements; dicts must have str keys and values that are str, list, dict or None; any other element, key type or value type raises the same fixed declaration error. Each key and each str leaf must have length 1 to max_length inclusive; empty or over-long strings raise the same fixed declaration error with no trimming or repair. Traversal is iterative over explicitly supplied values only with root depth 1; nested list/dict containers add levels and exceeding max_depth raises the same fixed declaration error. Total visited entries defined as dict-key occurrences plus str-leaf occurrences plus nested None blocked entries must be 0 to max_entries inclusive; larger inputs raise the same fixed payload error. No tar parsing, extraction, manifest fetching, range matching, resolution, normalization or execution is performed; wildcard detection is exact literal asterisk code 42 containment in the declared string with no glob expansion. Aggregation is deterministic over validated values: declared is False only for top-level None else True; total_keys counts dict-key occurrences; total_targets counts str-leaf occurrences; wildcard_key_occurrences and wildcard_target_occurrences count occurrences containing asterisk; wildcard_keys and wildcard_targets are ASCII code-point sorted unique lists of those containing asterisk. Blocked None entries are allowed inside structures and counted toward max_entries but not toward totals or wildcard lists. Returns a fresh dict with exactly declared, total_keys, total_targets, wildcard_key_occurrences, wildcard_target_occurrences, wildcard_keys and wildcard_targets in fixed order; declared is bool, counts are ints, lists are fresh sorted lists of fresh plain str. Inputs are never mutated and outputs share no mutable references with fresh containers each call and deterministic ordering. Implementation uses only math, re, json and unicodedata with plain functions and immutable literal module constants with local mutable containers and no decorators, classes, async, generators, globals, nonlocals, attribute assignment or deletion, dynamic calls or mutable defaults, and API run_feature(payload) preserves input. This is pattern enumeration only, not compatibility, provenance verification, safety, security or legal review; values are reported as declared and wildcard status implies unverified pattern only.

Examples (JSON input and expected output):

```json
{
  "input": {
    "exports": {
      ".": "./index.js",
      "./features/*": "./features/*.js"
    }
  },
  "output": {
    "declared": true,
    "total_keys": 2,
    "total_targets": 2,
    "wildcard_key_occurrences": 1,
    "wildcard_keys": [
      "./features/*"
    ],
    "wildcard_target_occurrences": 1,
    "wildcard_targets": [
      "./features/*.js"
    ]
  }
}
```

```json
{
  "input": {
    "exports": "./index.js"
  },
  "output": {
    "declared": true,
    "total_keys": 0,
    "total_targets": 1,
    "wildcard_key_occurrences": 0,
    "wildcard_keys": [],
    "wildcard_target_occurrences": 0,
    "wildcard_targets": []
  }
}
```

```json
{
  "input": {
    "exports": {
      ".": {
        "default": "./index.js",
        "import": "./esm.js",
        "require": "./cjs.js"
      },
      "./locale/*": null
    }
  },
  "output": {
    "declared": true,
    "total_keys": 5,
    "total_targets": 3,
    "wildcard_key_occurrences": 1,
    "wildcard_keys": [
      "./locale/*"
    ],
    "wildcard_target_occurrences": 0,
    "wildcard_targets": []
  }
}
```

Public regression tests: `tests/test_community_exports_wildcard_scan.py`.
