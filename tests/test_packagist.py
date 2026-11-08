import unittest
from unittest.mock import Mock

import requests

from src.packagist import Packagist


class PackagistTest(unittest.TestCase):
    def test_selects_only_highest_stable_full_semver(self):
        packagist = Packagist()
        packagist.get_package_versions = Mock(
            return_value=[
                "dev-main",
                "2.9.0-beta1",
                "v2.8.0",
                "2.10.0",
                "2.10.0.0",
            ]
        )

        self.assertEqual(packagist.get_latest_package_version("vendor/pkg"), "2.10.0")

    def test_returns_none_when_no_stable_releases_exist(self):
        packagist = Packagist()
        packagist.get_package_versions = Mock(return_value=["dev-main", "1.0.0-rc1"])

        self.assertIsNone(packagist.get_latest_package_version("vendor/pkg"))

    def test_uses_timeout_and_rejects_bad_response(self):
        packagist = Packagist(timeout=7)
        response = Mock()
        response.json.return_value = {"package": {"versions": {"1.0.0": {}}}}
        packagist.session.get = Mock(return_value=response)

        self.assertEqual(packagist.get_package_versions("vendor/pkg"), ["1.0.0"])
        packagist.session.get.assert_called_once_with(
            "https://packagist.org/packages/vendor/pkg.json", timeout=7
        )

        response.json.return_value = []
        packagist.get_package_info.cache_clear()
        self.assertEqual(packagist.get_package_versions("vendor/bad"), [])

    def test_network_failure_returns_no_package_info(self):
        packagist = Packagist()
        packagist.session.get = Mock(side_effect=requests.Timeout("offline"))

        self.assertIsNone(packagist.get_package_info("vendor/offline"))

    def test_package_name_is_escaped_in_url(self):
        self.assertEqual(
            Packagist.create_package_link("vendor/my package"),
            "https://packagist.org/packages/vendor/my%20package.json",
        )


if __name__ == "__main__":
    unittest.main()
