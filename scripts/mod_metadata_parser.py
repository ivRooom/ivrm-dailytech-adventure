#!/usr/bin/env python3
"""Shared parser for NeoForge, Forge, and Fabric MOD metadata."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

TOML_MOD_ID = re.compile(r'^\s*modId\s*=\s*["\']([^"\']+)["\']')
TOML_DISPLAY_NAME = re.compile(r'^\s*displayName\s*=\s*["\']([^"\']+)["\']')
TOML_ARRAY_HEADER = re.compile(r'^\s*\[\[([^\]]+)\]\](?:\s*#.*)?$')


def decode_zip_text(archive: zipfile.ZipFile, name: str) -> str:
    return archive.read(name).decode("utf-8", errors="replace")


def parse_mod_blocks(text: str) -> list[tuple[str, str | None]]:
    """Parse [[mods]] tables, including legal trailing TOML comments."""

    mods: list[tuple[str, str | None]] = []
    current_id: str | None = None
    current_name: str | None = None
    in_mod_block = False

    def finish_block() -> None:
        nonlocal current_id, current_name
        if current_id:
            mods.append((current_id, current_name))
        current_id = None
        current_name = None

    for line in text.splitlines():
        header_match = TOML_ARRAY_HEADER.match(line)
        if header_match:
            header = header_match.group(1).strip()
            if in_mod_block:
                finish_block()
            in_mod_block = header == "mods"
            continue

        if not in_mod_block:
            continue

        mod_id_match = TOML_MOD_ID.match(line)
        if mod_id_match:
            current_id = mod_id_match.group(1).strip().lower()

        name_match = TOML_DISPLAY_NAME.match(line)
        if name_match:
            current_name = name_match.group(1).strip()

    if in_mod_block:
        finish_block()

    return mods


def parse_standard_metadata(path: Path) -> tuple[str, str, list[str]] | None:
    """Return primary modId, display name, and bundled modIds from a JAR."""

    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())

        for metadata_name in (
            "META-INF/neoforge.mods.toml",
            "META-INF/mods.toml",
        ):
            if metadata_name not in names:
                continue

            mod_blocks = parse_mod_blocks(decode_zip_text(archive, metadata_name))
            if mod_blocks:
                mod_ids = list(dict.fromkeys(mod_id for mod_id, _ in mod_blocks))
                primary, primary_name = mod_blocks[0]
                return primary, primary_name or path.stem, mod_ids

        if "fabric.mod.json" in names:
            data = json.loads(decode_zip_text(archive, "fabric.mod.json"))
            mod_id = str(data.get("id", "")).strip().lower()
            if mod_id:
                display_name = str(data.get("name") or path.stem).strip()
                return mod_id, display_name, [mod_id]

    return None
