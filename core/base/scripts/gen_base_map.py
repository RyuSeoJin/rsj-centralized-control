# -*- coding: utf-8 -*-
"""base 규칙 지도 생성기 — base 규칙을 하는 일별로 묶고, 규칙마다 언제 읽나 · 주요 절 · 가리키는 규칙을 찍어 냅니다

파이프라인에서의 위치
--------------------
  core/base/base-groups.json        (정본 — 분야 · 표시 순서 · 색인 문서)
  core/base/rules/*.md · doc-playbook.md · dictionary.md
                                    (정본 — 제목 줄 · ## 절 · 다른 규칙 언급)
  core/base/rules/read-gates.md     (정본 — 「읽기 게이트」 표의 상황)
    │  이 스크립트
    ├──▶ core/base/base-map.md       (파생 — 손으로 고치지 않습니다)
    └──▶ README.md의 표시 구역       (파생 — 「base 규칙」 요약. 표시가 있는 README만 씁니다)

  · 규칙 사이의 관계는 문서 본문에서 다른 규칙 파일 이름(`xxx.md`)을 언급한 것으로 읽습니다.
  · 색인 문서(hubs)는 거의 모든 규칙을 가리켜 그림을 덮으므로 관계 그림에서 뺍니다.
  · 출력은 결정적입니다 — 순서를 고정하고 날짜 · 시각을 넣지 않습니다.

사용법
------
    python core/base/scripts/gen_base_map.py                    지도를 다시 씁니다
    python core/base/scripts/gen_base_map.py --check            쓰지 않고 다른지만 봅니다
    python core/base/scripts/gen_base_map.py --readme README.md [--check]
                                                                README의 표시 구역만 다시 씁니다
    python core/base/scripts/gen_base_map.py --base 경로        다른 base 폴더를 봅니다(시험용)
"""
import argparse
import io
import json
import os
import re
import sys

CMD = "python core/base/scripts/gen_base_map.py"
HERE = os.path.dirname(os.path.abspath(__file__))

README_START = "<!-- base-overview:start — 생성물입니다. 손으로 고치지 않습니다(gen_base_map.py --readme) -->"
README_END = "<!-- base-overview:end -->"
UNGROUPED = "분류 없음"


def base_dir(base=None):
    return base or os.path.dirname(HERE)


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def cell(text):
    return " ".join((text or "").split()).replace("|", "\\|") or "—"


def stem(rel):
    return os.path.splitext(os.path.basename(rel))[0]


def load_groups(base=None):
    """(분야 목록, 색인 문서 목록). 분야마다 {"label", "rules"}입니다. 없는 파일은 빼고,
    어느 분야에도 없는 규칙 파일은 맨 끝 「분류 없음」으로 모읍니다."""
    root = base_dir(base)
    try:
        data = json.loads(read(os.path.join(root, "base-groups.json")))
    except (OSError, ValueError):
        data = {}
    groups, seen = [], set()
    for g in data.get("groups", []) if isinstance(data.get("groups"), list) else []:
        rules = [r for r in g.get("rules", []) if os.path.isfile(os.path.join(root, r)) and r not in seen]
        seen.update(rules)
        if rules:
            groups.append({"label": str(g.get("label") or g.get("id") or ""), "rules": rules})
    rest = []
    rules_dir = os.path.join(root, "rules")
    if os.path.isdir(rules_dir):
        for n in sorted(os.listdir(rules_dir)):
            rel = "rules/" + n
            if n.endswith(".md") and rel not in seen:
                rest.append(rel)
    if rest:
        groups.append({"label": UNGROUPED, "rules": rest})
    hubs = [h for h in data.get("hubs", []) if isinstance(h, str)]
    return groups, hubs


def title_of(text):
    """제목 줄 `# 이름 — 설명`의 설명 부분."""
    for line in text.split("\n"):
        if line.startswith("# "):
            return line[2:].split(" — ", 1)[-1].strip()
    return ""


def sections_of(text):
    """`## 절` 제목들 — 앞 번호(`3.` · `§3`)는 떼고, 코드 블록 안은 건너뜁니다."""
    out, fence = [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
            continue
        if not fence and line.startswith("## "):
            t = re.sub(r"^(§?\d+(\.\d+)*\.?)\s+", "", line[3:].strip())
            out.append(t)
    return out


def gate_situations(base=None):
    """읽기 게이트 표에서 규칙 파일 → 그 파일을 읽는 상황 목록."""
    path = os.path.join(base_dir(base), "rules", "read-gates.md")
    try:
        text = read(path)
    except OSError:
        return {}
    out = {}
    in_gate = False
    for line in text.split("\n"):
        if line.startswith("## "):
            in_gate = line.startswith("## 읽기 게이트")
            continue
        if not in_gate or not line.startswith("|") or re.match(r"^\|\s*[-:]", line):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 2 or cols[0] == "상황":
            continue
        for m in re.finditer(r"core/base/((?:rules/)?[a-z0-9-]+\.md)", cols[1]):
            out.setdefault(m.group(1), [])
            if cols[0] not in out[m.group(1)]:
                out[m.group(1)].append(cols[0])
    # 읽기 게이트 자신은 표에 자기를 적지 않지만, 모든 작업 앞에서 읽는 문서입니다
    out.setdefault("rules/read-gates.md", []).insert(0, "모든 작업 — 무엇을 더 읽을지 정합니다")
    return out


def collect(base=None):
    """규칙마다 {"title", "sections", "gates", "refs"}. refs는 본문이 언급한 다른 base 규칙입니다."""
    root = base_dir(base)
    groups, hubs = load_groups(base)
    all_rules = [r for g in groups for r in g["rules"]]
    gates = gate_situations(base)
    info = {}
    for rel in all_rules:
        text = read(os.path.join(root, rel))
        refs = [o for o in all_rules if o != rel and re.search(r"(?<![a-z0-9-])%s\.md" % re.escape(stem(o)), text)]
        info[rel] = {"title": title_of(text), "sections": sections_of(text),
                     "gates": gates.get(rel, []), "refs": refs}
    return groups, hubs, info


def node_id(rel):
    return "r_" + "".join(c if c.isalnum() else "_" for c in stem(rel))


def link(rel, prefix):
    return "[%s](%s%s)" % (stem(rel), prefix, rel)


def group_graph(group, groups, hubs, info):
    """한 분야의 관계 그림 — 이 분야 규칙이 가리키는 규칙만 잇습니다(나가는 선). 들어오는 선까지
    그리면 선이 두 배가 되고, 그 선은 상대 분야의 그림에 나가는 선으로 이미 나옵니다.
    다른 분야 규칙은 회색 점선 상자, 색인 문서는 뺍니다. 이어진 것이 없으면 빈 목록."""
    group_of = dict((r, g["label"]) for g in groups for r in g["rules"])
    inside = [r for r in group["rules"] if r not in hubs]
    edges = [(src, dst) for src in inside for dst in info[src]["refs"] if dst not in hubs]
    if not edges:
        return []
    outside = []
    for a, b in edges:
        for n in (a, b):
            if n not in inside and n not in outside:
                outside.append(n)
    L = ["```mermaid", "flowchart LR"]
    for r in inside:
        L.append('  %s["%s"]' % (node_id(r), stem(r)))
    for r in outside:
        L.append('  %s["%s<br/>(%s)"]:::other' % (node_id(r), stem(r), group_of.get(r, "").replace('"', "'")))
    for a, b in edges:
        L.append("  %s --> %s" % (node_id(a), node_id(b)))
    if outside:
        L.append("  classDef other fill:#f3f4f6,stroke:#9ca3af,stroke-dasharray:4 3,color:#4b5563")
    L.append("```")
    return L


def render(base=None):
    groups, hubs, info = collect(base)
    L = ["# base 규칙 지도 — 하는 일별로 본 base 규칙", "",
         "> 이 파일은 생성물입니다. 손으로 고치지 않습니다. 정본은 `base-groups.json`과 각 규칙 문서 · 읽기 게이트이며,",
         "> 고친 뒤 `%s`(또는 `regen.py`)로 다시 만듭니다." % CMD, "",
         "base 규칙은 모든 저장소 · 프로젝트가 따릅니다. 이 지도는 규칙을 하는 일별로 묶고, 규칙마다 **언제 읽나**",
         "(읽기 게이트의 상황) · **주요 절** · **가리키는 규칙**(본문이 언급한 다른 base 규칙)을 보입니다.", ""]
    if hubs:
        L += ["**색인 문서** — %s는 거의 모든 규칙을 가리키는 입구라 관계 그림에서 뺍니다."
              % " · ".join(link(h, "") for h in hubs if h in info), ""]
    L += ["그림은 분야마다 그 분야 규칙이 가리키는 규칙(본문에서 언급하는 규칙)을 잇습니다. `A --> B`는 A가 B를",
          "가리킨다는 뜻이고, 회색 점선 상자는 다른 분야의 규칙입니다.", ""]
    for g in groups:
        L += ["## " + g["label"], "",
              "| 규칙 | 내용 | 언제 읽나 | 주요 절 | 가리키는 규칙 |", "|---|---|---|---|---|"]
        for r in g["rules"]:
            it = info[r]
            refs = "색인 — base 규칙 대부분" if r in hubs else " · ".join(stem(x) for x in it["refs"])
            L.append("| %s | %s | %s | %s | %s |" % (
                link(r, ""), cell(it["title"]), cell(" / ".join(it["gates"])),
                cell(" · ".join(it["sections"])), cell(refs)))
        pic = group_graph(g, groups, hubs, info)
        if pic:
            L += [""] + pic
        L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def render_overview(base=None):
    """README 표시 구역 — 분야마다 규칙 · 하는 일 · 언제 읽나."""
    groups, _hubs, info = collect(base)
    L = ["규칙마다 주요 절 · 가리키는 규칙 · 분야별 관계 그림은 [base 규칙 지도](core/base/base-map.md)에 있습니다.", "",
         "| 분야 | 규칙 | 내용 | 언제 읽나 |", "|---|---|---|---|"]
    for g in groups:
        for i, r in enumerate(g["rules"]):
            it = info[r]
            L.append("| %s | %s | %s | %s |" % (cell(g["label"]) if i == 0 else "", link(r, "core/base/"),
                                                cell(it["title"]), cell(" / ".join(it["gates"]))))
    return "\n".join(L) + "\n"


def replace_block(text, body):
    s = text.find(README_START)
    e = text.find(README_END)
    if s < 0 or e < s:
        return None
    return text[:s + len(README_START)] + "\n\n" + body + "\n" + text[e:]


def has_block(path):
    try:
        text = read(path)
    except OSError:
        return False
    return README_START in text and README_END in text


def write(path, new, check, label):
    try:
        with io.open(path, encoding="utf-8", newline="") as f:
            old = f.read()
    except OSError:
        old = None
    if check:
        if old != new:
            print("%s가 정본과 다릅니다 — %s 로 다시 만드세요." % (label, CMD))
            return 1
        print("%s가 최신입니다." % label)
        return 0
    if old != new:
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)
    else:
        os.utime(path, None)  # regen.py --check가 수정 시각으로 낡음을 봅니다
    print("%s를 썼습니다: %s" % (label, path))
    return 0


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="base 폴더 (기본: 이 스크립트가 속한 base)")
    ap.add_argument("--out", help="산출물 경로 (기본: core/base/base-map.md)")
    ap.add_argument("--check", action="store_true", help="쓰지 않고 다른지만 봅니다")
    ap.add_argument("--readme", help="이 README의 표시 구역(「base 규칙」 요약)만 다시 씁니다")
    args = ap.parse_args(argv)
    base = os.path.abspath(args.base) if args.base else None
    if args.readme:
        try:
            old = read(args.readme)
        except OSError:
            print("README가 없습니다: %s" % args.readme)
            return 1
        new = replace_block(old, render_overview(base))
        if new is None:
            print("README에 표시 구역이 없습니다 — 쓰지 않습니다: %s" % args.readme)
            return 0
        return write(args.readme, new, args.check, "README의 「base 규칙」")
    out = args.out or os.path.join(base_dir(base), "base-map.md")
    return write(out, render(base), args.check, "base 규칙 지도")


if __name__ == "__main__":
    sys.exit(main())
