"""앱 체험 모듈의 필수 파일과 실행 스크립트를 검사합니다."""
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parent
for relative in ('module.md', 'rules/runtime.md', 'runtime/app-preview.js', 'tests/runtime.cjs', 'tests/records.cjs'):
    assert (root / relative).is_file(), relative
node = shutil.which('node')
if node:
    subprocess.run([node, '--check', str(root / 'runtime/app-preview.js')], check=True)
else:
    print('Node 없음: JavaScript 문법 검사는 별도로 실행해야 합니다')
print('app-preview 필수 파일 검사 통과')
