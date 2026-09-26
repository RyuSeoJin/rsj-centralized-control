# -*- coding: utf-8 -*-
"""read-gates.md (정본) -> AGENTS.md · CLAUDE.md §참조 규칙 (파생)

파이프라인에서의 위치
--------------------
  core/base/rules/read-gates.md   (정본 — 읽기 게이트 · 착수 보고 · 경로별 참조 규칙)
    │  이 스크립트 — 절을 이름으로 찾아 두 자리에 찍는다
    ├──▶ AGENTS.md           (루트 · 전량)   Codex가 세션마다 자동으로 읽는다
    └──▶ CLAUDE.md §참조 규칙 (마커 안쪽만)  Claude Code가 세션마다 자동으로 읽는다

  · 도구마다 규칙을 따로 적어 두면 한쪽만 고쳤을 때 어긋나는데, 어긋나도 에러가 나지 않는다.
    그래서 정본을 하나 두고 찍어 내고, 낡으면 regen.py --check가 잡는다
  · CLAUDE.md는 통째로 파생물이 아니다. 마커 사이의 표만 갈아 끼우고 나머지는 손대지 않는다
  · 절 제목이 곧 인터페이스다 — SEC_* 상수의 이름으로 찾는다

사용법:
    python gen_read_gates.py --repo-root . --target agents
    python gen_read_gates.py --repo-root . --target claude
    python gen_read_gates.py --repo-root . --target agents --check   # 쓰지 않고 다른지만 본다
"""
import argparse
import io
import os
import re
import sys

#: 정본에서 찾아 쓰는 절 이름. read-gates.md의 「이 파일을 고칠 때」가 이것을 안내한다
SEC_GATE = "읽기 게이트"
SEC_REPORT = "착수 보고"
SEC_PATHS = "경로별 참조 규칙"

MARK_OPEN = "<!-- gen:read-gates -->"
MARK_CLOSE = "<!-- /gen:read-gates -->"

HEAD = """# AGENTS.md

<!-- core/base/rules/read-gates.md에서 생성됩니다. 직접 고치지 않습니다. -->

이 저장소의 규칙 정본은 `CLAUDE.md`와 `core/base/`입니다. 이 파일은 규칙을 새로 정의하지 않고,
**작업 전에 무엇을 읽어야 하는지**만 모아 둔 게이트입니다. 내용이 어긋나면 `CLAUDE.md`가
정본입니다.
"""

FOOT = ("`core/base/rules/read-gates.md`에서 생성 · "
        "고칠 곳은 그 파일이고, 고친 뒤에는 `core/base/scripts/regen.py`를 돌립니다")


def repo_root(start=None):
    d = start or os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(d, "workspace.json")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return d
        d = p


def sections(text):
    """## 제목 -> 그 절의 본문. ### 은 절을 가르지 않으므로 그대로 딸려 온다"""
    out, name, buf = {}, None, []
    for line in text.split("\n"):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if name is not None:
                out[name] = "\n".join(buf).strip("\n")
            name, buf = m.group(1), []
            continue
        if name is not None:
            buf.append(line)
    if name is not None:
        out[name] = "\n".join(buf).strip("\n")
    return out


def need(secs, name, src):
    if name not in secs:
        sys.stderr.write("%s 에 「%s」 절이 없습니다 — 절 제목이 인터페이스입니다\n"
                         % (src, name))
        sys.exit(2)
    return secs[name]


def only_table(block):
    """설명 문단을 떼고 표만 남긴다 — CLAUDE.md 쪽은 표 아래 설명을 이미 갖고 있다"""
    return "\n".join(l for l in block.split("\n") if l.startswith("|"))


def trim_hr(block):
    """절 끝의 구분선을 뗀다 — 정본에서는 다음 절과의 경계지만, 여기서는 꼬리말과 겹친다"""
    lines = block.split("\n")
    while lines and lines[-1].strip() in ("", "---"):
        lines.pop()
    return "\n".join(lines)


def build_agents(secs):
    parts = [HEAD]
    for name in (SEC_GATE, SEC_REPORT, SEC_PATHS):
        parts.append("## %s\n\n%s\n\n---\n" % (name, trim_hr(secs[name])))
    parts.append("%s\n" % FOOT)
    return "\n".join(parts)


def build_claude(old, table):
    """마커 사이만 갈아 끼운다. 마커가 없으면 어디에 넣을지 정할 수 없으므로 멈춘다"""
    i = old.find(MARK_OPEN)
    j = old.find(MARK_CLOSE)
    if i < 0 or j < 0 or j < i:
        sys.stderr.write("CLAUDE.md 에 %s … %s 마커가 없습니다\n" % (MARK_OPEN, MARK_CLOSE))
        sys.exit(2)
    return old[:i] + MARK_OPEN + "\n" + table + "\n" + old[j:]


def write(path, text, check):
    old = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
    if check:
        if old == text:
            print("최신입니다 — %s" % path)
            return 0
        print("정본과 다릅니다 — %s" % path)
        return 1
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("%s (%d자)" % (path, len(text)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--target", choices=("agents", "claude"), required=True)
    ap.add_argument("--check", action="store_true",
                    help="쓰지 않고 정본과 다른지만 봅니다")
    args = ap.parse_args()
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    root = repo_root(os.path.abspath(args.repo_root) if args.repo_root else None)
    src = os.path.join(root, "core", "base", "rules", "read-gates.md")
    secs = sections(io.open(src, encoding="utf-8").read())
    for n in (SEC_GATE, SEC_REPORT, SEC_PATHS):
        need(secs, n, "core/base/rules/read-gates.md")

    if args.target == "agents":
        return write(os.path.join(root, "AGENTS.md"), build_agents(secs), args.check)
    p = os.path.join(root, "CLAUDE.md")
    old = io.open(p, encoding="utf-8").read()
    return write(p, build_claude(old, only_table(secs[SEC_PATHS])), args.check)


if __name__ == "__main__":
    sys.exit(main())
