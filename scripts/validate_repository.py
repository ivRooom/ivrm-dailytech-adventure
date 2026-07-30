#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {
    "server.properties",
    "whitelist.json",
    "ops.json",
    "usercache.json",
}
FORBIDDEN_SUFFIXES = {".jar", ".pem", ".key", ".p12", ".jks", ".db", ".sqlite"}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "discord webhook": re.compile(r"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/"),
    "generic token": re.compile(r"(?i)(?:rcon_password|api_key|secret_key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
}
ID_PATTERN = re.compile(r"^[A-F0-9]{16}$")
MOD_ID_PATTERN = re.compile(r"^[a-z0-9_.-]+$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
VALID_SIDES = {"both", "server", "client"}
VALID_SIDE_SOURCES = {"filename-override", "mod-id-override", "default"}
VALID_SOURCES = {"curseforge", "modrinth", "github", "manual"}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def validate_files(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT)
        if path.name in FORBIDDEN_NAMES:
            fail(f"禁止ファイル: {rel}", errors)
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            fail(f"禁止拡張子: {rel}", errors)
        if path.stat().st_size > 5 * 1024 * 1024:
            fail(f"5MiB超過: {rel}", errors)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail(f"UTF-8でないファイル: {rel}", errors)
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                fail(f"秘密情報候補({label}): {rel}", errors)


def validate_json(errors: list[str]) -> None:
    for path in ROOT.rglob("*.json"):
        if ".git" in path.parts:
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"JSONエラー {path.relative_to(ROOT)}: {exc}", errors)


def validate_quest_source(errors: list[str]) -> None:
    source = ROOT / "config-src" / "ftbquests"
    ids: dict[str, Path] = {}
    quest_ids: set[str] = set()
    dependencies: list[tuple[Path, str]] = []

    for path in source.rglob("*.yml"):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            fail(f"YAMLエラー {path.relative_to(ROOT)}: {exc}", errors)
            continue

        def register(value: object) -> None:
            if not isinstance(value, str):
                return
            if not ID_PATTERN.fullmatch(value):
                fail(f"16桁HEXでないID {value}: {path.relative_to(ROOT)}", errors)
            elif value in ids:
                fail(f"ID重複 {value}: {ids[value].relative_to(ROOT)} / {path.relative_to(ROOT)}", errors)
            else:
                ids[value] = path

        for group in data.get("groups", []) or []:
            register(group.get("id"))
        chapter = data.get("chapter")
        if isinstance(chapter, dict):
            register(chapter.get("id"))
        for quest in data.get("quests", []) or []:
            quest_id = quest.get("id")
            register(quest_id)
            if isinstance(quest_id, str):
                quest_ids.add(quest_id)
            for dep in quest.get("dependencies", []) or []:
                dependencies.append((path, dep))

    for path, dep in dependencies:
        if dep not in quest_ids:
            fail(f"存在しないQuest依存 {dep}: {path.relative_to(ROOT)}", errors)


def require_fields(
    data: dict[str, Any],
    fields: set[str],
    *,
    label: str,
    errors: list[str],
) -> None:
    missing = sorted(fields - set(data))
    if missing:
        fail(f"{label} 必須項目不足: {missing}", errors)


def validate_side_overrides(errors: list[str]) -> None:
    path = ROOT / "manifests" / "side-overrides.json"
    if not path.exists():
        fail("manifests/side-overrides.json がありません", errors)
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(data, dict):
        fail("side-overrides.json のルートはobject必須", errors)
        return

    default = data.get("default")
    if default not in VALID_SIDES:
        fail(f"side-overrides default不正: {default}", errors)

    for section in ("byModId", "byFilename"):
        mapping = data.get(section)
        if not isinstance(mapping, dict):
            fail(f"side-overrides {section}はobject必須", errors)
            continue
        for key, side in mapping.items():
            if not isinstance(key, str) or not key:
                fail(f"side-overrides {section}に空キー", errors)
            if side not in VALID_SIDES:
                fail(f"side-overrides {section}.{key}のside不正: {side}", errors)


def validate_distribution_overrides(errors: list[str]) -> None:
    path = ROOT / "manifests" / "distribution-overrides.json"
    if not path.exists():
        fail("manifests/distribution-overrides.json がありません", errors)
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(data, dict):
        fail("distribution-overrides.json のルートはobject必須", errors)
        return

    for section in ("byModId", "byFilename"):
        mapping = data.get(section)
        if not isinstance(mapping, dict):
            fail(f"distribution-overrides {section}はobject必須", errors)
            continue
        for key, entry in mapping.items():
            if not isinstance(key, str) or not key:
                fail(f"distribution-overrides {section}に空キー", errors)
            if not isinstance(entry, dict):
                fail(f"distribution-overrides {section}.{key}はobject必須", errors)
                continue
            source = entry.get("source")
            if source not in VALID_SOURCES:
                fail(
                    f"distribution-overrides {section}.{key} source不正: {source}",
                    errors,
                )
            for id_field in ("projectId", "fileId"):
                value = entry.get(id_field)
                if value is not None and not (
                    (isinstance(value, int) and value > 0)
                    or (isinstance(value, str) and value.strip())
                ):
                    fail(
                        f"distribution-overrides {section}.{key} "
                        f"{id_field}不正: {value}",
                        errors,
                    )


def validate_mod_locks(errors: list[str]) -> None:
    required_root = {
        "schemaVersion",
        "name",
        "minecraft",
        "loader",
        "loaderVersion",
        "java",
        "generatedAt",
        "jarCount",
        "mods",
    }
    required_mod = {
        "name",
        "modId",
        "modIds",
        "filename",
        "sha256",
        "sizeBytes",
        "side",
        "sideSource",
        "source",
        "projectId",
        "fileId",
    }

    for path in sorted((ROOT / "manifests").glob("*.lock.json")):
        rel = path.relative_to(ROOT)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            fail(f"{rel} のルートはobject必須", errors)
            continue

        require_fields(data, required_root, label=str(rel), errors=errors)
        if data.get("schemaVersion") != 1:
            fail(f"{rel} schemaVersionは1必須", errors)
        if data.get("loader") not in {"neoforge", "forge", "fabric"}:
            fail(f"{rel} loader不正: {data.get('loader')}", errors)

        mods = data.get("mods")
        if not isinstance(mods, list):
            fail(f"{rel} modsはarray必須", errors)
            continue
        if data.get("jarCount") != len(mods):
            fail(
                f"{rel} jarCount={data.get('jarCount')} とmods件数={len(mods)}が不一致",
                errors,
            )

        filenames: set[str] = set()
        primary_ids: set[str] = set()
        for index, mod in enumerate(mods):
            label = f"{rel} mods[{index}]"
            if not isinstance(mod, dict):
                fail(f"{label}はobject必須", errors)
                continue
            require_fields(mod, required_mod, label=label, errors=errors)

            filename = mod.get("filename")
            if not isinstance(filename, str) or not filename.endswith(".jar"):
                fail(f"{label} filename不正: {filename}", errors)
            elif filename in filenames:
                fail(f"{rel} filename重複: {filename}", errors)
            else:
                filenames.add(filename)

            mod_id = mod.get("modId")
            if not isinstance(mod_id, str) or not MOD_ID_PATTERN.fullmatch(mod_id):
                fail(f"{label} modId不正: {mod_id}", errors)
            elif mod_id in primary_ids:
                fail(f"{rel} primary modId重複: {mod_id}", errors)
            else:
                primary_ids.add(mod_id)

            mod_ids = mod.get("modIds")
            if not isinstance(mod_ids, list) or not mod_ids:
                fail(f"{label} modIdsは1件以上のarray必須", errors)
            else:
                if len(set(mod_ids)) != len(mod_ids):
                    fail(f"{label} modIds重複", errors)
                for item in mod_ids:
                    if not isinstance(item, str) or not MOD_ID_PATTERN.fullmatch(item):
                        fail(f"{label} modIds不正: {item}", errors)
                if isinstance(mod_id, str) and mod_id not in mod_ids:
                    fail(f"{label} modIdがmodIdsに含まれない", errors)

            sha256 = mod.get("sha256")
            if not isinstance(sha256, str) or not SHA256_PATTERN.fullmatch(sha256):
                fail(f"{label} sha256不正", errors)
            if not isinstance(mod.get("sizeBytes"), int) or mod.get("sizeBytes", 0) <= 0:
                fail(f"{label} sizeBytes不正: {mod.get('sizeBytes')}", errors)
            if mod.get("side") not in VALID_SIDES:
                fail(f"{label} side不正: {mod.get('side')}", errors)
            if mod.get("sideSource") not in VALID_SIDE_SOURCES:
                fail(f"{label} sideSource不正: {mod.get('sideSource')}", errors)
            if mod.get("source") not in VALID_SOURCES:
                fail(f"{label} source不正: {mod.get('source')}", errors)

            for id_field in ("projectId", "fileId"):
                value = mod.get(id_field)
                if value is not None and not (
                    (isinstance(value, int) and value > 0)
                    or (isinstance(value, str) and value.strip())
                ):
                    fail(f"{label} {id_field}不正: {value}", errors)


def main() -> int:
    errors: list[str] = []
    validate_files(errors)
    validate_json(errors)
    validate_quest_source(errors)
    validate_side_overrides(errors)
    validate_distribution_overrides(errors)
    validate_mod_locks(errors)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Repository validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
