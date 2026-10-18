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
- Validates `package/package.json`, duplicate JSON keys, expected name/version, and optional SHA-512 integrity.
- Checks exact local `bin`/`exports` targets and common `main` resolution candidates. Reports wildcard exports as unverified patterns.
- Reports license metadata/file absence and declared install/prepare hooks for review.

Defaults: 64 MiB compressed, 256 MiB decompressed stream, 32 MiB per file, 128 MiB total regular files, 1 MiB manifest, 20,000 members. Python callers can supply `Limits(...)`.

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
