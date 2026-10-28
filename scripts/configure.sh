#!/bin/bash
set -euo pipefail
REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
TREE=${1:-"$REPO_ROOT/openwrt"}
TREE=$(cd "$TREE" && pwd)
cp "$REPO_ROOT/config/.config" "$TREE/.config"
(cd "$TREE" && bash "$REPO_ROOT/config/customize.sh")
python3 "$REPO_ROOT/scripts/plugins.py" config --tree "$TREE"
python3 "$REPO_ROOT/scripts/prepare-compat.py" "$TREE"

# OpenWrt can return success after Kconfig reports a dependency error.
make -C "$TREE" defconfig 2>&1 | tee "$TREE/configure.log"
python3 "$REPO_ROOT/scripts/check-config-log.py" "$TREE/configure.log"
python3 "$REPO_ROOT/scripts/plugins.py" verify --tree "$TREE"
