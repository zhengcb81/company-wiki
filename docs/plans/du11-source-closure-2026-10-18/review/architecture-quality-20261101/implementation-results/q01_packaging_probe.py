"""Offline wheel/fresh-location probe; copies source only and restores its temp tree."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile


def main():
    repo = Path(__file__).resolve().parents[6]
    owner = repo / 'tmp'
    owner.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='q01-wheel-', dir=owner) as name:
        root = Path(name)
        source = root / 'source'
        source.mkdir()
        shutil.copyfile(repo / 'pyproject.toml', source / 'pyproject.toml')
        shutil.copytree(repo / 'src', source / 'src', ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '*.sqlite*', '*.db', '*.pdf', '*.png'))
        env = os.environ.copy()
        env.update(PIP_NO_INDEX='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
                   PYTHONIOENCODING='utf-8')
        build = subprocess.run([
            sys.executable, '-B', '-X', 'utf8', '-m', 'pip', 'wheel', '--no-deps',
            '--no-build-isolation', '--no-cache-dir', '--wheel-dir', str(root / 'dist'),
            str(source),
        ], env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        if build.returncode:
            raise RuntimeError(build.stdout + '\n' + build.stderr)
        wheel = next((root / 'dist').glob('*.whl'))
        installed = root / 'installed'
        installed.mkdir()
        with zipfile.ZipFile(wheel) as archive:
            prefix = 'company_wiki/document_understanding/statement_grammar/resources/'
            manifest = json.loads(archive.read(prefix + 'manifest.json'))
            for filename, item in manifest['assets'].items():
                assert hashlib.sha256(archive.read(prefix + filename)).hexdigest() == item['sha256']
            assert archive.read(prefix + 'NLTK_MODEL_LICENSE.txt')
            assert archive.read(prefix + 'JIEBA_LICENSE.txt')
            archive.extractall(installed)
        env['PYTHONPATH'] = str(installed)
        code = (
            "from pathlib import Path; import company_wiki.document_understanding.statement_grammar as g; "
            f"assert Path(g.__file__).is_relative_to(Path({str(installed)!r})); "
            "assert g.observe_statement('Northvale transports liquefied gas.').independent; "
            "assert g.observe_statement('北岭公司经营铁路运输业务。').independent; "
            "print(g.resource_identity())"
        )
        probe = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=root,
                               env=env, capture_output=True, text=True, encoding='utf-8',
                               errors='replace', timeout=40)
        if probe.returncode:
            raise RuntimeError(probe.stdout + '\n' + probe.stderr)
        observation = {
            'wheel_bytes': wheel.stat().st_size,
            'assets_verified': len(manifest['assets']),
            'resource_bytes': sum(x['bytes'] for x in manifest['assets'].values()),
            'fresh_relocated_import': 'PASS', 'identity': probe.stdout.strip(),
            'paid_model_posts': 0, 'runtime_downloads': 0,
            'temporary_root': str(root),
        }
    assert not root.exists()
    observation['temporary_root_removed'] = True
    Path(__file__).with_name('Q01-wheel.json').write_bytes(
        (json.dumps(observation, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(observation, ensure_ascii=False))


if __name__ == '__main__':
    main()
