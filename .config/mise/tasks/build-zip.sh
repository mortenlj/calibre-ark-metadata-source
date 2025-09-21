#!/usr/bin/bash
#MISE description="Build the plugin zip file"
#USAGE arg <version> help="The version"

set -eo pipefail

mkdir -p build

cp README.rst build/about.txt
for f in LICENSE plugin-import-name*.txt *.py; do
    cp "$f" build/
done

pushd build
zip -v "../ark-metadata-${usage_version}.zip" ./*
popd
