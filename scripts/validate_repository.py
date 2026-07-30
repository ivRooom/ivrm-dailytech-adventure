#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

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


def main() -> int:
    errors: list[str] = []
    validate_files(errors)
    validate_json(errors)
    validate_quest_source(errors)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Repository validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
