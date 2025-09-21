import re
import shutil
from tempfile import NamedTemporaryFile


def update_file(file_path, pattern, version):
    print(f"Updating version in {file_path} ...")
    with open(file_path, "r") as f:
        lines = f.readlines()
    with NamedTemporaryFile("w", delete=False) as f:
        for line in lines:
            if m := re.match(pattern, line):
                line = line.replace(m.group(1), version)
            f.write(line)
    shutil.move(f.name, file_path)
