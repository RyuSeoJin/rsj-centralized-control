# -*- coding: utf-8 -*-
"""워크플로우 탐색기 조립 — 흐름 데이터(JSON)를 자기완결 HTML 한 장으로 만듭니다.

입력 형식과 검증 기준의 정본은 rules/explorer.md입니다. 이 도구는
  ① 데이터를 검증하고(끊긴 연결·조건 출구·구역·중복 id)
  ② 마스터 CSS·JS와 실행기(runtime/)를 인라인해 한 파일로 씁니다.

사용법
------
    python core/modules/workflow-explorer/scripts/build_explorer.py 입력.json 출력.html
    python core/modules/workflow-explorer/scripts/build_explorer.py 입력.json --check

프로젝트 생성기는 자기 원본을 이 형식으로 바꾼 뒤 build()를 부릅니다.
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
CORE = os.path.dirname(os.path.dirname(MODULE))
sys.path.insert(0, os.path.join(CORE, "base", "scripts"))
# 셸과 마스터는 qa-site 모듈의 것입니다 — 이 모듈은 qa-site를 전제합니다(module.md §전제 모듈)
sys.path.insert(0, os.path.join(CORE, "modules", "qa-site", "scripts"))
import shell  # noqa: E402

TYPES = ("term", "action", "process", "input", "output", "decision", "ref")
KINDS = ("normal", "yes", "no")


def validate(data):
    """데이터를 검사해 (오류, 경고) 목록을 돌려준다. 오류가 있으면 만들지 않는다."""
    errors, warns = [], []
    lanes = [l["key"] for l in data.get("lanes", [])] or ["u", "s"]
    ids = {}
    for f in data.get("flows", []):
        for n in f.get("nodes", []):
            if n["id"] in ids:
                errors.append("중복 id %s (%s · %s)" % (n["id"], ids[n["id"]], f["code"]))
            ids[n["id"]] = f["code"]
            if n.get("type") not in TYPES:
                errors.append("%s: 알 수 없는 도형 %r" % (n["id"], n.get("type")))
            if n.get("lane") not in lanes:
                errors.append("%s: 알 수 없는 구역 %r" % (n["id"], n.get("lane")))
    outs = {}
    for f in data.get("flows", []):
        for e in f.get("edges", []):
            for side in ("from", "to"):
                if e[side] not in ids:
                    errors.append("%s 흐름: 없는 도형 %s (%s→%s)" % (f["code"], e[side], e["from"], e["to"]))
            if e.get("kind", "normal") not in KINDS:
                errors.append("%s→%s: 알 수 없는 연결 %r" % (e["from"], e["to"], e.get("kind")))
            if e.get("exit") not in (None, "r", "d", "u"):
                errors.append("%s→%s: 알 수 없는 나가는 꼭짓점 %r (r·d·u)" % (e["from"], e["to"], e.get("exit")))
            outs.setdefault(e["from"], []).append(e)
    for e in data.get("links", []):
        for side in ("from", "to"):
            if e[side] not in ids:
                errors.append("흐름 사이 연결: 없는 도형 %s (%s→%s)" % (e[side], e["from"], e["to"]))
        outs.setdefault(e["from"], []).append(e)
    for f in data.get("flows", []):
        for n in f.get("nodes", []):
            es = outs.get(n["id"], [])
            kinds = [e.get("kind", "normal") for e in es]
            if n.get("type") == "decision" and not ("yes" in kinds and "no" in kinds):
                warns.append("%s: 조건의 예·아니오 출구가 모두 있지 않습니다 (%s)" % (n["id"], ", ".join(kinds) or "출구 없음"))
            if n.get("type") == "ref":
                if not n.get("target") or n["target"] not in ids:
                    errors.append("%s: 반복 지점의 도착 도형을 찾지 못했습니다 (%r)" % (n["id"], n.get("target")))
            elif not es and n.get("type") != "term":
                warns.append("%s: 나가는 연결이 없습니다" % n["id"])
    stale = [n["id"] for f in data.get("flows", []) for n in f.get("nodes", []) if (n.get("thumb") or {}).get("stale")]
    if stale:
        warns.append("낡은 화면 캡처 %d장 — 시뮬레이터가 캡처 뒤 바뀌었습니다 (%s)" % (len(stale), ", ".join(stale[:8]) + (" …" if len(stale) > 8 else "")))
    start = (data.get("meta") or {}).get("start")
    if start and start not in ids:
        errors.append("시작 도형 %s가 없습니다" % start)
    return errors, warns


# ── 작성 규칙 창(meta.guide) ──────────────────────────────────────────────
# 프로젝트가 흐름도 작성 규칙을 데이터로 넘기면 머리말의 버튼이 목차·본문이 있는 창을 엽니다.
# 블록 종류: p(문단) · h(소제목, level 3·4) · table(head·rows) · ul · ol · check(체크리스트) · code(도식).
# 글 안의 `코드` · **굵게** · [글](주소)를 옮기며, 「#섹션id」 링크는 창 안의 섹션으로 이어집니다.
def _inline(text):
    import re
    s = shell.esc(text)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)

    def link(m):
        label, href = m.group(1), m.group(2)
        if href.startswith("#"):
            return '<a href="#wfx-guide-%s" data-guide="%s">%s</a>' % (href[1:], href[1:], label)
        return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (href, label)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)


def _blocks(blocks):
    out = []
    for b in blocks:
        t = b.get("t")
        if t == "p":
            out.append("<p>%s</p>" % _inline(b["text"]))
        elif t == "h":
            lv = 3 if b.get("level", 3) <= 3 else 4
            out.append("<h%d>%s</h%d>" % (lv, _inline(b["text"]), lv))
        elif t == "table":
            head = "".join("<th>%s</th>" % _inline(c) for c in b.get("head", []))
            rows = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % _inline(c) for c in r) for r in b.get("rows", []))
            out.append('<div class="wfx-guide-table"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, rows))
        elif t in ("ul", "ol"):
            out.append("<%s>%s</%s>" % (t, "".join("<li>%s</li>" % _inline(i) for i in b.get("items", [])), t))
        elif t == "check":
            out.append('<ul class="wfx-guide-check">%s</ul>' % "".join("<li>%s</li>" % _inline(i) for i in b.get("items", [])))
        elif t == "code":
            out.append('<pre class="wfx-guide-code">%s</pre>' % shell.esc(b.get("text", "")))
    return "".join(out)


def guide_html(g):
    if not g:
        return "", ""
    esc = shell.esc
    stamp = " · ".join(x for x in (
        g.get("version") and "규칙 %s" % g["version"], g.get("confirmed") and "확정 %s" % g["confirmed"],
        g.get("revised") and "보완 %s" % g["revised"]) if x)
    toc = "".join('<li><a href="#wfx-guide-%s" data-guide="%s">%s</a></li>' % (esc(s["id"]), esc(s["id"]), esc(s["title"]))
                  for s in g.get("sections", []))
    secs = "".join('<section id="wfx-guide-%s"><h2>%s</h2>%s</section>' % (esc(s["id"]), esc(s["title"]), _blocks(s.get("blocks", [])))
                   for s in g.get("sections", []))
    button = '<button id="wfx-guide-open" class="wfx-guide-btn" aria-haspopup="dialog">%s</button>' % esc(g.get("button") or "작성 규칙")
    dialog = ('<dialog id="wfx-guide" class="wfx-guide" aria-labelledby="wfx-guide-title">'
              '<header><div><h2 id="wfx-guide-title">%s</h2><p>%s</p></div><button id="wfx-guide-close" aria-label="닫기">✕</button></header>'
              '<div class="wfx-guide-body"><nav aria-label="규칙 목차"><ol>%s</ol></nav><article id="wfx-guide-article">%s%s</article></div></dialog>'
              % (esc(g.get("title", "작성 규칙")), esc(stamp), toc, _blocks(g.get("intro", [])), secs))
    return button, dialog


def body(data, warns):
    meta = data.get("meta") or {}
    esc = shell.esc
    sim = meta.get("simulator")
    badges = "".join('<span class="lg-%s"><i></i>%s</span>' % (k, esc(v)) for k, v in (
        ("u", "유저 구역"), ("s", "시스템 구역"), ("yes", "예"), ("no", "아니오"), ("path", "진행 경로")))
    warn_html = ""
    if warns:
        warn_html = ('<details class="wfx-flownote"><summary>데이터 점검 %d건</summary><p>%s</p></details>'
                     % (len(warns), "<br>".join(esc(w) for w in warns)))
    guide_button, guide_dialog = guide_html(meta.get("guide"))
    # 오른쪽 칸 = 화면(2026-10-02 사용자 확정) — 불러오기 전에는 현재 위치의 캡처, 불러온 뒤에는 시뮬레이터
    load_btn = ('<button id="wfx-sim-load" title="%s">시뮬레이터 불러오기</button>' % esc(sim.get("note") or "불러오기를 누르면 시뮬레이터를 엽니다")) if sim else ""
    sim_html = (
        '<section class="wfx-simsec"><h2>화면</h2><p id="wfx-shot-title" class="wfx-shot-title"></p>'
        '<div class="wfx-simbar"><label class="wfx-follow"><input type="checkbox" id="wfx-follow" checked> 선택하면 이동</label>'
        '<span class="wfx-mode" role="group" aria-label="이동 뒤 보기"><button type="button" data-mode="stop">정지</button><button type="button" data-mode="run">연속</button></span>%s</div>'
        '%s'
        '<div id="wfx-stepbar" class="wfx-stepbar" hidden></div>'
        '<div id="wfx-sim"><div id="wfx-shot" class="wfx-shot-view"></div></div></section>'
        % (load_btn, '<div class="wfx-simbar wfx-simstate"><span id="wfx-sim-status">시뮬레이터 꺼짐</span><span id="wfx-sim-last"></span></div>' if sim else ''))
    return (
        '<body class="wfx-body"><div class="wfx-app">'
        '<header class="wfx-top"><h1>%s</h1><p class="wfx-lead">%s</p>%s<div class="wfx-legend">%s</div>'
        '<button id="wfx-simcol-toggle" class="wfx-simcol-toggle" aria-controls="wfx-simcol" aria-expanded="false">화면</button>%s</header>'
        '<main class="wfx-main"><div id="wfx-canvas"></div>'
        '<div class="wfx-tools"><div class="wfx-group"><button id="wfx-out" aria-label="축소">−</button>'
        '<span id="wfx-zoom">100%%</span><button id="wfx-in" aria-label="확대">+</button><button id="wfx-fit">전체 보기</button><button id="wfx-dock" aria-expanded="true">플로우 패널 접기</button></div>'
        '<div class="wfx-find"><input id="wfx-q" type="search" placeholder="코드·문구 검색" aria-label="도형 검색"><div id="wfx-results"></div></div></div>'
        '<details class="wfx-indexbox"><summary>흐름 목록</summary><ul id="wfx-index"></ul></details></main>'
        '<aside id="wfx-simcol" class="wfx-simcol" aria-label="화면">'
        '%s'
        '</aside>'
        '<aside class="wfx-side">'
        '<section><h2>현재 위치</h2><div id="wfx-options"></div></section>'
        '</aside>'
        '<section class="wfx-tracebox" aria-label="진행 경로 흐름도"><div id="wfx-trace-lanes"></div><div id="wfx-trace"></div></section>'
        '</div>%s'
        % (esc(meta.get("title", "워크플로우")), esc(meta.get("lead", "")), guide_button, badges, shell.header_toggle(),
           sim_html, guide_dialog))


def build(data, out_path):
    errors, warns = validate(data)
    if errors:
        raise SystemExit("워크플로우 데이터 오류 %d건\n  " % len(errors) + "\n  ".join(errors))
    css, js = shell.assets(os.path.join(CORE, "modules", "qa-site", "design-guide", "design-guide-master.css"))
    rt_css = shell.read(os.path.join(MODULE, "runtime", "workflow-explorer.css"))
    rt_js = shell.read(os.path.join(MODULE, "runtime", "workflow-explorer.js"))
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    doc = (shell.head((data.get("meta") or {}).get("title", "워크플로우"), css, js, rt_css)
           + body(data, warns)
           + '<script id="wfx-data" type="application/json">%s</script><script>%s</script></body></html>'
           % (payload, rt_js))
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    return warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    with io.open(a.data, encoding="utf-8") as f:
        data = json.load(f)
    if a.check or not a.out:
        errors, warns = validate(data)
        for m in errors:
            print("오류", m)
        for m in warns:
            print("경고", m)
        sys.exit(1 if errors else 0)
    warns = build(data, a.out)
    print("workflow-explorer: %s (경고 %d건)" % (a.out, len(warns)))


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    main()
