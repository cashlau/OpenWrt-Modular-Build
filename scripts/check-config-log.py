#!/usr/bin/env python3
"""Reject Kconfig errors even when make returns zero."""
import re
import sys
from pathlib import Path


def check(text):
    failures = [line for line in text.splitlines() if re.search(
        r'\berror:|recursive dependency detected|has a build dependency on .*which does not exist',
        line, flags=re.I)]
    if failures:
        raise ValueError('Invalid OpenWrt configuration:\n' + '\n'.join(failures))


if __name__ == '__main__':
    check(Path(sys.argv[1]).read_text())
