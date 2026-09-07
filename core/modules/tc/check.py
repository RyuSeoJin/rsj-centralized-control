# -*- coding: utf-8 -*-
"""tc 모듈 자기 점검 — 도구가 뜨고 시트가 만들어지는지 봅니다

무엇을 보나
----------
  ① scripts/의 도구를 실제로 불러 봅니다.
  ② design-template/의 빈 입력 골격으로 TC 시트를 한 장 만들어 봅니다. 게이팅 상태 목록은
     프로젝트가 정하므로 중앙에서는 비어 있고, **빈 목록으로도 만들어져야** 합니다.

무엇을 안 보나
-------------
  프로젝트 데이터를 읽지 않습니다. 중앙 저장소에는 `projects/`가 비어 있고, 게이트는
  거기서 돕니다 — 프로젝트가 있어야 도는 점검은 중앙에서 반드시 실패합니다.

  지금은 얕습니다. 프로젝트에서 실제로 걸린 것이 나오면 그 케이스를 여기 더합니다
  (rules/feature-request.md — 겪은 것을 중앙에 올리는 흐름).

사용법
------
    python core/modules/tc/check.py        통과하면 exit 0
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "base", "scripts"))
import modcheck  # noqa: E402

def main():
    here = modcheck.module_dir(__file__)
    src = os.path.join(here, "design-template", "tc-input-master.json")
    out = os.path.join(tempfile.mkdtemp(), "probe.xlsx")
    made = []
    r = subprocess.run(
        [sys.executable, os.path.join(here, "scripts", "build_tc_template_xlsx.py"),
         src, "-o", out],
        capture_output=True)
    if r.returncode != 0:
        tail = r.stderr.decode("utf-8", "replace").strip().splitlines()
        made.append("TC 시트 생성이 실패했습니다 — %s" % (tail[-1] if tail else "출력 없음"))
    else:
        made = modcheck.wrote(out, "TC 시트가 비어 있습니다")
    return modcheck.done("tc", modcheck.imports(__file__), made)


if __name__ == "__main__":
    sys.exit(main())
