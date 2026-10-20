"""Audit or compare inventories. Failed checks/changes return 1; bad input 2."""

import argparse
import json
import os
import stat
import sys

from .audit import audit
from .compare import compare_inventories
from .sarif import to_sarif

MAX_REPORT_BYTES = 16 * 1024 * 1024


def _read_report(path: str) -> str:
    """Read a bounded regular file; never wait for a FIFO or follow a symlink."""
    if not stat.S_ISREG(os.stat(path, follow_symlinks=False).st_mode):
        raise ValueError("A report must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_REPORT_BYTES:
            raise ValueError("A report must be a bounded regular file")
        data = source.read(MAX_REPORT_BYTES + 1)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("Report exceeds the byte budget")
    return data.decode("utf-8", errors="strict")


def _compare_reports(paths: list[str], as_json: bool) -> int:
    from .report import parse_inventory_report

    try:
        before, after = [parse_inventory_report(_read_report(path), max_bytes=MAX_REPORT_BYTES)
                         for path in paths]
        changes = compare_inventories(before, after)
    except (OSError, ValueError):
        # Input content, parser internals and host file paths never reach logs.
        print("Cannot compare reports: use regular UTF-8 files with valid inventories "
              "from pass/warning audits, at most 16 MiB each.", file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps(changes, indent=2, ensure_ascii=True))
    else:
        print(f"{len(changes['added'])} added; {len(changes['removed'])} removed; "
              f"{len(changes['changed'])} changed; {changes['unchanged_count']} unchanged")
        for category in ("added", "removed", "changed"):
            for item in changes[category]:
                print(f"{category.upper()}: {ascii(item['path'])}")
    return int(any(changes[key] for key in ("added", "removed", "changed")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect an npm .tgz or compare audit inventories offline")
    parser.add_argument("archive", nargs="?", help="npm .tgz to audit")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"),
                        help="Compare two JSON reports created with --include-inventory --json")
    parser.add_argument("--expected-name")
    parser.add_argument("--expected-version")
    parser.add_argument("--integrity", help="Expected sha512-base64 SRI token from a trusted source")
    parser.add_argument("--include-inventory", action="store_true", help="Include each regular file path, size and SHA-256")
    parser.add_argument("--strict-semver", action="store_true", help="Require package.json version to be valid SemVer")
    output_format = parser.add_mutually_exclusive_group()
    output_format.add_argument("--json", action="store_true", help="Emit a machine-readable report")
    output_format.add_argument("--sarif", action="store_true", help="Emit sanitized SARIF 2.1.0 without source locations")
    args = parser.parse_args(argv)
    if args.compare:
        if args.archive is not None or any(value is not None for value in
                                           (args.expected_name, args.expected_version, args.integrity)) or args.include_inventory or args.sarif or args.strict_semver:
            parser.error("--compare accepts only BEFORE, AFTER and optional --json; omit audit options")
        return _compare_reports(args.compare, args.json)
    if args.archive is None:
        parser.error("provide an archive to audit, or --compare BEFORE AFTER")
    report = audit(args.archive, expected_name=args.expected_name,
                   expected_version=args.expected_version, integrity=args.integrity,
                   include_inventory=args.include_inventory, strict_semver=args.strict_semver)
    if args.sarif:
        try:
            document = to_sarif(report)
        except ValueError:
            print("Cannot export SARIF: use a valid, bounded offline audit report.", file=sys.stderr)
            return 2
        print(json.dumps(document, indent=2, ensure_ascii=True))
    elif args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        package = report["package"] or {}
        print(f"{report['status'].upper()}: {package.get('name', '?')!r}@{package.get('version', '?')!r}")
        print(f"SHA-256: {report['sha256']}")
        print(f"Members: {report['member_count']}; regular payload bytes: {report['regular_file_bytes']}")
        for item in report["findings"]:
            suffix = f" ({item['member']!r})" if "member" in item else ""
            print(f"{item['level']}: {item['code']}: {ascii(item['message'])}{suffix}")
    return int(report["status"] == "fail")


if __name__ == "__main__":
    raise SystemExit(main())
