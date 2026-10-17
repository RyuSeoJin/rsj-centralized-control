# -*- coding: utf-8 -*-
"""game-html 모듈 자기 점검 — 도구가 뜨고, 시작 서식이 도구를 통과하는지 봅니다

  ① scripts/game_html_check.py를 불러 봅니다.
  ② design-template/game-shell.html이 점검에서 걸림 · 주의 없이 통과하는지 봅니다 —
     서식이 규칙을 어기면 받아 쓰는 모든 프로토타입이 같이 어기게 됩니다.
  ③ 일부러 어긴 작은 HTML이 걸리는지 봅니다(외부 파일 · CHANGELOG 없음 · rAF만 있음).
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "base", "scripts"))
import modcheck  # noqa: E402


def main():
    fails = modcheck.imports(__file__) or []
    here = modcheck.module_dir(__file__)
    sys.path.insert(0, os.path.join(here, "scripts"))
    import game_html_check as g  # noqa: E402

    shell = os.path.join(here, "design-template", "game-shell.html")
    f, w, _ = g.check(io.open(shell, encoding="utf-8").read())
    fails += ["서식 걸림 — %s" % x for x in f] + ["서식 주의 — %s" % x for x in w]

    bad = ('<html><script src="https://example.com/x.js"></script>'
           '<script>function loop(){requestAnimationFrame(loop)}</script></html>')
    f, w, _ = g.check(bad)
    if not any("외부 파일" in x for x in f):
        fails.append("외부 파일을 못 잡았습니다")
    for word in ("CHANGELOG", "실시간 루프", "CONFIG"):
        if not any(word in x for x in w):
            fails.append("%s 주의를 못 잡았습니다" % word)
    return modcheck.done("game-html", fails)


if __name__ == "__main__":
    sys.exit(main())
