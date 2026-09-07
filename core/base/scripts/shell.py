# -*- coding: utf-8 -*-
"""shell.py — 산출물 공통 셸(사이드바·상단 바·테마 토글)을 한 곳에서 발행

왜 모듈인가
-----------
  사이드바 항목을 생성기마다 적어 두면 문서마다 메뉴가 갈라집니다. 리포트에는 있는
  항목이 매트릭스에는 없는 식입니다. 항목은 여기 한 곳에 두고, 생성기는 「지금 어느
  문서인가」와 「이 문서의 절 목록」만 넘깁니다.

  스타일 정본은 `base/design-guide/design-guide-master.css`, 동작 정본은 같은 폴더의
  `design-guide-master.js`입니다. 산출물은 그 둘을 생성 시점 사본으로 inline해
  네트워크 요청 0건인 단일 파일이 됩니다.

쓰는 곳
-------
  **사이드바에서 열리는 문서에는 전부 입힙니다**(2026-08-05 개정). 메뉴로 들어간 페이지에
  그 메뉴가 없으면 돌아갈 길이 사라지기 때문입니다. 예외는 SUT 하나로, 검증 대상은 문서가
  아니라 테스트가 조작하는 제품이라 화면 구조를 건드리지 않습니다.
"""
import html
import io
import json
import os
import re


def _find_root():
    """저장소 루트 — `workspace.json`이 있는 폴더다.

    위로 거슬러 올라가며 찾는다. 중앙 규칙이 저장소 루트에 있든 `core/` 밑으로 묶이든
    같은 코드로 찾게 하려는 것이다. 못 찾으면 예전 자리로 물러선다.
    """
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(d, "workspace.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))
        d = parent


ROOT = _find_root()

#: 저장소 이름표. **중앙 규칙에 저장소 이름을 적지 않기 위한 파일이다** — 이 폴더를
#: 다른 저장소로 옮길 때 안을 뒤지지 않아도 되도록, 저장소마다 달라지는 값(이름·주소·
#: 부제)은 전부 바깥의 `workspace.json` 한 곳에 둔다. 프로젝트 목록은 여기 적지 않는다
try:
    with io.open(os.path.join(ROOT, "workspace.json"), encoding="utf-8") as _f:
        WS = json.load(_f)
except (OSError, ValueError):
    WS = {}

NAME = WS.get("name", os.path.basename(ROOT))
SUBTITLE = WS.get("subtitle", "")
REPO = WS.get("repo", "")
BLOB = REPO + "/blob/main"

#: 사이드바 「내려받기」 묶음 — 열어 보는 문서가 아니라 받아 가는 파일이다.
#: Pages에서 404가 나므로 절대 URL로 걸고, 저장소를 벗어나므로 새 탭이다.
#:
#: **2026-08-05 비웠습니다.** 여기 있던 「TC 시트」(xlsx)는 GitHub blob으로 곧장 나가
#: 저장소를 모르는 사람에게는 미리보기 없는 내려받기 버튼 하나가 전부였습니다. 「TC 시트
#: 구성」 문서가 같은 파일을 **받는 법과 함께** 주므로 사이드바 링크는 걷어냈습니다 —
#: 같은 파일로 가는 길이 둘이면 이름이 겹쳐 무엇이 다른지 눌러 봐야 압니다.
#: 비어 있으면 묶음 자체를 만들지 않으므로, 내려받을 것이 생기면 한 줄 넣는 것으로 살아납니다
OUT = ()

#: 저장소 자체로 가는 링크. 프로젝트가 아니라 **워크스페이스 전체**를 가리키므로
#: 프로젝트 묶음이 아니라 「소개」 끝에 붙인다
REPO_LINK = ("저장소 깃허브 링크", REPO, "git")

#: 사이드바에서 워크스페이스 이야기와 프로젝트 이야기를 가르는 기준.
#: 앞은 프로젝트가 늘어도 그대로이고, 뒤는 프로젝트마다 한 벌씩 생긴다
WORKSPACE_INTRO = ("central", "project")
PROJECT_INTRO = ("tree", "tcsheet", "dict", "report", "trace")

def project_cfg(slug):
    """프로젝트별 표시 설정. **없는 것이 기본**이다.

    프로젝트 목록을 중앙에 적어 두면 폴더를 만들 때마다 두 곳을 고쳐야 하고, 한쪽만
    고치면 어긋납니다. 그래서 폴더를 만드는 것이 곧 등록이고, 기본값과 달리 쓰고 싶은
    프로젝트만 자기 폴더에 `{slug}-site.json`을 둡니다.
    """
    p = os.path.join(ROOT, "projects", slug, "%s-site.json" % slug)
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def project_label(slug):
    """사이드바에 표시할 프로젝트 이름. 기본은 폴더 이름이다."""
    return project_cfg(slug).get("label", slug)


def project_prefix(slug):
    """소개 문서 파일명의 접두. 기본은 폴더 이름이고, slug가 길면 짧게 덮어쓴다 —
    접두가 길어지면 파일 목록에서 뒤쪽의 실제 구분이 보이지 않는다."""
    return project_cfg(slug).get("prefix", slug)


#: 사이드바 「소개」·「문서」 묶음 — (키, 라벨, 저장소 루트 기준 경로)
#:
#: **워크스페이스 문서는 `index.html` 한 장에 절로 쌓고 `#앵커`로 잇습니다.** 설명서가
#: 늘어도 파일이 늘지 않습니다 — 자기완결 단일 파일이라 장마다 CSS·JS 사본을 하나씩 더
#: 품게 되고, 이어서 읽는 내용인데 페이지를 넘겨야 하기 때문입니다.
#:
#: **프로젝트 산출물은 전부 그 프로젝트 폴더 안에 둡니다** — 밖에 두면 중앙 저장소로
#: 떼어낼 때 프로젝트 것이 함께 따라갑니다. 프로젝트마다 내용이 다르고 만드는 생성기도
#: 달라서 한 장으로 모으지 않습니다. `{slug}`는 폴더 이름, `{prefix}`는 파일 접두
INTRO = (
    ("central", "중앙 규칙 구조", "index.html"),
    ("project", "프로젝트 생성 방식", "index.html#project-guide"),
    ("tree", "기능 골격", "projects/{slug}/docs/{prefix}-feature-tree.html"),
    ("tcsheet", "TC 시트 구성", "projects/{slug}/docs/{prefix}-tc-sheet.html"),
    ("dict", "용어집", "projects/{slug}/docs/{prefix}-dictionary.html"),
    ("report", "자동화 QA 리포트", "projects/{slug}/docs/{prefix}-report.html"),
    ("trace", "추적 매트릭스", "projects/{slug}/docs/{prefix}-traceability.html"),
)


def esc(s):
    return html.escape(str(s if s is not None else ""))


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def assets(css_path, js_path=None):
    """마스터 CSS·JS를 읽어 온다. JS 경로를 안 주면 CSS 옆에서 찾는다."""
    css = read(css_path)
    if js_path is None:
        js_path = os.path.join(os.path.dirname(os.path.abspath(css_path)),
                               "design-guide-master.js")
    js = read(js_path) if os.path.exists(js_path) else ""
    return css, js


def head(title, css, js, extra_style=""):
    """<head>까지. JS는 <head>에서 동기로 돌아 첫 페인트 전에 테마를 정한다."""
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>%s</title><style>%s%s</style><script>%s</script></head>'
        % (esc(title), css, extra_style, js))


def header_toggle():
    """셸이 없는 문서용 — .doc-header 안에 넣으면 오른쪽 위에 붙는다."""
    return '<button class="icon-btn" data-theme-toggle>다크</button>'


def nav_group(title, items):
    """items: (라벨, href 또는 None, 활성 여부, 태그[, 새 탭 여부, 절 여부]).

    href가 None이면 링크 없이 회색으로 남습니다. 다섯 번째 값이 참이면 새 탭에서 열고,
    여섯 번째 값이 참이면 **문서 안의 절**로 한 단 들여 씁니다(`nav-sub`). 절은 지금 읽는
    자리를 스크립트가 표시하므로(design-guide-master.js의 스크롤 스파이) 활성 표시를 주지
    않습니다.
    """
    o = ['<div class="nav-sec">%s</div>' % esc(title)]
    for item in items:
        label, href, active, tag = item[:4]
        blank = bool(item[4]) if len(item) > 4 else False
        sub = bool(item[5]) if len(item) > 5 else False
        tag_html = ('<span class="tag">%s</span>' % esc(tag)) if tag else ""
        if sub:
            o.append('<a class="nav-sub" href="%s">%s</a>' % (esc(href), esc(label)))
        elif href:
            o.append('<a class="nav-i%s" href="%s"%s>%s%s</a>'
                     % (" on" if active else "", esc(href),
                        ' target="_blank" rel="noopener"' if blank else "",
                        esc(label), tag_html))
        else:
            o.append('<span class="nav-i nav-off">%s%s</span>' % (esc(label), tag_html))
    return "".join(o)


def sidebar_from(groups, head_href, head_title, head_sub, foot=""):
    """묶음을 그대로 받아 사이드바를 만든다.

    groups: (제목, items) 목록. 제목 앞에 "@"를 붙이면 **카테고리 머리말**로 나가고,
    그 아래 묶음들이 그 카테고리에 속한 것으로 읽힙니다.

    문서 안의 절 목록(「이 문서」)은 넣지 않습니다 — 본문 제목이 이미 그 역할을 하고,
    사이드바에 겹쳐 두면 항목이 두 배로 늘어 메뉴가 읽히지 않습니다.
    """
    o = ['<aside class="side">']
    o.append('<div class="side-head"><a href="%s">%s</a><span class="sub">%s</span></div>'
             % (esc(head_href), esc(head_title), esc(head_sub)))
    o.append('<nav class="side-nav">')
    for title, items in groups:
        if title.startswith("@"):
            o.append('<div class="nav-cat">%s</div>' % esc(title[1:]))
            continue
        o.append(nav_group(title, items))
    o.append('</nav>')
    if foot:
        o.append('<div class="side-foot">%s</div>' % esc(foot))
    o.append('</aside>')
    return "".join(o)


def intro_all(slug):
    """INTRO의 경로에서 `{slug}`·`{prefix}` 자리를 그 프로젝트 값으로 채운 목록."""
    pre = project_prefix(slug)
    return tuple((k, l, p.replace("{slug}", slug).replace("{prefix}", pre))
                 for k, l, p in INTRO)


def intro_group(current, root, slug, exists=None, keys=None, title="소개", subs=None):
    """소개 묶음. root = 저장소 루트로 가는 상대 경로 접두("" 또는 "../").

    keys를 주면 그 키만 순서대로 뽑는다 — 워크스페이스 문서와 프로젝트 문서를 갈라
    두기 위해서다. exists(경로)가 False면 링크 없이 회색으로 남긴다(아직 안 만든 페이지).
    """
    picked = [(k, l, p) for k, l, p in intro_all(slug) if keys is None or k in keys]
    if keys is not None:
        picked.sort(key=lambda t: list(keys).index(t[0]))
    items = []
    for key, label, path in picked:
        # 앵커는 같은 장의 절을 가리킨다 — 존재 판정은 `#` 앞의 파일로 한다
        file_part = path.split("#", 1)[0]
        # 지금 만들고 있는 페이지는 아직 파일이 없다 — 자기 자신은 항상 있는 것으로 본다
        ok = key == current or exists is None or bool(exists(file_part))
        items.append((label, (root + path) if ok else None, key == current, ""))
        # 그 항목이 가리키는 장의 절 — 한 장에 여러 절이 있으면 목차가 된다
        for s_label, s_anchor in (subs or {}).get(key, ()):
            items.append((s_label, (root + file_part + "#" + s_anchor) if ok else None,
                          False, "", False, True))
    return (title, items)


def repo_root():
    """저장소 루트. `workspace.json`이 있는 자리이므로 중앙 규칙이 어느 깊이에 있든 같다."""
    return ROOT


def root_rel(out_path):
    """출력 파일에서 저장소 루트로 가는 상대 경로 접두."""
    r = os.path.relpath(repo_root(), os.path.dirname(os.path.abspath(out_path)))
    r = r.replace(os.sep, "/")
    return "" if r == "." else r + "/"


def intro_path(key, slug):
    """소개 묶음 한 장의 저장소 루트 기준 경로. 정본은 INTRO 하나다 —
    본문에서 링크를 손으로 적으면 파일명이 바뀔 때 사이드바만 따라오고 본문은 남는다."""
    for k, _l, p in intro_all(slug):
        if k == key:
            return p
    raise KeyError(key)


def intro_href(key, out_path, slug):
    """출력 파일에서 소개 페이지 한 장으로 가는 상대 경로."""
    return root_rel(out_path) + intro_path(key, slug)


def has_project(slug):
    """그 프로젝트가 이 저장소에 실재하는가. 중앙 저장소에서는 늘 거짓이다."""
    return os.path.isdir(os.path.join(ROOT, "projects", slug))


def sidebar(slug, current, rel, foot="", out_path=None, exists=None, subs=None):
    """모든 문서가 쓰는 사이드바 — rel = 출력 파일에서 프로젝트 폴더로 가는 상대 경로 접두.

    구성은 두 덩어리다. 위는 **워크스페이스**(포트폴리오 홈과 규칙 구조), 아래는
    **프로젝트 하나**(그 프로젝트를 설명하는 문서 · 산출물 · 원본 파일)이다. 프로젝트가
    늘면 아래 덩어리가 하나 더 붙는 형태라, 지금 구조가 그대로 자란다.

    out_path를 주면 소개 묶음까지 붙어 어느 문서에서나 같은 메뉴가 나온다. 사이드바에서
    들어간 페이지에 사이드바가 없으면 돌아갈 길이 사라지므로, 새 문서는 반드시 준다.

    exists(경로)는 「그 소개 페이지가 있는가」의 판정이다. 기본값은 디스크 확인인데,
    소개 페이지를 여러 장 한꺼번에 다시 만들 때는 **아직 안 만든 장이 회색으로 굳으므로**
    생성기가 「만들 수 있는 페이지」 기준을 대신 넘긴다.
    """
    groups = []
    head_href, head_title, head_sub = rel + "index.html", NAME, SUBTITLE
    if out_path is not None:
        root = root_rel(out_path)
        if exists is None:
            # 소개 층은 여러 생성기가 나눠 만든다. 디스크만 보면 「아직 안 만든 장」이 회색으로
            # 굳으므로, 목록에 있는 문서는 있는 것으로 본다 — 목록 자체가 만들겠다는 선언이다
            planned = set(path.split("#", 1)[0] for _k, _l, path in intro_all(slug))
            exists = lambda p: p in planned  # noqa: E731
        ws_title, ws_items = intro_group(current, root, slug, exists=exists,
                                         keys=WORKSPACE_INTRO, subs=subs)
        # 저장소 링크는 워크스페이스 전체를 가리키므로 소개 묶음의 끝에 붙는다
        ws_items.append((REPO_LINK[0], REPO_LINK[1], False, REPO_LINK[2], True))
        groups.append((ws_title, ws_items))
        head_href = root + "index.html"
        head_title, head_sub = NAME, SUBTITLE
        # 프로젝트 묶음은 그 프로젝트가 **실재할 때만** 붙입니다. 중앙 저장소에는
        # 프로젝트가 없으므로, 붙이면 없는 프로젝트 이름이 문서에 찍혀 나갑니다
        if has_project(slug):
            groups.append(("@프로젝트: %s" % project_label(slug), ()))
            doc_title, doc_items = intro_group(current, root, slug, exists=exists,
                                               keys=PROJECT_INTRO, title="문서")
            groups.append((doc_title, doc_items))
    # 「내려받기」는 GitHub으로 나가므로 전부 새 탭이다.
    # 비었으면 묶음을 만들지 않습니다 — nav_group은 항목 수와 무관하게 머리말을 찍으므로
    # 그냥 두면 빈 「내려받기」 제목만 남습니다
    repo_items = [(label, url.format(S=slug), False, tag, True) for label, url, tag in OUT]
    if repo_items:
        groups.append(("내려받기", repo_items))
    return sidebar_from(groups, head_href, head_title, head_sub, foot)


def topbar(crumb_root, crumb_doc):
    return (
        '<header class="topbar">'
        '<button class="icon-btn side-toggle" aria-label="메뉴 열기">☰</button>'
        '<div class="crumb">%s · <b>%s</b></div><span class="sp"></span>'
        '<button class="icon-btn" data-theme-toggle>다크</button></header>'
        % (esc(crumb_root), esc(crumb_doc)))


def open_body(slug, current, rel, crumb_doc, foot="", out_path=None):
    """<body>부터 본문 시작(.wrap 열림)까지."""
    crumb_root = NAME if out_path is not None else slug
    return ('<body><div class="app">%s<div class="main">%s<div class="wrap">'
            % (sidebar(slug, current, rel, foot, out_path),
               topbar(crumb_root, crumb_doc)))


def close_body():
    return '</div></div></div><div class="backdrop"></div></body></html>'


def check_items(tcs):
    """확인 항목 수 — 시트의 한 행이 확인 항목 하나입니다.

    케이스(TC ID) 수와 다릅니다. 한 케이스가 확인 항목을 여럿 갖기 때문입니다.
    두 수를 한 자리에서 세는 이유는, 문서마다 따로 세면 「문서는 153인데 시트는
    297」처럼 갈라지기 때문입니다(2026-08-05 확정).
    """
    return sum(sum(max(1, len(e)) for e in t[5]) for t in tcs)


#: 저장소 밖으로 나가는 링크를 가리는 기준 — GitHub으로 나가는 링크다.
#: 읽던 문서를 덮지 않도록 새 탭으로 연다
_A_TAG = re.compile(r"<a\s[^>]*>")
_HREF = re.compile(r'href="([^"]*)"')


def new_tab_out(doc):
    """저장소 밖으로 나가는 링크에 새 탭 표시를 단다.

    링크마다 손으로 붙이면 새 링크가 생길 때마다 빠집니다. 어느 생성기가 찍었든
    저장 직전에 한 번에 다는 이유입니다. 이미 표시가 있는 링크(사이드바)는 두 번
    달지 않습니다.
    """
    def mark(m):
        tag = m.group(0)
        if "target=" in tag:
            return tag
        href = _HREF.search(tag)
        if not href:
            return tag
        url = href.group(1)
        if url.startswith(REPO) or url.startswith("https://github.com/"):
            return tag[:-1] + ' target="_blank" rel="noopener">'
        return tag
    return _A_TAG.sub(mark, doc)


def save(out_path, doc):
    """산출물을 쓴다 — 나가는 링크에 새 탭 표시를 달고 저장한다."""
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_tab_out(doc))


def table_tools(table_id, placeholder="검색", buttons=()):
    """표 도구 한 줄 — 검색 · 필터 칩 · 건수.

    buttons: (라벨, 종류, 값, 값2) 목록.
      ("결정적", "col", 2, "결정적")  → 2번 열 텍스트에 값이 있으면 표시
      ("이슈 있음", "attr", "issue", "1") → 행의 data-issue 가 "1"이면 표시
    """
    o = ['<div class="tbl-tools" data-table="%s">' % esc(table_id)]
    o.append('<input class="tbl-search" type="search" placeholder="%s">' % esc(placeholder))
    for label, kind, key, val in buttons:
        attr = ('data-col="%s"' % esc(key)) if kind == "col" else ('data-attr="%s"' % esc(key))
        o.append('<button class="fbtn" %s data-val="%s">%s</button>'
                 % (attr, esc(val), esc(label)))
    o.append('<span class="tbl-count"></span></div>')
    return "".join(o)
