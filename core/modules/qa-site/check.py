# -*- coding: utf-8 -*-
"""qa-site 모듈 자기 점검 — 셸과 생성기가 뜨는지 봅니다

  ① scripts/의 도구를 실제로 불러 봅니다.
  지금은 얕습니다. 실제로 걸린 것이 나오면 그 케이스를 여기 더합니다.

사용법
------
    python core/modules/qa-site/check.py        통과하면 exit 0
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "base", "scripts"))
import modcheck  # noqa: E402


def main():
    return modcheck.done("qa-site", modcheck.imports(__file__))


if __name__ == "__main__":
    sys.exit(main())
