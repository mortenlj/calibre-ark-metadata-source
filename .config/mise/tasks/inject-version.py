#!/usr/bin/env python
#MISE description="Inject the given version into the relevant files"
#USAGE arg <version> help="The version to inject, in the form <major>.<minor>.<patch>-<sha>"

import os

from common import update_file


def _update_pyproject(version):
    update_file("pyproject.toml", r"version = \"(0.1.0)\"", version)


def _update_plugin(version):
    plugin_version_str, _junk = version.split("+", maxsplit=1)
    plugin_version = plugin_version_str.replace(".", ", ")
    update_file("__init__.py", r"\s+version = \((0, 1, 0)\)", plugin_version)


def main():
    version = os.getenv("usage_version")
    print(f"Updating to {version} ...")
    _update_pyproject(version)
    _update_plugin(version)


if __name__ == "__main__":
    main()
