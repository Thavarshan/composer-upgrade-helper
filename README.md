# Composer Upgrade Helper (experimental Python utility)

A small Python learning project that reads the `require` section of a PHP project's `composer.json`, asks Packagist for newer versions, and **rewrites the file**.

**Status: experimental. This is not a safe, automatic production dependency updater.** It does not currently check Composer's dependency solver, PHP/platform compatibility, stability rules, version constraint ranges, or the project's test suite. Do not point it at a production project without a backup and a reviewable Git diff.

## What the current code does

- Reads `require` from the configured `composer.json`.
- Skips PHP/platform extension entries beginning with `php` or `ext-`.
- Looks up package versions using Packagist and attempts to compare them.
- Rewrites `require` constraints using caret (`^`) versions, then saves `composer.json` in place.
- Does **not** update `require-dev` or run `composer update`.

**Known limitations:** Composer constraints such as `*`, `^1.2 || ^2.0`, `~1.2` and dev branches are not reliably supported by the current Python version comparison. Some inputs may fail or produce incorrect changes. The tool has no dry-run or rollback mechanism yet.

## Local setup

Use a current Python 3 interpreter (the repository has older pinned dependencies; upgrade them only after testing).

```bash
git clone https://github.com/Thavarshan/composer-upgrade-helper.git
cd composer-upgrade-helper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run **only** against a disposable copy

1. In a separate test directory, create a valid `composer.json` with a few simple, public PHP dependencies, or copy one from a project into a temporary Git worktree.
2. Edit `app.py` and set `composer_file_path` to the **absolute path of that disposable file**. The checked-in default (`modified_files/composer.json`) is a placeholder and may not exist.
3. Run:

   ```bash
   python app.py
   ```

4. Inspect the resulting JSON and `git diff`. Do not accept constraints just because the script printed an update.
5. In a real PHP project, only after reviewing constraints and platform requirements, use `composer validate --strict`, `composer update --dry-run`, a normal `composer update` in an isolated branch, vulnerability auditing, and the project's tests before any merge.

For production dependency management, use established Composer tools and human review until this experiment is hardened.

## Improvements needed before trusting automatic writes

- Parse Composer constraints using Composer-compatible semantics instead of Python package-version rules.
- Add explicit CLI path input, dry-run/diff output, input validation, atomic file replacement and rollback safety.
- Preserve `require` and `require-dev` separately; do not mutate unsupported constraints.
- Exclude or handle prereleases, aliases and platform dependencies correctly.
- Add tests for complex constraints, version regressions, network failures, malformed JSON and file permission errors.
- Check dependency solver compatibility and run a complete project test matrix.

Contributions are welcome through [issues](https://github.com/Thavarshan/composer-upgrade-helper/issues) and focused pull requests. Please include a fixture and a failing test for bugs.

## License

MIT — see [LICENSE](LICENSE).
