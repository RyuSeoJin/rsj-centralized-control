# -*- coding: utf-8 -*-
"""소개 페이지 생성 — 「무엇을 할 줄 아는가」를 먼저 보이는 층

산출물과 무엇이 다른가
---------------------
  허브·리포트·추적 매트릭스는 **작업의 결과**입니다. 이미 맥락을 아는 사람이 봅니다.
  소개 페이지는 처음 온 사람에게 **왜 그렇게 했는지**를 말합니다. 그래서 여기서는
  수치와 표를 다시 서술하지 않고, 판단과 이유를 적은 뒤 상세는 산출물로 보냅니다.
  같은 내용을 두 곳에 적으면 한쪽만 고쳤을 때 갈라집니다.

수치는 전부 정본에서 읽는다
--------------------------
  기능 단위·화면 요소·TC 건수는 트리와 청사진·TC 입력에서, 자동화 건수는 테스트 파일에서,
  결함 주입 결과는 커밋된 매트릭스 표에서 읽습니다. **junit을 읽지 않습니다** — 원자료는
  `.gitignore` 대상이라 환경이 없는 곳에서 재생성하면 0으로 떨어집니다.

사용법
------
    python gen_intro_html.py --page landing --repo-root . \
        --project-dir projects/{프로젝트} --slug {프로젝트} \
        --css core/modules/qa-site/design-guide/design-guide-master.css -o index.html
"""
import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shell  # noqa: E402
import new_project  # noqa: E402

esc = shell.esc
BLOB = shell.BLOB


def card(title, body, foot=""):
    # title에 링크를 담는 경우가 있어 여기서 이스케이프하지 않는다 — 호출부가 책임진다
    o = ['<div class="card"><h3>%s</h3><p>%s</p>' % (title, body)]
    if foot:
        o.append('<p class="foot">%s</p>' % foot)
    o.append('</div>')
    return "".join(o)


# ────────────────────────────────────────────────────────────────
# 페이지 ② 저장소 구조 — 폴더 이름이 곧 참조 규칙이다
# ────────────────────────────────────────────────────────────────
def page_central(args, rel):
    """중앙 규칙 구조 — 모든 프로젝트가 따르는 절차·형식·소개가 어디 있고 무엇을 정하는지.

    목록은 폴더를 훑어 만들고 설명은 각 파일의 첫 문단·첫 줄에서 읽습니다. 여기에 요약을
    옮겨 적으면 규칙이 바뀔 때 이 페이지만 옛말을 하게 됩니다.
    """
    R = rel["root"]
    core = os.path.join(args.repo_root, "core")
    o = []
    w = o.append

    def collect(kind, ext):
        """base와 modules 양쪽을 훑어 (저장소 기준 폴더, 파일명, 실제 경로)를 모은다.

        폴더를 훑으므로 모듈이 늘어도 이 페이지는 따라옵니다 — 목록을 손으로 적지
        않는다는 규칙이 base와 modules로 갈린 뒤에도 그대로 적용됩니다.
        """
        roots = [("core/base/" + kind, os.path.join(core, "base", kind))]
        mod = os.path.join(core, "modules")
        if os.path.isdir(mod):
            for m in sorted(os.listdir(mod)):
                roots.append(("core/modules/%s/%s" % (m, kind),
                              os.path.join(mod, m, kind)))
        out = []
        for where, d in roots:
            if not os.path.isdir(d):
                continue
            for n in sorted(os.listdir(d)):
                if n.endswith(ext) and not n.startswith("_"):
                    out.append((where, n, os.path.join(d, n)))
        return out

    rule_items = collect("rules", ".md")
    script_items = collect("scripts", ".py")
    #: 파일명 → 저장소 기준 폴더 / 실제 경로. 같은 이름이 두 모듈에 있지는 않다
    rule_at = dict((n, (w_, p)) for w_, n, p in rule_items)
    script_at = dict((n, (w_, p)) for w_, n, p in script_items)
    rule_files = [n for _w, n, _p in rule_items]
    scripts = [n for _w, n, _p in script_items]
    # 평면에 있는 절차서·용어집은 base 바로 밑에 산다
    flat_at = {}
    for n in sorted(os.listdir(os.path.join(core, "base"))):
        if n.endswith(".md"):
            flat_at[n] = ("core/base", os.path.join(core, "base", n))
    proj_path = shell.intro_path("project", args.slug)
    proj_link = ('<a href="%s%s">프로젝트 규칙 구조</a>' % (R, esc(proj_path))
                 if os.path.exists(os.path.join(args.repo_root, proj_path))
                 else "<b>프로젝트 규칙 구조</b>")

    w('<div class="doc-header"><h1>중앙 규칙: 모든 프로젝트가 따라야 하는 규칙</h1>')
    w('<p class="doc-lead">프로젝트를 시작하기 전, <strong>절차와 판단 기준과 형식부터 '
      '세웠습니다.</strong> 작업을 진행하는 도중 중앙 규칙 단위로 바뀌어야 하는 규칙이 있다면 '
      '유저에게 추가·편집할 것인지 제안하고, 유저는 그에 대한 결정을 내립니다. 이를 기반으로 '
      '어긋나는 규칙이 있다면 한쪽으로 일치시킴으로써, <strong>프로젝트를 진행할수록 자라는 '
      '구조</strong>로 설계하였습니다.</p>')
    w('<div class="meta-row"><span class="badge">규칙 문서 <b>%d편</b></span>'
      '<span class="badge">생성 도구 <b>%d개</b></span>'
      '<span class="badge">확인 게이트 <b>2곳</b></span></div></div>' % (len(rule_files), len(scripts)))

    # ── 전체 그림
    w('<h2 id="map">중앙 규칙 워크플로우</h2>')
    w('<p>중앙 규칙은 <strong>모든 작업 앞에</strong> 있고, 프로젝트는 그 규칙을 기반으로 삼아 '
      '자신만의 프로젝트에 필요한 규칙이나 문서를 추가로 작성해 나갑니다. 아래 그림은 중앙 규칙의 '
      '워크플로우를 도식화한 이미지입니다.</p>')
    svg = os.path.join(args.repo_root, "structure.svg")   # 저장소 구조도는 그 저장소 것이라 루트에 둡니다
    if os.path.exists(svg):
        body = io.open(svg, encoding="utf-8").read()
        body = body[body.index("<svg"):]
        w('<div class="card" style="padding:14px">%s</div>' % body)

    # ── 왜 중앙에 모았나
    w('<h2 id="why">왜 중앙 규칙을 분리했나요?</h2>')
    w('<div class="card-grid">')
    w(card("한 프로젝트의 결정이 다른 프로젝트에 유입되지 않도록 사전 차단",
           "규칙을 프로젝트 안에 두고 대화로 키우면, 프로젝트가 늘었을 때 <strong>A의 스펙이 B에 "
           "섞여 들어옵니다.</strong> 규칙을 밖으로 빼면 프로젝트는 서로를 참조할 일이 없어지고, "
           "공유되는 것은 「따라야 하는 기준」뿐입니다."))
    w(card("매번 같은 판단을 참조",
           "규칙이 늘어남에 따라 여러 문서에 담길 수 있는 규칙들의 중복을 제거하고, "
           "<strong>하나의 규칙을 기반으로 동일한 판단을 참조</strong>할 수 있도록 의도하였습니다."))
    w('</div>')

    # ── 무엇이 중앙 규칙인가
    w('<h2 id="what">무엇이 중앙 규칙에 포함되나요?</h2>')
    w('<p>판별 기준은 <strong>「문장에서 프로젝트 이름을 지워도 성립하는가」</strong>입니다. '
      '성립하면 중앙 규칙이고, 아니면 %s입니다.</p>' % proj_link)
    w('<div class="card-grid">')
    w(card("<code>base/</code> — 절차와 판단 기준",
           "프로젝트의 진행 절차의 규칙을 사전에 정의함으로써, <strong>프로젝트가 늘어도 같은 방식으로 "
           "일하도록</strong> 유도합니다.",
           "파이프라인 절차서 · 규칙 문서 %d편 · 중앙 용어집 · 생성 도구" % len(rule_files)))
    w(card("<code>base/design-guide/</code> — 형식의 정본",
           "색·타이포·컴포넌트의 정본이 하나라, 문서마다 스타일을 다시 정하지 않습니다. "
           "산출물은 만들 때마다 그 사본을 품어 네트워크 요청 없이 혼자 열립니다.",
           '<a href="%score/base/design-guide/design-guide-ue-master-visual.html">시각 규칙서 열기</a>' % R))
    w(card("<code>base/design-template/</code> — 새 문서를 만들 때의 틀",
           "새 문서가 <strong>기존 템플릿으로 되는지, 기준을 고쳐야 하는지, 새로 만들어야 하는지</strong>를 "
           "세 갈래로 판별합니다. 문서의 목적과 다른 템플릿을 사용하지 않도록 <strong>일관적인 "
           "템플릿을 유도</strong>합니다.",
           "모듈을 켜면 그 템플릿도 함께 봅니다"))
    w(card("루트의 <code>main-*.html</code> — 저장소를 소개하는 층",
           "지금 읽고 계신 문서들입니다. 「프로젝트를 만들기 전에 세운 규칙」처럼 특정 프로젝트 "
           "소유가 아닌 이야기가 섞이므로 프로젝트 밖에 둡니다.",
           "전부 생성기가 만드는 파생물입니다"))
    w('</div>')

    # ── 절차 (playbook의 STEP 제목을 읽어 온다)
    w('<h2 id="step">중앙 규칙의 작업 절차</h2>')
    w('<p>문서 제작 요청이 오면 아래 순서를 처음부터 끝까지 따릅니다. 단계 이름은 절차서에서 '
      '그대로 읽어 온 것이라, 절차가 바뀌면 이 목록도 함께 바뀝니다.</p>')
    steps = []
    pb = os.path.join(core, "base", "doc-playbook.md")
    if os.path.exists(pb):
        for line in io.open(pb, encoding="utf-8"):
            m = re.match(r"^## (STEP \d+) — (.+)$", line.strip())
            if m:
                steps.append((m.group(1), m.group(2)))
    w('<div class="steps">')
    for no, title in steps:
        w('<div class="step"><div class="body"><b>%s</b> — %s</div></div>'
          % (esc(no), esc(title)))
    w('</div>')
    w('<div class="callout">이 절차의 핵심은 <strong>확인 게이트 두 곳</strong>입니다. '
      '아웃라인을 확인받기 전에는 본문을 쓰지 않고, 어떤 형식으로 낼지 정하기 전에는 만들지 '
      '않습니다. 다 쓰고 나서 방향이 어긋난 것을 알면 그때는 전부 다시 써야 하기 때문입니다.</div>')
    w('<div class="callout warn">규칙을 파악하는 과정에서 <strong>중앙 규칙과 다른 상태가 '
      '들어오면 그 자리에서 맞추지 않고 유저에게 되묻습니다</strong> — 이 프로젝트의 예외로 '
      '둘 것인지, 중앙 규칙을 고칠 것인지. 임의로 한쪽에 맞추면 어느 것이 기준인지 알 수 없게 '
      '되고, 다음 프로젝트가 그 상태를 물려받습니다.</div>')

    # ── 규칙 문서 (폴더를 훑고 첫 문단을 읽는다)
    w('<h2 id="doc">규칙 문서</h2>')
    w('<p>각 문서가 스스로 밝힌 존재 이유를 그대로 가져왔습니다 — 여기에 요약을 옮겨 적으면 '
      '규칙이 바뀔 때 이 페이지만 옛말을 하게 됩니다.</p>')
    placed = set()
    for group, names in RULE_GROUPS:
        rows = []
        for name in names:
            where_path = rule_at.get(name) or flat_at.get(name)
            if not where_path:
                continue
            where, path = where_path
            href = "%s/%s/%s" % (BLOB, where, name)
            base = name if where.endswith("base") else where.split("core/")[1] + "/" + name
            placed.add(name)
            rows.append((base, href, doc_intro(path)))
        if not rows:
            continue
        w('<h3>%s</h3><div class="tbl-scroll"><table><tbody>' % esc(group))
        for base, href, why in rows:
            w('<tr><td style="width:230px"><a href="%s"><code>%s</code></a></td><td>%s</td></tr>'
              % (esc(href), esc(base), esc(why)))
        w('</tbody></table></div>')
    left = [n for n in rule_files if n not in placed]
    if left:
        w('<h3>그 밖에</h3><div class="tbl-scroll"><table><tbody>')
        for name in left:
            where, path = rule_at[name]
            w('<tr><td style="width:230px"><a href="%s/%s/%s">'
              '<code>%s/%s</code></a></td><td>%s</td></tr>'
              % (BLOB, where, esc(name), esc(where.split("core/")[1]),
                 esc(name), esc(doc_intro(path))))
        w('</tbody></table></div>')
    w('<p class="foot">md 문서와 폴더 링크는 GitHub 저장소에서 열리고, HTML 문서는 이 사이트에서 '
      '바로 렌더링됩니다 — GitHub Pages에서는 md가 원본 텍스트로 뜨기 때문입니다.</p>')

    # ── 도구 (docstring 첫 줄을 읽는다)
    w('<h2 id="tool">사람이 반복하지 않게 만든 도구</h2>')
    w('<p>같은 일을 두 번 이상 손으로 하면 언젠가 한 번은 틀립니다. 아래는 그 자리마다 만들어 둔 '
      '도구이고, 설명은 각 파일이 스스로 적어 둔 첫 줄입니다.</p>')
    w(shell.table_tools("tool-tbl", "도구 검색"))
    w('<div class="tbl-scroll"><table id="tool-tbl"><thead><tr>'
      '<th class="sortable">도구</th><th>무엇을 하나</th></tr></thead><tbody>')
    for name in scripts:
        where, path = script_at[name]
        w('<tr><td><a href="%s/%s/%s"><code>%s</code></a></td><td>%s</td></tr>'
          % (BLOB, where, esc(name), esc(name), esc(script_summary(path))))
    w('</tbody></table></div>')

    w('<div class="doc-footer">이 문서는 파생물입니다 — '
      '<code>gen_intro_html.py --page central</code>로 재생성합니다. 규칙 목록·절차 단계·'
      '도구 설명은 전부 실제 파일에서 읽고, 구조도는 <code>structure.svg</code>를 읽습니다.</div>')

    return "".join(o)


def doc_intro(path, limit=230):
    """md 본문의 첫 문단 — 그 문서가 스스로 밝힌 존재 이유를 그대로 가져온다.

    길면 줄이되 **문장 도중에는 자르지 않는다.** 문장 중간에서 끊긴 설명은 무슨 말인지
    알 수 없어, 설명을 싣지 않은 것과 다르지 않다.
    """
    try:
        lines = io.open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return ""
    buf = []
    for line in lines[1:]:
        t = line.strip()
        if t.startswith("#") or t.startswith("|") or t.startswith("---"):
            if buf:
                break
            continue
        if not t:
            if buf:
                break
            continue
        buf.append(t)
    text = re.sub(r"[*`]", "", " ".join(buf))
    if len(text) <= limit:
        return text
    # 한도 안에서 마지막으로 끝난 문장까지만 남긴다. 한 문장도 못 담으면 그때만 말줄임한다
    cut = max(text.rfind(m, 0, limit + 1) for m in ("다.", "요.", "다!", "다?"))
    if cut > 0:
        return text[:cut + 2]
    return text[:limit].rstrip() + "…"


def script_summary(path):
    """생성 도구의 모듈 docstring 첫 줄 — 도구가 스스로 적어 둔 한 줄.

    함수 docstring을 집어 오지 않도록, 첫 def/class보다 앞에 있는 문자열만 인정한다.
    """
    try:
        src = io.open(path, encoding="utf-8").read()
    except OSError:
        return ""
    start = src.find('"""')
    if start < 0:
        return ""
    body_start = re.search(r"^(def |class )", src, re.M)
    if body_start and body_start.start() < start:
        return ""
    end = src.find('"""', start + 3)
    doc = src[start + 3:end if end > 0 else None]
    for line in doc.splitlines():
        head = line.strip()
        if head:
            return head.split(" — ", 1)[1] if " — " in head else head
    return ""


# ────────────────────────────────────────────────────────────────
# 페이지 ③ 프로젝트 규칙 구조 — 프로젝트 안에 무엇이 쌓이는가
# ────────────────────────────────────────────────────────────────
#: 규칙 문서를 묶는 축. 목록에 없는 파일은 「그 밖에」로 떨어지므로 새 문서가 사라지지 않는다
RULE_GROUPS = (
    ("무엇을 어떤 순서로 하는가", ("doc-playbook.md", "remaining-work.md", "git-rules.md")),
    ("테스트를 어떻게 설계하는가",
     ("depth-and-tn.md", "case-expansion.md", "verification-types.md",
      "tc-relations.md", "tc-sheet-format.md")),
    ("만들고 돌리는 규칙", ("automation.md", "sut-build.md")),
    ("문서를 어떻게 쓰고 어디에 두는가",
     ("doc-write-style.md", "html-output.md", "site-structure.md")),
)


def page_project(args, rel):
    """프로젝트 생성 방식 — 새 프로젝트가 무엇을 갖고 시작하고, 무엇을 일부러 안 만드는가.

    자리 목록은 `new_project.py`의 상수에서 그대로 읽습니다. 여기에 옮겨 적으면 도구가
    바뀔 때 이 페이지만 옛말을 하게 됩니다. 모듈 목록도 폴더를 훑어 만듭니다.
    """
    R = rel["root"]
    core = os.path.join(args.repo_root, "core")
    o = []
    w = o.append

    w('<h2 id="project-guide">프로젝트 생성 방식</h2>')
    w('<p class="doc-lead">새 프로젝트는 <strong>도구가 찍습니다.</strong> 손으로 만들면 '
      '프로젝트마다 자리가 조금씩 달라지고, 그러면 「어디를 보면 되는가」를 매번 다시 '
      '찾아야 합니다. 시작 모양을 하나로 고정해 두는 이유입니다.</p>')
    w('<div class="meta-row">'
      '<span class="badge">만드는 폴더 <b>%d개</b></span>'
      '<span class="badge">만드는 문서 <b>%d개</b></span></div>'
      % (len(new_project.DIRS), len(new_project.DOCS)))

    # ── 명령
    w('<h3 id="run">한 줄로 만듭니다</h3>')
    w('<pre><code>python core/base/scripts/new_project.py {제품}/{슬러그}</code></pre>')
    w('<p>슬러그는 소문자 kebab-case이고, <strong>폴더 이름이자 파일 접두</strong>가 됩니다. '
      '이미 있는 이름이면 도구가 멈춥니다 — 덮어쓰면 기존 기록이 사라지기 때문입니다.</p>')

    # ── 생기는 것
    w('<h3 id="made">무엇이 생기나</h3>')
    tree = ["projects/{제품}/{슬러그}/"]
    for _tpl, tail in new_project.DOCS:
        tree.append("    {슬러그}%s" % tail)
    for d in new_project.DIRS:
        tree.append("    %s/" % d)
    w('<pre><code>%s</code></pre>' % esc("\n".join(tree)))
    w('<div class="card-grid">')
    w(card("세 문서는 역할이 갈립니다",
           "<b>change-log</b>는 한 일을 쌓고, <b>remaining-work</b>는 할 일만 남기며 끝나면 "
           "지웁니다. 갱신 방향이 반대라 한 파일에 섞지 않습니다. <b>dictionary</b>는 그 "
           "프로젝트에서만 통하는 말을 모읍니다.",
           "앞의 둘은 작업 전 항상 먼저 읽습니다"))
    w(card("빈 폴더도 만듭니다",
           "조사를 하지 않는 프로젝트에서도 <code>analysis/</code>·<code>reference/</code>를 "
           "만듭니다. <b>비어 있는 것이 곧 「이 프로젝트는 조사를 하지 않았다」는 기록</b>이기 "
           "때문입니다. 자리를 조건부로 만들면 나중에 켤 때 자리를 새로 정하게 됩니다.",
           "빈 폴더는 .gitkeep으로 자리를 지킵니다"))
    w('</div>')

    # ── 안 만드는 것
    w('<h3 id="not">일부러 만들지 않는 것</h3>')
    w('<div class="callout warn"><strong>기능 골격 정본</strong>'
      '(<code>spec/{슬러그}-feature-tree.md</code>)은 만들지 않습니다. 빈 정본이 있으면 '
      '생성기가 0노드짜리 문서를 찍어내고, <strong>그것이 「골격이 있다」는 신호로 '
      '읽힙니다.</strong> 골격은 서식이 아니라 내용이라 도구가 만들 수 없습니다.</div>')
    w('<p>같은 이유로 <code>sut/</code>·<code>automation/</code>·<code>spec/sut-design/</code>도 '
      '만들지 않습니다. 이 셋이 있으면 「검증 대상을 직접 만든다」는 뜻이 되므로, 실제로 그렇게 '
      '정한 프로젝트에만 생깁니다.</p>')

    # ── 모듈 (폴더를 훑는다)
    w('<h3 id="module">만든 다음 — 모듈을 켭니다</h3>')
    w('<p>중앙 규칙이라고 해서 모든 프로젝트가 전부 따르는 것은 아닙니다. TC를 만들지 않는 '
      '프로젝트에 TC 시트 서식은 필요 없습니다. 그래서 <code>core/modules/</code>는 '
      '<strong>기본 참조 금지</strong>이고, change-log에 「이 모듈을 켠다」가 적혀 있을 때만 '
      '읽습니다.</p>')
    mod_root = os.path.join(core, "modules")
    if os.path.isdir(mod_root):
        w('<div class="tbl-scroll"><table><thead><tr><th>모듈</th><th>켜면 따르는 규칙</th>'
          '</tr></thead><tbody>')
        for m in sorted(os.listdir(mod_root)):
            rd = os.path.join(mod_root, m, "rules")
            if not os.path.isdir(rd):
                continue
            names = sorted(n for n in os.listdir(rd) if n.endswith(".md"))
            cells = []
            for n in names:
                cells.append('<a href="%s/core/modules/%s/rules/%s"><code>%s</code></a>'
                             % (BLOB, esc(m), esc(n), esc(n)))
            w('<tr><td style="width:120px"><code>%s</code></td><td>%s</td></tr>'
              % (esc(m), " · ".join(cells)))
        w('</tbody></table></div>')
    w('<p class="foot">모듈은 규칙과 도구를 자기 안에 함께 둡니다 — 규칙만 옮기고 도구가 남으면 '
      '켜지 않은 프로젝트에도 그 도구가 보입니다.</p>')

    # ── 순서
    w('<h3 id="next">그다음 순서</h3>')
    w('<div class="steps">')
    for no, body in (("①", "change-log의 <b>§프로젝트 정의</b>를 채웁니다 — 무엇을 다루고 "
                            "무엇을 남기는 프로젝트인가"),
                     ("②", "<b>§켠 모듈</b>을 정합니다. 안 켠 모듈의 규칙은 읽지 않습니다"),
                     ("③", "그 뒤의 순서는 켠 모듈이 정합니다")):
        w('<div class="step"><div class="body"><b>%s</b> — %s</div></div>' % (no, body))
    w('</div>')
    w('<div class="callout"><strong>목록에 등록하는 절차는 없습니다.</strong> 폴더를 만드는 것이 '
      '곧 등록이고, 생성기가 <code>projects/</code>를 훑습니다. 손으로 적는 목록은 문서가 늘 때마다 '
      '낡습니다.</div>')

    w('<p class="foot">자리 목록은 <code>new_project.py</code>에서, 모듈 목록은 폴더에서 '
      '읽습니다. 규칙 정본은 '
      '<a href="%s/core/base/rules/project-scaffold.md">project-scaffold.md</a>입니다.</p>'
      % BLOB)
    return "".join(o)


#: 워크스페이스 문서의 절 — (사이드바 키, 만드는 함수, 그 절 안의 목차).
#:
#: 목차를 여기 함께 적는 이유는, 절을 고치면서 사이드바를 잊는 것을 막기 위해서다.
#: 설명서가 늘면 줄을 하나 더하고 `shell.INTRO`에 앵커를 더한다.
SECTIONS = (
    ("central", page_central, (
        ("중앙 규칙 워크플로우", "map"),
        ("왜 중앙 규칙을 분리했나요?", "why"),
        ("무엇이 중앙 규칙에 포함되나요?", "what"),
        ("중앙 규칙의 작업 절차", "step"),
        ("규칙 문서", "doc"),
        ("사람이 반복하지 않게 만든 도구", "tool"),
    )),
    ("project", page_project, (
        ("한 줄로 만듭니다", "run"),
        ("무엇이 생기나", "made"),
        ("일부러 만들지 않는 것", "not"),
        ("만든 다음 — 모듈을 켭니다", "module"),
        ("그다음 순서", "next"),
    )),
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--project-dir", default=None,
                    help="사이드바의 프로젝트 문서 링크를 걸 프로젝트 폴더(선택)")
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

    out_dir = os.path.dirname(os.path.abspath(args.output))

    def prefix(target):
        p = os.path.relpath(target, out_dir).replace("\\", "/")
        return "" if p == "." else p + "/"

    rel = {"root": prefix(args.repo_root),
           "project": prefix(args.project_dir or args.repo_root)}

    body = "".join(fn(args, rel) for _k, fn, _n in SECTIONS)
    crumb = "중앙 규칙 구조"
    subs = dict((k, nav) for k, _fn, nav in SECTIONS)

    css, js = shell.assets(args.css, args.js)
    # 사이드바는 모든 문서가 같은 것을 씁니다 — 정본은 shell.sidebar 하나입니다
    # (만든 사람 정보는 넣지 않습니다 — 2026-08-04 사용자 확정)
    # 회색 처리는 「아무도 만들지 않는 페이지」에만 씁니다. 판정은 둘 중 하나면 통과입니다 —
    # ① 이 생성기가 만들 수 있다(--page 키가 있다) ② 파일이 이미 있다(다른 생성기가 만든다).
    # 디스크만 보면 여러 장을 한꺼번에 다시 만들 때 아직 안 만든 장이 회색으로 굳고,
    # 키만 보면 리포트·용어집처럼 남이 만드는 문서가 회색이 됩니다. 둘 다 실제로 겪었습니다
    planned = set(path.split("#", 1)[0]
                  for key, _l, path in shell.intro_all(args.slug)
                  if key in ("central", "project"))
    side = shell.sidebar(
        args.slug, "central", rel["project"], "",
        out_path=args.output, subs=subs,
        exists=lambda p: p in planned or os.path.exists(os.path.join(args.repo_root, p)))

    html_out = "".join([
        shell.head("%s — %s" % (shell.NAME, crumb), css, js),
        '<body><div class="app">', side, '<div class="main">',
        shell.topbar(shell.NAME, crumb),
        '<div class="wrap">', body, shell.close_body(),
    ])
    shell.save(args.output, html_out)
    print("saved %s" % args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
