"""워크플로우 탐색기 모듈의 필수 파일과 예시 데이터 조립을 검사합니다."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
for relative in ('module.md', 'rules/explorer.md', 'runtime/workflow-explorer.js', 'runtime/workflow-explorer.css',
                 'scripts/build_explorer.py', 'design-template/workflow-explorer-template-catalog.md',
                 'design-template/workflow-explorer-sample.json', 'design-template/workflow-explorer-node-table-sample.md',
                 'scripts/project_data.py', 'scripts/capture_ui.py'):
    assert (root / relative).is_file(), relative
sys.path.insert(0, str(root / 'scripts'))
import build_explorer  # noqa: E402
import project_data  # noqa: E402

sample = json.loads((root / 'design-template/workflow-explorer-sample.json').read_text(encoding='utf-8'))
errors, warns = build_explorer.validate(sample)
assert not errors, errors
broken = json.loads(json.dumps(sample))
broken['links'].append({'from': 'S9', 'to': 'Z9', 'kind': 'normal'})
assert build_explorer.validate(broken)[0], '끊긴 연결을 오류로 잡지 못했습니다'
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / 'sample.html'
    build_explorer.build(sample, str(out))
    text = out.read_text(encoding='utf-8')
    assert 'id="wfx-data"' in text
    assert 'id="wfx-dock"' in text, '플로우 패널 접기 버튼이 조립되지 않았습니다'
    assert 'id="wfx-guide"' in text and 'data-guide="lines"' in text and '<strong>파랑</strong>' in text, '작성 규칙 창(meta.guide)이 조립되지 않았습니다'
    assert not re.search(r'<script[^>]+src=|<link[^>]+href=', text), '외부 참조가 남았습니다'
# 노드 표 읽기 — 도형·구역·문구 줄바꿈·조건 판정·상태 키·연결 라벨과 다른 흐름으로 가는 연결
table = (root / 'design-template/workflow-explorer-node-table-sample.md').read_text(encoding='utf-8')
nodes, edges = project_data.read_node_table(table, 'S', 'sample')
by = {n['id']: n for n in nodes}
assert [n['id'] for n in nodes] == ['S1-01', 'S1-02', 'S1-03', 'S1-04'], nodes
assert by['S1-01']['type'] == 'term' and by['S1-02']['lane'] == 's' and by['S1-03']['text'] == '[화면]\n홈' and by['S1-04']['text'] == '[화면] 로그인\n계정 선택', by['S1-04']
assert by['S1-02']['check'] == {'path': 'user.signedIn'} and by['S1-03']['state'] == 'home' and by['S1-04']['actions'] == ['sign-in']
assert {'from': 'S1-02', 'to': 'S1-04', 'kind': 'no', 'label': '로그인 필요'} in edges and {'from': 'S1-03', 'to': 'T1', 'kind': 'normal', 'label': ''} in edges
for bad in (table.replace('흐름 S**', '흐름 X**'), table.replace('→ S1-02 |', '→→ S1-02 |')):
    try:
        project_data.read_node_table(bad, 'S', 'sample')
        raise AssertionError('읽지 못할 노드 표를 오류로 잡지 못했습니다')
    except ValueError:
        pass
# 배치 지정 — 도형·연결 필드, 흐름 사이 연결의 칩, 나가는 연결 순서
flows = [{'nodes': [dict(n) for n in nodes], 'edges': [dict(e) for e in edges if e['to'] != 'T1']}]
links = [{'from': 'S1-03', 'to': 'T1', 'kind': 'normal'}]
project_data.apply_layout(flows, links, {'below': {'S1-04'}, 'under': {'S1-03': 'S1-02'}, 'exit': {('S1-02', 'S1-03'): 'd'},
                                         'chip': {('S1-03', 'T1')}, 'order': {'S1-02': ['S1-04', 'S1-03']}})
lay = {n['id']: n for n in flows[0]['nodes']}
assert lay['S1-04']['below'] is True and lay['S1-03']['under'] == 'S1-02' and links[0]['chip'] is True
assert [e['to'] for e in flows[0]['edges'] if e['from'] == 'S1-02'] == ['S1-04', 'S1-03']
assert next(e for e in flows[0]['edges'] if e['to'] == 'S1-03')['exit'] == 'd'
assert project_data.attach_thumbs(flows, root / 'design-template', root / 'module.md') == 0  # 캡처 목록이 없으면 붙이지 않음
node = shutil.which('node')
if node:
    subprocess.run([node, '--check', str(root / 'runtime/workflow-explorer.js')], check=True)
else:
    print('Node 없음: JavaScript 문법 검사는 별도로 실행해야 합니다')
print('workflow-explorer 필수 파일·예시 조립·노드 표·배치 지정 검사 통과')
