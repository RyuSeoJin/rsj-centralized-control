"""제품 묶음의 경로 탐색과 생성 규칙을 검사합니다."""
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from project_paths import discover, resolve, validate_key

class ProjectPathsTest(unittest.TestCase):
    def test_nested_and_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for key in ('legacy', 'product/work'):
                p = root / 'projects' / key
                p.mkdir(parents=True)
                (p / (p.name + '-modules.json')).write_text('{"on": []}')
            self.assertEqual([key for key, _ in discover(root)], ['legacy', 'product/work'])
            self.assertEqual(resolve(root, 'work'), resolve(root, 'product/work'))
            with self.assertRaises(ValueError): resolve(root, 'product')
            other=root/'projects/other/work'
            other.mkdir(parents=True)
            (other/'work-modules.json').write_text('{"on": []}')
            with self.assertRaises(ValueError): resolve(root, 'work')

    def test_registered_roots(self):
        """옮기지 않고 등록한 옛 폴더를 project_roots로 찾습니다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'workspace.json').write_text(
                '{"name":"n","subtitle":"s","repo":"r","project_roots":["Legacy","wiki"]}', encoding='utf-8')
            old = root / 'Legacy' / 'Old_Game'
            old.mkdir(parents=True)
            (old / 'Old_Game-modules.json').write_text('{"on": []}')
            wiki = root / 'wiki'
            wiki.mkdir()
            (wiki / 'wiki-modules.json').write_text('{"on": []}')
            self.assertEqual([k for k, _ in discover(root)], ['Old_Game', 'wiki'])
            self.assertEqual(resolve(root, 'Old_Game'), old)
            self.assertEqual(resolve(root, 'wiki'), wiki)
            with self.assertRaises(ValueError): validate_key('Old_Game')
            self.assertEqual(validate_key('Old_Game', strict=False), ['Old_Game'])

    def test_invalid_keys(self):
        for key in ('../outside', '/absolute', 'a/b/c', 'Upper', 'a\\b', 'a//b'):
            with self.assertRaises(ValueError): validate_key(key)

    def test_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(__file__).with_name('new_project.py')
            result=subprocess.run([sys.executable,str(script),'product/work','--repo-root',tmp],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((Path(tmp)/'projects/product/work/work-change-log.md').is_file())
            self.assertEqual(len(discover(tmp)),1)
            result=subprocess.run([sys.executable,str(script),'product/work','--repo-root',tmp],capture_output=True)
            self.assertNotEqual(result.returncode,0)

if __name__ == '__main__':
    unittest.main()
