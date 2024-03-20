import re
import json
from packaging import version as version_parser
# Adjust import as necessary for your project structure
from .packagist import Packagist


class PackageUpdater:
    """
    Updates the composer.json file of a PHP project with the latest package versions from Packagist.
    """

    def __init__(self, composer_file):
        """
        Initializes the PackageUpdater with the path to the composer.json file.

        Args:
            composer_file (str): The file path to composer.json.
        """
        self.composer_file = composer_file
        self.package_dependencies = {}
        self.extensions = {}
        self._load_packages()

    def _load_packages(self):
        """
        Loads the package dependencies and extensions from the composer.json file.
        """
        dependencies = self._get_all_dependencies()
        for dependency, version in dependencies.items():
            if not re.match('^(ext-|php)', dependency):
                self.package_dependencies[dependency] = version
            else:
                self.extensions[dependency] = version

    def update(self):
        """
        Updates the composer.json file with the latest versions of the dependencies
        and returns a dictionary of updated packages and their new versions.

        Returns:
            dict: Updated packages with their latest versions.
        """
        composer_data = self._get_composer_data()
        updates = self.find_updatable_packages()  # Get updates

        # Merge updated dependencies and extensions into the composer data
        composer_data['require'] = {
            **self.extensions, **self.package_dependencies}

        with open(self.composer_file, 'w', encoding='utf-8') as write_file:
            json.dump(composer_data, write_file, indent=4)

        return updates

    def find_updatable_packages(self):
        """
        Identifies and updates package dependencies to their latest versions, if available.

        Returns:
            dict: A dictionary of package names and their updated versions.
        """
        updates = {}
        packagist = Packagist()

        for package, current_version in self.package_dependencies.items():
            current_version_stripped = current_version.replace('^', '')
            latest_version = packagist.get_latest_package_version(package)

            if version_parser.parse(current_version_stripped) < version_parser.parse(latest_version):
                updates[package] = latest_version  # Record the update
                self.package_dependencies[package] = f'^{latest_version}'

        return updates

    def _get_all_dependencies(self):
        """
        Retrieves all dependencies from the composer.json file.

        Returns:
            dict: A dictionary of all package dependencies.
        """
        return self._get_composer_data().get('require', {})

    def _get_composer_data(self):
        """
        Reads and returns the composer.json data.

        Returns:
            dict: The composer.json data as a dictionary.
        """
        with open(self.composer_file, 'r', encoding='utf-8') as json_file:
            return json.load(json_file)
