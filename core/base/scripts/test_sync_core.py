"""중앙 받기 도구 — 주소로 받기 · 태그 고르기 · 받은 뒤 손댄 파일 감지를 검사합니다."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = str(Path(__file__).with_name('sync_core.py'))


def git(cwd, *args):
    subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)


def run(*args):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True,
                          encoding='utf-8', env=env)


class SyncCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        # 중앙 저장소 흉내 — core/base/ 하나와 태그 둘
        self.central = base / 'central'
        rule = self.central / 'core' / 'base' / 'rules' / 'a.md'
        rule.parent.mkdir(parents=True)
        rule.write_text('v1\n', encoding='utf-8')
        git(self.central, 'init', '-q')
        git(self.central, 'add', '-A')
        git(self.central, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'one')
        git(self.central, 'tag', 'core-v1.0.0')
        rule.write_text('v2\n', encoding='utf-8')
        git(self.central, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'two')
        self.url = self.central.as_uri()
        self.repo = base / 'repo'
        self.repo.mkdir()
        (self.repo / 'workspace.json').write_text('{}', encoding='utf-8')

    def rule(self):
        return (self.repo / 'core' / 'base' / 'rules' / 'a.md').read_text(encoding='utf-8')

    def test_url_and_ref(self):
        r = run('--from', self.url, '--ref', 'core-v1.0.0', '--repo-root', str(self.repo))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rule(), 'v1\n')
        src = json.loads((self.repo / 'core' / '.source.json').read_text(encoding='utf-8'))
        self.assertEqual(src['source'], self.url)
        self.assertEqual(src['tag'], 'core-v1.0.0')
        r = run('--from', self.url, '--repo-root', str(self.repo))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rule(), 'v2\n')

    def test_local_edit_blocks(self):
        run('--from', self.url, '--repo-root', str(self.repo))
        (self.repo / 'core' / 'base' / 'rules' / 'a.md').write_text('local\n', encoding='utf-8')
        r = run('--from', self.url, '--repo-root', str(self.repo))
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.rule(), 'local\n')
        r = run('--from', self.url, '--repo-root', str(self.repo), '--discard-local')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rule(), 'v2\n')

    def test_bad_url_and_ref_on_folder(self):
        r = run('--from', self.url, '--ref', 'no-such-tag', '--repo-root', str(self.repo))
        self.assertNotEqual(r.returncode, 0)
        r = run('--from', str(self.central), '--ref', 'core-v1.0.0', '--repo-root', str(self.repo))
        self.assertNotEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
