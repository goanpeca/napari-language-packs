"""
This script will update the catalogs using the information from the
`repository-map.yml` file.

This script will:
- Check `repository-map.yml` urls are valid.
- Update the crowdin.yml to match `repository-map.yml`
- Clone repos or fetch from origin  based on information from `repository-map.yml`
- Checkout the current version
- Create a `gettext` catalog (*.pot) or update an existing catalogs
"""

# Standard library imports
import os
import subprocess
import sys
import time

# Third party imports
import click
import yaml

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(HERE)
REPOSITORIES_FOLDER = "repos"
LANGUAGE_PACKS_FOLDER = "language-packs"
REPO_MAP_FILE = "repository-map.yml"
CROWDIN_FILE = "crowdin.yml"


def load_repo_map():
    """
    Load yaml file with mapping of package names to repo url and version.
    """
    fpath = os.path.join(REPO_ROOT, REPO_MAP_FILE)
    with open(fpath, "r") as fh:
        data = yaml.safe_load(fh.read())

    return data


def save_crowdin(data):
    """
    Save crowdin `data`.
    """
    fpath = os.path.join(REPO_ROOT, CROWDIN_FILE)
    with open(fpath, "w") as fh:
        fh.write(yaml.safe_dump(data))


def load_crowdin():
    """
    Load crowdin data.
    """
    fpath = os.path.join(REPO_ROOT, CROWDIN_FILE)
    with open(fpath, "r") as fh:
        data = yaml.safe_load(fh.read())

    return data


def update_crowdin_config():
    """
    Update crowdin configuration to match `reposiory-map.yml`.
    """
    data = load_repo_map()
    crowdin_data = load_crowdin()
    _files = crowdin_data["files"]
    packages = [
        {
            "source": "/napari/locale/napari.pot",
            "translation": (
                f"/napari/locale/%locale_with_underscore%/LC_MESSAGES/%file_name%.po"
            ),
        }
    ]
    for pkg_name in sorted(data):
        if pkg_name != "napari":
            pkg_name_norm = pkg_name.replace("-", "_")
            packages.append({
                "source": f"/plugins/{pkg_name_norm}/locale/{pkg_name_norm}.pot",
                "translation": (
                    f"/plugins/{pkg_name_norm}/locale"
                    f"/%locale_with_underscore%/LC_MESSAGES/%file_name%.po"
                ),
            })

    crowdin_data["files"] = packages
    save_crowdin(crowdin_data)


def update_repo(package_name, url, version):
    """
    Clone or update repo for given package and checkout `version` reference.
    """
    repos_path = os.path.join(REPO_ROOT, REPOSITORIES_FOLDER)
    clone_path = os.path.join(repos_path, package_name)

    if not os.path.isdir(clone_path):
        args = ["git", "clone", url + ".git", package_name]
        p = subprocess.Popen(args, cwd=repos_path)
        p.communicate()
    else:
        args = ["git", "fetch", "origin"]
        p = subprocess.Popen(args, cwd=repos_path)
        p.communicate()

    args = ["git", "checkout", version]
    p = subprocess.Popen(args, cwd=clone_path)
    p.communicate()


def _get_all_dirs(root):
    """
    Return all dirs and subdirs found in `root`.
    """
    folders = []
    for root, dirs, _files in os.walk(root, topdown=False):
        for name in dirs:
            folders.append(os.path.join(root, name))
    return folders


def update_catalog(package_name, version):
    """
    Create or update pot catalogs for package_name and version.
    """
    package_repo_dir = os.path.join(REPO_ROOT, REPOSITORIES_FOLDER, package_name)

    if package_name == "napari":
        output = os.path.join(REPO_ROOT, package_name, "locale", f"{package_name}.pot")
    else:
        output = os.path.join(REPO_ROOT, "plugins", package_name, "locale", f"{package_name}.pot")

    # Create temp catalog
    keywords = ["-k", "_:1", "-k", "_p:1c,2", "-k", "_n:1,2", "-k", "_np:1c,2,3"]
    folders = _get_all_dirs(package_repo_dir)
    args = ["pybabel", "extract"] + folders + ["-o", output, "--no-default-keywords", "-w", "100000"] + keywords
    p = subprocess.Popen(args, cwd=REPO_ROOT)
    p.communicate()

    # Remove root path from messages
    with open(output, "r") as fh:
        data = fh.read()

    data = data.replace(f"{package_repo_dir}/", "")

    with open(output, "w") as fh:
        data = fh.write(data)

    # Update available *.po catalogs


if __name__ == "__main__":
    start_run_time = time.time()
    args = sys.argv[1:]
    data = load_repo_map()
    packages = []

    # Ensure repository map and crowdin config are in sync
    update_crowdin_config()

    if len(args) == 1:
        package_name = args[0]
        # Update package if found in the repository-map.yml
        if package_name in data:
            packages = [package_name]
    elif len(args) == 0:
        packages = sorted(data.keys())
    else:
        sys.exit(0)
    
    for package_name in packages:
        click.echo(click.style(f"\n\nUpdating catalog for \"{package_name}\"\n\n", fg="cyan"))
        url = data[package_name]["url"]
        version = data[package_name]["current-version-tag"]
        update_repo(package_name, url, version)
        update_catalog(package_name, version)

    delta = round(time.time() - start_run_time, 0)
    click.echo(
        click.style(
            f'\n\n\nCatalogs updated in {delta} seconds\n', fg="green"
        )
    )
