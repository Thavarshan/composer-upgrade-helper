# PHP Composer Package Updater

This project provides a Python tool to automatically update the `composer.json` file in a PHP project with the latest versions of dependencies from Packagist. It aims to streamline the maintenance of PHP project dependencies, ensuring they are always up to date with the latest releases.

## Features

- **Automatic Updates**: Automatically updates your `composer.json` with the latest versions of dependencies.
- **Packagist Integration**: Fetches version information directly from Packagist, the main Composer repository.
- **Logging and Error Handling**: Robust error handling and logging for smooth operation and troubleshooting.

## Requirements

- Python 3.6 or higher
- `requests` library
- `packaging` library

## Installation

Clone this repository to your local machine using:

```bash
git clone https://yourrepository.com/path/to/repo.git
```

Navigate into the project directory:

```bash
cd path/to/repo
```

It's recommended to use a virtual environment for Python projects. Create and activate one with:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Usage

To use the package updater, execute the `app.py` script from the command line:

```bash
python app.py
```

Make sure to adjust the `composer_file_path` in `app.py` to point to your `composer.json` file:

```python
composer_file_path = 'path/to/your/composer.json'
```

## Configuration

No additional configuration is needed. However, you can customize the logging level and other settings by modifying the Python scripts directly.

## How It Works

The `PackageUpdater` class in `package_updater.py` reads your `composer.json`, queries Packagist for the latest versions of each package, and updates your `composer.json` file accordingly. It differentiates between PHP extensions and regular packages to only update what's necessary.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any bugs, feature requests, or improvements.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
