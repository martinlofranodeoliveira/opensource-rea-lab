# Public project boundaries

Work only in this public repository. Never read, copy, import or publish unrelated private projects, user documents, credentials, `.env` files, local service units or private model configuration. Downloaded public artifacts stay under ignored `artifacts/` and are not committed.

Implement a specific useful roadmap item or supported issue, with tests. Preserve offline analysis: do not execute inspected packages, invoke their lifecycle hooks or add network calls to the audit library. Document observations separately from inferences and unknowns. Keep evidence exports sanitized and state coverage limitations.

Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` before proposing a commit. Do not create empty commits, split changes only to increase counts, forge authorship/time, or modify contribution statistics. No commit is needed when no meaningful validated change exists.

Changing dependencies, workflows, license, this instruction file or publishing controls requires maintainer review. Code changes must not write outside the selected working tree or access cloud resources.
