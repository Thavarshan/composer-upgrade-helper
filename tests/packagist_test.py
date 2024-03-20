import unittest
from src.packagist import Packagist


class PackagistTest(unittest.TestCase):

    def test_get_latest_version_of_given_package(self):
        package = 'monolog/monolog'
        packagist = Packagist()
        versions = packagist.get_package_versions(package)
        latest_version = packagist.get_latest_package_version(package)

        self.assertIn(latest_version, versions)
