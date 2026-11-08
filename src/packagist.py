"""Small, cached client for Packagist package version metadata."""

import logging
import re
from functools import lru_cache
from urllib.parse import quote

import requests


_STABLE_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$", re.IGNORECASE)


class Packagist:
    """Fetch stable release information from the Packagist API."""

    def __init__(self, timeout=15):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.timeout = timeout

    def get_latest_package_version(self, name):
        """Return the highest stable three-part release, or ``None``."""
        versions = self.get_package_versions(name)
        stable_versions = []
        for version in versions:
            match = _STABLE_VERSION.fullmatch(version) if isinstance(version, str) else None
            if match:
                stable_versions.append((tuple(int(part) for part in match.groups()), version))

        if not stable_versions:
            return None
        return max(stable_versions, key=lambda release: release[0])[1].lstrip("vV")

    def get_package_versions(self, name):
        """Return release names advertised by Packagist, or an empty list."""
        package_info = self.get_package_info(name)
        if not isinstance(package_info, dict):
            return []
        versions = package_info.get("versions", {})
        if not isinstance(versions, dict):
            return []
        return list(versions.keys())

    @lru_cache(maxsize=128)
    def get_package_info(self, name):
        """Fetch a package document; network and response errors fail closed."""
        try:
            response = self.session.get(self.create_package_link(name), timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            self.logger.warning("Unable to fetch Packagist package %s: %s", name, error)
            return None

        if not isinstance(payload, dict):
            self.logger.warning("Packagist returned an invalid document for %s", name)
            return None
        package = payload.get("package")
        if not isinstance(package, dict):
            self.logger.warning("Packagist response has no package object for %s", name)
            return None
        return package

    @staticmethod
    def create_package_link(name):
        """Construct a correctly escaped Packagist package API URL."""
        return "https://packagist.org/packages/{}.json".format(quote(name, safe="/"))
