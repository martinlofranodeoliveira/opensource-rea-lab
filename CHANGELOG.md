# Release notes

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
