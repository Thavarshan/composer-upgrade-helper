import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from app import main


class FakePackagist:
    def get_package_versions(self, name):
        return ["1.4.0"]


class AppTest(unittest.TestCase):
    def test_default_cli_mode_prints_diff_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            composer_file = Path(directory) / "composer.json"
            original = '{"name":"example/project","require":{"vendor/pkg":"^1.0"}}\n'
            composer_file.write_text(original, encoding="utf-8")
            output = StringIO()

            with patch("src.package_updater.Packagist", return_value=FakePackagist()):
                with redirect_stdout(output):
                    result = main([str(composer_file)])

            self.assertEqual(result, 0)
            self.assertIn("^1.4.0", output.getvalue())
            self.assertIn("Preview only", output.getvalue())
            self.assertEqual(composer_file.read_text(encoding="utf-8"), original)

    def test_write_flag_validates_and_applies_after_showing_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            composer_file = Path(directory) / "composer.json"
            composer_file.write_text(
                json.dumps(
                    {"name": "example/project", "require": {"vendor/pkg": "^1.0"}}
                ),
                encoding="utf-8",
            )
            output = StringIO()

            with patch("src.package_updater.Packagist", return_value=FakePackagist()):
                with patch(
                    "src.package_updater.PackageUpdater._validate_composer_json"
                ) as validate:
                    with redirect_stdout(output):
                        result = main([str(composer_file), "--write"])

            validate.assert_called_once()
            self.assertEqual(result, 0)
            self.assertIn("^1.4.0", output.getvalue())
            self.assertIn("Validated and wrote", output.getvalue())
            self.assertEqual(
                json.loads(composer_file.read_text(encoding="utf-8"))["require"][
                    "vendor/pkg"
                ],
                "^1.4.0",
            )


if __name__ == "__main__":
    unittest.main()
