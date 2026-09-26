# -*- coding: utf-8 -*-
"""aseprite 호스트 모듈 자기 점검 — 도구가 뜨는지만 봅니다

실제 설치 점검(`scripts/aseprite_env.py`)은 Aseprite가 깔린 컴퓨터에서 사람이 돌립니다.
중앙 게이트에는 Aseprite가 없으므로 여기서 실행까지 보면 게이트가 늘 실패합니다.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "base", "scripts"))

import modcheck  # noqa: E402


def main():
    return modcheck.done("aseprite", modcheck.imports(__file__))


if __name__ == "__main__":
    sys.exit(main())
