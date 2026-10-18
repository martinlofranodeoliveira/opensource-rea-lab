# Useful next work

Each item needs a concrete user benefit, regression tests and a documented limit. Completed work is removed from this queue and described in release notes.

- Add an optional comparison command for two audit inventories: report added/removed paths, changed digests and changed entrypoints, without storing vendor source.
- Add CI-friendly SARIF output with stable rule IDs and sanitized member paths.
- Document and test npm `browser` remapping semantics and conditional exports coverage; avoid claiming complete Node resolution.
- Add explicit support for scoped-package name/version validation and semver syntax checks without introducing online dependencies.
- Add tests for pathological PAX metadata, GNU longnames and nested manifest JSON depth.
- Provide a machine-readable JSON schema for reports, with backward-compatibility fixtures.
- Add a streaming implementation for the compressed hash input, keeping the existing decompression and manifest budgets intact.

New REA cases need a clearly identified public artifact, license/source links, fixed digest, investigation question, evidence IDs and explicit unanswered questions. A new project or analysis must justify a useful purpose before creation.
