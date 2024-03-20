import re
from functools import lru_cache
import logging
import requests
from packaging import version


class Packagist:
    """
    A client for interacting with the Packagist API to fetch PHP package information.

    Attributes:
        logger (logging.Logger): Logger instance for logging error messages.
        session (requests.Session): Session instance for making HTTP requests. This improves
                                    performance by reusing TCP connections.
    """

    def __init__(self):
        """
        Initializes the Packagist client with a logger and a requests session.
        """
        self.logger = logging.getLogger(__name__)  # Initializes a logger.
        # Creates a session to optimize network calls.
        self.session = requests.Session()

    def get_latest_package_version(self, name):
        """
        Retrieves the latest semantic version of a specified package.

        Args:
            name (str): The name of the package to query.

        Returns:
            str: The latest version of the package, adhering to semantic versioning.
        """
        versions = self.get_package_versions(name)
        # Filters out versions that do not conform to semantic versioning.
        semantic_versions = [ver for ver in versions if re.match(
            r'^v?\d+(\.\d+){0,2}(-\w+)?$', ver)]

        # If there are stable versions available, exclude pre-releases and build metadata versions.
        if len(semantic_versions) > 1:
            semantic_versions = [
                ver for ver in semantic_versions if not re.search(r'[-+]', ver)]

        # Fallback to the original version list if no semantic versions are found.
        if not semantic_versions:
            semantic_versions = versions

        # Uses the packaging.version.parse to accurately compare versions.
        latest_version = max(
            semantic_versions, key=lambda x: version.parse(x.replace('v', '')))

        return latest_version

    def get_package_versions(self, name):
        """
        Fetches all available versions of a specified package.

        Args:
            name (str): The name of the package.

        Returns:
            list[str]: A list of version strings for the package.
        """
        package_info = self.get_package_info(name)
        if package_info is not None:
            return list(package_info.get('versions', {}).keys())
        return []

    # Cache the results to avoid repeated API calls for the same package.
    @lru_cache(maxsize=128)
    def get_package_info(self, name):
        """
        Retrieves detailed information about a specified package from Packagist.

        Args:
            name (str): The name of the package.

        Returns:
            dict: A dictionary containing package information, or None if an error occurs.
        """
        try:
            response = self.session.get(self.create_package_link(name))
            response.raise_for_status()  # Checks for HTTP request errors.
            return response.json().get('package')
        except requests.RequestException as e:
            # Logs any request exceptions.
            self.logger.error("Error fetching package info: %s", e)
            return None

    def create_package_link(self, name):
        """
        Constructs the URL for accessing the Packagist API for a specific package.

        Args:
            name (str): The name of the package.

        Returns:
            str: The URL for the package's API endpoint on Packagist.
        """
        return f'https://packagist.org/packages/{name}.json'
