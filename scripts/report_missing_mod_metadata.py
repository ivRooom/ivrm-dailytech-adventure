#!/usr/bin/env python3
"""Report every production JAR that needs an explicit metadata override."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

from export_oci_mod_lock import ExportError, load_json, resolve_metadata_override
from mod_metadata_parser import parse_standard_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Scan every production MOD JAR and report all files that expose no "
            "supported NeoForge, Forge, or Fabric metadata."
        )
    )
    parser.add_argument(
        "--mods-dir",
        type=Path,
        default=Path("/opt/ivrm/compose/minecraft-main/mods"),
    )
    parser.add_argument(
        "--metadata-overrides",
        type=Path,
        default=Path("manifests/metadata-overrides.json"),
    )
    parser.add_argument("--expected-count", type=int, default=80)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.mods_dir.is_dir():
        raise ExportError(f"MOD directory does not exist: {args.mods_dir}")

    overrides = load_json(args.metadata_overrides)
    jars = sorted(args.mods_dir.glob("*.jar"), key=lambda path: path.name.lower())
    if len(jars) != args.expected_count:
        raise ExportError(
            f"JAR count must be {args.expected_count}, got {len(jars)}"
        )

    standard: list[str] = []
    overridden: list[str] = []
    missing: list[str] = []

    for jar in jars:
        try:
            parsed = parse_standard_metadata(jar)
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
            raise ExportError(f"Unable to inspect JAR metadata: {jar.name}: {exc}") from exc

        if parsed is not None:
            standard.append(jar.name)
            continue
        if resolve_metadata_override(jar.name, overrides) is not None:
            overridden.append(jar.name)
            continue
        missing.append(jar.name)

    print(f"JAR count={len(jars)}")
    print(f"Standard metadata={len(standard)}")
    print(f"Filename overrides={len(overridden)}")
    print(f"Missing metadata={len(missing)}")

    if overridden:
        print("\nReviewed filename overrides:")
        for filename in overridden:
            print(f"- {filename}")

    if missing:
        print("\nAll JARs requiring review:")
        for filename in missing:
            print(f"- {filename}")
        print(
            "\nAdd reviewed byFilename entries to "
            "manifests/metadata-overrides.json before exporting the lock."
        )
        return 1

    print("\nAll production JARs have standard metadata or reviewed overrides.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ExportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
