# -*- coding: utf-8 -*-
"""모듈 확인과 켜기 — 무엇이 있고 무엇이 켜져 있는지 보고, 동의를 받은 뒤 켭니다

왜 도구인가
----------
  「이 기능은 어느 모듈에 있나」를 폴더를 뒤져 찾으면 매번 답이 달라집니다. 모듈마다
  `module.md`가 자기소개(언제 켜나·켜면 따라오는 것·전제)를 갖고 있고, 이 도구가 그것을
  모아 보여 줍니다. 판별 흐름의 정본은 rules/feature-request.md입니다.

켜는 것은 되돌리기 쉽지 않다
--------------------------
  모듈을 켜면 그 모듈의 규칙 **전부**가 그 프로젝트에 적용되고 폴더가 늘어납니다. 그래서
  이 도구는 **묻지 않습니다** — 동의를 받은 뒤에 실행하는 도구입니다(rules §3).

사용법
------
    python core/base/scripts/module.py list [슬러그]
    python core/base/scripts/module.py on {슬러그} {모듈}
    python core/base/scripts/module.py off {슬러그} {모듈}
"""
import argparse
import io
import json
import os
import re
import sys

#: 모듈을 켜면 프로젝트에 생기는 폴더. 없으면 만들 것이 없다는 뜻이다.
#: 정본은 각 모듈의 module.md이며, 여기 목록과 어긋나면 문서 쪽이 정본이다
MODULE_DIRS = {
    "automation": ("automation/tests", "automation/result"),
    "sut": ("sut", "spec/sut-design"),
}


def core_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def repo_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(d, "workspace.json")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return os.path.dirname(core_root())
        d = p


def modules():
    """core/modules/를 훑어 (이름, 한 줄 설명, 언제 켜나, 전제 이름, 전제 사유)를 모은다."""
    root = os.path.join(core_root(), "modules")
    out = []
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        md = os.path.join(root, name, "module.md")
        title, when, needs, why = "", "", "", ""
        if os.path.exists(md):
            lines = io.open(md, encoding="utf-8").read().split("\n")
            for i, l in enumerate(lines):
                if l.startswith("# ") and not title:
                    title = l[2:].split(" — ", 1)[-1].strip()
                if l.startswith("## 언제 켜나"):
                    raw = next((x.strip() for x in lines[i + 1:i + 4] if x.strip()), "")
                    when = raw.replace("**", "").strip()
                if l.startswith("## 전제 모듈"):
                    # 한 문단을 통째로 읽습니다 — 사유가 줄바꿈으로 이어지면 잘립니다
                    para = []
                    for x in lines[i + 1:]:
                        if not x.strip():
                            if para:
                                break
                            continue
                        para.append(x.strip())
                    raw = " ".join(para)
                    # 전제 절의 **첫 백틱**이 바로 위 모듈이다. 그 위는 도구가 따라간다
                    m = re.search(r"`([a-z][a-z0-9-]*)`", raw)
                    needs = m.group(1) if m else ""
                    # 백틱 뒤의 설명이 「왜 그 모듈이 필요한가」다
                    why = re.sub(r"^`[^`]*`\s*[-—]*\s*", "", raw).strip()
        out.append((name, title, when, needs, why))
    return out


def prereq_chain(name):
    """켜야 하는 순서대로 전제를 늘어놓는다 — 맨 아래 것이 먼저다.

    한 단만 보면 「먼저 켜세요」를 여러 번 만나야 사슬의 길이를 알 수 있습니다. 한 번에
    끝까지 보여 주려고 따라 올라갑니다.
    """
    need_of = dict((m[0], m[3]) for m in modules())
    chain, seen = [], set()
    cur = need_of.get(name, "")
    while cur and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        cur = need_of.get(cur, "")
    chain.reverse()          # 아래에서부터 켠다
    return chain


def state_path(root, slug):
    return os.path.join(root, "projects", slug, "%s-modules.json" % slug)


def read_state(root, slug):
    try:
        with io.open(state_path(root, slug), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"on": []}


def write_state(root, slug, st):
    with io.open(state_path(root, slug), "w", encoding="utf-8", newline="") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
        f.write("\n")


def cmd_list(root, slug):
    on = set(read_state(root, slug)["on"]) if slug else set()
    for name, title, when, needs, why in modules():
        mark = "●" if name in on else "○"
        if not slug:
            mark = " "
        print("%s %-6s %s" % (mark, name, title))
        if when:
            print("       언제 켜나 — %s" % when)
        if needs:
            print("       전제 — `%s` %s" % (needs, why))
    if slug:
        print("\n● 켜짐 / ○ 꺼짐 — 정본은 %s" % os.path.relpath(state_path(root, slug), root))
    return 0


def cmd_on(root, slug, name):
    names = [m[0] for m in modules()]
    if name not in names:
        sys.exit("그런 모듈이 없습니다: %s (있는 것: %s)" % (name, ", ".join(names)))
    proj = os.path.join(root, "projects", slug)
    if not os.path.isdir(proj):
        sys.exit("그런 프로젝트가 없습니다: projects/%s" % slug)

    st = read_state(root, slug)
    if name in st["on"]:
        print("이미 켜져 있습니다: %s" % name)
        return 0

    # 전제 모듈 — 꺼진 것이 있으면 멈춥니다. 자동으로 켜지 않는 이유는 「무엇이 켜지는지」를
    # 유저가 알고 동의해야 하기 때문입니다(rules/feature-request.md §3). 대신 사슬 전체를
    # 한 번에 보여 줍니다 — 한 단씩 알려 주면 몇 번을 더 쳐야 하는지 모른 채 막힙니다
    chain = prereq_chain(name)
    missing = [m for m in chain if m not in st["on"]]
    if missing:
        info = dict((m[0], (m[1], m[4])) for m in modules())
        # 사슬 전체를 보입니다 — 이미 켠 것까지 함께 보여야 어디까지 왔는지 압니다
        print("`%s` 모듈을 활성화하려면 먼저 켜야 하는 모듈이 존재합니다" % name)
        print("")
        for i, m in enumerate(chain, 1):
            title = info.get(m, ("", ""))[0]
            # 「왜 필요한가」는 그 모듈을 전제로 삼는 쪽이 압니다 — 사슬에서 한 칸 위입니다
            requirer = chain[i] if i < len(chain) else name
            why = info.get(requirer, ("", ""))[1]
            mark = "● 활성" if m in st["on"] else "○ 비활성"
            print("  %d. %-12s %s" % (i, m, mark))
            if title:
                print("     %s" % title)
            if why:
                print("     → `%s`에 필요합니다 — %s" % (requirer, why))
            print("")
        print("모듈은 저절로 활성화되지 않습니다. 필요한 모듈은 직접 활성화해주세요.")
        print("")
        for m in missing + [name]:
            print("  python core/base/scripts/module.py on %s %s" % (slug, m))
        return 1

    made = []
    for d in MODULE_DIRS.get(name, ()):
        p = os.path.join(proj, *d.split("/"))
        if not os.path.isdir(p):
            os.makedirs(p)
            io.open(os.path.join(p, ".gitkeep"), "w", encoding="utf-8").close()
            made.append(d + "/")

    st["on"] = sorted(st["on"] + [name])
    write_state(root, slug, st)
    print("켰습니다: %s" % name)
    for m in made:
        print("   만듦 " + m)
    print("\nchange-log에 **왜 켰는지** 한 줄 남기세요 — 파일은 무엇이 켜졌는지만 압니다.")
    return 0


def dependents(name):
    """이 모듈을 (한 단이든 여러 단이든) 전제로 삼는 모듈들."""
    return [m[0] for m in modules() if name in prereq_chain(m[0])]


def cmd_off(root, slug, name):
    st = read_state(root, slug)
    if name not in st["on"]:
        print("켜져 있지 않습니다: %s" % name)
        return 0

    # 이것을 전제로 삼는 모듈이 켜져 있으면 멈춥니다 — 끄면 그쪽이 발밑을 잃습니다
    blocked = [m for m in dependents(name) if m in st["on"]]
    if blocked:
        info = dict((m[0], m[1]) for m in modules())
        print("`%s` 모듈을 전제로 삼는 모듈이 켜져 있어 끌 수 없습니다" % name)
        print("")
        for i, m in enumerate(blocked, 1):
            print("  %d. %-12s ● 활성" % (i, m))
            print("     %s" % info.get(m, ""))
            print("")
        print("먼저 위 모듈을 끈 뒤에 다시 시도해 주세요.")
        print("")
        for m in blocked + [name]:
            print("  python core/base/scripts/module.py off %s %s" % (slug, m))
        return 1
    st["on"] = [m for m in st["on"] if m != name]
    write_state(root, slug, st)
    # 폴더는 지우지 않는다 — 그 안에 작업물이 들어 있을 수 있다
    print("껐습니다: %s\n폴더와 파일은 그대로 둡니다 — 지우는 것은 사람이 판단합니다." % name)
    return 0


def main():
    # 한글 출력이 콘솔 기본 인코딩으로 나가면, 다른 도구가 받아 읽을 때 깨집니다.
    # 오류는 stderr로 나가므로 둘 다 맞춥니다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("slug", nargs="?")
    p = sub.add_parser("on"); p.add_argument("slug"); p.add_argument("module")
    p = sub.add_parser("off"); p.add_argument("slug"); p.add_argument("module")
    args = ap.parse_args()
    root = repo_root()
    if args.cmd == "list":
        return cmd_list(root, args.slug)
    if args.cmd == "on":
        return cmd_on(root, args.slug, args.module)
    return cmd_off(root, args.slug, args.module)


if __name__ == "__main__":
    sys.exit(main())
