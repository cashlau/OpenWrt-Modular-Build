#!/usr/bin/env python3
"""Manage third-party sources and explicit firmware selections (stdlib only)."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]*\Z")


def run(*args, cwd=None, capture=False):
    return subprocess.run(args, cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def load(root=ROOT):
    catalog = {}
    source_names = set()
    packages = set()
    for path in sorted((root / 'third-party').glob('*/plugin.json')):
        name = path.parent.name
        if not SAFE.fullmatch(name):
            raise ValueError(f'Invalid plugin name: {name}')
        item = json.loads(path.read_text())
        for package in item['packages']:
            if not SAFE.fullmatch(package) or package in packages:
                raise ValueError(f'Invalid or duplicate package: {package}')
            packages.add(package)
        for source in item.get('sources', []):
            n = source['name']
            if not SAFE.fullmatch(n) or n in source_names:
                raise ValueError(f'Invalid or duplicate source: {n}')
            source_names.add(n)
            if source['kind'] not in ('feed', 'clone'):
                raise ValueError(f'Invalid source kind: {n}')
            if not re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?', source['url']):
                raise ValueError(f'Invalid source URL: {n}')
            if any(c.isspace() for c in source.get('ref', '')) or ';' in source.get('ref', ''):
                raise ValueError(f'Invalid ref: {n}')
        local = item.get('local')
        if local and (not SAFE.fullmatch(local) or not (path.parent / local / 'Makefile').is_file()):
            raise ValueError(f'Invalid local source: {name}')
        catalog[name] = item
    choices = {}
    for number, line in enumerate((root / 'third-party/plugins.conf').read_text().splitlines(), 1):
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r'([\w.+-]+)\s*=\s*([yn])', line)
        if not match:
            raise ValueError(f'Invalid plugins.conf line {number}')
        name, value = match.groups()
        if name not in catalog or name in choices:
            raise ValueError(f'Unknown or duplicate plugin: {name}')
        choices[name] = value == 'y'
    enabled, visiting = [], set()

    def visit(name):
        if name not in catalog:
            raise ValueError(f'Unknown dependency: {name}')
        if name in visiting:
            raise ValueError(f'Dependency cycle: {name}')
        if name in enabled:
            return
        if choices.get(name) is False:
            raise ValueError(f'Required dependency explicitly disabled: {name}')
        visiting.add(name)
        for dep in catalog[name].get('requires', []):
            visit(dep)
        visiting.remove(name)
        enabled.append(name)

    for name, value in choices.items():
        if value:
            visit(name)
    # Validate dependencies of disabled entries as well.
    for name, item in catalog.items():
        for dep in item.get('requires', []):
            if dep not in catalog:
                raise ValueError(f'{name}: unknown dependency {dep}')
    return catalog, enabled


def prepare(tree, catalog, enabled):
    if not (tree / 'include/toplevel.mk').is_file():
        raise ValueError('Expected a fresh OpenWrt source tree')
    if (tree / '.modular-sources.json').exists():
        raise ValueError('Sources already prepared; use a fresh source tree')
    feeds = []
    lines = []
    for name in enabled:
        for source in catalog[name].get('sources', []):
            if source['kind'] == 'feed':
                ref = source.get('ref', '')
                # ^ pins a commit; ; follows a named branch or tag.
                suffix = ('^' if re.fullmatch(r'[0-9a-f]{40}', ref) else ';') + ref if ref else ''
                lines.append(f"src-git {source['name']} {source['url']}{suffix}\n")
                feeds.append(source['name'])
    with (tree / 'feeds.conf.default').open('a') as out:
        out.write('\n' + ''.join(lines))
    run('./scripts/feeds', 'update', '-a', cwd=tree)
    # Install the shared dependency feed first; preserve full history for versions.
    for feed in feeds:
        directory = tree / 'feeds' / feed
        if run('git', 'rev-parse', '--is-shallow-repository', cwd=directory, capture=True).strip() == 'true':
            run('git', 'fetch', '--unshallow', cwd=directory)
        run('git', 'fetch', '--tags', cwd=directory)
        run('./scripts/feeds', 'install', '-a', '-f', '-p', feed, cwd=tree)
    run('./scripts/feeds', 'install', '-a', cwd=tree)
    revisions = {}
    for name in enabled:
        item = catalog[name]
        for source in item.get('sources', []):
            if source['kind'] == 'feed':
                destination = tree / 'feeds' / source['name']
            else:
                destination = tree / 'package/third-party' / source['name']
                destination.parent.mkdir(parents=True, exist_ok=True)
                run('git', 'clone', '--', source['url'], str(destination))
                ref = source.get('ref')
                if ref:
                    try:
                        commit = run('git', 'rev-parse', '--verify', ref + '^{commit}', cwd=destination, capture=True).strip()
                    except subprocess.CalledProcessError:
                        commit = run('git', 'rev-parse', '--verify', 'origin/' + ref + '^{commit}', cwd=destination, capture=True).strip()
                    run('git', 'checkout', '--detach', commit, cwd=destination)
            revisions[source['name']] = dict(url=source['url'], ref=source.get('ref', ''),
                commit=run('git', 'rev-parse', 'HEAD', cwd=destination, capture=True).strip())
        if item.get('local'):
            shutil.copytree(ROOT / 'third-party' / name / item['local'],
                            tree / 'package/third-party' / name)
        hook = ROOT / 'third-party' / name / 'prepare.sh'
        if hook.is_file():
            run('bash', str(hook), cwd=tree)
    (tree / '.modular-sources.json').write_text(json.dumps(revisions, indent=2) + '\n')


def selections(catalog, enabled):
    return {package: name in enabled for name, item in catalog.items() for package in item['packages']}


def configure(tree, catalog, enabled):
    desired = selections(catalog, enabled)
    path = tree / '.config'
    kept = []
    apps = [p.removeprefix('luci-app-') for p in desired if p.startswith('luci-app-')]
    for line in path.read_text().splitlines():
        match = re.match(r'(?:# )?CONFIG_PACKAGE_([^= ]+)', line)
        package = match.group(1) if match else ''
        if package in desired or any(package.startswith('luci-i18n-' + app + '-') for app in apps):
            continue
        kept.append(line)
    for package, value in desired.items():
        kept.append(f'CONFIG_PACKAGE_{package}=y' if value else f'# CONFIG_PACKAGE_{package} is not set')
    path.write_text('\n'.join(kept) + '\n')


def verify(tree, catalog, enabled):
    lines = set((tree / '.config').read_text().splitlines())
    failures = []
    for package, value in selections(catalog, enabled).items():
        actual = f'CONFIG_PACKAGE_{package}=y' in lines
        module = f'CONFIG_PACKAGE_{package}=m' in lines
        if (value and not actual) or (not value and (actual or module)):
            failures.append(f'{package}: expected {"y" if value else "n"}')
    if failures:
        raise ValueError('Plugin selection mismatch after make defconfig:\n' + '\n'.join(failures))
    print('Plugin selections verified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['list', 'prepare', 'config', 'verify'])
    parser.add_argument('--tree', type=Path, default=ROOT / 'openwrt')
    args = parser.parse_args()
    catalog, enabled = load()
    if args.command == 'list':
        for name in catalog:
            print(f'{name}={"y" if name in enabled else "n"}')
    else:
        globals()[{'config': 'configure'}.get(args.command, args.command)](args.tree.resolve(), catalog, enabled)


if __name__ == '__main__':
    main()
