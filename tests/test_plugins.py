import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('plugins', Path(__file__).resolve().parents[1] / 'scripts/plugins.py')
plugins = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plugins)


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'third-party').mkdir()

    def manifest(self, name, **kwargs):
        path = self.root / 'third-party' / name / 'plugin.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(dict(packages=[name], **kwargs)))

    def choices(self, text):
        (self.root / 'third-party/plugins.conf').write_text(text)

    def test_dependencies_are_ordered_and_shared_once(self):
        self.manifest('common')
        self.manifest('one', requires=['common'])
        self.manifest('two', requires=['common'])
        self.choices('one=y\ntwo=y\n')
        _, enabled = plugins.load(self.root)
        self.assertEqual(enabled, ['common', 'one', 'two'])

    def test_dependency_explicitly_disabled_is_error(self):
        self.manifest('common')
        self.manifest('one', requires=['common'])
        self.choices('one=y\ncommon=n\n')
        with self.assertRaisesRegex(ValueError, 'explicitly disabled'):
            plugins.load(self.root)

    def test_cycles_and_misspelled_switches_fail(self):
        self.manifest('one', requires=['two'])
        self.manifest('two', requires=['one'])
        self.choices('one=y\n')
        with self.assertRaisesRegex(ValueError, 'cycle'):
            plugins.load(self.root)
        self.choices('typo=y\n')
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            plugins.load(self.root)

    def test_off_overrides_old_config_and_translation(self):
        catalog = {'one': {'packages': ['luci-app-one', 'one']}, 'two': {'packages': ['luci-app-two']}}
        config = self.root / '.config'
        config.write_text('CONFIG_TARGET_x86=y\nCONFIG_PACKAGE_luci-app-one=y\nCONFIG_PACKAGE_one=y\nCONFIG_PACKAGE_luci-i18n-one-zh-cn=y\n# CONFIG_PACKAGE_luci-app-two is not set\n')
        plugins.configure(self.root, catalog, ['two'])
        plugins.verify(self.root, catalog, ['two'])
        self.assertIn('CONFIG_TARGET_x86=y', config.read_text())
        self.assertNotIn('CONFIG_PACKAGE_luci-i18n-one-zh-cn=y', config.read_text())
        self.assertIn('# CONFIG_PACKAGE_one is not set', config.read_text())

    def test_defconfig_dropping_enabled_plugin_is_error(self):
        (self.root / '.config').write_text('# CONFIG_PACKAGE_one is not set\n')
        with self.assertRaisesRegex(ValueError, 'expected y'):
            plugins.verify(self.root, {'one': {'packages': ['one']}}, ['one'])

    def test_all_disabled_has_no_third_party_downloads_or_hooks(self):
        (self.root / 'include').mkdir()
        (self.root / 'include/toplevel.mk').touch()
        (self.root / 'feeds.conf.default').write_text('')
        with patch.object(plugins, 'run') as run:
            plugins.prepare(self.root, {'one': {'packages': ['one'], 'sources': []}}, [])
        self.assertEqual([call.args for call in run.call_args_list],
                         [('./scripts/feeds', 'update', '-a'), ('./scripts/feeds', 'install', '-a')])
        self.assertEqual(json.loads((self.root / '.modular-sources.json').read_text()), {})

    def test_real_catalog_all_on_and_each_individually_off(self):
        catalog, enabled = plugins.load()
        self.assertEqual(len(enabled), 11)
        for disabled in catalog:
            active = [name for name in enabled if name != disabled]
            (self.root / '.config').write_text((plugins.ROOT / 'config/.config').read_text())
            plugins.configure(self.root, catalog, active)
            plugins.verify(self.root, catalog, active)


if __name__ == '__main__':
    unittest.main()
