"""프로젝트 원본을 탐색기 데이터로 바꿀 때 쓰는 공용 도구입니다.

규칙: rules/explorer.md §6. 프로젝트 생성기는 원본 경로·흐름 목록·배치 지정 값만 갖고, 읽기와 붙이기는 여기서 합니다.

- read_node_table(text, code, name) — 기획서의 「워크플로우 노드 · 흐름 {코드}」 표 → (도형 목록, 연결 목록)
- apply_layout(flows, links, layout) — 배치 지정 값(below · rowFirst · under · colAfter · exit · passBelow · chip · order)을 도형·연결에 붙입니다
- attach_thumbs(flows, ui_dir, simulator_html) — 캡처 목록(manifest.json)의 그림을 도형 썸네일로 넣습니다
- section_names(rules) — 흐름도 작성 규칙 데이터에서 「섹션 · 이름」 표를 찾아 {섹션: 이름}으로 돌려줍니다
"""
import base64
import hashlib
import json
import re
from pathlib import Path

#: 노드 표의 도형 · 구역 이름 → 탐색기 값
TYPES = {'시작·종료': 'term', '행동': 'action', '입력': 'input', '출력': 'output', '조건': 'decision', '공통 처리': 'process'}
LANES = {'유저': 'u', '시스템': 's'}


def cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def plain(value):
    value = value.replace('`', '').strip()
    return '' if value in ('—', '-', '') else value


def read_node_table(text, code, name=''):
    """노드 표 → (도형 목록, 연결 목록). 다른 흐름으로 가는 연결도 함께 돌려줍니다. 표를 못 읽으면 ValueError."""
    m = re.search(r'^\*\*워크플로우 노드 · 흐름 %s\*\*\s*$' % re.escape(code), text, flags=re.M)
    if not m:
        raise ValueError('%s: 「워크플로우 노드 · 흐름 %s」 표가 없습니다' % (name, code))
    rows, head = [], None
    for line in text[m.end():].splitlines():
        if line.startswith('#'):
            break
        if not line.startswith('|'):
            if rows:
                break
            continue
        if head is None:
            head = cells(line)
            continue
        if set(line.replace('|', '').strip()) <= set('-: '):
            continue
        rows.append(dict(zip(head, cells(line))))
    nodes, edges = [], []
    for r in rows:
        label = r['문구'].replace(' / ', '\n')  # 표 한 칸에서는 줄바꿈 대신 「 / 」로 나눕니다
        mm = re.match(r'^(\[[^\]]+\])\s*(.+)$', label)
        node = {'id': r['코드'], 'code': r['코드'], 'type': TYPES[r['도형']], 'lane': LANES[r['구역']],
                'text': mm.group(1) + '\n' + mm.group(2) if mm else label, 'note': '근거 · ' + r['근거']}
        if plain(r['실행 action']):
            node['actions'] = [a.strip() for a in plain(r['실행 action']).split(',') if a.strip()]
        crit = plain(r['판정 기준'])
        if crit:
            key, _, value = crit.partition('=')
            node['check'] = {'path': key.strip()}
            if value:
                node['check']['equals'] = value.strip()
        if plain(r['상태 키']):
            node['state'] = plain(r['상태 키'])
        nodes.append(node)
        for part in r['나감'].split(' / '):
            part = part.strip()
            if part in ('?', '—', ''):
                continue
            em = re.match(r'^(예|아니오)?\s*→\s*(\S+)(?:\s*·\s*(.+))?$', part)
            if not em:
                raise ValueError('%s %s: 나감을 읽지 못했습니다 — %r' % (name, r['코드'], part))
            kind = {'예': 'yes', '아니오': 'no'}.get(em.group(1), 'normal')
            edges.append({'from': r['코드'], 'to': em.group(2), 'kind': kind, 'label': em.group(3) or (em.group(1) or '')})
    return nodes, edges


def apply_layout(flows, links, layout):
    """배치 지정 값을 붙입니다. layout의 키(모두 선택):

    below · rowFirst — 도형 id 집합 / under · colAfter — {도형: 기준 도형}
    exit — {(출발, 도착): 'r'|'d'|'u'} / passBelow — {(출발, 도착): [도형, …]} / chip — {(출발, 도착)}
    order — {출발 도형: [도착 순서]} (나가는 연결 순서를 바꿉니다)
    """
    get = lambda key, empty: layout.get(key) or empty
    below, row_first, under, col_after = get('below', set()), get('rowFirst', set()), get('under', {}), get('colAfter', {})
    exit_, pass_below, chip, order = get('exit', {}), get('passBelow', {}), get('chip', set()), get('order', {})
    for f in flows:
        for n in f['nodes']:
            if n['id'] in below:
                n['below'] = True
            if n['id'] in row_first:
                n['rowFirst'] = True
            if n['id'] in under:
                n['under'] = under[n['id']]
            if n['id'] in col_after:
                n['colAfter'] = col_after[n['id']]
        for e in f.get('edges', []):
            pair = (e['from'], e['to'])
            if pair in exit_:
                e['exit'] = exit_[pair]
            if pair in pass_below:
                e['passBelow'] = pass_below[pair]
            if pair in chip:  # 같은 흐름 안 섹션을 건너는 연결도 칩으로
                e['chip'] = True
        es = f.get('edges', [])
        for src, seq in order.items():
            idx = [i for i, e in enumerate(es) if e['from'] == src]
            picked = sorted((es[i] for i in idx), key=lambda e: seq.index(e['to']) if e['to'] in seq else len(seq))
            for i, e in zip(idx, picked):
                es[i] = e
    for l in links or []:
        if (l['from'], l['to']) in chip:
            l['chip'] = True


def attach_thumbs(flows, ui_dir, simulator_html):
    """캡처 목록의 그림을 도형 썸네일(data URL)로 넣고, 넣은 수를 돌려줍니다.

    시뮬레이터 파일의 해시가 찍을 때와 다르면 낡은 캡처(stale)로 표시합니다. 상태 키가 없는 도형은 캡처가
    실제로 닿은 출발 상태와 행동 순서를 도달 방법(reach)으로, 찍지 못한 도형은 그 까닭을 reachNote로 붙입니다.
    """
    ui_dir, simulator_html = Path(ui_dir), Path(simulator_html)
    mpath = ui_dir / 'manifest.json'
    if not mpath.exists():
        return 0
    manifest = json.loads(mpath.read_text(encoding='utf-8'))
    items, failed = manifest.get('items', {}), manifest.get('failed', {})
    states = {n['id']: n.get('state') for f in flows for n in f['nodes']}
    sha = hashlib.sha256(simulator_html.read_bytes()).hexdigest() if simulator_html.exists() else ''
    count = 0
    for f in flows:
        for n in f['nodes']:
            it = items.get(n['id'])
            if it and not n.get('state') and states.get(it.get('from')):
                n['reach'] = {'state': states[it['from']], 'actions': it.get('actions', [])}
            if n['id'] in failed and not n.get('state'):
                n['reachNote'] = failed[n['id']]
            if not it or not (ui_dir / it['file']).exists():
                continue
            data = base64.b64encode((ui_dir / it['file']).read_bytes()).decode('ascii')
            n['thumb'] = {'src': 'data:image/webp;base64,' + data, 'w': it['w'], 'h': it['h'],
                          'stale': it.get('simulatorSha256') != sha}
            count += 1
    return count


def section_names(rules):
    """흐름도 작성 규칙 데이터에서 머리글이 「섹션 · 이름」인 표를 찾아 {섹션: 이름}으로 돌려줍니다."""
    found = {}
    for sec in (rules or {}).get('sections', []):
        for b in sec.get('blocks', []):
            if b.get('t') == 'table' and b.get('head', [])[:2] == ['섹션', '이름']:
                found.update({r[0]: r[1] for r in b.get('rows', []) if len(r) >= 2})
    return found
