# -*- coding: utf-8 -*-
"""gdd 모듈 자기 점검 — 빌드 도구와 서식이 제자리에 있는지 봅니다

  ① scripts/build_gdd.sh가 있고, 가리키는 base 마스터 · 글꼴 도구가 실재하는지 봅니다.
  지금은 얕습니다. 실제로 걸린 것이 나오면 그 케이스를 여기 더합니다.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "base", "scripts"))
import modcheck  # noqa: E402


def main():
    here = modcheck.module_dir(__file__)
    core = os.path.dirname(os.path.dirname(here))
    need = [os.path.join(here, "scripts", "build_gdd.sh"),
            os.path.join(core, "base", "design-guide", "design-guide-ue-master.css"),
            os.path.join(core, "base", "scripts", "embed_fonts.py")]
    fails = ["없습니다 — %s" % p for p in need if not os.path.isfile(p)]
    return modcheck.done("gdd", fails)


if __name__ == "__main__":
    sys.exit(main())
