# Composer Upgrade Helper

Composer Upgrade Helper finds newer stable package releases from Packagist while keeping updates inside the simple Composer version ranges you already selected.

## Requirements

- Python 3.9 or newer
- Composer CLI is required only when applying updates
- Network access to Packagist is required to fetch package versions

## Install

```bash
git clone https://github.com/Thavarshan/composer-upgrade-helper.git
cd composer-upgrade-helper
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Preview updates

Pass the target project's `composer.json`. The command prints a unified diff and never changes the file by default:

```bash
python app.py ../my-php-project/composer.json
```

To validate the preview with `composer validate --strict` and atomically write it, pass `--write`:

```bash
python app.py ../my-php-project/composer.json --write
```

The helper preserves the rest of the JSON document and updates both `require` and `require-dev`. It considers only stable three-part releases and only the simple caret (`^1.2`) and tilde (`~1.2.3`) constraints. It keeps the existing range ceiling, so `^1.2` will not jump to `2.0.0`, and `~1.2.3` will not jump to `1.3.0`. Wildcards, exact versions, OR expressions, aliases, development branches, and prerelease constraints are left unchanged with a skip message.

The helper also leaves PHP, HHVM, Composer API, PHP extension, and system library platform requirements untouched. A failed Packagist request yields no update for that package. Applying changes fails closed if Composer is unavailable, validation fails, or the source file changes while the preview is being prepared.

## Development

Run the offline unit suite and linter with:

```bash
python -m pip install 'pytest>=8.4,<9' 'flake8>=7,<8'
python -m pytest
python -m flake8 app.py src tests
```

## Contributing

Bug reports and pull requests are welcome. Please include offline tests for changes to version selection or file writing.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
