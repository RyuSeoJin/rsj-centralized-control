# -*- coding: utf-8 -*-
"""규칙 검사 — 규칙대로 썼는지 기계가 봅니다

왜 도구인가
----------
  규칙은 눈으로 훑어서는 안 걸립니다. 제목 하나가 「~않는다」로 끝나 있어도, 이름표에
  프로젝트 항목이 하나 더 있어도 읽는 데 지장이 없어서 그대로 지나갑니다. 그렇게 몇 장이
  쌓이면 문서마다 말투가 갈리고, 중앙 규칙에 프로젝트가 스며듭니다.

  **규칙은 잊히고 검사는 잊히지 않습니다.** 규칙이 늘면 여기에 검사를 더합니다.

무엇을 보나 — 문체 (rules/doc-write-style.md)
----------
  ① 제목의 평서형   「~다」로 끝나는 제목 (§1-1 — 제목도 본문과 같은 기준입니다)
  ② 본문의 비경어체  「~다.」로 끝나되 「~니다.」가 아닌 문장 (§1)
  ③ 독스트링 첫 줄   소개 페이지가 도구 설명으로 싣는 줄이라 본문과 같은 자리입니다 (§3-3)

무엇을 보나 — 이름표 (rules/site-structure.md §프로젝트 관련된 내용은 …)
----------
  ④ workspace.json이 담는 항목  이름표는 저장소 이야기만 담습니다. 프로젝트 목록이나
                                진행 중인 프로젝트 같은 항목이 들어오면 중앙 규칙에
                                프로젝트가 드러나고, 목록은 폴더와 이중 정본이 됩니다.
  ⑤ 모듈이 더한 서식의 목록     모듈에 design-template/이 있으면 그 안에 카탈로그가
                                있어야 합니다. base 카탈로그가 모듈 이름을 적지 않으므로,
                                모듈이 목록을 빠뜨리면 켜도 아무도 못 찾습니다.
  ⑥ 모듈의 자기 점검            도구(scripts/)를 가진 모듈은 check.py도 가져야 합니다.
                                중앙 게이트가 모듈 이름을 모르고 폴더만 훑으므로, 점검을
                                빠뜨린 모듈은 검사에 **아예 들어오지 않습니다**.

무엇을 건너뛰나
--------------
  코드 펜스 · 인용(>) · 표 · 코드 주석과 독스트링 둘째 줄부터 (§3-3·§3-4)
  그리고 아래 WAIVER — 시트 표기 규약(`~한다`·`~된다`)을 예시로 펼치는 자리입니다 (§3-2)

사용법
------
    python core/base/scripts/check_rules.py          걸린 곳을 낸다 (없으면 exit 0)
"""
import io
import json
import os
import re
import sys

#: 문체 예외 — (파일, 사유). §3-2의 시트 표기 규약을 예시로 펼치는 문서들이다.
#: 여기 적힌 파일은 **본문 검사만** 건너뛰고 제목은 그대로 본다
WAIVER = {
    "core/modules/tc/rules/tc-sheet-format.md": "시트 표기 규약(~한다·~된다) 예시",
    "core/modules/tc/rules/depth-and-tn.md": "시트 표기 규약 예시",
    "core/modules/tc/rules/case-expansion.md": "시트 표기 규약 예시",
}

POLITE = ("니다", "십시오")
BODY = re.compile(r"[가-힣][^.\n]{4,80}?(?<!니)다[.]")


def repo_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(d, "workspace.json")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return d
        d = p


def is_statement(text):
    """평서형인가 — 「~다」로 끝나면 서술문이다(§1-1). 의문·감탄은 아니다."""
    t = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip().rstrip("?!").strip()
    if not t or not re.search(r"[가-힣]", t):
        return False
    return t.endswith("다") and not t.endswith(POLITE)


def strip_quotes(line, in_quote):
    """큰따옴표 안을 지웁니다 — 원문 발췌는 고치지 않습니다(§3-4).

    인용이 여러 줄에 걸치는 경우가 있어 열림 상태를 줄 사이로 넘깁니다.
    """
    out, segs = [], line.split('"')
    for i, seg in enumerate(segs):
        out.append(" " * len(seg) if in_quote else seg)
        if i < len(segs) - 1:
            in_quote = not in_quote
            out.append(" ")
    return "".join(out), in_quote


def check_md(path, rel):
    hits = []
    fence = False
    in_quote = False
    body_ok = rel not in WAIVER
    for i, line in enumerate(io.open(path, encoding="utf-8").read().split("\n"), 1):
        st = line.strip()
        if st.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if line.startswith("#"):
            _, in_quote = strip_quotes(line, in_quote)
            t = re.sub(r"^#+\s*", "", line).strip()
            if is_statement(t):
                hits.append((i, "제목", t[:56]))
            continue
        # 인용과 표는 건너뜁니다 — 원문 발췌(§3-4)와 데이터 표기가 섞입니다
        if not body_ok or st.startswith((">", "|")):
            _, in_quote = strip_quotes(line, in_quote)
            continue
        clean, in_quote = strip_quotes(line, in_quote)
        for m in BODY.finditer(clean):
            hits.append((i, "본문", m.group(0)[-56:]))
    return hits


def check_py(path):
    """독스트링 첫 줄만 봅니다 — 소개 페이지가 그 줄을 도구 설명으로 싣습니다."""
    s = io.open(path, encoding="utf-8").read()
    m = re.match(r'\s*(?:#[^\n]*\n)*\s*(?:"""|\'\'\')(.*)', s)
    if not m:
        return []
    first = m.group(1).split("\n", 1)[0].strip()
    return [(1, "독스트링", first[:56])] if is_statement(first) else []


#: 이름표가 담는 항목. **이 셋뿐입니다** — 프로젝트 이야기는 한 자리도 두지 않습니다
WS_KEYS = ("name", "subtitle", "repo")


def check_workspace(root):
    """이름표에 모르는 항목이 있는지 봅니다."""
    p = os.path.join(root, "workspace.json")
    if not os.path.exists(p):
        return [("workspace.json", 0, "이름표", "파일이 없습니다 — 저장소 루트의 이정표입니다")]
    try:
        with io.open(p, encoding="utf-8") as f:
            ws = json.load(f)
    except ValueError as e:
        return [("workspace.json", 0, "이름표", "json을 읽을 수 없습니다 — %s" % e)]
    hits = []
    for k in sorted(ws):
        if k not in WS_KEYS:
            hits.append(("workspace.json", 0, "이름표",
                         "모르는 항목 `%s` — 담는 것은 %s 셋뿐입니다"
                         % (k, " · ".join(WS_KEYS))))
    for k in WS_KEYS:
        if not str(ws.get(k, "")).strip():
            hits.append(("workspace.json", 0, "이름표", "`%s`이(가) 비어 있습니다" % k))
    return hits


def check_module_templates(root):
    """모듈이 템플릿을 더해 놓고 목록에 안 적었는지 봅니다.

    base 카탈로그는 모듈 이름을 적지 않습니다 — 적으면 base가 모듈을 알게 되어
    `core/base/`만 떼어냈을 때 없는 파일을 가리키게 되기 때문입니다. 그래서 base는
    「모듈에 design-template/이 있으면 그 카탈로그도 본다」고만 적습니다.

    그 대가로 **모듈이 카탈로그를 빠뜨리면 아무도 그 템플릿을 모르게 됩니다.** 켜도
    목록에 안 나오고, 규칙 문장만으로는 걸리지 않습니다. 그 자리를 여기서 봅니다.
    """
    mods = os.path.join(root, "core", "modules")
    if not os.path.isdir(mods):
        return []
    hits = []
    for name in sorted(os.listdir(mods)):
        d = os.path.join(mods, name, "design-template")
        if not os.path.isdir(d):
            continue
        rel = "core/modules/%s/design-template" % name
        files = [f for f in os.listdir(d) if not f.startswith(".")]
        if not files:
            hits.append((rel, 0, "모듈 서식", "폴더가 비어 있습니다 — 쓰지 않으면 지웁니다"))
            continue
        if not any(f.endswith("catalog.md") for f in files):
            hits.append((rel, 0, "모듈 서식",
                         "카탈로그가 없습니다 — 이 폴더의 것을 아무도 못 찾습니다. "
                         "`{모듈}-template-catalog.md`를 둡니다"))
    return hits


def check_module_checks(root):
    """도구를 가진 모듈이 자기 점검을 빠뜨렸는지 봅니다.

    중앙 게이트는 `core/modules/*/check.py`를 훑어 돌립니다 — 모듈 이름을 적지 않아
    모듈이 늘어도 게이트가 안 낡습니다. 그 대가로 **점검을 안 둔 모듈은 검사에 아예
    들어오지 않고, 그 사실이 아무 데서도 드러나지 않습니다.** 그 자리를 여기서 봅니다.

    규칙 문서만 있는 모듈은 돌릴 것이 없어 강제하지 않습니다. 도구가 있으면 그 도구가
    뜨는지는 볼 수 있으므로, 가르는 기준을 `scripts/`의 유무로 둡니다
    (rules/git-rules.md §6-3 · rules/feature-request.md).
    """
    mods = os.path.join(root, "core", "modules")
    if not os.path.isdir(mods):
        return []
    hits = []
    for name in sorted(os.listdir(mods)):
        d = os.path.join(mods, name)
        scripts = os.path.join(d, "scripts")
        if not os.path.isdir(scripts):
            continue
        if not any(f.endswith(".py") for f in os.listdir(scripts)):
            continue
        if not os.path.exists(os.path.join(d, "check.py")):
            hits.append(("core/modules/%s" % name, 0, "모듈 점검",
                         "도구가 있는데 check.py가 없습니다 — 게이트가 이 모듈을 "
                         "지나칩니다. base/scripts/modcheck.py를 쓰면 몇 줄입니다"))
    return hits


def main():
    # 한글 출력이 콘솔 기본 인코딩으로 나가면, 다른 도구가 받아 읽을 때 깨집니다.
    # 오류는 stderr로 나가므로 둘 다 맞춥니다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    root = repo_root()
    found = 0
    for rel, line, kind, text in check_workspace(root) + check_module_templates(root) + check_module_checks(root):
        print("%s:%d  [%s] %s" % (rel, line, kind, text))
        found += 1
    for cur, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for n in sorted(names):
            p = os.path.join(cur, n)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            try:
                hits = check_md(p, rel) if n.endswith(".md") else (
                    check_py(p) if n.endswith(".py") else [])
            except (UnicodeDecodeError, OSError):
                continue
            for line, kind, text in hits:
                print("%s:%d  [%s] %s" % (rel, line, kind, text))
                found += 1
    if found:
        print("")
        print("규칙과 다른 곳 %d건 — rules/doc-write-style.md · rules/site-structure.md"
              % found)
        return 1
    print("규칙 검사 통과 — 걸린 곳이 없습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
