#!/usr/bin/env python
# fmt: off
#MISE description="Update the project to use a newer version of Python"
#USAGE arg <version> help="The version of Python to use, in the form <major>.<minor>"
_DUMMY_ = "This is just to make sure black doesn't format the above comment block: https://github.com/psf/black/issues/1245"
# fmt: on

import os
import re
import subprocess
from tempfile import NamedTemporaryFile


def _update_file(file_path, pattern, version):
    print(f"Updating {file_path} ...")
    with open(file_path, "r") as f:
        lines = f.readlines()
    with NamedTemporaryFile("w", delete=False) as f:
        for line in lines:
            if m := re.match(pattern, line):
                line = line.replace(m.group(1), version)
            f.write(line)
    os.replace(f.name, file_path)


def _update_pyproject(version):
    _update_file("pyproject.toml", r"requires-python = \"~=(\d\.\d+)\"", version)


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
