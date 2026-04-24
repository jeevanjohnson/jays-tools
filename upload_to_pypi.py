import shutil
import subprocess
import sys

import config

# Dev Notes:
# - Referencing: https://semver.org/
# - `map` takes a function and some arguments, and applies the function to each of the arguments. 
#    It returns an iterator (a lazy generator) that you can convert to a list or iterate over directly.
# - TODO: License file, currently using MIT License, but should add a LICENSE file to the repo.
# - TODO: This was written quickly, improve readability and error handling, for production use.

# To go back commits and revert to a previous version:
# git reset --hard {commit_hash} to reset to a previous commit if something goes wrong.
# then git push --force-with-lease to update the remote repo with the reset commit history.

def get_name(file_path: str) -> str:
    """Extract package name from pyproject.toml."""
    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("name = "):
                name = line.split("=")[1].strip().strip('"')
                return name

    raise ValueError("Name not found in file")


def get_version(file_path: str) -> str:
    """Extract version from pyproject.toml."""
    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("version = "):
                version = line.split("=")[1].strip().strip('"')
                return version

    raise ValueError("Version not found in file")


def update_version(version: str, update_type: str) -> str:
    """Update version string based on update type (patch, minor, major)."""
    major, minor, patch = map(int, version.split("."))

    if update_type == "patch":
        patch += 1
    elif update_type == "minor":
        minor += 1
        patch = 0
    elif update_type == "major":
        major += 1
        minor = 0
        patch = 0

    return f"{major}.{minor}.{patch}"


def update_version_in_file(file_path: str, version_number: str) -> None:
    """Update version in pyproject.toml file."""
    with open(file_path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if line.startswith("version = "):
            lines[i] = f'version = "{version_number}"\n'
            break

    with open(file_path, "w") as f:
        f.writelines(lines)

args = sys.argv[1:]
version = get_version("pyproject.toml")
name = get_name("pyproject.toml")

if len(args) == 0:
    print(
        "No arguments provided\n",
        "Usage: python upload.py [patch|minor|major]\n",
        "Defaulting to patch update (incrementing the last number in the version)\n\n",
        'Reminder: Patch updates are for bug fixes and small improvements, "' \
        'minor updates are for new features that are backwards compatible, and major updates are for breaking changes.',
    )
    sys.exit(0)

if len(args) > 1:
    print(
        "Too many arguments, only one argument is allowed"
    )
    sys.exit(1)

update_type = args[0]

if update_type not in ["patch", "minor", "major"]:
    print(
        f"Invalid update type: {update_type}\n",
        "Usage: python upload.py [patch|minor|major]\n",
        'Reminder: Patch updates are for bug fixes and small improvements, "' \
        'minor updates are for new features that are backwards compatible, and major updates are for breaking changes.',
    )
    sys.exit(1)

new_version = update_version(version, update_type)
update_version_in_file("pyproject.toml", new_version)

subprocess.run(
    [sys.executable, "-m", "pip", "install", "hatchling", "twine"],
    capture_output=True,
    text=True,
)


subprocess.run(
    [sys.executable, "-m", "pip", "install", "build"],
    capture_output=True,
    text=True,
)

result = subprocess.run(
    [sys.executable, "-m", "build"],
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    print("Build failed:")
    print(result.stdout)
    print(result.stderr)

    # revert version change
    update_version_in_file("pyproject.toml", version)
    sys.exit(1)

# Check if the package with the new version already exists on PyPI
result = subprocess.run(
    [
        sys.executable, "-m", "pip", "install", f"{name}=={new_version}",
    ],
    capture_output=True,
    text=True,
)

if result.returncode == 0:
    print(f"Version {new_version} of package {name} already exists on PyPI. Please update the version number manually and try again.")
    # revert version change
    update_version_in_file("pyproject.toml", version)
    sys.exit(1)

result = subprocess.run(
    [
        sys.executable, "-m", "twine", "upload", "dist/*",
        "--skip-existing",
        "--non-interactive",
        "--username", "__token__",
        "--password", config.PYPI_API_TOKEN,
    ],
    capture_output=True,
    text=True,
)

if result.returncode != 0:
    print("Upload failed:")
    print(result.stderr)
    print(result.stdout)
    # revert version change
    update_version_in_file("pyproject.toml", version)
    sys.exit(1)
else:
    print("Upload successful!")
    print(f"You can find latest version here: https://pypi.org/project/{name}/{new_version}/")

# Now delete dist folder
try:
    shutil.rmtree("dist")
except FileNotFoundError:
    pass