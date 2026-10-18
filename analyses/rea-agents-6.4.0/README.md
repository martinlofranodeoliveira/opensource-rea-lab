# Case 001: inspect the published REA dispatcher before running it

Analyzed on 2026-10-18. The purpose is to establish a reproducible artifact boundary and inspect a small shipped JavaScript entrypoint with REA. It is not an endorsement or a complete security audit of REA.

## Target and identity

| Field | Observed value |
| --- | --- |
| Official source | [morluto/rea](https://github.com/morluto/rea) |
| Distribution | [rea-agents 6.4.0 on npm](https://www.npmjs.com/package/rea-agents/v/6.4.0) |
| Tarball | `https://registry.npmjs.org/rea-agents/-/rea-agents-6.4.0.tgz` |
| SHA-256 | `59eb1604b8db75f522d4a975c36ce6b4a2ad465e43bad165f9a8f728391db9b8` |
| Compressed bytes | 1,825,761 |
| Archive members | 1,161 |
| Regular file payload bytes | 7,776,450 |
| Declared license | MIT |

The expected SHA-512 SRI token was obtained from the official version metadata at `https://registry.npmjs.org/rea-agents/6.4.0` and matched the downloaded bytes. Both fixed digests are embedded in the reproduction script. Matching a hash establishes byte identity against that expected value; it is not independent proof of publisher identity or safety.

## Questions and results

1. **Does the tarball pass the implemented structural checks? Answered.** The offline report contains no errors. It reports one warning: the package declares a `prepare` lifecycle hook. The hook was never executed. Both declared command names, `rea` and `rea-agents`, target the existing `scripts/rea.mjs` file. See [audit.json](audit.json).
2. **Can REA statically parse the actual shipped dispatcher? Answered within the selected slice.** The byte-identical `package.json` and `scripts/rea.mjs` were copied from that verified tarball into a fresh two-file directory. REA reported two relevant files, one parsed JavaScript file, 469 AST nodes and zero parse failures. Its 14 findings are analyzer observations, not vulnerability counts.
3. **What does the dispatcher appear to select? Partially answered.** Direct inspection of the shipped syntax shows a branch for MCP service mode, a branch for MCP doctor mode, and a general CLI branch. Those branches refer to compiled modules under `dist/`. This is a static interpretation of the dispatcher, not observed execution. The compiled targets are deliberately absent from the two-file slice, so their implementation and runtime effects are not established here.
4. **Is the full package safe and correct at runtime? Unresolved and outside this case.** No package code, setup command, lifecycle script, browser, cloud resource or native provider was executed. Dependencies and runtime behavior were not audited.

## REA evidence ledger

The [sanitized excerpt](rea-excerpt.json) preserves selected counters, hashes and coverage. It is an analyst derivative, **not** a portable canonical Evidence bundle; its redacted form must not be presented as replayable original Evidence.

| Record | Evidence ID | What it supports |
| --- | --- | --- |
| Two-file analysis parent | `ev_4ad6ace932769562625303a8a20aab6256354762894105d4dfc4971a800a1870` | Retained static analysis of the defined slice |
| Slice summary | `ev_bd0669b55f29f19e1e4c1dbc3c8aa4e327a9f132898a207be1d2b6c2b1631de9` | Parse counters and slice-level coverage |
| Dispatcher asset view | `ev_6f50f7de894545bac872a54d6c8e12e7180ea105063901caec1cc4d6a58a9db6` | Exact file digest, 3,786 bytes and complete parse status |

Exact selected file digests:

- `package.json`: `1c6244e5689db5354fffc0e92f4ee0e0237c3a6d645de564ade2d8375fa570f9`
- `scripts/rea.mjs`: `3554288a08c455fa419dad662d73710fb17debe94b9e71dd1282761117c5981e`

REA's directory identity for this slice is `329568cd34b1bceef0fefd2a99ab6b38d42f64e3aec20c31c8006595fa6b64a3`. That is a directory-content identity, not the tarball hash. The summary used a 256 MiB JavaScript analyzer heap setting and a 10,000 ms per-source timeout. The connected analyzer identifies itself as `rea-javascript-application`, version `1`; that provider protocol version is separate from the inspected package's version.

Application inventory coverage was reported complete **for the slice**. Semantic coverage was **unknown**, with 110 semantic unknowns. Static imports and inferred relationships cannot establish execution, policy enforcement, or correct behavior. Missing findings cannot prove absence from the whole package.

## Why the case is intentionally small

An initial whole-package request was interrupted after large semantic expansion. Its retained partial Evidence was recovered without rerunning the producer:

- Parent: `ev_080fa0bdb46755908d785ab98c2c1f92b05cedf9a9bb29e5e31eb0a7ead4decb`
- Summary: `ev_989e88e8aaa8c0df42389c1cbd8ca0dbba67c61d84d76609b7a4b2ebbffca8c0`
- It retained observations for 1,118 parsed JavaScript files, with zero parse failures, but **application and semantic coverage were partial**, with 20,888 semantic unknowns and result/worker budget limitations.

No whole-package semantic or safety claim follows from those counters. The focused entrypoint slice answers the smaller question with a practical analysis budget. The REA session was closed after retaining this sanitized derivative to release analysis resources.

## Reproduce

From the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/reproduce.py --output artifacts/case001 --prepare-rea --entrypoint-only
rea analyze-javascript-application "$PWD/artifacts/case001/extracted/package" --json
```

Use a trusted existing REA installation; see the upstream [application analysis guide](https://github.com/morluto/rea/blob/main/docs/javascript-application-workflows.md) for its requirements. This command parses the selected files statically. Analyzer versions can change counters and Evidence IDs. Digests of the pinned vendor files remain the stable comparison points. Do not commit downloaded vendor files or machine-specific raw analysis dumps.
