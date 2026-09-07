# -*- coding: utf-8 -*-
"""automation 모듈 자기 점검 — 도구가 뜨는지 봅니다

무엇을 보나
----------
  scripts/의 도구를 실제로 불러 봅니다. 리포트 생성기는 프로젝트 폴더를 받아야 돌아서
  여기서는 산출까지 내지 않습니다 — 뜨는 데까지가 프로젝트 없이 확인할 수 있는 선입니다.

무엇을 안 보나
-------------
  프로젝트 데이터를 읽지 않습니다. 중앙 저장소에는 `projects/`가 비어 있고, 게이트는
  거기서 돕니다 — 프로젝트가 있어야 도는 점검은 중앙에서 반드시 실패합니다.

  지금은 얕습니다. 프로젝트에서 실제로 걸린 것이 나오면 그 케이스를 여기 더합니다
  (rules/feature-request.md — 겪은 것을 중앙에 올리는 흐름).

사용법
------
    python core/modules/automation/check.py        통과하면 exit 0
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "base", "scripts"))
import modcheck  # noqa: E402

def main():
    return modcheck.done("automation", modcheck.imports(__file__))


if __name__ == "__main__":
    sys.exit(main())
