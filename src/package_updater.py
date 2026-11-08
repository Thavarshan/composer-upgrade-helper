"""Create conservative, reviewable Composer dependency update previews."""

import copy
import difflib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from .packagist import Packagist


_SUPPORTED_CONSTRAINT = re.compile(r"^([~^])(\d+(?:\.\d+){0,2})$")
_STABLE_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$", re.IGNORECASE)
_PLATFORM_PACKAGES = {
    "php",
    "hhvm",
    "composer-plugin-api",
    "composer-runtime-api",
}


class PackageUpdater:
    """Preview compatible stable updates for a project's ``composer.json``."""

    def __init__(self, composer_file, packagist=None):
        self.composer_file = Path(composer_file)
        if self.composer_file.is_symlink():
            raise ValueError("Refusing to read a symlink as composer.json")
        if not self.composer_file.is_file():
            raise FileNotFoundError("composer.json does not exist or is not a file")

        self._original_bytes = self.composer_file.read_bytes()
        self.composer_data = self._parse_composer_data(self._original_bytes)
        self.packagist = packagist or Packagist()
        self.preview_data = copy.deepcopy(self.composer_data)
        self.updates = {}
        self.skipped = {}

    @staticmethod
    def _parse_composer_data(contents):
        try:
            data = json.loads(contents.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("composer.json must contain valid UTF-8 JSON") from error

        if not isinstance(data, dict):
            raise ValueError("composer.json must contain a JSON object")

        for section in ("require", "require-dev"):
            dependencies = data.get(section, {})
            if not isinstance(dependencies, dict):
                raise ValueError("composer.json {} must be an object".format(section))
            for package, constraint in dependencies.items():
                if not isinstance(package, str) or not isinstance(constraint, str):
                    raise ValueError(
                        "composer.json {} dependencies must map names to strings".format(
                            section
                        )
                    )
        return data

    @staticmethod
    def _is_platform_package(name):
        normalized = name.lower()
        return (
            normalized in _PLATFORM_PACKAGES
            or normalized.startswith(("php-", "hhvm-", "ext-", "lib-"))
        )

    @staticmethod
    def _parse_constraint(constraint):
        """Return operator, numeric floor, and exclusive upper bound if supported."""
        match = _SUPPORTED_CONSTRAINT.fullmatch(constraint)
        if not match:
            return None

        operator, version_text = match.groups()
        parts = tuple(int(part) for part in version_text.split("."))
        floor = parts + (0,) * (3 - len(parts))

        if operator == "^":
            if floor[0] > 0:
                upper = (floor[0] + 1, 0, 0)
            elif floor[1] > 0:
                upper = (0, floor[1] + 1, 0)
            else:
                upper = (0, 0, floor[2] + 1)
        elif len(parts) == 3:
            upper = (floor[0], floor[1] + 1, 0)
        else:
            upper = (floor[0] + 1, 0, 0)

        return operator, floor, upper

    @staticmethod
    def _parse_stable_version(version):
        if not isinstance(version, str):
            return None
        match = _STABLE_VERSION.fullmatch(version)
        if not match:
            return None
        return tuple(int(part) for part in match.groups())

    def update(self, write=False):
        """Build an update preview; write it only when ``write=True``."""
        self.preview_data = copy.deepcopy(self.composer_data)
        self.updates = {}
        self.skipped = {}

        for section in ("require", "require-dev"):
            dependencies = self.preview_data.get(section, {})
            section_updates = {}
            for package, constraint in dependencies.items():
                if self._is_platform_package(package):
                    continue

                parsed_constraint = self._parse_constraint(constraint)
                if not parsed_constraint:
                    self.skipped[package] = "unsupported Composer constraint: {}".format(
                        constraint
                    )
                    continue

                operator, floor, upper = parsed_constraint
                versions = self.packagist.get_package_versions(package)
                compatible = []
                for version in versions:
                    parsed_version = self._parse_stable_version(version)
                    if parsed_version and floor <= parsed_version < upper:
                        compatible.append(parsed_version)

                if not compatible:
                    self.skipped[package] = "no newer stable release within {}".format(
                        constraint
                    )
                    continue

                latest = max(compatible)
                if latest <= floor:
                    continue

                new_constraint = "{}{}.{}.{}".format(operator, *latest)
                dependencies[package] = new_constraint
                section_updates[package] = {
                    "from": constraint,
                    "to": new_constraint,
                }

            if section_updates:
                self.updates[section] = section_updates

        if write and self.updates:
            self.apply()
        return self.updates

    def apply(self):
        """Validate and atomically write the most recent non-empty preview."""
        if not self.updates:
            return False
        self._write_preview()
        return True

    def diff(self):
        """Return a unified diff of the current file and the generated preview."""
        current = self._original_bytes.decode("utf-8").splitlines(keepends=True)
        preview = self._serialize_preview().decode("utf-8").splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(
                current,
                preview,
                fromfile="composer.json (current)",
                tofile="composer.json (preview)",
            )
        )

    def _serialize_preview(self):
        return (json.dumps(self.preview_data, indent=4, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )

    def _validate_composer_json(self, contents):
        composer = shutil.which("composer")
        if not composer:
            raise RuntimeError("Composer CLI is required before writing updates")

        with tempfile.TemporaryDirectory(prefix="composer-upgrade-helper-") as directory:
            composer_file = Path(directory) / "composer.json"
            composer_file.write_bytes(contents)
            environment = os.environ.copy()
            environment.pop("COMPOSER", None)
            environment.setdefault("COMPOSER_ROOT_VERSION", "1.0.0")
            try:
                result = subprocess.run(
                    [
                        composer,
                        "validate",
                        "--strict",
                        "--no-check-publish",
                        "--no-check-lock",
                        "--no-interaction",
                        "--no-plugins",
                    ],
                    cwd=directory,
                    capture_output=True,
                    env=environment,
                    text=True,
                    timeout=30,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("Composer validation timed out") from error
            if result.returncode:
                output = (result.stdout + result.stderr).strip()
                raise RuntimeError("Composer validation failed: {}".format(output))

    def _write_preview(self):
        preview_bytes = self._serialize_preview()
        self._validate_composer_json(preview_bytes)

        if self.composer_file.is_symlink():
            raise RuntimeError("Refusing to replace a symlinked composer.json")
        if self.composer_file.read_bytes() != self._original_bytes:
            raise RuntimeError("composer.json changed while updates were being prepared")

        permissions = stat.S_IMODE(self.composer_file.stat().st_mode)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".{}-".format(self.composer_file.name),
                suffix=".tmp",
                dir=str(self.composer_file.parent),
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(preview_bytes)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.chmod(str(temporary_path), permissions)

            if self.composer_file.is_symlink() or self.composer_file.read_bytes() != self._original_bytes:
                raise RuntimeError("composer.json changed while updates were being prepared")

            os.replace(str(temporary_path), str(self.composer_file))
            temporary_path = None
            self._original_bytes = preview_bytes
            self.composer_data = copy.deepcopy(self.preview_data)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
