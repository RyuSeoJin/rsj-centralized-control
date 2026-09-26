# -*- coding: utf-8 -*-
"""추적 매트릭스 생성 — 기능 단위 → TC → 자동화 함수 → 이슈를 한 줄로 잇습니다

무엇을 증명하려는 문서인가
------------------------
  ① **TC가 기획에서 나왔다** — 케이스마다 어느 기능 단위를 덮는지가 좌표로 적혀 있고,
     덮이지 않은 기능 단위가 하나도 없다는 것을 기계가 대조한다
  ② **설계가 실행까지 이어져 있다** — TC ID가 곧 자동화 함수명이라, 리포트만 보고 시트를
     찾을 수 있고 반대로도 간다
  ③ **결함이 어디서 나왔는지 되짚힌다** — 이슈가 어느 TC 수행 중에 검출됐는지가 남는다

  이 셋이 끊기면 「TC를 많이 썼다」는 말밖에 남지 않는다. 사슬이 이어져 있어야 커버리지
  수치가 의미를 갖는다.

조인 키
-------
  기능 단위 ↔ TC       TC의 covers(13번째 값) 중 `>`가 든 값 = 트리 경로
  TC ↔ 자동화   junit의 테스트 이름 `test_tc_{영역}_{번호}_…` → TC ID
  TC ↔ 이슈     issues.json의 detections[].tcId

  전부 이미 있는 값이라 새로 판단할 것이 없다. 이 스크립트는 조인만 한다.

사용법
------
    python gen_traceability_html.py --project-dir <프로젝트 디렉터리> --slug <프로젝트명> \
        --css <design-guide-master.css> -o <출력 html>
"""
import argparse
import html
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
# 모듈 도구는 base의 공용 부품(shell.py·norm.py)을 씁니다. 모듈은 base 위에서만 돕니다 —
# 반대 방향(base가 모듈을 부르는 것)은 두지 않습니다
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "base", "scripts"))
# 셸(사이드바·상단 바)은 qa-site 모듈이 가집니다 — tc가 qa-site를 전제하는 이유입니다
sys.path.insert(0, os.path.join(_HERE, "..", "..", "qa-site", "scripts"))
import shell  # noqa: E402
from check_tc_coverage import tree_leaves  # noqa: E402

VT_CHIP = {"결정적": "det", "확률적": "prob", "루브릭": "rub", "금칙": "ban"}
NAME_RE = re.compile(r"^(test_tc_([a-z]+)_(\d+)_[^\[]*)")


def esc(s):
    return html.escape(str(s if s is not None else ""))


def read_json(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def automation_map(junit):
    """{TC ID: (함수명, 'pass'|'fail')}"""
    out = {}
    if not os.path.exists(junit):
        return out
    for case in ET.parse(junit).getroot().iter("testcase"):
        m = NAME_RE.match(case.get("name") or "")
        if not m:
            continue
        tid = "TC-%s-%s" % (m.group(2).upper(), m.group(3))
        failed = any(c.tag in ("failure", "error") for c in case)
        out[tid] = (m.group(1).rstrip("_"), "fail" if failed else "pass")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--css", required=True)
    ap.add_argument("--js", help="동작 정본(생략 시 CSS 옆의 design-guide-master.js)")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()
    # 한글 출력이 콘솔 기본 인코딩으로 나가면, 다른 도구가 받아 읽을 때 깨집니다.
    # 오류는 stderr로 나가므로 둘 다 맞춥니다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    P, S = args.project_dir, args.slug
    cfg = read_json(os.path.join(P, "test-case", "%s-tc-input-v1.0.json" % S))
    tcs = cfg["tcs"]
    leaves, tree_version = tree_leaves(os.path.join(P, "spec", "%s-feature-tree.md" % S))
    issues = read_json(os.path.join(P, "test-case", "%s-issues.json" % S))["issues"]
    auto = automation_map(os.path.join(P, "automation", "result", "matrix", "junit-none.xml"))

    # TC ↔ 이슈
    issue_of = {}
    for it in issues:
        for d in it.get("detections") or []:
            if d.get("tcId") and d["tcId"] != "-":
                issue_of.setdefault(d["tcId"], []).append((it["no"], it.get("status", "")))

    # 기능 단위 ↔ TC — 꼬리 일치도 인정한다(대조기와 같은 규칙)
    leaf_full = [" > ".join(l["path"]) for l in leaves]

    def match(full, p):
        return full == p or full.endswith(" > " + p) or p.endswith(" > " + full)

    tc_leaves, leaf_tcs = {}, {f: [] for f in leaf_full}
    for t in tcs:
        cov = t[12] if len(t) > 12 else []
        paths = [c for c in (cov or []) if ">" in c]
        hit = [f for f in leaf_full if any(match(f, p) for p in paths)]
        tc_leaves[t[0]] = hit
        for f in hit:
            leaf_tcs[f].append(t[0])

    areas = cfg.get("area_codes") or {}
    code_of = {v["code"]: k for k, v in areas.items() if isinstance(v, dict)}

    css, js = shell.assets(args.css, args.js)
    O = []
    w = O.append

    rel = os.path.relpath(P, os.path.dirname(os.path.abspath(args.output)))
    rel = "" if rel == "." else rel.replace("\\", "/") + "/"

    w(shell.head("%s — 추적 매트릭스" % S, css, js))
    w(shell.open_body(S, "trace", rel, "추적 매트릭스",
                      "골격 v%s · 테스트 케이스 %d개" % (tree_version, len(tcs)),
                      out_path=args.output))

    w('<div class="doc-header"><h1>%s — 추적 매트릭스</h1>' % esc(S))
    w('<p class="doc-lead">기능 단위 하나가 어떤 테스트 케이스가 되고, 그 케이스가 어떤 '
      '자동화 함수로 실행되며, 거기서 어떤 결함이 나왔는지를 한 줄로 잇습니다. '
      '<strong>이 사슬이 끊기면 「TC를 많이 썼다」는 말밖에 남지 않습니다</strong> — '
      '커버리지 수치가 의미를 가지려면 기획에서 나와 실행까지 닿아 있어야 합니다.</p>')
    w('<div class="meta-row">')
    for k, v in (("기능 골격", "v" + tree_version), ("구현 기능 단위", "%d개" % len(leaves)),
                 ("테스트 케이스",
                  "%d개(확인 항목 %d개)" % (len(tcs), shell.check_items(tcs))),
                 ("자동화", "%d개" % len(auto)), ("이슈", "%d건" % len(issues))):
        w('<span class="badge">%s <b>%s</b></span>' % (esc(k), esc(v)))
    w('</div></div>')

    linked = sum(1 for t in tcs if tc_leaves[t[0]])
    covered = sum(1 for f in leaf_full if leaf_tcs[f])
    w('<div class="stats">')
    for num, lbl in (("%d/%d" % (covered, len(leaves)), "테스트 케이스가 붙은 기능 단위"),
                     ("%d/%d" % (linked, len(tcs)), "기능 단위에 닿는 테스트 케이스"),
                     ("%d/%d" % (len(auto), len(tcs)), "자동화된 테스트 케이스"),
                     (len(issue_of), "이슈가 달린 테스트 케이스")):
        w('<div class="stat"><div class="num">%s</div><div class="lbl">%s</div></div>'
          % (esc(num), esc(lbl)))
    w('</div>')

    w('<div class="callout">기능 단위에 닿지 않는 케이스가 있는 것은 정상입니다. '
      '푸터 링크·빈 상태 안내처럼 <strong>기획 트리에 없지만 화면에 있는 조작</strong>은 '
      '화면 요소(testid)로만 좌표를 답니다 — 커버리지를 두 축으로 보는 이유입니다.</div>')

    # ── 케이스별 사슬
    w('<h2 id="chain">케이스별 사슬</h2>')
    # 표 도구는 마스터 동작 정본이 붙인다 — 검색·필터·정렬을 문서마다 다시 짜지 않는다
    w(shell.table_tools(
        "chain-tbl", "TC ID · 기능 단위 · 함수명 검색",
        tuple(("검증유형 " + vt, "col", 2, vt) for vt in ("결정적", "금칙", "확률적", "루브릭"))
        + (("이슈 있음", "attr", "issue", "1"),)))

    w('<div class="tbl-scroll"><table id="chain-tbl"><thead><tr>'
      '<th class="sortable">TC</th><th class="sortable">영역</th>'
      '<th class="sortable">검증유형</th><th>덮는 기능 단위</th>'
      '<th class="sortable">자동화 함수</th><th class="sortable">결과</th>'
      '<th class="sortable">이슈</th></tr></thead><tbody>')
    for t in tcs:
        tid, vt, actor = t[0], t[6], t[7]
        code = tid.split("-")[1]
        hit = tc_leaves[tid]
        cov = t[12] if len(t) > 12 else []
        ids = [c for c in (cov or []) if ">" not in c]
        leaf_cell = "<br>".join(esc(x) for x in hit) if hit \
            else '<span class="foot">화면 요소 %d개</span>' % len(ids)
        fn, res = auto.get(tid, (None, None))
        if fn:
            fn_cell = "<code>%s</code>" % esc(fn)
            res_cell = ('<span class="chip chip-ok">Pass</span>' if res == "pass"
                        else '<span class="chip chip-no">Fail</span>')
        else:
            fn_cell = '<span class="foot">—</span>'
            res_cell = ('<span class="chip chip-unk">사람 전용</span>'
                        if actor == "사람 전용" else '<span class="foot">—</span>')
        iss = issue_of.get(tid) or []
        iss_cell = " ".join('<span class="chip chip-ok">%s</span>' % esc(n) for n, _ in iss) \
            or '<span class="foot">—</span>'
        w('<tr data-vt="%s" data-issue="%d"><td><code>%s</code></td><td>%s</td>'
          '<td><span class="chip chip-%s">%s</span></td><td>%s</td><td>%s</td>'
          '<td>%s</td><td>%s</td></tr>'
          % (esc(vt), 1 if iss else 0, esc(tid), esc(code_of.get(code, code)),
             VT_CHIP.get(vt, "unk"), esc(vt), leaf_cell, fn_cell, res_cell, iss_cell))
    w('</tbody></table></div>')

    # ── 기능 단위 기준
    w('<h2 id="leaf">기능 단위 기준</h2>')
    w('<p>반대 방향입니다 — 골격의 기능 단위마다 어떤 케이스가 붙었는지 봅니다. '
      '<strong>빈 행이 하나도 없어야</strong> 「빠짐없이 봤다」가 성립합니다.</p>')
    w(shell.table_tools("leaf-tbl", "기능 단위 검색",
                        (("덮이지 않음", "col", 2, "덮이지 않음"),)))
    w('<div class="tbl-scroll"><table id="leaf-tbl"><thead><tr>'
      '<th class="sortable">기능 단위</th><th class="num sortable">TC</th>'
      '<th>케이스</th></tr></thead><tbody>')
    for f in leaf_full:
        got = leaf_tcs[f]
        w('<tr><td>%s</td><td class="num">%d</td><td>%s</td></tr>'
          % (esc(f), len(got),
             " ".join("<code>%s</code>" % esc(x) for x in got) if got
             else '<span class="chip chip-no">덮이지 않음</span>'))
    w('</tbody></table></div>')

    w('<div class="doc-footer">이 문서는 파생물입니다 — '
      '<code>gen_traceability_html.py</code>로 재생성합니다. 조인 키는 covers · TC ID · '
      'detections이며 전부 정본에 이미 있는 값입니다.</div>')


    w(shell.close_body())

    shell.save(args.output, "".join(O))
    print("saved %s | 기능 단위 %d(덮임 %d) · TC %d(기능 단위 연결 %d) · 자동화 %d · 이슈 연결 %d"
          % (args.output, len(leaves), covered, len(tcs), linked, len(auto), len(issue_of)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
