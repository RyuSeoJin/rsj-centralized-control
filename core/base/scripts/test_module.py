"""복수 전제의 활성화 차단과 해제 보호를 검사합니다."""
# CHANGELOG · 2026-10-12: 다중 전제 회귀 시험
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import module


class ModuleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.core = self.root / 'core'
        self.project = self.root / 'projects' / 'sample'
        self.project.mkdir(parents=True)
        self.state = self.project / 'sample-modules.json'
        self.state.write_text('{"on": []}', encoding='utf-8')
        (self.root / 'workspace.json').write_text('{"modules": ["shared"]}', encoding='utf-8')
        self.add('shared', '', 'workspace')
        self.add('plan', '')
        self.add('child', '- `plan` — planning\n- `shared` — shell')
        self.patch = patch.object(module, 'core_root', return_value=str(self.core))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def add(self, name, parents, scope='project'):
        folder = self.core / 'modules' / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'module.md').write_text('# '+name+'\n## 전제 모듈\n'+parents+'\n## 다음 절\n', encoding='utf-8')
        (folder / 'module.json').write_text(json.dumps({'scope': scope, 'creates': []}), encoding='utf-8')

    def call(self, fn, name):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(str(self.root), 'sample', name)

    def test_both_required_and_parent_off_blocked(self):
        self.assertEqual(self.call(module.cmd_on, 'child'), 1)
        self.assertEqual(self.call(module.cmd_on, 'plan'), 0)
        self.assertEqual(self.call(module.cmd_on, 'child'), 0)
        self.assertEqual(self.call(module.cmd_off, 'plan'), 1)
        (self.root / 'workspace.json').write_text('{"modules": []}', encoding='utf-8')
        self.assertEqual(self.call(module.cmd_on, 'child'), 1)
        self.assertEqual(self.call(module.cmd_off, 'child'), 0)
        self.assertEqual(self.call(module.cmd_off, 'plan'), 0)

    def test_other_missing_parent(self):
        self.call(module.cmd_on, 'plan')
        (self.root / 'workspace.json').write_text('{"modules": []}', encoding='utf-8')
        self.assertEqual(self.call(module.cmd_on, 'child'), 1)
        self.assertNotIn('child', json.loads(self.state.read_text())['on'])

    def test_diamond_legacy_and_transitive(self):
        self.add('plan', '`shared`입니다. 기존 문단')
        self.assertEqual(module.prereq_chain('child'), ['shared', 'plan'])
        self.assertIn('child', module.dependents('shared'))

    def test_cycle_and_unknown_rejected(self):
        self.add('plan', '`child` — cycle')
        with self.assertRaises(ValueError):
            self.call(module.cmd_on, 'child')
        self.add('plan', '`missing` — unknown')
        with self.assertRaises(ValueError):
            self.call(module.cmd_on, 'child')
        self.assertEqual(json.loads(self.state.read_text())['on'], [])

    def test_regen_rejects_before_collecting_jobs(self):
        import regen
        self.state.write_text('{"on": ["child"]}', encoding='utf-8')
        with patch.object(regen, 'ROOT', str(self.root)), patch.object(regen, 'base_jobs') as jobs:
            with self.assertRaises(ValueError):
                regen.jobs()
            jobs.assert_not_called()
        self.state.write_text('{"on": ["child", "plan"]}', encoding='utf-8')
        module.validate_workspace(str(self.root))

    def test_invalid_scope_and_broken_state_rejected(self):
        self.state.write_text('{"on": ["shared"]}', encoding='utf-8')
        with self.assertRaises(ValueError):
            module.validate_workspace(str(self.root))
        self.state.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            module.validate_workspace(str(self.root))

    def test_output_owner_is_required(self):
        self.state.write_text('{"on": ["child", "plan"]}', encoding='utf-8')
        with patch.object(module, 'repo_root', return_value=str(self.root)):
            module.require_output_module('child', self.project / 'out.html')
            with self.assertRaises(ValueError):
                module.require_output_module('child', self.root / 'out.html')
            module.require_output_module('child', self.root / 'out.html', 'sample')
