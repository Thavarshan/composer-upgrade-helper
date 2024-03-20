import re
import json
import unittest
from src.package_updater import PackageUpdator


class PackageUpdatorTest(unittest.TestCase):

    def test_get_all_dependencies(self):
        updator = PackageUpdator('composer.json')

        with open('composer.json', 'r+') as composer_file:
            dependencies = json.load(composer_file).get('require')

        self.assertEqual(dependencies, updator.get_all_dependencies())

    def test_get_package_dependencies(self):
        packages = {}
        updator = PackageUpdator('composer.json')

        with open('composer.json', 'r+') as composer_file:
            dependencies = json.load(composer_file).get('require')

            for dependency in dependencies:
                if not re.match('(ext)', dependency) and not re.match('(php)', dependency):
                    packages[dependency] = dependencies[dependency]

        self.assertEqual(packages, updator.get_packages())

    def test_find_updatable_packages(self):
        updator = PackageUpdator('composer.json')
        self.assertTrue(updator.find_updatable_packages())

    def test_update_packages(self):
        updator = PackageUpdator('composer.json')
        updator.update()
