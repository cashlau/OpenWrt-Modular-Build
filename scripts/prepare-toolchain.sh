#!/bin/bash
set -euo pipefail
test -f include/toplevel.mk
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

# Preserve official versioned packages and their default-version configuration.
# Consumers explicitly depend on golang1.27/host, so their PATH and build order
# refer to the same compiler instead of relying on a virtual golang provider.
python3 "$SCRIPT_DIR/prepare-go.py" "$PWD"
./scripts/feeds update -i -a
./scripts/feeds install -p packages golang1.27 golang-bootstrap
test -s package/feeds/packages/golang1.27/Makefile
printf '%s\n' 'Official versioned Go providers retained; consumer dependencies explicitly use Go 1.27.'
