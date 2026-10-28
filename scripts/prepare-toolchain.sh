#!/bin/bash
set -euo pipefail
test -f include/toplevel.mk
# Update the OpenWrt host Go toolchain, not Ubuntu's system Go.
# Download and inspect the replacement before moving the existing directory.
GO_STAGE=$(mktemp -d "$PWD/.golang-update.XXXXXX")

git clone --depth=1 --branch 27.x \
    https://github.com/sbwml/packages_lang_golang.git "$GO_STAGE/new"

echo 'Downloaded Go version declarations:'

grep -E '^[[:space:]]*(GO_VERSION_MAJOR_MINOR|GO_VERSION_PATCH|PKG_VERSION)[[:space:]]*[:?+]?=' \
    "$GO_STAGE/new/golang/Makefile" || true

if ! grep -Eq '^[[:space:]]*(GO_VERSION_MAJOR_MINOR|PKG_VERSION)[[:space:]]*[:?]?=[[:space:]]*1\.27([.[:space:]]|$)' \
    "$GO_STAGE/new/golang/Makefile"; then
    echo "Go 1.27 version check failed; original toolchain retained."
    exit 1
fi

test -s "$GO_STAGE/new/golang-package.mk"

mv feeds/packages/lang/golang "$GO_STAGE/original"
mv "$GO_STAGE/new" feeds/packages/lang/golang

echo "Go build files updated; original saved at $GO_STAGE/original"

grep -E '^[[:space:]]*(GO_VERSION_MAJOR_MINOR|GO_VERSION_PATCH|PKG_VERSION)[[:space:]]*[:?+]?=' \
    feeds/packages/lang/golang/golang/Makefile

