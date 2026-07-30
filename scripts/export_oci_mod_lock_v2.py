#!/usr/bin/env python3
"""Compatibility entrypoint using the corrected MOD metadata parser."""

from __future__ import annotations

import sys

import export_oci_mod_lock as legacy
from mod_metadata_parser import parse_standard_metadata


legacy.parse_standard_metadata = parse_standard_metadata


if __name__ == "__main__":
    try:
        sys.exit(legacy.main())
    except legacy.ExportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
