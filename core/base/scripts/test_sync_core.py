"""중앙 받기 도구 — 주소로 받기 · 태그 고르기 · 받은 뒤 손댄 파일 감지 · 줄바꿈 무시를 검사합니다."""
import hashlib
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

    def test_crlf_is_not_a_local_edit(self):
        # 중앙 폴더에 CRLF로 체크아웃된 파일이 있어도 LF로 받습니다
        (self.central / 'core' / 'base' / 'rules' / 'a.md').write_bytes(b'v2\r\n')
        r = run('--from', str(self.central), '--repo-root', str(self.repo))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        mine = self.repo / 'core' / 'base' / 'rules' / 'a.md'
        self.assertEqual(mine.read_bytes(), b'v2\n')
        # 받은 뒤 줄바꿈만 CRLF로 바뀐 파일은 손댄 파일이 아닙니다
        mine.write_bytes(b'v2\r\n')
        r = run('--local', '--repo-root', str(self.repo))
        self.assertNotIn('a.md', r.stdout)
        r = run('--from', str(self.central), '--repo-root', str(self.repo), '--check')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('바뀜 0', r.stdout)

    def test_old_record_with_raw_crlf_hash(self):
        # 줄바꿈을 맞추기 전의 받은 기록(CRLF 바이트의 해시)도 손댄 파일로 잡지 않습니다
        run('--from', self.url, '--repo-root', str(self.repo))
        mine = self.repo / 'core' / 'base' / 'rules' / 'a.md'
        mine.write_bytes(b'v2\r\n')
        src_path = self.repo / 'core' / '.source.json'
        src = json.loads(src_path.read_text(encoding='utf-8'))
        src['files']['base/rules/a.md'] = hashlib.sha256(b'v2\r\n').hexdigest()
        src_path.write_text(json.dumps(src), encoding='utf-8')
        r = run('--from', self.url, '--repo-root', str(self.repo))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        src = json.loads(src_path.read_text(encoding='utf-8'))
        self.assertEqual(src['files']['base/rules/a.md'], hashlib.sha256(b'v2\n').hexdigest())

    def test_from_defaults_to_recorded_source(self):
        r = run('--check', '--repo-root', str(self.repo))
        self.assertNotEqual(r.returncode, 0)  # 받은 기록이 없으면 --from이 필요합니다
        run('--from', self.url, '--ref', 'core-v1.0.0', '--repo-root', str(self.repo))
        r = run('--check', '--repo-root', str(self.repo))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('바뀜 1', r.stdout)
        self.assertEqual(self.rule(), 'v1\n')
        # 받은 기록의 폴더가 없으면 멈춥니다
        src_path = self.repo / 'core' / '.source.json'
        src = json.loads(src_path.read_text(encoding='utf-8'))
        src['source'] = str(self.repo / 'no-such-folder')
        src_path.write_text(json.dumps(src), encoding='utf-8')
        r = run('--check', '--repo-root', str(self.repo))
        self.assertNotEqual(r.returncode, 0)

    def write_log(self, *titles):
        log = self.central / 'center-change-log.md'
        log.write_text('# log\n\n' + ''.join('### %s\n\n본문\n\n' % t for t in titles),
                       encoding='utf-8')

    def test_new_entries_by_last_entry_and_time(self):
        self.write_log('2026-10-15 13:15 — 둘째', '2026-10-15 11:47 — 첫째', '2026-10-14 — 옛')
        r = run('--from', str(self.central), '--repo-root', str(self.repo))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        src_path = self.repo / 'core' / '.source.json'
        src = json.loads(src_path.read_text(encoding='utf-8'))
        self.assertEqual(src['last_entry'], '2026-10-15 13:15 — 둘째')
        # 받은 뒤 맨 위에 더해진 항목만 새 항목입니다 — 시각이 받은 시각보다 앞서도 고릅니다
        self.write_log('2026-10-15 09:00 — 셋째', '2026-10-15 13:15 — 둘째',
                       '2026-10-15 11:47 — 첫째', '2026-10-14 — 옛')
        r = run('--from', str(self.central), '--repo-root', str(self.repo), '--check')
        self.assertIn('셋째', r.stdout)
        self.assertNotIn('둘째', r.stdout)
        # 맨 위 항목 기록이 없으면 받은 시각과 시각까지 견줍니다 — 같은 날 앞선 항목은 빼고,
        # 같은 분 항목과 날짜만 있는 같은 날 항목은 넣습니다
        del src['last_entry']
        src['synced'] = '2026-10-15 13:15'
        src_path.write_text(json.dumps(src), encoding='utf-8')
        self.write_log('2026-10-15 14:00 — 넷째', '2026-10-15 13:15 — 둘째',
                       '2026-10-15 11:47 — 첫째', '2026-10-15 — 날짜만', '2026-10-14 — 옛')
        r = run('--from', str(self.central), '--repo-root', str(self.repo), '--check')
        for title in ('넷째', '둘째', '날짜만'):
            self.assertIn(title, r.stdout)
        for title in ('첫째', '옛'):
            self.assertNotIn(title, r.stdout)

    def test_bad_url_and_ref_on_folder(self):
        r = run('--from', self.url, '--ref', 'no-such-tag', '--repo-root', str(self.repo))
        self.assertNotEqual(r.returncode, 0)
        r = run('--from', str(self.central), '--ref', 'core-v1.0.0', '--repo-root', str(self.repo))
        self.assertNotEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
