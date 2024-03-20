# app.py
from src.package_updater import PackageUpdater


def main():
    """
    The main function to update PHP project dependencies in the composer.json file
    to their latest versions using the PackageUpdater class. It then reports the
    updates to the terminal.
    """
    # Define the path to your composer.json file.
    composer_file_path = 'modified_files/composer.json'

    # Create an instance of PackageUpdater with the path to the composer.json file.
    updater = PackageUpdater(composer_file_path)

    # Update the composer.json file and capture any updates made.
    updates = updater.update()

    # Check if there were any updates and report them.
    if updates:
        print("The following packages have been updated to their latest versions:")
        for package, version in updates.items():
            # Print each package and its updated version.
            print(f"{package}: ^{version}")
    else:
        # If no updates were made, inform the user.
        print("All packages are already up to date.")


if __name__ == "__main__":
    # Entry point of the script. Executes the main function when the script is run.
    main()
