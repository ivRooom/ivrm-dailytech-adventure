#!/usr/bin/env python3
"""Export and verify the live OCI Minecraft MOD lock.

This script is intentionally dependency-free. It verifies that the host MOD
directory, /data/mods, and the running mc-main container contain exactly the
same JAR filenames and SHA-256 hashes, then emits a public-safe JSON lock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOML_MOD_ID = re.compile(r'^\s*modId\s*=\s*["\']([^"\']+)["\']')
TOML_DISPLAY_NAME = re.compile(r'^\s*displayName\s*=\s*["\']([^"\']+)["\']')
CURSEFORGE_FILE = re.compile(r"-cf-(\d+)\.jar$", re.IGNORECASE)
VALID_MOD_ID = re.compile(r"^[a-z0-9_.-]+$")


class ExportError(RuntimeError):
    """Raised when the live MOD state cannot be safely exported."""


def command_prefix() -> list[str]:
    return ["docker"] if os.geteuid() == 0 else ["sudo", "docker"]


def run(command: list[str], *, check: bool = True) -> str:
    result = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise ExportError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExportError(f"Required JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ExportError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ExportError(f"JSON root must be an object: {path}")
    return data


def inspect_container(container: str) -> tuple[str, str]:
    output = run(
        command_prefix()
        + [
            "inspect",
            container,
            "--format",
            "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
        ]
    )
    parts = output.split()
    if len(parts) != 2:
        raise ExportError(f"Unexpected docker inspect output for {container}: {output}")
    return parts[0], parts[1]


def inspect_optional_container(container: str) -> str:
    result = subprocess.run(
        command_prefix()
        + ["inspect", container, "--format", "{{.State.Status}}"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return result.stdout.strip() if result.returncode == 0 else "not-created"


def directory_hashes(directory: Path) -> dict[str, str]:
    if not directory.is_dir():
        raise ExportError(f"MOD directory does not exist: {directory}")
    jars = sorted(directory.glob("*.jar"), key=lambda item: item.name.lower())
    return {jar.name: sha256_file(jar) for jar in jars}


def container_hashes(container: str) -> dict[str, str]:
    shell = (
        'set -eu; '
        'for file in /data/mods/*.jar; do '
        '[ -f "$file" ] || continue; '
        'sha256sum "$file"; '
        "done"
    )
    output = run(command_prefix() + ["exec", container, "sh", "-lc", shell])
    hashes: dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ExportError(f"Unexpected container sha256sum output: {line}")
        digest, raw_path = parts
        filename = Path(raw_path.lstrip("*")).name
        hashes[filename] = digest
    return hashes


def compare_hash_sets(
    label: str,
    expected: dict[str, str],
    actual: dict[str, str],
) -> None:
    expected_names = set(expected)
    actual_names = set(actual)
    missing = sorted(expected_names - actual_names)
    extra = sorted(actual_names - expected_names)
    mismatched = sorted(
        name
        for name in expected_names & actual_names
        if expected[name] != actual[name]
    )

    details: list[str] = []
    if missing:
        details.append(f"missing={missing}")
    if extra:
        details.append(f"extra={extra}")
    if mismatched:
        details.append(f"hash-mismatch={mismatched}")
    if details:
        raise ExportError(f"{label} does not match host MODs: " + "; ".join(details))


def decode_zip_text(archive: zipfile.ZipFile, name: str) -> str:
    return archive.read(name).decode("utf-8", errors="replace")


def parse_mod_blocks(text: str) -> list[tuple[str, str | None]]:
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
        stripped = line.strip()
        if stripped == "[[mods]]":
            if in_mod_block:
                finish_block()
            in_mod_block = True
            continue
        if stripped.startswith("[[") and in_mod_block:
            finish_block()
            in_mod_block = False
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


def parse_jar_metadata(path: Path) -> tuple[str, str, list[str]]:
    try:
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
                    display = primary_name or path.stem
                    return primary, display, mod_ids

            if "fabric.mod.json" in names:
                data = json.loads(decode_zip_text(archive, "fabric.mod.json"))
                mod_id = str(data.get("id", "")).strip().lower()
                if mod_id:
                    display = str(data.get("name") or path.stem).strip()
                    return mod_id, display, [mod_id]
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise ExportError(f"Unable to inspect JAR metadata: {path.name}: {exc}") from exc

    raise ExportError(
        f"No NeoForge/Forge/Fabric MOD metadata found in {path.name}. "
        "Review the JAR before publishing the lock."
    )


def infer_distribution(
    filename: str,
) -> tuple[str, int | str | None, int | str | None]:
    match = CURSEFORGE_FILE.search(filename)
    if match:
        return "curseforge", None, int(match.group(1))
    return "manual", None, None


def resolve_distribution(
    filename: str,
    mod_ids: list[str],
    overrides: dict[str, Any],
) -> tuple[str, int | str | None, int | str | None]:
    by_filename = overrides.get("byFilename", {})
    by_mod_id = overrides.get("byModId", {})

    selected: dict[str, Any] | None = None
    if filename in by_filename:
        selected = by_filename[filename]
    else:
        matches = [
            by_mod_id[mod_id]
            for mod_id in mod_ids
            if mod_id in by_mod_id
        ]
        if len(matches) > 1 and any(item != matches[0] for item in matches[1:]):
            raise ExportError(
                f"Conflicting distribution overrides for {filename}"
            )
        if matches:
            selected = matches[0]

    if selected is None:
        return infer_distribution(filename)
    if not isinstance(selected, dict):
        raise ExportError(f"Distribution override must be an object: {filename}")

    source = selected.get("source", "manual")
    if source not in {"curseforge", "modrinth", "github", "manual"}:
        raise ExportError(f"Invalid distribution source for {filename}: {source}")
    return source, selected.get("projectId"), selected.get("fileId")


def resolve_side(
    filename: str,
    mod_ids: list[str],
    overrides: dict[str, Any],
) -> tuple[str, str]:
    by_filename = overrides.get("byFilename", {})
    by_mod_id = overrides.get("byModId", {})
    default = overrides.get("default", "both")

    if filename in by_filename:
        return str(by_filename[filename]), "filename-override"

    matches = {
        str(by_mod_id[mod_id])
        for mod_id in mod_ids
        if mod_id in by_mod_id
    }
    if len(matches) > 1:
        raise ExportError(
            f"Conflicting side overrides for {filename}: {sorted(matches)}"
        )
    if matches:
        return matches.pop(), "mod-id-override"
    return str(default), "default"


def validate_side(side: str, filename: str) -> None:
    if side not in {"both", "server", "client"}:
        raise ExportError(f"Invalid side '{side}' for {filename}")


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as temporary:
        temporary.write(encoded)
        temp_path = Path(temporary.name)
    temp_path.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the live OCI MOD directories and export a JSON lock."
    )
    parser.add_argument(
        "--main-dir",
        type=Path,
        default=Path("/opt/ivrm/compose/minecraft-main"),
    )
    parser.add_argument("--container", default="mc-main")
    parser.add_argument("--resource-container", default="mc-resource")
    parser.add_argument("--expected-count", type=int, default=80)
    parser.add_argument("--minecraft", default="26.1.2")
    parser.add_argument("--loader", default="neoforge")
    parser.add_argument("--loader-version", default="26.1.2.81")
    parser.add_argument("--java", type=int, default=25)
    parser.add_argument(
        "--side-overrides",
        type=Path,
        default=Path("manifests/side-overrides.json"),
    )
    parser.add_argument(
        "--distribution-overrides",
        type=Path,
        default=Path("manifests/distribution-overrides.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("manifests/main-26.1.2-80.lock.json"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    host_dir = args.main_dir / "mods"
    data_dir = args.main_dir / "data" / "mods"

    main_status, health = inspect_container(args.container)
    if (main_status, health) != ("running", "healthy"):
        raise ExportError(
            f"{args.container} must be running healthy, got {main_status}/{health}"
        )

    resource_status = inspect_optional_container(args.resource_container)
    if resource_status in {"running", "restarting"}:
        raise ExportError(
            f"{args.resource_container} must remain stopped, got {resource_status}"
        )

    side_overrides = load_json(args.side_overrides)
    distribution_overrides = load_json(args.distribution_overrides)
    host = directory_hashes(host_dir)
    data = directory_hashes(data_dir)
    container = container_hashes(args.container)

    if len(host) != args.expected_count:
        raise ExportError(
            f"Host JAR count must be {args.expected_count}, got {len(host)}"
        )
    compare_hash_sets("Data MOD directory", host, data)
    compare_hash_sets("Container /data/mods", host, container)

    mods: list[dict[str, Any]] = []
    seen_primary_ids: dict[str, str] = {}

    for filename, digest in sorted(host.items(), key=lambda item: item[0].lower()):
        jar_path = host_dir / filename
        mod_id, display_name, mod_ids = parse_jar_metadata(jar_path)
        if not VALID_MOD_ID.fullmatch(mod_id):
            raise ExportError(f"Invalid primary modId '{mod_id}' in {filename}")
        if mod_id in seen_primary_ids:
            raise ExportError(
                f"Duplicate primary modId '{mod_id}': "
                f"{seen_primary_ids[mod_id]} and {filename}"
            )
        seen_primary_ids[mod_id] = filename

        side, side_source = resolve_side(filename, mod_ids, side_overrides)
        validate_side(side, filename)
        source, project_id, file_id = resolve_distribution(
            filename,
            mod_ids,
            distribution_overrides,
        )

        mods.append(
            {
                "name": display_name,
                "modId": mod_id,
                "modIds": mod_ids,
                "filename": filename,
                "sha256": digest,
                "sizeBytes": jar_path.stat().st_size,
                "side": side,
                "sideSource": side_source,
                "source": source,
                "projectId": project_id,
                "fileId": file_id,
            }
        )

    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "name": "IVRM DailyTech Adventure Main",
        "minecraft": args.minecraft,
        "loader": args.loader,
        "loaderVersion": args.loader_version,
        "java": args.java,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "jarCount": len(mods),
        "mods": mods,
    }
    atomic_json_write(args.output, payload)

    lock_sha = sha256_file(args.output)
    checksum_path = args.output.with_suffix(args.output.suffix + ".sha256")
    checksum_path.write_text(
        f"{lock_sha}  {args.output.name}\n",
        encoding="utf-8",
    )

    server_only = sum(1 for mod in mods if mod["side"] == "server")
    both = sum(1 for mod in mods if mod["side"] == "both")
    client_only = sum(1 for mod in mods if mod["side"] == "client")

    print("OCI MOD lock export complete")
    print(f"Main={main_status}/{health}")
    print(f"Resource={resource_status}")
    print(f"Host/Data/Container JAR count={len(mods)}")
    print(f"Side classification: both={both} server={server_only} client={client_only}")
    print(f"Output={args.output}")
    print(f"SHA256={lock_sha}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ExportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
