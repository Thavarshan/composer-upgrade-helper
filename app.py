"""Command line entry point for Composer Upgrade Helper."""

import argparse
import sys
from pathlib import Path

from src.package_updater import PackageUpdater


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Preview compatible stable dependency updates for composer.json."
    )
    parser.add_argument(
        "composer_file",
        type=Path,
        help="path to the target composer.json file",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="validate the preview with Composer and atomically write it",
    )
    args = parser.parse_args(argv)

    try:
        updater = PackageUpdater(args.composer_file)
        updates = updater.update()
        preview_diff = updater.diff()
        if args.write and updates:
            updater.apply()
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as error:
        print("Error: {}".format(error), file=sys.stderr)
        return 2

    if updates:
        print(preview_diff, end="")
        if args.write:
            print("\nValidated and wrote the updates to {}.".format(args.composer_file))
        else:
            print("\nPreview only. Re-run with --write to apply these changes.")
    else:
        print("No compatible stable updates found.")

    for package, reason in sorted(updater.skipped.items()):
        print("Skipped {}: {}".format(package, reason))
    return 0


if __name__ == "__main__":
    sys.exit(main())
