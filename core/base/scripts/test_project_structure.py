"""선택 구조의 호환·참조·소유 경계와 생성 충돌을 검사합니다."""
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from project_structure import load_structure, resource_path, path_role


class StructureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # 임시 폴더가 Windows 짧은 이름(RECORD~1)으로 오면 resolve() 결과와 달라집니다.
        # 도구는 실제 경로를 돌려주므로, 비교하는 쪽도 실제 경로로 맞춥니다
        self.project = Path(self.tmp.name).resolve() / 'work'
        self.project.mkdir()
        self.config = self.project/'work-structure.json'
        (self.project/'ui').mkdir()
        (self.project/'ui/spec.md').write_text('draft', encoding='utf-8')
        self.data = {'schema_version':1, 'resources':[
            dict(id='ui', label='UI', path='ui', kind='directory', role='navigation'),
            dict(id='spec', label='Spec', path='ui/spec.md', kind='file', role='specification', parent='ui')]}

    def write(self):
        self.config.write_text(json.dumps(self.data), encoding='utf-8')

    def test_legacy_and_registered_paths(self):
        self.assertIsNone(load_structure(self.project))
        self.assertEqual(resource_path(self.project,'spec','ui/spec.md'),self.project/'ui/spec.md')
        self.write()
        self.assertEqual(resource_path(self.project,'spec','old.md'),self.project/'ui/spec.md')
        with self.assertRaises(ValueError):resource_path(self.project,'missing','ui/spec.md')

    def test_invalid_config_is_not_legacy(self):
        self.config.write_text('{broken',encoding='utf-8')
        with self.assertRaises(ValueError):resource_path(self.project,'spec','ui/spec.md')

    def test_escapes_and_missing_files(self):
        for value in ('../outside.md','C:/outside.md','/outside.md','ui\\spec.md','missing.md'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.data['resources'][1]['path']=value
                self.write();load_structure(self.project)

    def test_bad_graphs(self):
        for field,value in [('parent','spec'),('parent','missing'),('depends_on',['spec']),('depends_on',['missing'])]:
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                self.data['resources'][1][field]=value
                self.write();load_structure(self.project)
            self.data['resources'][1].pop(field,None)

    def test_duplicate_and_output_collision(self):
        self.data['resources'].append(dict(self.data['resources'][1]))
        self.write()
        with self.assertRaises(ValueError):load_structure(self.project)
        self.data['resources'].pop()
        (self.project/'build.py').write_text('',encoding='utf-8')
        self.data['jobs']=[dict(label='build',script='build.py',inputs=['spec'],outputs=['ui/spec.md'])]
        self.write()
        with self.assertRaises(ValueError):load_structure(self.project)

    def test_roles_follow_relocated_files(self):
        self.data['resources'][1]['role']='reference'
        self.write()
        self.assertEqual(path_role(self.project,self.project/'ui/spec.md'),'reference')
        self.data['resources'][1]['role']='archive'
        self.write()
        self.assertEqual(path_role(self.project,self.project/'ui/spec.md'),'archive')

    def test_custom_scaffold_and_invalid_preflight(self):
        template = Path(self.tmp.name)/'layout.json'
        template.write_text(json.dumps({'schema_version':1,'resources':[self.data['resources'][0]]}),encoding='utf-8')
        command = [sys.executable,str(Path(__file__).with_name('new_project.py')),'product/custom','--repo-root',self.tmp.name,'--structure',str(template)]
        result = subprocess.run(command,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        target = Path(self.tmp.name)/'projects/product/custom'
        self.assertTrue((target/'ui').is_dir())
        self.assertFalse((target/'spec').exists())
        self.assertIsNotNone(load_structure(target))
        self.data['resources'][0]['path']='../outside'
        template.write_text(json.dumps(self.data),encoding='utf-8')
        command[2]='product/invalid'
        self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
        self.assertFalse((Path(self.tmp.name)/'projects/product/invalid').exists())


if __name__ == '__main__':
    unittest.main()
