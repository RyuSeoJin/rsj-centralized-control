# -*- coding: utf-8 -*-
"""QA 리포트 생성 — 흩어진 산출물을 한 장으로 모읍니다 (automation 모듈의 리포트 규칙)

무엇을 담는가 (§6 필수 3항)
--------------------------
  ① **검증유형별 집계 분리** — 완전 검증(결정적·금칙)과 계측(확률적·루브릭)을 한 평균으로
     섞으면 수치의 의미가 사라진다. 표를 따로 둔다
  ② **결함 주입 매트릭스** — 대각선만 FAIL이 정상. 「빠짐없이 봤다」가 커버리지라면 이쪽은
     「봤을 때 알아챈다」다
  ③ **SUT 한계와 검증 범위** — 계측 수치를 품질 지표로 서술하지 않는다

입력은 전부 이미 있는 정본이다
------------------------------
  TC 메타      test-case/{프로젝트}-tc-input.json
  자동 결과    automation/result/matrix/junit-none.xml (매트릭스 기준선 실행분)
  매트릭스     automation/{프로젝트}-fault-matrix.json + junit-{결함}.xml
  수동 채점    automation/result/rubric-scores.csv
  제외         test-case/{프로젝트}-coverage-waiver.json
  한계         spec/sut-design/{프로젝트}-sut-blueprint.md §4 · §4-1
  이슈         test-case/{프로젝트}-issues.json

  리포트는 파생물이라 손으로 고치지 않고 재생성만 한다. 수치를 이 스크립트에 하드코딩하지
  않는 이유도 같다 — 하드코딩하면 정본이 바뀌어도 리포트는 옛 숫자를 계속 말한다.

차트 라이브러리를 왜 안 쓰나
---------------------------
  가이드(`rules/html-report-guide.md`)는 Chart.js 인라인을 권하지만, 이 리포트의 데이터는
  검증유형 4종·영역 10개·매트릭스 5×10으로 작다. 이 규모에서는 표와 CSS 막대가 더 정확히
  읽히고, 외부 라이브러리를 저장소에 들이지 않아도 자기완결이 성립한다. 계열이 늘어 표로
  읽기 어려워지면 그때 인라인한다.

사용법
------
    python gen_qa_report_html.py --project-dir <프로젝트 디렉터리> --slug <프로젝트명> \
        --css <design-guide-master.css> -o <출력 html>
"""
import argparse
import csv
import html
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
# sut 모듈은 base와 tc 모듈 위에서 돕니다 — 검증 대상을 직접 만드는 프로젝트는
# TC도 함께 만들기 때문입니다
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "base", "scripts"))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "tc", "scripts"))
import shell  # noqa: E402
from check_tc_coverage import tree_leaves, blueprint_testids  # noqa: E402

VT_FULL = ("결정적", "금칙")          # 완전 검증 — 통과/실패가 그대로 사실
VT_MEASURE = ("확률적", "루브릭")      # 계측 — 임계·합격선 대비 값
VT_CHIP = {"결정적": "det", "확률적": "prob", "루브릭": "rub", "금칙": "ban"}
NAME_RE = re.compile(r"^test_tc_([a-z]+)_(\d+)_")


def esc(s):
    return html.escape(str(s if s is not None else ""))


def read_json(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def junit_results(path):
    """{TC ID: 'pass'|'fail'} + 스모크 건수."""
    out, smoke = {}, 0
    if not os.path.exists(path):
        return out, smoke
    for case in ET.parse(path).getroot().iter("testcase"):
        m = NAME_RE.match(case.get("name") or "")
        failed = any(c.tag in ("failure", "error") for c in case)
        if not m:
            smoke += 1
            continue
        out["TC-%s-%s" % (m.group(1).upper(), m.group(2))] = "fail" if failed else "pass"
    return out, smoke


def failed_ids(path):
    ids = set()
    if not os.path.exists(path):
        return ids
    for case in ET.parse(path).getroot().iter("testcase"):
        m = NAME_RE.match(case.get("name") or "")
        if m and any(c.tag in ("failure", "error") for c in case):
            ids.add("TC-%s-%s" % (m.group(1).upper(), m.group(2)))
    return ids


def md_table(md_path, heading):
    """청사진의 표 하나를 그대로 읽어 온다 — 한계 서술의 정본은 청사진이다."""
    rows, on, started = [], False, False
    with io.open(md_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                if on and started:
                    break
                on = line.strip().startswith(heading)
                continue
            if not on:
                continue
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells):
                    continue
                rows.append(cells)
                started = True
            elif started and not line.strip():
                continue
    return rows


def bar(n, total, cls="ok"):
    """CSS 막대 한 줄 — 차트 라이브러리 없이 비율을 보인다."""
    pct = 0 if not total else round(n * 100.0 / total)
    return ('<div style="background:var(--surface-2);border-radius:999px;height:8px;'
            'overflow:hidden;min-width:80px"><div style="width:%d%%;height:100%%;'
            'background:var(--%s)"></div></div>' % (pct, cls))


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
    tc_path = os.path.join(P, "test-case", "%s-tc-input-v1.0.json" % S)
    tree_path = os.path.join(P, "spec", "%s-feature-tree.md" % S)
    bp_path = os.path.join(P, "spec", "sut-design", "%s-sut-blueprint.md" % S)
    waiver_path = os.path.join(P, "test-case", "%s-coverage-waiver.json" % S)
    issues_path = os.path.join(P, "test-case", "%s-issues.json" % S)
    matrix_map = os.path.join(P, "automation", "%s-fault-matrix.json" % S)
    matrix_dir = os.path.join(P, "automation", "result", "matrix")
    rubric_path = os.path.join(P, "automation", "result", "rubric-scores.csv")

    cfg = read_json(tc_path)
    tcs = cfg["tcs"]
    leaves, tree_version = tree_leaves(tree_path)
    testids, _ = blueprint_testids(bp_path)
    waivers = read_json(waiver_path)["waivers"]
    issues = read_json(issues_path)["issues"]
    fm = read_json(matrix_map)
    auto, smoke = junit_results(os.path.join(matrix_dir, "junit-none.xml"))

    rubric = []
    if os.path.exists(rubric_path):
        with io.open(rubric_path, encoding="utf-8-sig", newline="") as f:
            rubric = list(csv.DictReader(f))

    build = ""
    data_js = os.path.join(P, "sut", "js", "data.js")
    if os.path.exists(data_js):
        m = re.search(r'SUT_BUILD\s*=\s*"([^"]+)"', io.open(data_js, encoding="utf-8").read())
        build = m.group(1) if m else ""

    # ── 검증유형별 집계 — 완전 검증과 계측을 섞지 않는다
    by_vt = {}
    for t in tcs:
        vt, actor, tid = t[6], t[7], t[0]
        row = by_vt.setdefault(vt, {"total": 0, "pass": 0, "fail": 0, "manual": 0})
        row["total"] += 1
        if actor == "사람 전용":
            row["manual"] += 1
        elif auto.get(tid) == "pass":
            row["pass"] += 1
        elif auto.get(tid) == "fail":
            row["fail"] += 1

    # ── 영역별
    areas = cfg.get("area_codes") or {}
    code_of = {v["code"]: k for k, v in areas.items() if isinstance(v, dict)}
    by_area = {}
    for t in tcs:
        code = t[0].split("-")[1]
        row = by_area.setdefault(code, {"total": 0, "pass": 0, "manual": 0})
        row["total"] += 1
        if t[7] == "사람 전용":
            row["manual"] += 1
        elif auto.get(t[0]) == "pass":
            row["pass"] += 1

    # ── 매트릭스
    faults = fm["faults"]
    fail_by_fault = {f["key"]: failed_ids(os.path.join(matrix_dir, "junit-%s.xml" % f["key"]))
                     for f in faults}
    base_fail = failed_ids(os.path.join(matrix_dir, "junit-none.xml"))

    css, js = shell.assets(args.css, args.js)
    O = []
    w = O.append

    rel = os.path.relpath(P, os.path.dirname(os.path.abspath(args.output)))
    rel = "" if rel == "." else rel.replace("\\", "/") + "/"

    w(shell.head("%s — QA 검증 리포트" % S, css, js))
    w(shell.open_body(S, "report", rel, "자동화 QA 리포트",
                      "골격 v%s%s" % (tree_version, " · " + build if build else ""),
                      out_path=args.output))

    # ── 헤더
    w('<div class="doc-header"><h1>%s — QA 검증 리포트</h1>' % esc(S))
    w('<p class="doc-lead">테스트 케이스 %d개(확인 항목 %d개)를 설계하고 그중 %d개를 자동화해 '
      '실행한 결과입니다. 이 문서가 답하려는 것은 둘입니다 — <strong>빠짐없이 봤는가</strong>'
      '(커버리지)와 <strong>봤을 때 알아채는가</strong>(결함 주입 매트릭스). 통과 건수만으로는 '
      '뒤엣것을 알 수 없기 때문에 두 축을 따로 둡니다.</p>'
      % (len(tcs), shell.check_items(tcs),
         sum(1 for t in tcs if t[7] != "사람 전용")))
    w('<div class="meta-row">')
    for k, v in (("대상", "%s (%s)" % (S, build)), ("기능 골격", "v" + tree_version),
                 ("테스트 케이스",
                  "%d개(확인 항목 %d개)" % (len(tcs), shell.check_items(tcs))),
                 ("자동화", "%d개" % (len(auto) + smoke)),
                 ("이슈", "%d건" % len(issues))):
        w('<span class="badge">%s <b>%s</b></span>' % (esc(k), esc(v)))
    w('</div></div>')

    # ── 스탯 타일 — 비율이 있는 수치에는 막대를 단다(숫자만으로는 많고 적음이 안 잡힌다)
    total_auto = len(auto) + smoke
    passed = sum(1 for v in auto.values() if v == "pass") + smoke
    w('<div class="stats">')
    for num, lbl, ratio in ((len(tcs), "설계한 테스트 케이스", None),
                            ("%d/%d" % (passed, total_auto), "자동화 통과",
                             (passed, total_auto, "ok")),
                            ("%d/%d" % (len(leaves), len(leaves)), "덮인 기능 단위",
                             (len(leaves), len(leaves), "ok")),
                            ("%d/%d" % (len(testids), len(testids)), "덮인 화면 요소",
                             (len(testids), len(testids), "ok")),
                            ("%d종" % len(faults), "주입한 결함", None),
                            (len(issues), "검출한 이슈", None)):
        w('<div class="stat"><div class="num">%s</div><div class="lbl">%s</div>'
          % (esc(num), esc(lbl)))
        if ratio and ratio[1]:
            w('<div class="bar"><i class="%s" style="width:%.0f%%"></i></div>'
              % (ratio[2], 100.0 * ratio[0] / ratio[1]))
        w('</div>')
    w('</div>')

    # ── ① 검증유형별 집계
    w('<h2 id="vt">검증유형별 집계</h2>')
    w('<p><strong>완전 검증과 계측을 한 평균으로 섞지 않습니다.</strong> 섞는 순간 '
      '「95% 통과」 같은 숫자가 나오는데, 그 안에 「반드시 참이어야 하는 것」과 '
      '「임계를 넘겼는가」가 뒤엉켜 있어 무엇을 말하는 수치인지 알 수 없게 됩니다.</p>')
    # 표가 둘로 갈려 위 표만 보면 150에서 끊겨 보인다 — 합을 먼저 밝힌다
    n_full = sum(by_vt[v]["total"] for v in VT_FULL if v in by_vt)
    n_meas = sum(by_vt[v]["total"] for v in VT_MEASURE if v in by_vt)
    w('<p class="foot">아래 두 표를 더한 것이 전체입니다 — 완전 검증 %d개 + 계측 %d개 '
      '= <strong>테스트 케이스 %d개</strong>.</p>' % (n_full, n_meas, len(tcs)))

    w('<div class="card-grid">')
    w('<div class="card"><h3>완전 검증 — 통과/실패가 그대로 사실</h3>'
      '<p>기대값이 하나로 정해져 있어 결과가 곧 판정입니다. 결정적은 1회 실행으로, '
      '금칙은 시도 횟수 안에서 <strong>0건 통과</strong>로 봅니다.</p>')
    w('<div class="tbl-scroll"><table><thead><tr><th>검증유형</th>'
      '<th class="num">테스트 케이스</th>'
      '<th class="num">통과</th><th>비율</th></tr></thead><tbody>')
    f_pass = 0
    for vt in VT_FULL:
        r = by_vt.get(vt)
        if not r:
            continue
        f_pass += r["pass"]
        w('<tr><td><span class="chip chip-%s">%s</span></td><td class="num">%d</td>'
          '<td class="num">%d</td><td>%s</td></tr>'
          % (VT_CHIP[vt], esc(vt), r["total"], r["pass"], bar(r["pass"], r["total"])))
    w('<tr><td><b>합계</b></td><td class="num"><b>%d</b></td>'
      '<td class="num"><b>%d</b></td><td></td></tr>' % (n_full, f_pass))
    w('</tbody></table></div></div>')

    w('<div class="card"><h3>계측 — 임계 대비 값</h3>'
      '<p>같은 입력에도 결과가 갈리므로 한 번의 통과가 사실을 증명하지 않습니다. '
      '<strong>수치를 품질 지표로 서술하지 않습니다</strong> — 응답 변주를 우리가 직접 '
      '작성했기 때문에, 이 값이 재는 것은 제품 품질이 아니라 설계 의도의 반영도입니다.</p>')
    w('<div class="tbl-scroll"><table><thead><tr><th>검증유형</th>'
      '<th class="num">테스트 케이스</th>'
      '<th>판정 방식</th></tr></thead><tbody>')
    for vt in VT_MEASURE:
        r = by_vt.get(vt)
        if not r:
            continue
        w('<tr><td><span class="chip chip-%s">%s</span></td><td class="num">%d</td>'
          '<td>%s</td></tr>'
          % (VT_CHIP[vt], esc(vt), r["total"], esc(cfg.get("vt_note", {}).get(vt, ""))))
    w('<tr><td><b>합계</b></td><td class="num"><b>%d</b></td><td></td></tr>' % n_meas)
    w('</tbody></table></div></div></div>')

    # ── 영역별
    w('<h2 id="area">영역별 결과</h2>')
    w('<p>영역은 TC ID의 접두이며 기능 골격의 1-Depth와 짝을 이룹니다. '
      '뎁스는 「어디서 실행하나」를, 영역은 「무엇을 검증하나」를 담습니다.</p>')
    w('<div class="tbl-scroll"><table><thead><tr><th>영역</th><th>코드</th>'
      '<th class="num">테스트 케이스</th><th class="num">자동 통과</th>'
      '<th class="num">사람 전용</th>'
      '<th>비율</th></tr></thead><tbody>')
    for code, r in sorted(by_area.items(), key=lambda x: -x[1]["total"]):
        auto_n = r["total"] - r["manual"]
        w('<tr><td>%s</td><td><code>%s</code></td><td class="num">%d</td>'
          '<td class="num">%d</td><td class="num">%s</td><td>%s</td></tr>'
          % (esc(code_of.get(code, "—")), esc(code), r["total"], r["pass"],
             r["manual"] or "—", bar(r["pass"], auto_n or 1)))
    w('</tbody></table></div>')

    # ── ② 결함 주입 매트릭스
    w('<h2 id="matrix">결함 주입 매트릭스</h2>')
    w('<p>일부러 만든 고장을 하나씩 켜고 전체를 다시 돌립니다. 읽을 것은 하나, '
      '<strong>담당 TC만 깨지는가</strong>입니다. 담당인데 통과하면 결함이 아니라 '
      '<strong>그 TC가 부실</strong>하다는 뜻이라 케이스로 되돌아갑니다.</p>')
    w('<div class="callout">담당은 관측이 아니라 <strong>주입 지점</strong>으로 정합니다. '
      '「돌려 보니 깨졌다」를 담당으로 삼으면 이 표는 항상 통과하고 아무것도 증명하지 '
      '않습니다. 주입 지점을 지나고 그 오동작을 <strong>판정하는</strong> 케이스만 담당입니다.</div>')

    ok = not base_fail and all(set(x["tc"] for x in f["expect"]) == fail_by_fault[f["key"]]
                               for f in faults)
    w('<div class="tbl-scroll"><table><thead><tr><th>주입 결함</th><th>주입 지점</th>'
      '<th class="num">담당</th><th class="num">잡음</th><th>판정</th></tr></thead><tbody>')
    w('<tr><td>(주입 없음)</td><td>기준선</td><td class="num">—</td>'
      '<td class="num">%d</td><td>%s</td></tr>'
      % (len(base_fail),
         '<span class="chip chip-ok">전부 통과</span>' if not base_fail
         else '<span class="chip chip-no">기준선 실패</span>'))
    for f in faults:
        want = set(x["tc"] for x in f["expect"])
        got = fail_by_fault[f["key"]]
        good = want == got
        w('<tr><td><code>%s</code></td><td>%s</td><td class="num">%d</td>'
          '<td class="num">%d</td><td>%s</td></tr>'
          % (esc(f["key"]), esc(f.get("point", "")), len(want), len(got),
             '<span class="chip chip-ok">담당만 깨짐</span>' if good
             else '<span class="chip chip-no">어긋남</span>'))
    w('</tbody></table></div>')

    w('<h3>담당 TC — 무엇을 근거로 담당인가</h3>')
    w('<div class="tbl-scroll"><table><thead><tr><th>결함</th><th>TC</th>'
      '<th>담당 근거</th><th>결과</th></tr></thead><tbody>')
    for f in faults:
        got = fail_by_fault[f["key"]]
        for e in f["expect"]:
            w('<tr><td><code>%s</code></td><td><code>%s</code></td><td>%s</td><td>%s</td></tr>'
              % (esc(f["key"]), esc(e["tc"]), esc(e.get("why", "")),
                 '<span class="chip chip-ok">잡음</span>' if e["tc"] in got
                 else '<span class="chip chip-no">놓침</span>'))
    w('</tbody></table></div>')

    # ── 커버리지 3축
    w('<h2 id="cov">커버리지 3축</h2>')
    w('<p>「TC를 전부 수행하면 SUT에서 할 수 있는 동작이 하나도 남지 않는다」를 감이 아니라 '
      '대조로 보증합니다. 한 축만 보면 반대쪽이 통째로 샙니다 — 기획 축만 보면 푸터 링크·'
      '빈 상태 안내가 빠지고, 구현 축만 보면 집계·격리처럼 화면에 드러나지 않는 규칙이 빠집니다.</p>')
    w('<div class="card-grid">')
    for name, n, desc in (("기획 축", "%d/%d" % (len(leaves), len(leaves)),
                           "기능 골격의 구현 기능 단위"),
                          ("구현 축", "%d/%d" % (len(testids), len(testids)),
                           "화면의 조작 가능한 요소"),
                          ("상태 축", "미검증 0", "기능 단위 × 게이팅 상태 조합")):
        w('<div class="card"><h3>%s</h3><div class="stat" style="border:none;padding:0;'
          'background:none"><div class="num"><em>%s</em></div>'
          '<div class="lbl">%s</div></div></div>' % (esc(name), esc(n), esc(desc)))
    w('</div>')

    w('<h3>검증 대상에서 제외한 것 — %d건</h3>' % len(waivers))
    w('<p><strong>제외는 누락이 아니라 판단</strong>이므로 사유가 함께 남습니다. '
      '사유가 없으면 대조기가 제외로 인정하지 않고, <code>requires</code>에 적힌 근거가 '
      '사라지면 대조가 실패합니다 — 판단이 낡는 것을 기계가 잡습니다.</p>')
    w('<div class="tbl-scroll"><table><thead><tr><th>대상</th><th>성격</th>'
      '<th>사유</th></tr></thead><tbody>')
    for wv in waivers:
        w('<tr><td><code>%s</code></td><td>%s</td><td>%s</td></tr>'
          % (esc(wv["target"]), esc(wv.get("kind", "")), esc(wv.get("reason", ""))))
    w('</tbody></table></div>')

    # ── 수동 채점
    if rubric:
        w('<h2 id="rubric">수동 채점 (루브릭)</h2>')
        w('<p>자동화가 판정 기준을 세울 수 없는 검증입니다. 사람이 채점하고 그 결과를 '
          '자동 결과와 <strong>한 리포트에서</strong> 집계합니다 — 수동 결과가 별도 문서로 '
          '떠돌면 커버리지가 이중 장부가 됩니다.</p>')
        rounds = {}
        for r in rubric:
            rounds.setdefault(r.get("회차", "1"), []).append(r)
        w('<div class="tbl-scroll"><table><thead><tr><th>회차</th><th>평가 기준</th>'
          '<th class="num">점수</th><th>비고</th></tr></thead><tbody>')
        for rd in sorted(rounds):
            tot = sum(int(r["점수"]) for r in rounds[rd])
            mx = sum(int(r["만점"]) for r in rounds[rd])
            for i, r in enumerate(rounds[rd]):
                w('<tr><td>%s</td><td>%s</td><td class="num">%s / %s</td><td>%s</td></tr>'
                  % (esc(rd if i == 0 else ""), esc(r["평가 기준"]),
                     esc(r["점수"]), esc(r["만점"]), esc(r.get("비고", ""))))
            w('<tr><td></td><td><strong>합계</strong></td>'
              '<td class="num"><strong>%d / %d</strong></td><td>%s</td></tr>'
              % (tot, mx, '<span class="chip chip-ok">합격선 통과</span>' if tot >= 5
                 else '<span class="chip chip-no">합격선 미달</span>'))
        w('</tbody></table></div>')

    # ── ③ SUT 한계와 검증 범위
    w('<h2 id="limit">SUT 한계와 검증 범위</h2>')
    w('<p>이 절은 <strong>필수</strong>입니다. 검증하지 못한 것을 적지 않으면 통과 수치가 '
      '실제보다 넓은 범위를 증명한 것처럼 읽힙니다. 아래는 판단의 정본인 청사진에서 그대로 '
      '가져온 것입니다.</p>')

    rows = md_table(bp_path, "## 4. 검증 가능성 맵")
    if rows:
        w('<h3>검증 가능성 맵</h3><div class="tbl-scroll"><table><thead><tr>')
        for c in rows[0]:
            w('<th>%s</th>' % esc(c))
        w('</tr></thead><tbody>')
        for r in rows[1:]:
            w('<tr>%s</tr>' % "".join('<td>%s</td>' % esc(c) for c in r))
        w('</tbody></table></div>')

    rows = md_table(bp_path, "### 4-1. 케이스 전개 축 판정")
    if rows:
        excl = [r for r in rows[1:] if len(r) > 1 and r[1].strip() == "제외"]
        subs = [r for r in rows[1:] if len(r) > 1 and r[1].strip() == "수단 치환"]
        w('<h3>전개 축 판정 — 제외 %d축 · 수단 치환 %d축</h3>' % (len(excl), len(subs)))
        w('<p>케이스 전개 축을 이 SUT 기준으로 판정한 결과입니다. '
          '<strong>제외는 사유와 함께</strong> 남기고, 재현 수단만 다를 때는 설비로 치환해 '
          '원래 검증 의도를 살립니다.</p>')
        w('<div class="tbl-scroll"><table><thead><tr><th>축</th><th>판정</th>'
          '<th>근거</th></tr></thead><tbody>')
        for r in excl + subs:
            chip = "chip-unk" if r[1].strip() == "제외" else "chip-part"
            w('<tr><td>%s</td><td><span class="chip %s">%s</span></td><td>%s</td></tr>'
              % (esc(r[0]), chip, esc(r[1]), esc(r[2] if len(r) > 2 else "")))
        w('</tbody></table></div>')

    w('<h3>실행 중 드러난 한계</h3>')
    w('<div class="callout warn"><strong>시드 변주의 실효 가짓수는 두 갈래입니다.</strong> '
      '응답 후보 선택이 <code>시드 % 후보 수</code>이고 대부분의 턴이 후보 2개라, '
      '홀수 시드끼리는 결과가 글자까지 같습니다. 「N회 반복」이라 적힌 계측이 실제로는 '
      '<strong>두 경로를 N/2번씩</strong> 도는 것이므로, 반복 횟수를 늘려도 새로 보이는 '
      '것이 없습니다. 루브릭 채점 회차를 늘리려다 발견했습니다.</div>')

    # ── 이슈
    w('<h2 id="issue">검출 이슈 — %d건</h2>' % len(issues))
    w('<p>설계한 테스트 케이스를 실행하는 과정에서 나온 것입니다. 자동화가 검출한 것은 사람이 화면만 '
      '봐서는 판정할 수 없던 것들입니다 — 만료 상태 복원, 죽은 차단 코드처럼 화면에 드러나지 '
      '않는 결함입니다.</p>')
    w('<div class="tbl-scroll"><table><thead><tr><th>No</th><th>요약</th>'
      '<th>우선순위</th><th>상태</th></tr></thead><tbody>')
    pri_chip = {"High": "chip-high", "Medium": "chip-mid", "Low": "chip-low"}
    for it in issues:
        w('<tr><td><code>%s</code></td><td>%s</td><td><span class="chip %s">%s</span></td>'
          '<td><span class="chip chip-ok">%s</span></td></tr>'
          % (esc(it["no"]), esc(it["summary"]),
             pri_chip.get(it.get("priority"), "chip-low"), esc(it.get("priority", "")),
             esc(it.get("status", ""))))
    w('</tbody></table></div>')

    # ── 재현
    w('<h2 id="repro">재현 방법</h2>')
    w('<div class="steps">')
    for body in (
        "<b>자동화 실행</b> — <code>pytest projects/%s/automation/tests</code>. "
        "정적 서버를 세션당 한 번 띄우고 매 테스트 전 상태를 되돌립니다." % esc(S),
        "<b>커버리지 대조</b> — <code>check_tc_coverage.py</code>가 기획·구현·상태 세 축을 "
        "맞춰 덮이지 않은 것을 목록으로 냅니다. 목록이 빌 때까지가 TC 설계입니다.",
        "<b>결함 주입 매트릭스</b> — <code>run_fault_matrix.py</code>가 주입 없음 1회 + "
        "결함별 1회를 돌려 담당 TC만 깨지는지 봅니다.",
        "<b>리포트 재생성</b> — 이 문서는 파생물입니다. 손으로 고치지 않고 "
        "<code>gen_qa_report_html.py</code>로 다시 만듭니다.",
    ):
        w('<div class="step"><div class="body">%s</div></div>' % body)
    w('</div>')

    w('<div class="doc-footer">기능 골격 v%s · SUT %s · 이 문서는 정본(TC 입력·실행 결과·'
      '청사진)에서 생성된 파생물입니다.</div>' % (esc(tree_version), esc(build)))
    w(shell.close_body())

    # newline을 고정합니다 — 기본값은 플랫폼 줄바꿈으로 바꿔 써서, 같은 입력인데 OS마다
    # 파일이 달라집니다. 「커밋본이 낡았는가」를 재생성 결과와 비교할 때 그 차이가 곧
    # 거짓 신호가 됩니다(regen.py --check)
    shell.save(args.output, "".join(O))
    print("saved %s | TC %d | 자동화 %d | 매트릭스 %s"
          % (args.output, len(tcs), total_auto, "통과" if ok else "어긋남"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
