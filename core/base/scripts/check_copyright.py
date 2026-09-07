# -*- coding: utf-8 -*-
"""저작권 게이트 — 사람이 봐야 할 커밋인지 가릅니다

왜 도구인가
----------
  기계는 저작권을 판단하지 못합니다. 이 그림이 남의 스크린샷인지, 이 문장이 원문 인용인지,
  이 단어가 상표인지는 볼 수 없습니다. 그래서 이 도구는 판단하지 않고 **조건만 가릅니다** —
  사람을 불러야 하는 커밋인가, 조용히 지나가도 되는 커밋인가.

  게이트를 사람 판단에만 맡기면 **안 걸린 커밋에서 아무 말도 나오지 않아** 게이트를 돌았는지
  건너뛴 건지 구분이 안 됩니다. 통과도 한 줄로 남기는 이유입니다.

  커밋에 한번 들어가면 파일을 지워도 이력에는 남습니다. push 시점에 잡으면 이력을 고쳐야
  하지만, 커밋 시점에 잡으면 스테이징에서 빼기만 하면 됩니다 (rules/git-rules.md §5).

무엇을 보나
----------
  기본은 **커밋에 들어갈 후보 전부**입니다 — 스테이징된 것, 아직 스테이징 안 한 수정,
  그리고 추적되지 않은 새 파일. 게이트가 도는 자리가 커밋을 제안하기 **전**이라
  대개 아직 `git add` 전이고, 스테이징만 보면 매번 빈손으로 돌게 됩니다 (§4-0).

무엇을 잡나
----------
  ① 이진 파일        git이 이진으로 판정한 것. 확장자를 .md로 바꿔 넣어도 여기서 걸립니다
  ② 미디어 확장자    svg처럼 이진이 아닌 것까지 덮습니다
  ③ 조사 자료 자리   analysis/ · reference/ — 남의 것이 사는 자리라 확률이 가장 높습니다
  ④ 이미지 문법      새로 들어온 줄의 마크다운 이미지 · img 태그 · base64 · CSS에 박은 데이터.
                     파일이 아니라 링크나 문자열로 들어오는 경우입니다

  못 잡는 것이 하나 있습니다 — **원문 텍스트를 그대로 붙여 넣는 것**입니다. 이미지도
  이진도 아니라 신호가 없습니다. 규칙대로 analysis/에 두면 ③이 잡지만, 곧장 spec/에
  붙이면 조용합니다. 그 자리는 도구가 아니라 절차가 덮습니다 (doc-playbook.md).

무엇을 건너뛰나 — EXEMPT
----------
  자작이 확정된 자리입니다. 다만 **이미 있는 파일을 고칠 때만** 건너뜁니다. 구조도를 고칠
  때마다 묻는 것은 형식이 되지만, 그 자리에 **새 파일이 들어오는 것은 새 저작물이 생기는
  일**이라 한 번은 봅니다. 면제 자리에 남의 그림을 새로 넣어 지나가는 길을 막습니다.

  이름을 바꿔 자리를 옮긴 것도 면제되지 않습니다 — 이름 추적을 꺼 두어 옮겨 온 파일이
  새 파일로 잡힙니다.

사용법
------
    python core/base/scripts/check_copyright.py                 커밋 전 — 들어갈 후보 전부를 본다
    python core/base/scripts/check_copyright.py --range A..B    push 전 — 올라갈 커밋 전체를 본다

  걸릴 것이 없으면 exit 0, 있으면 목록과 체크리스트를 내고 exit 1.
"""
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TAB = chr(9)

#: 미디어로 보는 확장자. 이진 판정(①)이 대부분을 덮지만 svg는 텍스트라 여기서 잡는다
MEDIA_EXT = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".ico", ".svg",
    ".mp4", ".mov", ".webm", ".avi", ".mp3", ".wav",
    ".pdf", ".psd", ".ai", ".sketch", ".fig",
    ".zip", ".rar", ".7z",
)

#: 조사 자료가 사는 자리. 경로 이름이 중립적이라 중앙 규칙에 적어도 프로젝트가 드러나지 않는다
SURVEY_DIRS = ("analysis", "reference")

#: 면제 — 자작이 확정된 자리. (경로, 사유)로 두어 왜 면제인지가 함께 읽히게 한다
EXEMPT = (
    ("structure.svg", "이 저장소의 구조도 정본"),
    ("core/base/diagrams/", "설명 그림의 정본"),
    ("core/base/design-guide/", "스타일 정본"),
    ("core/base/design-template/", "문서 서식"),
)

#: 이미지가 파일이 아니라 문법으로 들어오는 통로
IMG_SYNTAX = (
    (re.compile(r"!\["), "마크다운 이미지"),
    (re.compile(r"<img[\s>]", re.I), "img 태그"),
    (re.compile(r"data:image/", re.I), "base64 이미지"),
    (re.compile(r"url\(\s*[\"']?data:", re.I), "CSS에 박은 데이터"),
)

#: 문법(④)을 훑을 텍스트 확장자
TEXT_EXT = (".md", ".html", ".htm", ".css", ".js", ".json", ".yml", ".yaml", ".txt", ".py")

CHECKLIST = (
    "대상 서비스의 스크린샷 포함 여부",
    "원문 텍스트 인용 포함 여부 (최소 범위 · 출처 표기)",
    "상표 · 로고 노출 여부",
    "비공개 자료(유출본 · 내부 문서) 포함 여부 — 발견 시 커밋 금지",
)


def git(args):
    """git을 돌려 표준출력을 돌려줍니다. 실패하면 None입니다."""
    try:
        p = subprocess.run(["git"] + args, capture_output=True)
    except FileNotFoundError:
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def exempt_reason(path, status):
    """면제 자리의 **수정**이면 사유를, 아니면 None을 돌려줍니다.

    새로 들어온 파일은 면제하지 않습니다 — 자작이 확정된 자리라는 근거는 이미 거기
    있는 파일에 대한 것이고, 새 파일은 아직 아무도 보지 않았기 때문입니다.
    """
    if status != "M":
        return None
    for pat, why in EXEMPT:
        if path == pat or (pat.endswith("/") and path.startswith(pat)):
            return why
    return None


def looks_binary(path):
    """추적되지 않은 파일이 이진인지 봅니다 — git과 같이 NUL 바이트로 가릅니다."""
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(8000)
    except OSError:
        return False


def has_head():
    """커밋이 하나라도 있는지 봅니다. 첫 커밋 전에는 HEAD가 없습니다."""
    return git(["rev-parse", "--verify", "HEAD"]) is not None


def diff_base(rng):
    """diff에 넘길 기준을 정합니다."""
    if rng:
        return [rng]
    return ["HEAD"] if has_head() else ["--cached"]


def diff_rows(base):
    """git이 아는 변경을 [(경로, 이진인가, 상태)]로 돌려줍니다."""
    args = ["--no-renames", "--diff-filter=ACM"] + base
    num = git(["diff", "--numstat"] + args)
    nam = git(["diff", "--name-status"] + args)
    if num is None or nam is None:
        return None
    status = {}
    for line in nam.splitlines():
        parts = line.split(TAB)
        if len(parts) >= 2:
            status[parts[1].strip()] = parts[0].strip()[:1]
    rows = []
    for line in num.splitlines():
        parts = line.split(TAB)
        if len(parts) < 3:
            continue
        path = parts[2].strip()
        rows.append((path, parts[0] == "-", status.get(path, "A")))
    return rows


def collect(rng):
    """볼 대상을 모읍니다. 범위가 없으면 커밋에 들어갈 후보 전부입니다."""
    rows = diff_rows(diff_base(rng))
    if rows is None or rng:
        return rows
    seen = set(p for p, _, _ in rows)
    for path in (git(["ls-files", "--others", "--exclude-standard"]) or "").splitlines():
        path = path.strip()
        if path and path not in seen:
            rows.append((path, looks_binary(path), "A"))
    return rows


def new_lines(rng, path, status):
    """이번에 새로 들어온 줄만 돌려줍니다."""
    if not rng and status == "A" and git(["ls-files", "--error-unmatch", path]) is None:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return f.read().splitlines()
        except OSError:
            return []
    out = git(["diff", "-U0", "--no-renames"] + diff_base(rng) + ["--", path]) or ""
    return [ln[1:] for ln in out.splitlines()
            if ln.startswith("+") and not ln.startswith("+++")]


def scan(rows, rng):
    """조건에 걸린 것을 사유별로 모읍니다."""
    hits, skipped = {}, []

    def hit(why, path, note=""):
        hits.setdefault(why, []).append((path, note))

    for path, is_binary, status in rows:
        why = exempt_reason(path, status)
        if why:
            skipped.append((path, why))
            continue
        ext = os.path.splitext(path)[1].lower()
        if is_binary:
            hit("git이 이진으로 판정한 파일입니다", path, "확장자는 %s" % (ext or "없음"))
        elif ext in MEDIA_EXT:
            hit("미디어 파일이 들어왔습니다", path)
        if any(s in SURVEY_DIRS for s in path.split("/")[:-1]):
            hit("조사 자료 자리에 새 파일이 있습니다", path)
        if not is_binary and ext in TEXT_EXT:
            found = []
            for line in new_lines(rng, path, status):
                for pat, label in IMG_SYNTAX:
                    if pat.search(line) and label not in found:
                        found.append(label)
            if found:
                hit("문서에 이미지가 문법으로 들어왔습니다", path, " · ".join(found))
    return hits, skipped


def main():
    argv = sys.argv[1:]
    rng = None
    if argv:
        if argv[0] != "--range" or len(argv) != 2:
            sys.exit("쓰는 법: check_copyright.py [--range A..B]")
        rng = argv[1]

    if git(["rev-parse", "--git-dir"]) is None:
        print("저작권 게이트 — git 저장소가 아니라 볼 것이 없습니다")
        return 0

    rows = collect(rng)
    if rows is None:
        sys.exit("그 범위를 읽지 못했습니다: %s" % rng)

    hits, skipped = scan(rows, rng)
    where = rng if rng else "커밋 후보"
    if not hits:
        tail = " · 면제 %d개" % len(skipped) if skipped else ""
        print("저작권 게이트 — 볼 것이 없습니다 (%s %d개 파일%s)" % (where, len(rows), tail))
        return 0

    n = sum(len(v) for v in hits.values())
    print("저작권 게이트 — 사람이 봐야 할 것이 %d건입니다 (%s)\n" % (n, where))
    for why in hits:
        print("  " + why)
        for path, note in hits[why]:
            print("    %s%s" % (path, ("  — " + note) if note else ""))
    print("\n아래 넷을 확인하고, 하나라도 걸리면 커밋을 보류하고 사용자에게 보고합니다.")
    for item in CHECKLIST:
        print("  [ ] " + item)
    if skipped:
        print("\n건너뛴 자리 %d개 — 자작이 확정된 곳입니다" % len(skipped))
        for path, why in skipped:
            print("    %s  — %s" % (path, why))
    return 1


if __name__ == "__main__":
    sys.exit(main())
