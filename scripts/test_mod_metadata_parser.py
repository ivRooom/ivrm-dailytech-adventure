#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from mod_metadata_parser import parse_standard_metadata


class ModMetadataParserTest(unittest.TestCase):
    def test_neoforge_mods_header_with_inline_comment(self) -> None:
        metadata = '''modLoader="javafml"
loaderVersion="[2,)"
license="MIT"

[[mods]] #mandatory
modId="example_mod"
version="1.0.0"
displayName="Example Mod"

[[dependencies.example_mod]]
modId="neoforge"
type="required"
versionRange="[26.1.2,)"
ordering="NONE"
side="BOTH"
'''

        with tempfile.TemporaryDirectory() as directory:
            jar_path = Path(directory) / "example.jar"
            with zipfile.ZipFile(jar_path, "w") as archive:
                archive.writestr("META-INF/neoforge.mods.toml", metadata)

            self.assertEqual(
                parse_standard_metadata(jar_path),
                ("example_mod", "Example Mod", ["example_mod"]),
            )

    def test_multiple_mod_blocks(self) -> None:
        metadata = '''modLoader="javafml"
loaderVersion="[2,)"
license="MIT"

[[mods]]
modId="first_mod"
displayName="First Mod"

[[mods]] # another bundled mod
modId="second_mod"
displayName="Second Mod"
'''

        with tempfile.TemporaryDirectory() as directory:
            jar_path = Path(directory) / "bundle.jar"
            with zipfile.ZipFile(jar_path, "w") as archive:
                archive.writestr("META-INF/neoforge.mods.toml", metadata)

            self.assertEqual(
                parse_standard_metadata(jar_path),
                ("first_mod", "First Mod", ["first_mod", "second_mod"]),
            )


if __name__ == "__main__":
    unittest.main()
