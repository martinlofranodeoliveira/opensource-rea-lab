# Release notes

## 2026-10-19 — Bounded semantic version syntax API

- Added pure `npm_tarball_audit.semver.parse_semver` for complete SemVer 2.0.0
  syntax, with strings for core numbers and fresh lists for prerelease/build
  identifiers. Numeric components are not converted to Python integers.
- Inclusive default length budget of 4,096 Python code points, checked before
  parsing; invalid text or budgets raise a fixed `ValueError` without input
  content. No whitespace repair, npm ranges, tags or `v` prefixes.
- Build identifiers preserve valid hyphens and leading zeroes; numeric
  prerelease identifiers still reject leading zeroes.
- This is an additive library API. Auditor, CLI, dependencies, identity behavior
  and existing tests remain unchanged. Version precedence, npm names and audit
  integration are outside this feature.

## 2026-10-19 — SARIF export

- Added `--sarif` and pure `npm_tarball_audit.sarif.to_sarif` for SARIF 2.1.0
  results from offline audits. Existing JSON/human audit output and inventory
  comparison behavior remain available.
- Stable `NTA/<code>` rule IDs, deterministic rule ordering and original result
  ordering. Pass/warning/fail audits retain their ordinary audit exit codes;
  invalid export input returns an error without partial output.
- Neutral messages omit original diagnostics and host metadata. Member display
  is bounded, quoted and escaped; unsafe paths are omitted. Exports contain no
  file locations or source snippets and do not imply package execution,
  extraction, provenance or a malware verdict.
- No runtime dependencies were added. Schema validation is performed separately
  against a fixed official OASIS schema during independent acceptance testing.
- Validation: 87 public tests and 26 frozen independent checks passed, including
  offline schema validation and hostile-name/message/limit fixtures. The original
  67 public tests were preserved.
