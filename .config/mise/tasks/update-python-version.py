#!/usr/bin/env python
#MISE description="Update the project to use a newer version of Python"
#USAGE arg <version> help="The version of Python to use, in the form <major>.<minor>"

import os
import subprocess
from common import update_file

def _update_pyproject(version):
    update_file("pyproject.toml", r"requires-python = \"~=(\d\.\d+)\"", version)


def _update_mise(version):
    print("Telling mise to use the new version ...")
    subprocess.run(["mise", "use", f"python@{version}"], check=True)


def _sync_uv():
    print("Syncing virtualenv ...")
    subprocess.run(["uv", "sync"], check=True)


def main():
    version = os.getenv("usage_version")
    print(f"Updating to Python {version} ...")
    _update_pyproject(version)
    _update_mise(version)
    _sync_uv()


if __name__ == "__main__":
    main()
