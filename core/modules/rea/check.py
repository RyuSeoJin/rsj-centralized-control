# -*- coding: utf-8 -*-
"""rea 호스트 모듈 자기 점검 — 도구가 뜨는지와 Node.js 버전 판정만 봅니다

실제 설치 점검(`scripts/rea_env.py`)은 REA를 쓸 컴퓨터에서 사람이 돌립니다.
중앙 게이트에는 Node.js · REA가 없을 수 있으므로 여기서 실행까지 보면 게이트가 늘 실패합니다.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "base", "scripts"))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import modcheck  # noqa: E402


def node_rule():
    """REA가 받는 Node.js 버전 경계를 바르게 가르는지 봅니다."""
    import rea_env
    cases = {"v22.23.4": True, "v22.23.3": False, "v22.24.0": True, "v22.19.0": False,
             "v24.22.1": True, "v24.22.0": False, "v24.13.0": False, "v24.23.0": True,
             "v26.12.1": True, "v26.12.0": False, "v26.13.0": True, "v27.0.0": True,
             "v23.9.0": False, "v20.11.1": False, "": False}
    return ["Node.js 판정 — %r는 %s이어야 합니다" % (k, "통과" if want else "실패")
            for k, want in cases.items() if rea_env.node_ok(k)[0] != want]


def main():
    return modcheck.done("rea", modcheck.imports(__file__), node_rule())


if __name__ == "__main__":
    sys.exit(main())
