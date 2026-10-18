"""Command-line interface. Failures return 1, invalid arguments return 2."""

import argparse
import json

from .audit import audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect an npm .tgz without extraction or package execution")
    parser.add_argument("archive")
    parser.add_argument("--expected-name")
    parser.add_argument("--expected-version")
    parser.add_argument("--integrity", help="Expected sha512-base64 SRI token from a trusted source")
    parser.add_argument("--include-inventory", action="store_true", help="Include each regular file path, size and SHA-256")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report")
    args = parser.parse_args(argv)
    report = audit(args.archive, expected_name=args.expected_name,
                   expected_version=args.expected_version, integrity=args.integrity,
                   include_inventory=args.include_inventory)
    if args.json:
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
