# Useful next work

Each item needs a concrete user benefit, regression tests and a documented limit. Completed work is removed from this queue and described in release notes.

- Extend the inventory comparison command with explicit entrypoint-declaration comparison. Pure inventory comparison, bounded JSON report loading and `--compare BEFORE AFTER` are available; they compare regular-file paths, sizes and hashes, not entrypoint semantics. Do not store vendor source.
- Document and test npm `browser` remapping semantics and conditional exports coverage; avoid claiming complete Node resolution.
- Add explicit validation for scoped npm package names, with backward-compatibility fixtures and no online dependencies. Opt-in SemVer manifest auditing is available; syntax checks do not validate package names.
- Add tests for pathological PAX metadata and GNU longnames. Manifest JSON now has an explicit tested nesting budget; keep malformed-input and escape fixtures when extending it.
- Provide a machine-readable JSON schema for reports, with backward-compatibility fixtures.
- Add a streaming implementation for the compressed hash input, keeping the existing decompression and manifest budgets intact.

New REA cases need a clearly identified public artifact, license/source links, fixed digest, investigation question, evidence IDs and explicit unanswered questions. A new project or analysis must justify a useful purpose before creation.

## Completed

- Opt-in SemVer manifest auditing through `audit(..., strict_semver=True)` and
  `--strict-semver`, preserving default behavior and existing JSON/SARIF outputs.
  No range matching, precedence or compatibility is inferred.
- Bounded pure `parse_semver` API for SemVer 2.0.0 syntax, fresh string/list
  results, fixed errors and explicit resource limits.
  See [release notes](CHANGELOG.md).
- SARIF 2.1.0 export through a pure API and `--sarif`, with stable rule IDs,
  bounded escaped member display and neutral messages that omit host paths.
  See [release notes](CHANGELOG.md) for behavior and limits.
