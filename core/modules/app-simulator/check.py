"""app-simulator 모듈의 필수 파일과 조립 도구를 검사합니다."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
for relative in ('module.md', 'rules/simulator.md', 'runtime/sim-shell.js', 'scripts/build_simulator.py'):
    assert (root / relative).is_file(), relative
sys.path.insert(0, str(root / 'scripts'))
import build_simulator as b  # noqa: E402

shell = b.runtime()
for name in ('const SimShell', 'function relay(', 'function capture(', "'wfx-app'", 'getDisplayMedia'):
    assert name in shell, '셸 실행기에 %s가 없습니다' % name
sample = {'a': '</script>' + chr(0x2028)}
assert b.js_json(sample) == '{"a":"' + chr(92) + 'u003c/script>' + chr(92) + 'u2028"}', b.js_json(sample)
assert b.fill('<p>{{a}}</p>', {'a': 'x'}) == '<p>x</p>'
try:
    b.fill('<p>{{a}}{{b}}</p>', {'a': 'x'})
    raise AssertionError('채우지 못한 토큰을 잡지 못했습니다')
except ValueError:
    pass
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    (d / 'a.png').write_bytes(b'\x89PNG same')
    (d / 'b.png').write_bytes(b'\x89PNG same')
    (d / 'c.svg').write_text('<svg/>', encoding='utf-8')
    (d / 'skip.png').write_bytes(b'\x89PNG other')
    (d / 'note.txt').write_text('x', encoding='utf-8')
    assets, aliases = b.collect_assets(d, keep=lambda p: p.stem != 'skip', assets={'first': 'data:,'})
    assert list(assets) == ['first', 'a', 'c'] and aliases == {'b': 'a'}, (list(assets), aliases)
    assert assets['c'].startswith('data:image/svg+xml;base64,')
    assert b.inline_assets('x{background:url({{asset:c.svg}})}', d).startswith('x{background:url(data:image/svg+xml;base64,')
    out = d / 'out.html'
    b.write_or_check(out, 'ok')
    b.write_or_check(out, 'ok', check=True)
    try:
        b.write_or_check(out, 'changed', check=True)
        raise AssertionError('재생성 누락을 잡지 못했습니다')
    except SystemExit:
        pass
node = shutil.which('node')
if node:
    subprocess.run([node, '--check', str(root / 'runtime/sim-shell.js')], check=True)
else:
    print('Node 없음: JavaScript 문법 검사는 별도로 실행해야 합니다')
print('app-simulator 필수 파일·조립 도구 검사 통과')
