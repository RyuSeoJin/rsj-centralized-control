# -*- coding: utf-8 -*-
"""TC 시트 구성 생성 — xlsx를 받지 않고도 워크북 다섯 시트를 화면에서 읽습니다

왜 만드는가
----------
  시트는 xlsx로 배포하는데, 사이드바의 「내려받기」는 GitHub의 blob 주소로 나갑니다.
  저장소를 모르는 방문자에게는 **미리보기 없는 내려받기 버튼 하나**가 전부라 막다른
  길입니다. 그래서 같은 내용을 화면에서 바로 읽는 자리를 둡니다.

  대신 **xlsx를 읽지 않습니다.** 정본은 TC 설계 입력(json)과 이슈 json이고 xlsx도 거기서
  나오는 파생물이라, 파생물을 파생물이 읽으면 사슬만 길어집니다. 명세서 시트만 예외인데
  그 문구의 정본이 `build_tc_template_xlsx.py`에 있어 **그 모듈을 그대로 읽습니다** —
  다시 적으면 정본이 둘이 되어 한쪽만 낡습니다(CLAUDE.md §정본과 파생).

시트를 그대로 옮기지 않는 자리
----------------------------
  xlsx는 기대결과가 여럿이면 **행이 늘고 칸을 병합**합니다(테스트 케이스 153개 →
  확인 항목 297행). 화면에서는 한 케이스를 한 행에 두고 스텝과 기대결과를 그 안에서
  짝지어 보입니다. 종이(행 단위 실행
  기록)와 화면(읽기)은 좋은 모양이 다릅니다. 열은 하나도 빼지 않고 가로 스크롤로 봅니다.

  **실행 결과(Pass/Fail)는 싣지 않습니다.** 결과는 junit에서 나오는데 이 층은 junit을 읽지
  않습니다 — 환경 없이 재생성하면 0으로 떨어집니다. 결과는 자동화 QA 리포트가, 사슬은 추적
  매트릭스가 맡고 여기는 **설계 내용**만 봅니다.

사용법
------
    python gen_tc_sheet_html.py --project-dir <프로젝트 디렉터리> --slug <프로젝트명> \
        --css <design-guide-master.css> -o <출력 html>
"""
import argparse
import html
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
# 모듈 도구는 base의 공용 부품(shell.py·norm.py)을 씁니다. 모듈은 base 위에서만 돕니다 —
# 반대 방향(base가 모듈을 부르는 것)은 두지 않습니다
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "base", "scripts"))
import shell  # noqa: E402
from build_tc_template_xlsx import (  # noqa: E402
    DEFAULT_LISTS, ISSUE_HEADERS, ISSUE_KEYS, expected_by_step, normalize_tc, spec_rows)

VT_CHIP = {"결정적": "det", "확률적": "prob", "루브릭": "rub", "금칙": "ban"}
PRI_CHIP = {"High": "high", "Medium": "mid", "Low": "low"}

#: 칩 순서 = xlsx 탭 순서. 둘이 다르면 「같은 걸 보는 게 맞나」 싶어집니다
#: (tc-sheet-format.md §워크북 구성 — 2026-08-05 확정)
TABS = ("명세서", "목록", "Summary", "Test Case", "이슈 관리 시트")


def esc(s):
    return html.escape(str(s if s is not None else ""))


def read_json(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def lines(text):
    """시트 셀의 줄바꿈을 <br>로 — 사전조건·스텝이 여러 줄입니다."""
    return "<br>".join(esc(x) for x in str(text or "").split("\n") if x.strip())


def panel_spec(w, cfg):
    """명세서 — build_tc_template_xlsx.spec_rows()가 정본입니다."""
    w('<p>해당 xlsx 파일의 모든 시트의 구조나 데이터 컬럼을 나열한 매뉴얼입니다. html '
      '단독으로 설정한 것이 아닌, xlsx의 명세서 시트를 그대로 읽어 보여줍니다.</p>')
    tbl = False
    for item in spec_rows(cfg.get("area_codes")):
        kind = item[0]
        if kind in ("gap", "title"):
            continue
        if tbl and kind in ("section", "note"):
            w('</tbody></table></div>')
            tbl = False
        if kind == "section":
            w('<h3>%s</h3>' % esc(item[1]))
        elif kind == "note":
            w('<div class="callout">%s</div>' % esc(item[1]))
        elif kind == "head":
            w('<div class="tbl-scroll"><table><thead><tr>%s</tr></thead><tbody>'
              % "".join("<th>%s</th>" % esc(v) for v in item[1:]))
            tbl = True
        elif kind == "row":
            w("<tr>%s</tr>" % "".join("<td>%s</td>" % esc(v) for v in item[1:]))
    if tbl:
        w('</tbody></table></div>')


def panel_lists(w, cfg, project):
    """목록 — 드롭다운 참조 값의 정본."""
    lists = dict(DEFAULT_LISTS)
    lists["프로젝트"] = [project]
    lists.update(cfg.get("lists") or {})
    w('<p>특정 데이터 컬럼에서 어떤 값이 드롭다운의 형태로 참조되는 지 정리한 시트입니다.</p>')
    w('<div class="tbl-scroll"><table><thead><tr><th>목록</th><th>값</th></tr></thead><tbody>')
    for name, vals in lists.items():
        chips = " ".join('<span class="chip">%s</span>' % esc(v) for v in vals)
        w("<tr><td>%s</td><td>%s</td></tr>" % (esc(name), chips))
    w('</tbody></table></div>')


def panel_summary(w, rows, cfg):
    """Summary — 1-Depth(영역) 기준 집계. xlsx는 COUNTIFS 수식, 여기는 계산된 값입니다."""
    order = cfg.get("d1_order") or []
    seen = [d for d in order if any(r["path"] and r["path"][0] == d for r in rows)]
    seen += sorted({r["path"][0] for r in rows if r["path"] and r["path"][0] not in order})
    w('<p>1-Depth를 기반으로 어떤 영역에 대한 검증인지 볼 수 있는 요약 영역입니다. '
      'Test Case 영역이 채워지면 <code>COUNTIFS</code> 수식에 의해 바로 반영되는 구조입니다.</p>')
    w('<div class="tbl-scroll"><table><thead><tr><th>1-Depth (영역)</th>'
      '<th class="num">테스트 케이스</th><th class="num">확인 항목</th>'
      '<th class="num">High</th><th class="num">Medium</th><th class="num">Low</th>'
      '<th>검증유형</th></tr></thead><tbody>')
    tot = [0, 0, 0, 0, 0]
    for d1 in seen:
        got = [r for r in rows if r["path"] and r["path"][0] == d1]
        # 확인 항목 = 시트의 행. 스텝 하나가 기대 결과를 여럿 가지면 그만큼 행이 늡니다
        steps = sum(sum(max(1, len(g)) for g in expected_by_step(r["steps"], r["exp"])[1])
                    for r in got)
        pri = [sum(1 for r in got if r["prio"] == p) for p in ("High", "Medium", "Low")]
        vts = {}
        for r in got:
            vts[r["vt"]] = vts.get(r["vt"], 0) + 1
        w('<tr><td>%s</td><td class="num">%d</td><td class="num">%d</td>'
          '<td class="num">%d</td><td class="num">%d</td><td class="num">%d</td><td>%s</td></tr>'
          % (esc(d1), len(got), steps, pri[0], pri[1], pri[2],
             " ".join('<span class="chip chip-%s">%s %d</span>'
                      % (VT_CHIP.get(k, "unk"), esc(k), v) for k, v in sorted(vts.items()))))
        tot = [tot[0] + len(got), tot[1] + steps,
               tot[2] + pri[0], tot[3] + pri[1], tot[4] + pri[2]]
    w('<tr><td><b>합계</b></td>%s<td></td></tr>'
      % "".join('<td class="num"><b>%d</b></td>' % n for n in tot))
    w('</tbody></table></div>')


def panel_cases(w, rows, code_of):
    """Test Case — 열을 하나도 빼지 않고 가로로 봅니다."""
    w('<p>Test Case 시트입니다. 표를 옆으로 밀어 전부 볼 수 있습니다. 실제 xlsx 파일과 '
      '데이터를 표현하는 방식은 비슷하나, 셀 단위로 들어가는 값들에 대해서는 정확한 표현이 '
      '되지 않았으니, 정확한 확인은 xlsx 파일 다운을 통해 확인해주시길 바랍니다.</p>')
    w('<div class="callout">실행 결과(Pass/Fail) 열은 <strong>비어 있습니다.</strong> 시트에서 '
      '노란 칸이 그 자리이고 <strong>실행 단계에서 채웁니다.</strong> 실제 수행 결과는 '
      '자동화 QA 리포트가 담습니다.</div>')
    w(shell.table_tools(
        "tc-tbl", "TC ID · 케이스 · 스텝 · 기대결과 검색",
        tuple(("검증유형 " + vt, "col", 5, vt) for vt in ("결정적", "금칙", "확률적", "루브릭"))
        + (("사람 전용", "col", 6, "사람 전용"),)))
    cols = "".join('<col class="c%d">' % i for i in range(1, 13))
    w('<div class="tbl-scroll"><table id="tc-tbl"><colgroup>%s</colgroup><thead>' % cols)
    w('<tr>'
      '<th class="sortable">TC ID</th><th class="sortable">뎁스 경로</th><th>케이스</th>'
      '<th>사전조건</th><th>Test-Step → Expected-Result</th>'
      '<th class="sortable">검증유형</th><th class="sortable">실행 주체</th>'
      '<th class="sortable">우선순위</th><th>선행 TC</th><th>대상</th>'
      '<th class="sortable">상태</th><th>Note</th></tr></thead><tbody>')
    for r in rows:
        stepl, groups = expected_by_step(r["steps"], r["exp"])
        pairs = []
        for i, st in enumerate(stepl):
            exp = groups[i] if i < len(groups) else []
            got = "".join('<div class="body">→ %s</div>' % esc(e) for e in exp) \
                or '<div class="body foot">→ (판정 없음)</div>'
            pairs.append('<div class="step"><div class="body"><b>%d.</b> %s</div>%s</div>'
                         % (i + 1, esc(st), got))
        code = r["id"].split("-")[1] if "-" in r["id"] else ""
        w('<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td>'
          '<td><div class="steps">%s</div></td>'
          '<td><span class="chip chip-%s">%s</span></td><td>%s</td>'
          '<td><span class="chip chip-%s">%s</span></td><td>%s</td><td>%s</td>'
          '<td>%s</td><td class="foot">%s</td></tr>'
          % (esc(r["id"]),
             esc(" &gt; ".join(r["path"])).replace("&amp;gt;", "&gt;"),
             esc(r["case"]) or '<span class="foot">—</span>',
             lines(r["pre"]) or '<span class="foot">—</span>',
             "".join(pairs),
             VT_CHIP.get(r["vt"], "unk"), esc(r["vt"]), esc(r["exec"]),
             PRI_CHIP.get(r["prio"], "unk"), esc(r["prio"]),
             esc(r["par"]), esc(r["target"]),
             " ".join('<span class="chip">%s</span>' % esc(s.strip())
                      for s in r["state"].split(",") if s.strip()),
             lines(r["note"])))
    w('</tbody></table></div>')
    return code_of


def panel_issues(w, issues):
    """이슈 관리 시트 — 정본은 issues.json이고 시트는 그 파생입니다."""
    w('<p>JIRA 를 쓰지 않고 이슈 등록, 관리 방식을 시트로 표현한 시트입니다. '
      '<code>Issue No.</code>로 Test Case와 이어집니다.</p>')
    if not issues:
        w('<div class="callout">등록된 이슈가 없습니다.</div>')
        return
    w('<div class="tbl-scroll"><table><thead><tr>%s</tr></thead><tbody>'
      % "".join("<th>%s</th>" % esc(h) for h in ISSUE_HEADERS))
    for it in issues:
        w("<tr>%s</tr>" % "".join(
            "<td>%s</td>" % lines(it.get(k, "")) for k in ISSUE_KEYS))
    w('</tbody></table></div>')
    det = [(it.get("no"), d) for it in issues for d in (it.get("detections") or [])]
    if det:
        w('<h3>검출된 자리</h3>')
        w('<p>이슈가 <strong>어느 케이스를 수행하다 나왔는지</strong>입니다. 이 연결이 있어야 '
          '결함에서 설계로 되짚을 수 있습니다.</p>')
        w('<div class="tbl-scroll"><table><thead><tr><th>Issue No.</th><th>TC</th>'
          '<th>증상</th></tr></thead><tbody>')
        for no, d in det:
            w('<tr><td>%s</td><td><code>%s</code></td><td>%s</td></tr>'
              % (esc(no), esc(d.get("tcId", "")), esc(d.get("symptom", ""))))
        w('</tbody></table></div>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--css", required=True)
    ap.add_argument("--js")
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
    rows = [normalize_tc(t) for t in cfg["tcs"]]
    tree_version = str(cfg.get("tree_version", "")).replace("%s-tree-v" % S, "")
    issues_path = os.path.join(P, "test-case", "%s-issues.json" % S)
    issues = read_json(issues_path).get("issues", []) if os.path.exists(issues_path) else []
    code_of = {}
    for name, v in (cfg.get("area_codes") or {}).items():
        if not name.startswith("_"):
            code_of[(v.get("code") if isinstance(v, dict) else str(v))] = name

    css, js = shell.assets(args.css, args.js)
    # 열이 열둘이라 폭을 정해 주지 않으면 브라우저가 칸을 균등하게 눌러 글자가 세로로
    # 깨집니다. 표에 min-width를 주고 짧은 칸은 줄바꿈을 막아, 좁은 화면에서는 표만
    # 가로로 밀리게 합니다(본문은 밀리지 않습니다). 마스터를 건드리지 않는 문서 전용
    # 규칙이며, 용어집이 같은 방식을 씁니다
    extra = (
        "#tc-tbl{min-width:1820px;table-layout:fixed}"
        "#tc-tbl th,#tc-tbl td{vertical-align:top}"
        "#tc-tbl td:nth-child(1),#tc-tbl td:nth-child(6),#tc-tbl td:nth-child(7),"
        "#tc-tbl td:nth-child(8),#tc-tbl td:nth-child(9),#tc-tbl td:nth-child(10)"
        "{white-space:nowrap}"
        "#tc-tbl col.c1{width:96px}#tc-tbl col.c2{width:148px}#tc-tbl col.c3{width:150px}"
        "#tc-tbl col.c4{width:196px}#tc-tbl col.c5{width:430px}#tc-tbl col.c6{width:88px}"
        "#tc-tbl col.c7{width:96px}#tc-tbl col.c8{width:86px}#tc-tbl col.c9{width:104px}"
        "#tc-tbl col.c10{width:66px}#tc-tbl col.c11{width:120px}#tc-tbl col.c12{width:240px}"
        "#tc-tbl .steps{gap:6px}"
        "#tc-tbl .step{padding:6px 8px}"
        "#tc-tbl .step .body{font-size:12px;line-height:1.55}"
    )
    rel = os.path.relpath(P, os.path.dirname(os.path.abspath(args.output))).replace(os.sep, "/")
    rel = "" if rel == "." else rel + "/"
    xlsx = "%s/projects/%s/test-case/%s-tc-v1.0.xlsx" % (shell.BLOB, S, S)

    O = []
    w = O.append
    w(shell.head("%s — TC 시트 구성" % S, css, js, extra))
    w(shell.open_body(S, "tcsheet", rel, "TC 시트 구성",
                      "테스트 케이스 %d개 · 골격 v%s" % (len(rows), tree_version),
                      out_path=args.output))

    w('<div class="doc-header"><h1>TC 시트 구성</h1>')
    w('<p class="doc-lead">Test Case 목록만 넘기면, 받는 사람은 해당 TC의 규칙을 모르기 '
      '때문에 어떻게 수행해야 할 지 모릅니다. 그래서 테스트 케이스를 설계하고 관리하는 데 '
      '필요한 장치들을 구성하였습니다.</p>')
    w('<div class="meta-row">')
    for k, v in (("테스트 케이스", "%d개(확인 항목 %d개)" % (len(rows), sum(
                     sum(max(1, len(g)) for g in expected_by_step(r["steps"], r["exp"])[1])
                     for r in rows))),
                 ("영역", "%d개" % len({r["path"][0] for r in rows if r["path"]})),
                 ("기준 골격", "v" + tree_version),
                 ("이슈", "%d건" % len(issues))):
        w('<span class="badge">%s <b>%s</b></span>' % (esc(k), esc(v)))
    w('</div></div>')

    # ── 받는 법
    w('<h2 id="get">시트를 직접 다운받아서 보는 법</h2>')
    w('<p>하단의 「다운받지 않고 시트 구경하기」 탭을 통해 TC를 다운받지 않고 볼수는 '
      '있습니다.<br>하지만 하단의 시트는 html 디자인에 따라 표 형태로 보기 좋게 구성한 '
      '방식이라 데이터 컬럼이나 수식 등이 어떻게 들어갔는지는 정확한 판단이 힘듭니다.</p>')
    w('<p>Excel에서 열어야 수식, 데이터 컬럼, 시트 디자인 등을 정확하게 볼 수 있어 '
      'xlsx 파일을 다운받아 보는 것을 추천드립니다.</p>')
    w('<p><a class="fbtn" href="%s" target="_blank" rel="noopener">TC 시트 내려받기 (xlsx)</a></p>'
      % esc(xlsx))
    w('<div class="callout">[TC 시트 내려받기 (xlsx)] 버튼을 클릭 시 GitHub 사이트가 '
      '열리며, <b>Download</b> 버튼을 통해 다운받으실 수 있습니다.</div>')
    # 안내 사진 — 없으면 통째로 건너뜁니다. 사진이 빠져도 위 문장만으로 성립해야 한다는
    # 규칙(html-report-guide.md §1 래스터 이미지)을 코드로도 지키는 자리입니다.
    # 자기완결 예외라 base64가 아니라 상대 경로로 겁니다
    shot = os.path.join(P, "docs", "tc-xlsx-download.png")
    if os.path.exists(shot):
        src = os.path.relpath(shot, os.path.dirname(os.path.abspath(args.output)))
        w('<p><img src="%s" alt="GitHub의 TC 시트 xlsx 파일 화면 — '
          '파일 이름 줄 오른쪽의 아래 화살표 아이콘이 다운로드 버튼이다" '
          'style="width:100%%;height:auto;display:block;border:1px solid var(--hair);'
          'border-radius:8px"></p>' % esc(src.replace(os.sep, "/")))

    # ── 시트 칩
    w('<h2 id="sheets">다운받지 않고 시트 구경하기</h2>')
    w('<p>앞서 말했듯이, html로 표현된 시트의 경우 xlsx 파일에서 열어 확인하는 것과 데이터 '
      '컬럼이 달라서, 정확한 파일은 xlsx 파일을 다운받아 확인해주시길 바랍니다.</p>')
    w('<p>시트는 「명세서」, 「목록」, 「Summary」, 「Test Case」, 「이슈 관리 시트」로 '
      '이루어져 있으며, 하단의 chip을 눌러 각각의 html로 구현한 시트를 확인할 수 있습니다.</p>')
    w('<div class="tabs" data-tabs="sheets">')
    for i, name in enumerate(TABS):
        w('<button class="tab-btn%s" data-panel="pane-%d">%s</button>'
          % (" on" if i == 0 else "", i, esc(name)))
    w('</div>')

    for i, name in enumerate(TABS):
        w('<div class="tab-panel" id="pane-%d"><h3>%s</h3>' % (i, esc(name)))
        if name == "명세서":
            panel_spec(w, cfg)
        elif name == "목록":
            panel_lists(w, cfg, cfg.get("project", S))
        elif name == "Summary":
            panel_summary(w, rows, cfg)
        elif name == "Test Case":
            panel_cases(w, rows, code_of)
        else:
            panel_issues(w, issues)
        w('</div>')

    w('<div class="doc-footer">이 문서는 파생물입니다 — <code>gen_tc_sheet_html.py</code>로 '
      '재생성합니다. 케이스는 <code>tc-input-v1.0.json</code>, 이슈는 <code>issues.json</code>, '
      '명세서는 <code>build_tc_template_xlsx.py</code>의 <code>spec_rows()</code>에서 읽습니다 — '
      'xlsx를 읽지 않습니다. 실행 결과는 자동화 QA 리포트, 기능 단위와의 연결은 추적 '
      '매트릭스가 담습니다.</div>')
    w(shell.close_body())

    shell.save(args.output, "".join(O))
    print("saved %s | 시트 %d · TC %d · 이슈 %d"
          % (args.output, len(TABS), len(rows), len(issues)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
