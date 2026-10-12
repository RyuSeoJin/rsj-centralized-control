# -*- coding: utf-8 -*-
"""모듈 지도 생성기 — 하는 일에서 켤 모듈을 찾는 안내를 모듈 폴더에서 찍어 냅니다

파이프라인에서의 위치
--------------------
  core/modules/groups.json          (정본 — 분야 · 표시 순서 · 분야별 질문)
  core/modules/*/module.json        (정본 — 분야 · 적용 범위 · 함께 쓰는 짝 · 고르는 짝)
  core/modules/*/module.md          (정본 — 한 줄 설명 · 언제 켜나 · 전제 모듈)
    │  이 스크립트 — module.py의 읽기 함수를 그대로 씁니다
    └──▶ core/modules/module-map.md (파생 — 손으로 고치지 않습니다)

  · base는 모듈 이름을 모릅니다. 폴더를 훑기만 하므로 모듈이 늘거나 줄어도 이 파일은 안 바뀝니다.
  · 출력은 결정적입니다 — 순서를 고정하고 날짜 · 시각을 넣지 않습니다. 그래야 같은 정본에서
    늘 같은 파일이 나와 regen.py --check가 흔들리지 않습니다.

사용법
------
    python core/base/scripts/gen_module_map.py              지도를 다시 씁니다
    python core/base/scripts/gen_module_map.py --check      쓰지 않고 다른지만 봅니다
    python core/base/scripts/gen_module_map.py --core 경로  다른 core 폴더를 봅니다(시험용)
"""
import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import module as modlib  # noqa: E402

CMD = "python core/base/scripts/gen_module_map.py"

SCOPE_LABEL = {"workspace": "워크스페이스", "host": "호스트"}


def cell(text):
    """표 칸에 넣을 수 있게 줄바꿈과 세로선을 다듬습니다."""
    return " ".join((text or "").split()).replace("|", "\\|") or "—"


def collect(core=None):
    """지도에 필요한 것을 한 번에 모읍니다 — 모듈마다 같은 파일을 여러 번 읽지 않도록."""
    groups = modlib.grouped(core)
    order = [m[0] for _g, mods in groups for m in mods]
    info = {}
    for g, mods in groups:
        for name, title, when, needs, why in mods:
            info[name] = {
                "title": title, "when": when, "needs": needs, "why": why,
                "group": g["label"],
                "scope": modlib.module_scope(name, core),
                "chain": modlib.prereq_chain(name, core),
                "pairs": modlib.pairs(name, core),
                "instead": modlib.instead(name, core),
            }
    return groups, order, info


def pair_rows(order, info, key):
    """짝 목록을 한 쌍에 한 번만 냅니다.

    [(앞 모듈, 뒤 모듈, 앞이 적은 이유, 뒤가 적은 이유), ...] — 앞 모듈은 지도 순서에서
    먼저 나오는 쪽입니다. 한쪽만 적었으면 다른 쪽 이유는 빈 문자열입니다.
    """
    pos = dict((n, i) for i, n in enumerate(order))
    rows = {}
    for name in order:
        for other, why in info[name][key]:
            if other == name:
                continue
            a, b = sorted((name, other), key=lambda n: (pos.get(n, len(order)), n))
            row = rows.setdefault((a, b), {"a": "", "b": ""})
            side = "a" if name == a else "b"
            if why and not row[side]:
                row[side] = why
    out = [(a, b, r["a"], r["b"]) for (a, b), r in rows.items()]
    out.sort(key=lambda r: (pos.get(r[0], len(order)), pos.get(r[1], len(order)), r[0], r[1]))
    return out


def chain_text(name, chain):
    """`sut` ← `automation` ← `tc` — 왼쪽이 이 모듈, 오른쪽으로 갈수록 먼저 켜는 것입니다."""
    return " ← ".join("`%s`" % n for n in [name] + list(reversed(chain)))


def render(core=None):
    groups, order, info = collect(core)
    L = []
    L.append("# 모듈 지도 — 하는 일에서 켤 모듈을 찾습니다")
    L.append("")
    L.append("> 이 파일은 생성물입니다. 손으로 고치지 않습니다. 정본은 `groups.json`과 각 모듈의")
    L.append("> `module.json` · `module.md`이며, 고친 뒤 `%s`(또는 `regen.py`)로 다시 만듭니다." % CMD)
    L.append("")
    L.append("모듈이 많아 목록만으로는 고르기 어렵습니다. 이 지도는 **하는 일**에서 출발해 켤 모듈에")
    L.append("닿게 합니다. 모듈 하나의 자세한 내용은 그 모듈의 `module.md`에 있습니다. 켜져 있는지는")
    L.append("`python core/base/scripts/module.py list {프로젝트}`로 봅니다.")
    L.append("")

    # 1. 사다리
    L.append("## 1. 어떤 일을 하나요?")
    L.append("")
    L.append("분야마다 질문 하나가 있습니다. 「예」이면 그 아래 모듈의 「언제 켜나」를 읽고 고릅니다.")
    L.append("전제 사슬은 왼쪽이 그 모듈이고 오른쪽 끝이 가장 먼저 켜는 모듈입니다.")
    L.append("")
    if not groups:
        L.append("아직 모듈이 없습니다.")
        L.append("")
    for g, mods in groups:
        head = g["label"]
        if g.get("ask"):
            head += " — " + g["ask"]
        L.append("### " + head)
        L.append("")
        for m in mods:
            name = m[0]
            it = info[name]
            line = "- `%s`" % name
            if it["scope"] in SCOPE_LABEL:
                line += " (%s)" % SCOPE_LABEL[it["scope"]]
            if it["title"]:
                line += " — " + it["title"]
            L.append(line)
            if it["when"]:
                L.append("  - 언제 켜나: " + " ".join(it["when"].split()))
            if it["chain"]:
                L.append("  - 전제 사슬: " + chain_text(name, it["chain"]))
        L.append("")

    # 2. 적용 범위
    by_scope = {"workspace": [], "host": []}
    for name in order:
        if info[name]["scope"] in by_scope:
            by_scope[info[name]["scope"]].append(name)
    L.append("## 2. 적용 범위")
    L.append("")
    L.append("| 범위 | 켜는 자리 | 모듈 |")
    L.append("|---|---|---|")
    L.append("| 프로젝트 | `module.py on {프로젝트} {모듈}` — 그 프로젝트의 `{폴더}-modules.json`에 남습니다 "
             "| 아래 둘에 들지 않는 모든 모듈 |")
    L.append("| 워크스페이스 | `workspace.json`의 `modules` — 저장소 전체에 켜집니다 | %s |"
             % (" · ".join("`%s`" % n for n in by_scope["workspace"]) or "—"))
    L.append("| 호스트 | 프로젝트에 켜지 않습니다 — 이 컴퓨터의 환경을 다룰 때만 읽습니다 | %s |"
             % (" · ".join("`%s`" % n for n in by_scope["host"]) or "—"))
    L.append("")

    # 3. 함께 쓰는 모듈
    L.append("## 3. 함께 쓰는 모듈")
    L.append("")
    rows = pair_rows(order, info, "pairs")
    if rows:
        L.append("전제는 아니지만 함께 켜면 더 잘 맞는 짝입니다. 한쪽을 켰다면 다른 쪽도 살펴봅니다.")
        L.append("")
        L.append("| 모듈 | 함께 쓰는 모듈 | 이유 |")
        L.append("|---|---|---|")
        for a, b, wa, wb in rows:
            why = " / ".join(w for w in dict.fromkeys([wa, wb]) if w)
            L.append("| `%s` | `%s` | %s |" % (a, b, cell(why)))
    else:
        L.append("아직 적힌 짝이 없습니다.")
    L.append("")

    # 4. 둘 중 하나
    L.append("## 4. 둘 중 하나를 고르는 모듈")
    L.append("")
    rows = pair_rows(order, info, "instead")
    if rows:
        L.append("하는 일이 겹쳐 보통 하나만 켜는 짝입니다. 어느 쪽이 맞는지는 아래 기준으로 가립니다.")
        L.append("")
        L.append("| 이 모듈 | 이쪽이 맞을 때 | 저 모듈 | 저쪽이 맞을 때 |")
        L.append("|---|---|---|---|")
        for a, b, wa, wb in rows:
            # a가 적은 이유는 「언제 b가 맞는가」, b가 적은 이유는 「언제 a가 맞는가」입니다
            L.append("| `%s` | %s | `%s` | %s |" % (a, cell(wb), b, cell(wa)))
    else:
        L.append("아직 적힌 짝이 없습니다.")
    L.append("")

    return "\n".join(L).rstrip("\n") + "\n"


def default_out(core=None):
    return os.path.join(modlib.modules_dir(core), "module-map.md")


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", help="core 폴더 (기본: 이 스크립트가 속한 core)")
    ap.add_argument("--out", help="산출물 경로 (기본: core/modules/module-map.md)")
    ap.add_argument("--check", action="store_true", help="쓰지 않고 다른지만 봅니다")
    args = ap.parse_args(argv)
    core = os.path.abspath(args.core) if args.core else None
    if not os.path.isdir(modlib.modules_dir(core)):
        print("모듈 폴더가 없습니다 — 만들 지도가 없습니다.")
        return 0
    out = args.out or default_out(core)
    text = render(core)
    try:
        with io.open(out, encoding="utf-8", newline="") as f:
            old = f.read()
    except OSError:
        old = None
    if args.check:
        if old != text:
            print("모듈 지도가 정본과 다릅니다 — %s 로 다시 만드세요." % CMD)
            return 1
        print("모듈 지도가 최신입니다.")
        return 0
    if old != text:
        with io.open(out, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    else:
        # 내용이 같아도 시각은 맞춥니다 — regen.py --check가 수정 시각으로 낡음을 보기 때문입니다
        os.utime(out, None)
    print("모듈 지도를 썼습니다: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
