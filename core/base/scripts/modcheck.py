# -*- coding: utf-8 -*-
"""모듈 자기 점검 거들기 — 각 모듈의 check.py가 같은 모양이 되게 합니다

왜 여기 있나
-----------
  모듈마다 점검을 따로 쓰면 출력도 판정도 제각각이 됩니다. 게이트는 종료 코드만 보므로
  돌기는 하지만, **사람이 로그를 읽을 때 어느 모듈이 무엇을 봤는지 알 수 없게 됩니다.**
  그래서 뜨는지 보는 부분과 결과를 내는 부분을 여기 두고, 모듈은 자기만의 확인을 더합니다.

  base가 모듈을 거드는 방향입니다. 반대로 base가 모듈을 **참조**하지는 않습니다 — 여기에
  모듈 이름은 한 자리도 없습니다.

점검은 얕게 시작합니다
---------------------
  아직 돌려 보지 않은 도구에 두꺼운 점검을 쓰면 **추측으로 쓴 점검**이 됩니다. 그건 허술한
  점검보다 나쁩니다 — 틀린 것을 통과시키면서 통과했다고 말하기 때문입니다.

  처음에는 「도구가 뜨는가」까지만 두고, 프로젝트에서 실제로 걸린 것이 나오면 그때 그 케이스를
  더합니다. 무엇을 보는지는 규칙이 아니라 겪은 것이 정합니다 (rules/feature-request.md).

사용법 — 모듈의 check.py에서
---------------------------
    import modcheck

    def main():
        ok = modcheck.imports(__file__)
        # 이 모듈만의 확인을 여기 더합니다
        return modcheck.done("tc", ok)
"""
import importlib.util
import io
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def module_dir(check_file):
    """check.py의 자리에서 그 모듈의 폴더를 얻습니다."""
    return os.path.dirname(os.path.abspath(check_file))


def imports(check_file):
    """모듈의 scripts/를 실제로 불러 봅니다.

    문법만 보는 것과 다릅니다 — 없는 것을 import하거나 뜨는 도중에 터지는 경우는
    불러 봐야 걸립니다. 게이트가 문법은 따로 보므로 여기서는 뜨는지를 봅니다.
    """
    d = os.path.join(module_dir(check_file), "scripts")
    if not os.path.isdir(d):
        return []
    sys.path.insert(0, d)
    fails = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".py") or name.startswith("_"):
            continue
        path = os.path.join(d, name)
        spec = importlib.util.spec_from_file_location(name[:-3], path)
        try:
            spec.loader.exec_module(importlib.util.module_from_spec(spec))
        except Exception as e:                    # 뜨기만 하면 되므로 종류를 가리지 않는다
            fails.append("%s — %s: %s" % (name, type(e).__name__, e))
    return fails


def wrote(path, why):
    """산출을 하나 내 봤는지 봅니다. 비어 있으면 만들어진 것이 아닙니다."""
    try:
        if os.path.getsize(path) > 0:
            return []
    except OSError:
        pass
    return ["%s — %s" % (why, path)]


def done(name, *groups):
    """결과를 내고 종료 코드를 돌려줍니다. 0이 통과입니다."""
    fails = [f for g in groups for f in g]
    if not fails:
        print("모듈 점검 %s — 통과" % name)
        return 0
    print("모듈 점검 %s — %d건 걸렸습니다" % (name, len(fails)))
    for f in fails:
        print("  " + f)
    return 1
