#!/usr/bin/env python3
"""Narrow compatibility fixes for versioned feeds and virtual providers."""
import re
import sys
from pathlib import Path


def replace(path, pattern, replacement):
    text = path.read_text()
    text, count = re.subn(pattern, replacement, text, flags=re.M)
    if not count:
        raise ValueError(f'Upstream format changed, inspect {path}')
    path.write_text(text)


def prepare(tree):
    config = set((tree / '.config').read_text().splitlines())
    selected = lambda name: f'CONFIG_PACKAGE_{name}=y' in config or f'CONFIG_PACKAGE_{name}=m' in config
    nikki = tree / 'package/feeds/nikki/nikki/Makefile'
    if nikki.exists():
        if selected('mihomo-alpha') and selected('mihomo-meta'):
            raise ValueError('Select only one Mihomo provider')
        provider = 'mihomo-alpha' if selected('mihomo-alpha') else 'mihomo-meta'
        other = 'mihomo-meta' if provider == 'mihomo-alpha' else 'mihomo-alpha'
        alternate = tree / 'package/feeds/nikki' / other
        if alternate.is_symlink():
            alternate.unlink()
        elif alternate.exists():
            raise ValueError(f'Expected an installed feed symlink: {alternate}')
        if not (tree / 'package/feeds/nikki' / provider / 'Makefile').exists():
            raise ValueError(f'Mihomo provider missing: {provider}')
        # Resolve the virtual dependency explicitly, retaining the chosen core.
        replace(nikki, r'\+mihomo(?:-meta|-alpha)?(?=\s|$)', '+' + provider)
        print(f'Nikki core provider: {provider}; unused alternative omitted from Kconfig')

    weechat = tree / 'package/feeds/luci/luci-app-weechat/Makefile'
    if weechat.exists():
        provider = 'weechat-full' if selected('weechat-full') else 'weechat-minimal'
        replace(weechat, r'\+weechat(?:-minimal|-full)?(?=\s|$)', '+' + provider)
        print(f'WeeChat virtual dependency resolved to {provider}')

    # This pinned feed's optional Prosody requires Lua 5.4 modules it does not
    # yet provide. Do not expose an unusable, unselected application to Kconfig.
    prosody = tree / 'package/feeds/packages/prosody'
    if prosody.exists():
        text = (prosody / 'Makefile').read_text()
        modules = ('luafilesystem', 'luaexpat', 'luasec', 'luasocket')
        missing = [name + '5.4' for name in modules
                   if 'define Package/' + name + '5.4' not in
                   (tree / 'feeds/packages/lang/lua' / name / 'Makefile').read_text()]
        if missing and '+luafilesystem5.4' in text:
            if selected('prosody'):
                raise ValueError('Prosody requires unavailable modules: ' + ', '.join(missing))
            if not prosody.is_symlink():
                raise ValueError('Expected installed Prosody feed symlink')
            prosody.unlink()
            print('Omitted unused Prosody with unavailable Lua 5.4 dependencies')


if __name__ == '__main__':
    prepare(Path(sys.argv[1]).resolve())
