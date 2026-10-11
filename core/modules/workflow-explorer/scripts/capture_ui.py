"""탐색기 UI 구역용 화면 캡처 엔진입니다.

규칙: rules/explorer.md §6. 두 방식이 같은 캡처 목록(manifest.json)과 그림({도형}.webp)을 만듭니다.

- replay(...)  — 탐색기를 열어 시뮬레이터를 불러오고, 상태 키 도형에서 출발해 연결의 실행 action을 차례로 눌러
                 탐색기 경로가 실제로 그 도형에 닿았을 때만 찍습니다. 닿지 못하면 실패 목록에 남깁니다.
- recipes(...) — 시뮬레이터를 직접 열고 상태 이동(goto) 뒤 도형마다 정한 재현 순서(레시피)를 실행해 찍습니다.
                 경로 재생으로 만들 수 없는 화면(조건의 한쪽 · 금방 지나가는 화면 · 셸 패널)에 씁니다.

앱 문서의 함수 이름·버튼 속성·셸 선택자처럼 시뮬레이터마다 다른 것은 전부 인자로 받습니다.
필요: pip install playwright pillow · 설치된 Microsoft Edge(channel msedge)
"""
import functools
import hashlib
import http.server
import io
import json
import threading
import time
from datetime import datetime
from pathlib import Path

THUMB_W, QUALITY = 220, 62

#: 탐색기 안에서 실행하는 계획 함수 — 도형마다 (출발 상태 도형, 누를 action 목록)을 고릅니다.
#: UI 구역을 채울 도형은 상태 키 도형 · 화면 기록이 있는 도형 · 출력 도형이고, 시작·종료 도형은 화면이 아니라 찍지 않습니다.
PLAN_JS = r"""
() => {
  const W = window.WorkflowExplorer, N = W.nodes, O = W.out;
  const res = id => { const seen = {}; while (N[id] && N[id].type === 'ref' && N[id].target && !seen[id]) { seen[id] = 1; id = N[id].target; } return id; };
  const acts = e => (e.actions || []).concat(N[res(e.to)].actions || []);
  const starts = Object.keys(N).filter(k => N[k].state);
  const targets = Object.keys(N).filter(k => N[k].type !== 'ref' && N[k].type !== 'term' && (N[k].state || (N[k].screens && N[k].screens.length) || N[k].type === 'output'));
  // 상태 도형 전부에서 동시에 넓이 우선 탐색 — 가장 가까운 상태에서 출발하는 경로를 고릅니다.
  const prev = {}, q = [];
  starts.forEach(s => { prev[s] = null; q.push(s); });
  while (q.length) { const id = q.shift(); (O[id] || []).forEach(e => { const t = res(e.to); if (!(t in prev)) { prev[t] = e; q.push(t); } }); }
  return targets.map(t => {
    if (N[t].state) return { id: t, from: t, actions: [] };
    if (!(t in prev)) return { id: t, from: null, actions: [] };
    const edges = []; let id = t; while (prev[id]) { edges.unshift(prev[id]); id = prev[id].from; }
    const actions = [];
    edges.forEach(e => { const xs = acts(e), a = xs.filter(x => !x.endsWith('*'))[0] || xs[0]; if (a) actions.push(a); });
    return { id: t, from: id, actions };
  });
}
"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory):
    """문서 폴더를 임시 로컬 서버로 엽니다(iframe 상대 경로가 file://에서 막히지 않게)."""
    handler = functools.partial(QuietHandler, directory=str(directory))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def save_thumb(png, path, width=THUMB_W, quality=QUALITY):
    """캡처를 폭 width의 WebP로 줄여 저장하고 높이를 돌려줍니다.

    같은 파일을 미리보기 서버 · 탐색기 재생성이 잠깐 붙잡고 있으면 쓰기가 실패하므로 몇 번 다시 시도합니다."""
    from PIL import Image
    img = Image.open(io.BytesIO(png)).convert('RGB')
    h = round(img.height * width / img.width)
    img = img.resize((width, h), Image.LANCZOS)
    for attempt in range(10):
        try:
            img.save(path, 'WEBP', quality=quality, method=6)
            return h
        except OSError:
            if attempt == 9:
                raise
            time.sleep(1.5)


def _item(nid, h, width, src, actions, sha):
    return {'file': '%s.webp' % nid, 'w': width, 'h': h, 'from': src, 'actions': actions,
            'simulatorSha256': sha, 'capturedAt': datetime.now().strftime('%Y-%m-%d %H:%M')}


def _report(ok, failed):
    print('찍은 도형 %d · 실패 %d' % (len(ok), len(failed)))
    for k, v in sorted(failed.items()):
        print('실패', k, v)


def replay(docs, explorer, simulator, out, *, press_js, only=None, skip=None, wait_prefixes=(),
           reset_js='', shell_js='', before_shot_js='', note='', width=THUMB_W, quality=QUALITY):
    """경로 재생 캡처.

    docs        탐색기 · 시뮬레이터 HTML이 있는 문서 폴더
    explorer    탐색기 파일 이름 / simulator 시뮬레이터 HTML 경로(해시를 캡처에 기록) / out 그림 폴더
    press_js    앱 문서에서 action 하나를 누르는 함수 식 `(a) => 'click'|'handle'|'missing'`
    wait_prefixes  누르지 않고 기다리는 사건의 앞부분(시뮬레이터가 스스로 알리는 것)
    reset_js    상태 이동 전 앱 문서에서 실행(앞 도형의 시트·팝업 걷어 내기) / shell_js 그때 셸 문서에서 실행
    before_shot_js 찍기 직전 앱 문서에서 실행(진입 연출 끝내기 등)
    skip        {도형: 까닭} — 찍지 않는 도형. 레시피로 찍은 도형(actions == ['recipe'])은 덮지 않습니다
    """
    from playwright.sync_api import sync_playwright
    docs, out, simulator = Path(docs), Path(out), Path(simulator)
    skip = skip or {}
    out.mkdir(parents=True, exist_ok=True)
    mpath = out / 'manifest.json'
    manifest = json.loads(mpath.read_text(encoding='utf-8')) if mpath.exists() else {'items': {}}
    sha = hashlib.sha256(simulator.read_bytes()).hexdigest()
    # 레시피로 찍은 도형은 경로 재생으로 덮지 않습니다 — 금방 지나가는 화면은 경로 재생으로는 다음 화면이 찍힙니다.
    recipe = {k: v for k, v in manifest.get('items', {}).items() if v.get('actions') == ['recipe']}
    srv = serve(docs)
    url = 'http://127.0.0.1:%d/%s' % (srv.server_address[1], explorer)
    ok, failed = {}, {}

    def save_partial(done):
        cur = json.loads(mpath.read_text(encoding='utf-8')) if mpath.exists() else {'items': {}}
        cur.setdefault('items', {}).update(done)
        cur['failed'] = {k: v for k, v in cur.get('failed', {}).items() if k not in done}
        mpath.write_text(json.dumps(cur, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1600, 'height': 1000})
        # 탐색기 보기 방식은 연속으로 둡니다 — 정지(기본)는 시뮬레이터 사건으로 경로를 옮기지 않아 도착 확인을 할 수 없습니다.
        page.add_init_script("try { localStorage.setItem('wfx-mode', 'run'); localStorage.setItem('wfx-follow', 'off'); } catch (e) {}")
        page.goto(url)
        page.click('#wfx-sim-load')
        page.wait_for_function('() => window.WorkflowExplorer.sim.connected', timeout=60000)
        plans = page.evaluate(PLAN_JS)
        app = page.frame_locator('.wfx-sim-frame').frame_locator('#app')
        for plan in plans:
            nid = plan['id']
            if (only and nid not in only) or nid in recipe or nid in skip:
                continue
            if not plan['from']:
                failed[nid] = '상태 키 도형에서 닿는 경로가 없음'
                continue
            app_frame = next((f for f in page.frames if f.parent_frame and f.parent_frame.parent_frame), None)
            if app_frame and (reset_js or shell_js):
                if reset_js:
                    app_frame.evaluate(reset_js)
                if shell_js:
                    app_frame.parent_frame.evaluate(shell_js)
                time.sleep(2.5)
            page.evaluate('id => window.WorkflowExplorer.startAt(id)', plan['from'])
            try:
                page.wait_for_function('() => !window.WorkflowExplorer.sim.busy', timeout=45000)
            except Exception:
                failed[nid] = '상태 이동 시간 초과 (%s)' % plan['from']
                continue
            time.sleep(1.2)
            how = []
            for act in plan['actions']:
                if act.split(':')[0] in wait_prefixes:
                    how.append('%s:wait' % act)
                    time.sleep(2.2)
                    continue
                r = app_frame.evaluate(press_js, act) if app_frame else 'missing'
                how.append('%s:%s' % (act, r))
                time.sleep(0.9)
            time.sleep(0.6)
            reached = page.evaluate("""id => { const S = window.WorkflowExplorer.state;
                return S.pos === id || S.segments.some(s => s.steps.some(st => st.node === id)); }""", nid)
            if not reached:
                failed[nid] = '경로가 도형에 닿지 않음 · 출발 %s · %s · 멈춘 곳 %s' % (
                    plan['from'], ' → '.join(how) or '행동 없음', page.evaluate('() => window.WorkflowExplorer.state.pos'))
                continue
            if app_frame and before_shot_js:
                app_frame.evaluate(before_shot_js)
                time.sleep(0.4)
            png = app_frame.parent_frame.locator('#app').screenshot() if app_frame else app.locator('body').screenshot()
            h = save_thumb(png, out / ('%s.webp' % nid), width, quality)
            ok[nid] = _item(nid, h, width, plan['from'], plan['actions'], sha)
            print('찍음', nid, '←', plan['from'], ' '.join(plan['actions']))
            save_partial(ok)  # 브라우저가 중간에 죽어도 찍은 것까지는 남깁니다
        browser.close()
    srv.shutdown()
    # 전체 실행이면 이번 결과만 남깁니다(실패한 도형의 예전 그림은 목록에서 빠져 탐색기에 붙지 않습니다).
    # only로 일부만 찍으면 나머지 기존 항목과, 이번에 찍지 않은 도형의 실패 기록을 유지합니다.
    manifest = json.loads(mpath.read_text(encoding='utf-8')) if mpath.exists() else manifest
    items = dict(manifest.get('items', {})) if only else dict(recipe)
    items.update(ok)
    if only:
        failed = {**{k: v for k, v in manifest.get('failed', {}).items() if k not in only and k not in items}, **failed}
    manifest = {'simulator': simulator.name, 'note': note or '캡처 도구가 만듭니다. 손으로 고치지 않습니다.',
                'items': dict(sorted(items.items())), 'failed': dict(sorted(failed.items()))}
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    _report(ok, failed)
    return ok, failed


#: 레시피 단계 종류 — 앱 문서에서 실행 · 셸 문서에서 실행 · 기다림(초)
J, S, W = 'js', 'shell', 'wait'


def recipes(docs, simulator, out, table, *, goto_js, ready_js, query='?wfx', checks=None, prelude_js='',
            reset_js='', after_js='', cleanup_js='', no_cleanup=(), only=None, width=THUMB_W, quality=QUALITY):
    """레시피 캡처.

    table       {도형: (출발 상태, [(J|S|W, 값), …], 찍을 곳)} — 찍을 곳은 'app'(기기 화면) 또는 셸 요소 선택자
    goto_js     셸 문서에서 실행하는 상태 이동 함수 식 `(state) => Promise<bool>`
    ready_js    시뮬레이터가 연결 준비를 마쳤는지 판정하는 식
    checks      {도형: 'return …'} — 찍기 직전 화면이 의도대로인지 출력해 봅니다(사람이 확인)
    prelude_js  상태 이동 뒤 앱 문서에 심는 도우미 / reset_js 상태 이동 전 앱 문서에서 실행(앞 레시피의 흔적 지우기)
    after_js    찍은 뒤 앱 문서에서 실행(레시피가 바꾼 브라우저 동작 되돌리기 등)
    cleanup_js  레시피 앞뒤로 앱 문서에서 실행(진입 연출 끝내기 등) — no_cleanup의 도형은 건너뜁니다
    """
    from playwright.sync_api import sync_playwright
    docs, out, simulator = Path(docs), Path(out), Path(simulator)
    checks = checks or {}
    out.mkdir(parents=True, exist_ok=True)
    mpath = out / 'manifest.json'
    sha = hashlib.sha256(simulator.read_bytes()).hexdigest()
    srv = serve(docs)
    url = 'http://127.0.0.1:%d/%s%s' % (srv.server_address[1], simulator.name, query)
    ok, failed = {}, {}

    def save():
        cur = json.loads(mpath.read_text(encoding='utf-8')) if mpath.exists() else {'items': {}, 'failed': {}}
        cur.setdefault('items', {}).update(ok)
        cur['failed'] = {**{k: v for k, v in cur.get('failed', {}).items() if k not in ok}, **failed}
        cur['items'] = dict(sorted(cur['items'].items()))
        cur['failed'] = dict(sorted(cur['failed'].items()))
        mpath.write_text(json.dumps(cur, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1600, 'height': 1000})
        page.goto(url, timeout=120000)
        page.wait_for_function(ready_js, timeout=120000)
        for nid, (st, steps, target) in table.items():
            if only and nid not in only:
                continue
            frame = next((f for f in page.frames if f.parent_frame is page.main_frame), None)
            try:
                if reset_js:
                    frame.evaluate(reset_js)
                if not page.evaluate(goto_js, st):
                    failed[nid] = '상태 이동 실패 (%s)' % st
                    save()
                    continue
                time.sleep(0.6)
                frame = next((f for f in page.frames if f.parent_frame is page.main_frame), None)
                if prelude_js:
                    frame.evaluate(prelude_js)
                clean = cleanup_js and nid not in no_cleanup
                if clean:
                    frame.evaluate(cleanup_js)
                for kind, val in steps:
                    if kind == W:
                        time.sleep(val)
                    elif kind == J:
                        frame.evaluate('() => { %s }' % (val if val.startswith('return') else val + ';'))
                    elif kind == S:
                        page.evaluate('() => { %s }' % val)
                if clean:
                    frame.evaluate(cleanup_js)
                    time.sleep(0.2)
                if checks.get(nid):
                    print('확인', nid, frame.evaluate('() => { %s }' % checks[nid]))
                png = page.locator('#app').screenshot() if target == 'app' else page.locator(target).first.screenshot()
                if after_js:
                    frame.evaluate(after_js)
            except Exception as e:  # 한 도형이 실패해도 다음 도형을 찍습니다
                failed[nid] = '레시피 실행 오류 · %s' % str(e).splitlines()[0][:160]
                save()
                continue
            h = save_thumb(png, out / ('%s.webp' % nid), width, quality)
            ok[nid] = _item(nid, h, width, st, ['recipe'], sha)
            print('찍음', nid, '←', st)
            save()
        browser.close()
    srv.shutdown()
    _report(ok, failed)
    return ok, failed
