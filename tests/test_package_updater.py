import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.package_updater import PackageUpdater


class FakePackagist:
    def __init__(self, versions):
        self.versions = versions
        self.queried = []

    def get_package_versions(self, name):
        self.queried.append(name)
        return self.versions.get(name, [])


class PackageUpdaterTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.composer_file = Path(self.directory.name) / "composer.json"

    def create_composer_file(self, data):
        original = (json.dumps(data, indent=2) + "\n").encode("utf-8")
        self.composer_file.write_bytes(original)
        return original

    def test_preview_updates_simple_constraints_without_writing(self):
        data = {
            "name": "example/project",
            "require": {
                "php": ">=8.3",
                "ext-json": "*",
                "phpunit/phpunit": "^10.2",
                "vendor/caret": "^1.2",
                "vendor/tilde": "~1.2.3",
                "vendor/wildcard": "*",
                "vendor/or": "1.2 || ^2.0",
                "vendor/exact": "1.2.3",
                "vendor/prefix": "v1.2.3",
                "vendor/dev": "dev-main as 1.0.x-dev",
                "vendor/prerelease": "^1.2.0-beta1",
            },
            "require-dev": {"vendor/dev-tool": "^2.0"},
            "scripts": {"test": "phpunit"},
        }
        original = self.create_composer_file(data)
        packagist = FakePackagist(
            {
                "phpunit/phpunit": ["v10.6.1", "11.0.0", "10.7.0-rc1"],
                "vendor/caret": ["1.2.0", "v1.8.2", "2.0.0"],
                "vendor/tilde": ["1.2.4", "1.2.10", "1.3.0", "1.2.11-beta1"],
                "vendor/wildcard": ["2.0.0"],
                "vendor/or": ["2.3.0"],
                "vendor/exact": ["1.3.0"],
                "vendor/prefix": ["2.0.0"],
                "vendor/dev": ["1.0.0"],
                "vendor/prerelease": ["1.3.0"],
                "vendor/dev-tool": ["2.5.0", "3.0.0"],
            }
        )

        updater = PackageUpdater(self.composer_file, packagist=packagist)
        updates = updater.update()

        self.assertEqual(updates["require"]["vendor/caret"]["to"], "^1.8.2")
        self.assertEqual(updates["require"]["vendor/tilde"]["to"], "~1.2.10")
        self.assertEqual(updates["require"]["phpunit/phpunit"]["to"], "^10.6.1")
        self.assertEqual(updates["require-dev"]["vendor/dev-tool"]["to"], "^2.5.0")
        self.assertEqual(
            set(packagist.queried),
            {"phpunit/phpunit", "vendor/caret", "vendor/tilde", "vendor/dev-tool"},
        )
        self.assertEqual(self.composer_file.read_bytes(), original)
        self.assertEqual(updater.preview_data["require"]["php"], ">=8.3")
        self.assertEqual(updater.preview_data["require"]["vendor/wildcard"], "*")
        self.assertIn("composer.json (preview)", updater.diff())

    def test_platform_packages_are_skipped_without_prefix_false_positives(self):
        data = {
            "require": {
                "php": ">=8.3",
                "php-64bit": "*",
                "hhvm": "*",
                "ext-curl": "*",
                "lib-openssl": "*",
                "composer-plugin-api": "^2.0",
                "composer-runtime-api": "^2.0",
                "phpunit/phpunit": "^10.0",
            }
        }
        self.create_composer_file(data)
        packagist = FakePackagist({"phpunit/phpunit": ["10.5.0"]})

        PackageUpdater(self.composer_file, packagist=packagist).update()

        self.assertEqual(packagist.queried, ["phpunit/phpunit"])

    def test_explicit_write_is_atomic_preserves_mode_and_requires_validation(self):
        original = self.create_composer_file(
            {"name": "example/project", "require": {"vendor/pkg": "^1.0"}}
        )
        os.chmod(self.composer_file, 0o640)
        updater = PackageUpdater(
            self.composer_file,
            packagist=FakePackagist({"vendor/pkg": ["1.4.2"]}),
        )
        with patch.object(updater, "_validate_composer_json") as validate:
            updater.update(write=True)

        validate.assert_called_once()
        saved = json.loads(self.composer_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["require"]["vendor/pkg"], "^1.4.2")
        self.assertEqual(stat.S_IMODE(self.composer_file.stat().st_mode), 0o640)
        self.assertNotEqual(self.composer_file.read_bytes(), original)
        self.assertEqual(list(self.composer_file.parent.glob("*.tmp")), [])

    def test_validation_failure_keeps_original_file(self):
        original = self.create_composer_file(
            {"name": "example/project", "require": {"vendor/pkg": "^1.0"}}
        )
        updater = PackageUpdater(
            self.composer_file,
            packagist=FakePackagist({"vendor/pkg": ["1.4.2"]}),
        )
        with patch.object(
            updater, "_validate_composer_json", side_effect=RuntimeError("invalid")
        ):
            with self.assertRaisesRegex(RuntimeError, "invalid"):
                updater.update(write=True)
        self.assertEqual(self.composer_file.read_bytes(), original)

    def test_rejects_bad_json_directories_and_symlinks(self):
        self.composer_file.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "valid UTF-8 JSON"):
            PackageUpdater(self.composer_file, packagist=FakePackagist({}))

        self.composer_file.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "JSON object"):
            PackageUpdater(self.composer_file, packagist=FakePackagist({}))

        directory = Path(self.directory.name) / "directory"
        directory.mkdir()
        with self.assertRaises(FileNotFoundError):
            PackageUpdater(directory, packagist=FakePackagist({}))

        self.composer_file.unlink()
        target = Path(self.directory.name) / "target.json"
        target.write_text("{}", encoding="utf-8")
        self.composer_file.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            PackageUpdater(self.composer_file, packagist=FakePackagist({}))

    def test_refuses_to_replace_file_changed_since_preview(self):
        self.create_composer_file(
            {"name": "example/project", "require": {"vendor/pkg": "^1.0"}}
        )
        updater = PackageUpdater(
            self.composer_file,
            packagist=FakePackagist({"vendor/pkg": ["1.4.2"]}),
        )
        updater.update()
        changed = '{"name":"other/project"}\n'
        self.composer_file.write_text(changed, encoding="utf-8")

        with patch.object(updater, "_validate_composer_json"):
            with self.assertRaisesRegex(RuntimeError, "changed"):
                updater.apply()
        self.assertEqual(self.composer_file.read_text(encoding="utf-8"), changed)


if __name__ == "__main__":
    unittest.main()
