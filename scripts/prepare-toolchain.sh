#!/bin/bash
set -euo pipefail
test -f include/toplevel.mk

# Current official feeds use versioned Go packages. Preserve those providers.
GO_DIR=feeds/packages/lang/golang
test -s "$GO_DIR/golang1.27/Makefile"
test -s "$GO_DIR/golang-bootstrap/Makefile"
test -s "$GO_DIR/golang-values.mk"
grep -Eq '^PKG_NAME[[:space:]]*:=[[:space:]]*golang1\.27$' "$GO_DIR/golang1.27/Makefile"

python3 - <<'PY'
from pathlib import Path
import re
path = Path('feeds/packages/lang/golang/golang-values.mk')
text, count = re.subn(r'^GO_DEFAULT_VERSION\s*:=.*$', 'GO_DEFAULT_VERSION:=1.27', path.read_text(), flags=re.M)
if count != 1:
    raise SystemExit('Unsupported official Go layout: GO_DEFAULT_VERSION missing or duplicated')
path.write_text(text)
PY

# Index all versioned host providers without downloading or replacing the feed.
./scripts/feeds update -i packages
./scripts/feeds install -p packages golang golang1.27 golang-bootstrap
test -s package/feeds/packages/golang1.27/Makefile
printf '%s\n' 'Official Go providers retained; default compiler selected: Go 1.27.'
