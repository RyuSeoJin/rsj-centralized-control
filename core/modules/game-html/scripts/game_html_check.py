# -*- coding: utf-8 -*-
"""HTML 게임 프로토타입 점검 — rules/game-html.md §10의 함정을 훑습니다

  python core/modules/game-html/scripts/game_html_check.py {파일.html}

무엇을 보나
----------
  걸림(종료 코드 1)
    ① 스크립트 문법      node가 있으면 인라인 스크립트마다 `new Function`으로 봅니다(없으면 건너뜀 · 알림)
    ② 외부 파일          `<script src>` · `<link href>` · `<img src>`가 http(s)를 가리킴 — 한 파일로 열려야 합니다
    ③ 함수 이름 겹침     줄 맨 앞의 `function 이름(` 선언이 같은 이름으로 둘 이상 — 뒤의 것이 앞의 것을 조용히 덮습니다
  주의(종료 코드 0, 알림만)
    ④ CHANGELOG          파일 앞부분 주석에 CHANGELOG가 없음
    ⑤ 저장 키 판 번호    `SAVE_KEY`가 없거나 `-v숫자`로 끝나지 않음
    ⑥ 저장 try           `localStorage` 읽기 · 쓰기 줄 근처(앞 3줄)에 try가 없음
    ⑦ 실시간 루프        `requestAnimationFrame`만 있고 타이머(`setInterval`)가 없음 — 가려진 탭에서 멈춥니다
    ⑧ 수치 한곳          `CONFIG`가 없음

  판단이 필요한 것(화면이 넘치는지, 옛 저장이 열리는지)은 브라우저에서 봅니다(§9).
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT = re.compile(r"<script(?P<attr>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)
EXTERNAL = re.compile(r"<(?:script|link|img)\b[^>]*\b(?:src|href)\s*=\s*[\"']https?://", re.I)
FUNC_DECL = re.compile(r"^(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(", re.M)


def inline_scripts(html):
    return [m.group("body") for m in SCRIPT.finditer(html) if "src=" not in m.group("attr").lower()]


def duplicate_functions(html):
    """인라인 스크립트에서 줄 맨 앞의 함수 선언을 모아, 이름이 겹치는 것을 [(이름, [줄 번호…])]로 돌려줍니다.
    줄 번호는 HTML 파일 기준입니다."""
    seen = {}
    for m in SCRIPT.finditer(html):
        if "src=" in m.group("attr").lower():
            continue
        base = html.count("\n", 0, m.start("body")) + 1
        body = m.group("body")
        for f in FUNC_DECL.finditer(body):
            seen.setdefault(f.group(1), []).append(base + body.count("\n", 0, f.start()))
    return [(name, lines) for name, lines in seen.items() if len(lines) > 1]


def syntax_errors(scripts):
    """node로 문법만 봅니다. node가 없으면 None을 돌려 건너뛴 것을 알립니다."""
    node = shutil.which("node")
    if not node:
        return None
    errs = []
    for i, src in enumerate(scripts):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(src)
            path = f.name
        try:
            code = "const s=require('fs').readFileSync(process.argv[1],'utf8');try{new Function(s)}catch(e){console.log(e.message);process.exit(1)}"
            r = subprocess.run([node, "-e", code, path], capture_output=True, text=True, encoding="utf-8")
            if r.returncode != 0:
                errs.append("스크립트 %d — %s" % (i + 1, (r.stdout or r.stderr).strip()))
        finally:
            os.unlink(path)
    return errs


def check(html):
    """(걸림 목록, 주의 목록, 알림 목록)을 돌려줍니다."""
    fails, warns, notes = [], [], []
    scripts = inline_scripts(html)
    errs = syntax_errors(scripts)
    if errs is None:
        notes.append("node가 없어 문법 검사를 건너뜀")
    else:
        fails += ["문법 — %s" % e for e in errs]
    for m in EXTERNAL.finditer(html):
        fails.append("외부 파일 — %s" % m.group(0)[:80])
    for name, nums in duplicate_functions(html):
        fails.append("함수 이름 겹침 — %s (줄 %s)" % (name, " · ".join(str(n) for n in nums)))
    js = "\n".join(scripts)
    if "CHANGELOG" not in html[:4000]:
        warns.append("CHANGELOG — 파일 앞부분 주석에 버전 · 날짜 · 바뀐 것을 둡니다(§1)")
    key = re.search(r"SAVE_KEY\s*=\s*['\"]([^'\"]+)['\"]", js)
    if "localStorage" in js and not key:
        warns.append("저장 키 — localStorage를 쓰는데 SAVE_KEY가 없습니다(§6)")
    elif key and not re.search(r"-v\d+$", key.group(1)):
        warns.append("저장 키 판 번호 — `%s`이(가) `-v숫자`로 끝나지 않습니다(§6)" % key.group(1))
    lines = js.split("\n")
    for i, l in enumerate(lines):
        if re.search(r"localStorage\.(?:get|set)Item", l) and not any("try" in x for x in lines[max(0, i - 3):i + 1]):
            warns.append("저장 try — %d번째 줄의 localStorage 접근이 try로 감싸여 있지 않습니다(§6)" % (i + 1))
    if "requestAnimationFrame" in js and "setInterval" not in js:
        warns.append("실시간 루프 — requestAnimationFrame만 있습니다. 판정은 타이머 + 고정 스텝으로(§5-2)")
    if not re.search(r"\bCONFIG\b", js):
        warns.append("수치 한곳 — CONFIG가 없습니다(§4)")
    return fails, warns, notes


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    path = argv[0]
    if not os.path.isfile(path):
        print("파일이 없습니다 — %s" % path)
        return 2
    fails, warns, notes = check(io.open(path, encoding="utf-8").read())
    for n in notes:
        print("  · %s" % n)
    for w in warns:
        print("  ⚠ %s" % w)
    for f in fails:
        print("  ✗ %s" % f)
    print("%s — 걸림 %d · 주의 %d" % ("통과" if not fails else "걸림", len(fails), len(warns)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
