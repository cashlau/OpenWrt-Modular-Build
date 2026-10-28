#!/usr/bin/env python3
"""Use an explicit versioned Go host dependency, preserving upstream defaults."""
import re
import sys
from pathlib import Path


def prepare(tree):
    go_dir = tree / 'feeds/packages/lang/golang'
    for name in ('golang1.27', 'golang-bootstrap'):
        if not (go_dir / name / 'Makefile').is_file():
            raise ValueError(f'Official Go provider is missing: {name}')
    changed = []
    seen = set()
    # Feed symlinks are covered by their source files. Include direct plugins.
    for source in (tree / 'feeds', tree / 'package/third-party', tree / 'package/custom'):
        for path in sorted(source.rglob('Makefile')):
            actual = path.resolve()
            if actual in seen or go_dir.resolve() in actual.parents:
                continue
            seen.add(actual)
            text = path.read_text()
            updated = re.sub(r'(?<![\w.-])golang/host\b', 'golang1.27/host', text)
            if updated != text:
                path.write_text(updated)
                changed.append(str(path.relative_to(tree)))
    # Feed indexes cache Makefile dependencies. They must be regenerated after
    # changing the requested compiler, before creating the package build graph.
    caches = [tree / 'tmp/info'] + list((tree / 'feeds').glob('*.tmp/info'))
    for directory in caches:
        for path in directory.glob('.packageinfo*'):
            if path.is_file() or path.is_symlink():
                path.unlink()
    for path in (tree / 'tmp/.packageinfo', tree / 'tmp/.config-package.in'):
        if path.is_file():
            path.unlink()
    print(f'Explicit Go 1.27 host dependencies applied to {len(changed)} Makefiles')
    for path in changed:
        print('  ' + path)


if __name__ == '__main__':
    prepare(Path(sys.argv[1]).resolve())
