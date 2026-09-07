# -*- coding: utf-8 -*-
"""{프로젝트}-dictionary.md (정본) -> -dictionary.html (파생, 자기완결 단일 파일)

파이프라인에서의 위치
--------------------
  projects/{프로젝트}/{프로젝트}-dictionary.md   (정본 — 묶음별 표)
    │  이 스크립트 — 표를 한 장으로 합치고 검색·묶음 필터를 붙인다
    ▼
  같은 폴더의 {프로젝트}-dictionary.html

  · 생성 시점의 design-guide-master.css·js 전문을 inline (네트워크 요청 0건)
  · 셸을 입히지 않는다 — 한 장으로 끝나는 문서라 테마 토글만 머리말에 붙는다
    (배치 규칙: rules/site-structure.md §셸과 사이드바)
  · 용어를 한 표로 합치는 이유는 검색이 한 번에 끝나기 때문이다. 묶음은 열로 남기고
    필터 칩으로 좁힌다

사용법:
    python gen_dictionary_html.py projects/{프로젝트}/{프로젝트}-dictionary.md \
        --css core/base/design-guide/design-guide-master.css -o {같은 폴더}/{프로젝트}-dictionary.html
"""
import argparse
import datetime
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shell  # noqa: E402


def esc(s):
    return html.escape(str(s if s is not None else ""))


#: md 링크를 저장소 절대 URL로 바꿀 때 쓰는 기준 폴더 — main()이 채운다
BASE_DIR = [None]


def md_href(href):
    """Pages는 .md를 원본 텍스트로 내보내므로 md 링크는 저장소 절대 URL로 건다
    (규칙: rules/html-report-guide.md §Pages 링크). 그 밖의 링크는 그대로 둔다."""
    if not href.endswith(".md") or "://" in href:
        return href
    base = BASE_DIR[0]
    if not base:
        return href
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full = os.path.normpath(os.path.join(base, href))
    rel = os.path.relpath(full, repo).replace(os.sep, "/")
    return "%s/%s" % (shell.BLOB, rel)


def inline(md):
    """표 칸 안의 최소 마크다운만 옮긴다 — 코드·굵게·링크."""
    out = esc(md)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                 lambda m: '<a href="%s">%s</a>' % (md_href(m.group(2)), m.group(1)), out)
    return out


def parse(text):
    """(머리말 문단들, [(묶음, [(용어, 요약, 정본), …]), …])"""
    lead, groups = [], []
    cur, rows, buf = None, [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            continue
        if s.startswith("## "):
            if cur:
                groups.append((cur, rows))
            cur, rows = s[3:].strip(), []
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 3 or set("".join(cells)) <= set("-: "):
                continue
            if cells[0] in ("용어",):
                continue
            rows.append(tuple(cells[:3]))
            continue
        if cur is None:
            if s:
                buf.append(s)
            elif buf:
                lead.append(" ".join(buf))
                buf = []
    if buf:
        lead.append(" ".join(buf))
    if cur:
        groups.append((cur, rows))
    return lead, groups


def css_version(css):
    for line in css.splitlines():
        t = line.strip()
        if t.startswith("v") and "(" in t:
            return t.split()[0]
    return "v1.0"


def main():
    # 한글 출력이 콘솔 기본 인코딩으로 나가면, 다른 도구가 받아 읽을 때 깨집니다.
    # 오류는 stderr로 나가므로 둘 다 맞춥니다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--css", required=True)
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()
    # 없는 파일이면 스택을 쏟지 않고 한 줄로 알립니다 — 대개 경로를 잘못 친 경우입니다
    if not os.path.exists(args.input):
        sys.exit("그런 파일이 없습니다: %s" % args.input)

    BASE_DIR[0] = os.path.dirname(os.path.abspath(args.input))
    text = shell.read(args.input)
    lead, groups = parse(text)
    if not groups:
        sys.exit("용어 표를 찾지 못함")

    slug = os.path.basename(args.input).replace("-dictionary.md", "")
    css, js = shell.assets(args.css)
    total = sum(len(r) for _, r in groups)
    title = "%s 용어집" % slug

    # 묶음·용어 칸은 짧은 말이라 접히면 오히려 읽기 나쁘다 — 이 표에서만 줄바꿈을 막는다
    extra = ("#dict td:first-child,#dict td:nth-child(2){white-space:nowrap}"
             "#dict td:first-child{color:var(--muted)}")

    # 사이드바에서 열리는 문서이므로 셸을 입힌다 — 메뉴로 들어와 메뉴가 사라지면 돌아갈 길이 없다
    rel = os.path.relpath(os.path.dirname(os.path.abspath(args.input)),
                          os.path.dirname(os.path.abspath(args.output))).replace(os.sep, "/")
    rel = "" if rel == "." else rel + "/"

    o = []
    w = o.append
    w(shell.head(title, css, js, extra))
    w(shell.open_body(slug, "dict", rel, "용어집",
                      "수록 %d개" % total, out_path=args.output))
    w('<header class="doc-header">')
    w("<h1>%s — 이 프로젝트에서만 통하는 말</h1>" % esc(slug))
    for p in lead[:2]:
        w('<p class="doc-lead">%s</p>' % inline(p))
    w('<div class="meta-row">')
    w('<span class="badge">수록 <b>%d</b></span>' % total)
    w('<span class="badge">정본 <b>%s-dictionary.md</b></span>' % esc(slug))
    w('<span class="badge">기준일 <b>%s</b></span>' % datetime.date.today().isoformat())
    w("</div>")
    # 2026-08-05: 허브를 폐지해 「프로젝트 개요」로 잇는다. 경로는 shell.INTRO에서 읽으므로
    # 파일명이 바뀌어도 따라온다 — 여기에 손으로 적으면 사이드바만 고쳐지고 이 줄이 남는다
    w('<nav class="toc"><a href="%s/core/base/dictionary.md">중앙 용어집(범용 용어)</a>'
      '<a href="%s">중앙 규칙 구조</a></nav>'
      % (shell.BLOB, shell.intro_href("central", args.output, slug)))
    w("</header>")

    w('<h2 id="terms">용어</h2>')
    w('<p>묶음은 열로 남기고 칩으로 좁힙니다. 정의를 새로 쓰는 자리가 아니므로 값이 필요하면 '
      '정본 열의 문서를 엽니다 — 두 곳에 적은 정의는 언젠가 갈라집니다.</p>')
    w(shell.table_tools("dict", "용어 · 요약 · 정본 검색",
                        [(g, "col", 0, g) for g, _ in groups]))
    w('<div class="tbl-scroll"><table id="dict"><thead><tr><th>묶음</th><th>용어</th>'
      '<th>한 줄 요약</th><th>정본</th></tr></thead><tbody>')
    for group, rows in groups:
        for term, summary, canon in rows:
            w("<tr><td>%s</td><td><b>%s</b></td><td>%s</td><td>%s</td></tr>"
              % (esc(group), inline(term), inline(summary), inline(canon)))
    w("</tbody></table></div>")

    w('<footer class="doc-footer">%s 용어집 · 정본 %s-dictionary.md · '
      'design-guide-master %s 스냅샷 · 파생 문서(직접 수정 금지)</footer>'
      % (esc(slug), esc(slug), esc(css_version(css))))
    w(shell.close_body())

    shell.save(args.output, "\n".join(o))
    print("saved %s | 묶음 %d · 용어 %d" % (args.output, len(groups), total))


if __name__ == "__main__":
    main()
