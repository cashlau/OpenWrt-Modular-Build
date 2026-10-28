import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


compat = module('compat', 'prepare-compat.py')
logcheck = module('logcheck', 'check-config-log.py')


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tree = Path(self.temp.name)
        (self.tree / '.config').write_text('')

    def file(self, name, content):
        path = self.tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def provider(self, name):
        src = self.file(f'feeds/nikki/{name}/Makefile', f'PKG_NAME:={name}\n')
        link = self.tree / f'package/feeds/nikki/{name}'
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(src.parent)
        return link

    def test_nikki_keeps_stable_provider_and_source_of_alternative(self):
        nikki = self.file('package/feeds/nikki/nikki/Makefile', 'DEPENDS:=+curl +mihomo\n')
        meta, alpha = self.provider('mihomo-meta'), self.provider('mihomo-alpha')
        compat.prepare(self.tree)
        self.assertTrue(meta.is_symlink())
        self.assertFalse(alpha.is_symlink())
        self.assertTrue((self.tree / 'feeds/nikki/mihomo-alpha/Makefile').exists())
        self.assertIn('+mihomo-meta', nikki.read_text())
        compat.prepare(self.tree)  # safe to repeat

    def test_explicit_alpha_is_respected(self):
        self.file('package/feeds/nikki/nikki/Makefile', 'DEPENDS:=+mihomo\n')
        meta, alpha = self.provider('mihomo-meta'), self.provider('mihomo-alpha')
        (self.tree / '.config').write_text('CONFIG_PACKAGE_mihomo-alpha=y\n')
        compat.prepare(self.tree)
        self.assertTrue(alpha.is_symlink())
        self.assertFalse(meta.is_symlink())

    def test_weechat_selects_concrete_provider(self):
        path = self.file('package/feeds/luci/luci-app-weechat/Makefile', 'LUCI_DEPENDS:=+luci-base +weechat +rpcd-mod-ucode\n')
        compat.prepare(self.tree)
        self.assertIn('+weechat-minimal ', path.read_text())

    def test_broken_prosody_is_omitted_only_when_unselected(self):
        src = self.file('feeds/packages/net/prosody/Makefile', 'DEPENDS:=+luafilesystem5.4\n')
        for name in ('luafilesystem', 'luaexpat', 'luasec', 'luasocket'):
            self.file(f'feeds/packages/lang/lua/{name}/Makefile', f'define Package/{name}\nendef\n')
        path = self.tree / 'package/feeds/packages/prosody'
        path.parent.mkdir(parents=True)
        path.symlink_to(src.parent)
        (self.tree / '.config').write_text('CONFIG_PACKAGE_prosody=y\n')
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            compat.prepare(self.tree)
        self.assertTrue(path.exists())
        (self.tree / '.config').write_text('')
        compat.prepare(self.tree)
        self.assertFalse(path.is_symlink())
        self.assertTrue(src.exists())

    def test_make_success_log_with_kconfig_error_is_rejected(self):
        with self.assertRaises(ValueError):
            logcheck.check('tmp/.config-package.in:1:error: recursive dependency detected!\n# configuration written to .config\n')
        with self.assertRaises(ValueError):
            logcheck.check("WARNING: Makefile 'x' has a build dependency on 'golang1.27/host', which does not exist")
        logcheck.check('# configuration written to .config\nPlugin selections verified.\n')

    def test_official_versioned_go_providers_are_preserved(self):
        self.file('include/toplevel.mk', '')
        for name in ('golang', 'golang1.26', 'golang1.27', 'golang-bootstrap'):
            self.file(f'feeds/packages/lang/golang/{name}/Makefile', f'PKG_NAME:={name}\n')
        consumer = self.file('feeds/packages/net/cloudflared/Makefile', 'PKG_BUILD_DEPENDS:=golang/host\n')
        cache = self.file('feeds/packages.tmp/info/.packageinfo-cloudflared', 'stale')
        values = self.file('feeds/packages/lang/golang/golang-values.mk', 'GO_DEFAULT_VERSION:=1.26\nOTHER:=keep\n')
        feed = self.file('scripts/feeds', '#!/bin/sh\nexit 0\n')
        feed.chmod(0o755)
        link = self.tree / 'package/feeds/packages/golang1.27'
        link.parent.mkdir(parents=True)
        link.symlink_to(self.tree / 'feeds/packages/lang/golang/golang1.27')
        subprocess.run(['bash', str(ROOT / 'scripts/prepare-toolchain.sh')], cwd=self.tree, check=True)
        self.assertEqual(values.read_text(), 'GO_DEFAULT_VERSION:=1.26\nOTHER:=keep\n')
        self.assertTrue((self.tree / 'feeds/packages/lang/golang/golang1.26/Makefile').exists())
        self.assertEqual(consumer.read_text(), 'PKG_BUILD_DEPENDS:=golang1.27/host\n')
        self.assertFalse(cache.exists())
