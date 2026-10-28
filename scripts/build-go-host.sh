#!/bin/bash
set -euo pipefail
REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
TREE=${1:-"$REPO_ROOT/openwrt"}
TREE=$(cd "$TREE" && pwd)
test -f "$TREE/include/toplevel.mk"

# Build the actual compiler before any target package can invoke it.
make -C "$TREE" package/feeds/packages/golang1.27/host/compile -j2 V=s \
    2>&1 | tee "$TREE/go-host-build.log"
GO="$TREE/staging_dir/hostpkg/lib/go-1.27/bin/go"
test -x "$GO"
VERSION=$("$GO" version)
printf '%s\n' "$VERSION"
case "$VERSION" in
    'go version go1.27.'*) ;;
    *) echo 'Unexpected Go host compiler version'; exit 1 ;;
esac
# Compile AND run a tiny host program to verify the installed toolchain.
SMOKE_DIR=$(mktemp -d "$TREE/tmp/go-host-smoke.XXXXXX")
trap 'rm -rf "$SMOKE_DIR"' EXIT
printf 'package main\nimport "fmt"\nfunc main(){fmt.Print("go-host-ok")}\n' > "$SMOKE_DIR/main.go"
GOTOOLCHAIN=local GOENV=off "$GO" build -o "$SMOKE_DIR/check" "$SMOKE_DIR/main.go"
test "$("$SMOKE_DIR/check")" = go-host-ok
printf '%s\n' 'Go 1.27 compiler executable and smoke test verified.'
