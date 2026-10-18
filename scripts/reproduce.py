#!/usr/bin/env python3
"""Fetch one pinned official public artifact and reproduce the offline audit.

This never invokes npm, lifecycle hooks or downloaded JavaScript. --prepare-rea
only writes already-inspected regular files into a fresh analysis directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from npm_tarball_audit import audit  # noqa: E402

URL = "https://registry.npmjs.org/rea-agents/-/rea-agents-6.4.0.tgz"
SHA256 = "59eb1604b8db75f522d4a975c36ce6b4a2ad465e43bad165f9a8f728391db9b8"
INTEGRITY = "sha512-Vj1zWfSlna5bphGoaoI/TcVBuYvze9u+OyPC3Shz8YkBqaCTqB4COnnRoX7XDwMpwI24ZlFEel2yEj0k8LTWEQ=="


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/rea-agents-6.4.0"))
    parser.add_argument("--prepare-rea", action="store_true")
    parser.add_argument("--entrypoint-only", action="store_true", help="Prepare the documented two-file REA slice (requires --prepare-rea)")
    args = parser.parse_args()
    if args.entrypoint_only and not args.prepare_rea:
        parser.error("--entrypoint-only requires --prepare-rea")
    args.output.mkdir(parents=True, exist_ok=True)
    archive_path = args.output / "rea-agents-6.4.0.tgz"
    if not archive_path.exists():
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read(64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024:
            raise SystemExit("Download exceeds 64 MiB")
        if hashlib.sha256(data).hexdigest() != SHA256:
            raise SystemExit("Pinned SHA-256 mismatch; refusing to save artifact")
        archive_path.write_bytes(data)
    report = audit(archive_path, expected_name="rea-agents", expected_version="6.4.0", integrity=INTEGRITY)
    if report["sha256"] != SHA256 or report["status"] == "fail":
        raise SystemExit("Pinned artifact validation failed")
    (args.output / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.prepare_rea:
        target = args.output / "extracted"
        if target.exists():
            raise SystemExit("Extraction destination exists; choose a fresh --output directory")
        target.mkdir()
        with tarfile.open(archive_path, "r:gz") as archive:
            if args.entrypoint_only:
                wanted = {"package/package.json", "package/scripts/rea.mjs"}
                for member in archive:
                    if member.name not in wanted:
                        continue
                    destination = target / member.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, destination.open("wb") as output:
                        shutil.copyfileobj(source, output)
            else:
                archive.extractall(target, filter="data")
        print(f"REA target: {(target / 'package').resolve()}")
    print(json.dumps({"status": report["status"], "sha256": report["sha256"], "members": report["member_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
