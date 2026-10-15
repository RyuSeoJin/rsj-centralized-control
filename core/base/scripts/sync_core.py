# -*- coding: utf-8 -*-
"""중앙 저장소의 core/를 이 저장소로 받아 옵니다 — 이 저장소에서 손댄 파일이 있으면 멈춥니다

왜 도구인가
----------
  core/를 손으로 복사하면 세 가지가 조용히 틀어집니다. 중앙에서 지운 파일이 남고, 이 저장소에서
  고친 파일이 덮여 사라지고, 무엇을 언제 받았는지 기록이 없습니다. 이 도구는 받을 때의 파일별
  해시를 core/.source.json에 남겨 두고, 다음에 받을 때 그 해시로 「받은 뒤 손댄 파일」을 가립니다
  (rules/central-sync.md).

사용법
------
  {중앙 저장소}는 로컬 폴더 또는 git 주소(https://… · git@…)입니다. 주소를 주면 임시 폴더로
  얕게 clone해서 받고 끝나면 지웁니다. --ref로 태그 · 브랜치를 고를 수 있습니다(주소일 때만).

    python core/base/scripts/sync_core.py --from {중앙 저장소} --check    무엇이 바뀌는지만 본다
    python core/base/scripts/sync_core.py --from {주소} --ref core-v2.0.0 그 태그로 받는다
    python core/base/scripts/sync_core.py --from {중앙 저장소}            받는다
    python core/base/scripts/sync_core.py --from {중앙 저장소} --discard-local
                                                                          손댄 파일을 버리고 받는다
    python core/base/scripts/sync_core.py --local                         받은 뒤 손댄 파일만 본다
    python core/base/scripts/sync_core.py --check                         지난번 받은 자리에서 본다
                                                                          (작업 시작 때의 확인)
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workspace  # noqa: E402

SKIP_DIRS = ("__pycache__", ".git", "node_modules")
SOURCE = ".source.json"


def lf(data):
    """글 파일이면 줄바꿈을 LF로 맞춥니다. NUL 바이트가 있으면 이진 파일로 보고 그대로 둡니다.

    git의 core.autocrlf 설정이나 편집기에 따라 같은 내용이 CRLF로 체크아웃되는 일이 흔합니다.
    줄바꿈만 다른 파일을 「손댄 파일」로 잡으면 받기가 까닭 없이 멈춥니다.
    """
    return data if b"\0" in data else data.replace(b"\r\n", b"\n")


def files(core, raw=False):
    """core/ 아래 파일의 상대 경로 → sha256(줄바꿈을 LF로 맞춘 내용). 받은 기록 파일과 캐시는 뺍니다.

    raw=True면 맞추지 않은 바이트의 해시입니다 — 줄바꿈을 맞추기 전에 쓴 받은 기록과 견줄 때 씁니다.
    """
    out = {}
    for cur, dirs, names in os.walk(core):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            if n == SOURCE or n.endswith(".pyc"):
                continue
            p = os.path.join(cur, n)
            rel = os.path.relpath(p, core).replace(os.sep, "/")
            with open(p, "rb") as f:
                data = f.read()
            out[rel] = hashlib.sha256(data if raw else lf(data)).hexdigest()
    return out


def read_source(core):
    try:
        with io.open(os.path.join(core, SOURCE), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def local_changes(core, src):
    """받은 뒤 이 저장소에서 바뀐 파일 — (갈래, 경로) 목록."""
    before = src.get("files", {})
    if not before:
        return []
    now = files(core)
    # 옛 받은 기록은 맞추지 않은 바이트의 해시라, 그 해시와 같아도 손대지 않은 것으로 봅니다
    old = files(core, raw=True)
    out = [("수정", p) for p in sorted(now)
           if p in before and before[p] not in (now[p], old[p])]
    out += [("추가", p) for p in sorted(now) if p not in before]
    out += [("삭제", p) for p in sorted(before) if p not in now]
    return out


def git_head(repo):
    try:
        r = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True)
        head = r.stdout.strip() if r.returncode == 0 else None
        r = subprocess.run(["git", "-C", repo, "status", "--porcelain", "--", "core"],
                           capture_output=True, text=True)
        dirty = bool(r.stdout.strip()) if r.returncode == 0 else None
        r = subprocess.run(["git", "-C", repo, "describe", "--tags", "--exact-match"],
                           capture_output=True, text=True)
        tag = r.stdout.strip() if r.returncode == 0 else None
        return head, dirty, tag
    except OSError:
        return None, None, None


ENTRY = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?\s+—\s+(.+)$")


def entries(central):
    """중앙 이력 항목 — (날짜, 시각 또는 None, 제목 줄) 목록. 파일 순서(최신이 위)대로입니다."""
    p = os.path.join(central, "center-change-log.md")
    if not os.path.exists(p):
        return []
    out = []
    for line in io.open(p, encoding="utf-8").read().split("\n"):
        m = ENTRY.match(line.strip())
        if m:
            out.append((m.group(1), m.group(2), line.strip()[4:]))
    return out


def new_entries(central, src):
    """지난번 받은 뒤 새로 생긴 중앙 이력 항목 제목.

    받은 기록에 그때 맨 위 항목(last_entry)이 있으면 그 위의 항목만 고릅니다 — 중앙에서 항목을
    적은 시각과 push한 시각이 어긋나도 빠뜨리지 않습니다. 없거나 찾지 못하면 받은 시각과 견줍니다.
    시각이 있는 항목은 시각까지, 날짜만 있는 옛 항목은 날짜로 견줍니다. 같은 분이면 새 항목으로
    봅니다 — 처리한 항목을 한 번 더 보이는 편이 새 항목을 놓치는 것보다 낫기 때문입니다.
    """
    items = entries(central)
    last = src.get("last_entry")
    titles = [t for _d, _t, t in items]
    if last in titles:
        return titles[:titles.index(last)]
    since = src.get("synced")
    if not since:
        return titles
    return [title for d, t, title in items
            if (d + " " + t >= since[:16] if t else d >= since[:10])]


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="central", help="중앙 저장소 — 로컬 폴더 또는 git 주소")
    ap.add_argument("--ref", help="주소로 받을 때 태그 · 브랜치 (생략하면 기본 브랜치)")
    ap.add_argument("--check", action="store_true", help="받지 않고 바뀔 것만 봅니다")
    ap.add_argument("--discard-local", action="store_true",
                    help="이 저장소에서 손댄 core/ 파일을 버리고 받습니다 (사용자 확인 뒤에만)")
    ap.add_argument("--local", action="store_true", help="받은 뒤 손댄 파일만 봅니다")
    ap.add_argument("--repo-root", default=None)
    args = ap.parse_args()

    root = os.path.abspath(args.repo_root) if args.repo_root else workspace.repo_root()
    core = os.path.join(root, "core")
    src = read_source(core)

    changed = local_changes(core, src) if os.path.isdir(core) else []
    if args.local:
        if not src:
            print("받은 기록(core/%s)이 없습니다." % SOURCE)
            return 1
        if not changed:
            print("받은 뒤 손댄 core/ 파일이 없습니다.")
            return 0
        print("받은 뒤 손댄 core/ 파일 %d개 — 중앙에 되돌려 보낼 것입니다 (rules/central-sync.md §3)"
              % len(changed))
        for kind, p in changed:
            print("   %s  core/%s" % (kind, p))
        return 1

    if not args.central:
        # 생략하면 지난번 받은 자리에서 봅니다 — 작업 시작 때의 확인을 명령 하나로 하기 위함
        args.central = src.get("source")
        if not args.central:
            sys.exit("--from {중앙 저장소 경로 또는 주소}가 필요합니다 — 받은 기록에 자리가 없습니다")
        if not is_url(args.central) and not os.path.isdir(args.central):
            sys.exit("받은 기록의 중앙 저장소 폴더가 이 컴퓨터에 없습니다: %s\n"
                     "--from {중앙 저장소 경로 또는 주소}로 다시 실행합니다" % args.central)
    tmp = None
    if is_url(args.central):
        tmp = tempfile.mkdtemp(prefix="central-")
        cmd = ["git", "clone", "--quiet", "--depth", "1"]
        if args.ref:
            cmd += ["--branch", args.ref]
        r = subprocess.run(cmd + [args.central, tmp], capture_output=True, text=True)
        if r.returncode:
            shutil.rmtree(tmp, ignore_errors=True)
            sys.exit("중앙 저장소를 받지 못했습니다: %s\n%s" % (args.central, r.stderr.strip()))
        central = tmp
    elif args.ref:
        sys.exit("--ref는 주소로 받을 때만 씁니다 — 로컬 폴더는 그 폴더에서 원하는 커밋으로 옮긴 뒤 받습니다")
    else:
        central = os.path.abspath(args.central)
    try:
        return receive(args, root, core, src, changed, central, args.central if tmp else None)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def is_url(value):
    return value.startswith(("https://", "http://", "git@", "ssh://", "file://")) or value.endswith(".git")


def receive(args, root, core, src, changed, central, url):
    c_core = os.path.join(central, "core")
    if not os.path.isdir(os.path.join(c_core, "base")):
        sys.exit("중앙 저장소가 아닙니다 — core/base/가 없습니다: %s" % central)
    if os.path.abspath(c_core) == os.path.abspath(core):
        sys.exit("받는 쪽과 중앙 저장소가 같은 자리입니다")

    theirs = files(c_core)
    mine = files(core) if os.path.isdir(core) else {}
    add = sorted(p for p in theirs if p not in mine)
    mod = sorted(p for p in theirs if p in mine and theirs[p] != mine[p])
    rem = sorted(p for p in mine if p not in theirs)
    head, dirty, tag = git_head(central)

    print("중앙 저장소  %s" % (url or central))
    print("   커밋 %s%s%s" % (head or "(없음)", " · 태그 " + tag if tag else "",
                           " · 커밋 안 된 변경 있음" if dirty else ""))
    print("받은 기록    %s" % (src.get("synced") or "(처음 받습니다)"))
    print("더함 %d · 바뀜 %d · 지움 %d" % (len(add), len(mod), len(rem)))
    for label, items in (("더함", add), ("바뀜", mod), ("지움", rem)):
        for p in items[:200]:
            print("   %s  core/%s" % (label, p))
    fresh = new_entries(central, src)
    if fresh:
        print("\n새 중앙 이력 항목 — 태그를 처리합니다 (rules/change-log-writing.md §6)")
        for e in fresh:
            print("   " + e)

    if changed and not args.discard_local:
        print("\n받은 뒤 이 저장소에서 손댄 core/ 파일이 있어 멈춥니다 — 덮으면 사라집니다.")
        for kind, p in changed:
            print("   %s  core/%s" % (kind, p))
        print("중앙에 먼저 되돌려 보내거나(rules/central-sync.md §3), 버려도 된다는 확인을 받은 뒤 "
              "--discard-local로 다시 실행합니다.")
        return 1
    if args.check:
        return 0

    # 받기 — 중앙에 없는 파일은 지우고, 있는 파일은 덮어씁니다
    for p in rem:
        os.remove(os.path.join(core, *p.split("/")))
    for cur, dirs, _n in os.walk(core, topdown=False):
        if not os.listdir(cur) and cur != core:
            os.rmdir(cur)
    for p in add + mod:
        dst = os.path.join(core, *p.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        src_path = os.path.join(c_core, *p.split("/"))
        with open(src_path, "rb") as f:
            data = f.read()
        with open(dst, "wb") as f:
            f.write(lf(data))
        shutil.copymode(src_path, dst)
    record = {
        "source": url or central.replace(os.sep, "/"),
        "commit": head,
        "tag": tag,
        "dirty": dirty,
        "synced": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last_entry": next((t for _d, _t, t in entries(central)), None),
        "files": files(core),
    }
    with io.open(os.path.join(core, SOURCE), "w", encoding="utf-8", newline="\n") as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\n받았습니다. 다음 — regen.py · check_rules.py를 돌리고 repo-change-log.md에 기록합니다.")
    if dirty:
        print("⚠ 중앙 저장소에 커밋 안 된 변경이 있었습니다 — 기록의 커밋은 그 변경을 담지 않습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
