# -*- coding: utf-8 -*-
"""app-planning-slides 모듈 자기 점검 — 도구가 뜨고 두 문서가 만들어지는지 봅니다

무엇을 보나
----------
  ① scripts/의 도구를 실제로 불러 봅니다.
  ② design-template/의 예시 둘로 전체 문서 · 기능별 문서를 만들어 봅니다.
  ③ 만든 파일에 Google Slides 변환 때 굳는 요소(차트 · SmartArt · 그라데이션 · 그림자 ·
     허용하지 않은 글꼴)가 없는지 봅니다.
  ④ `all`이 기능 ID를 대조하는지, 잘못된 입력(영역 유형 · ID 중복 · 흐름도 연결 · 변경 표시)을
     막는지 봅니다.

무엇을 안 보나
-------------
  프로젝트 데이터를 읽지 않고, 슬라이드가 보기 좋은지는 보지 않습니다. 그림으로 확인하는 일은
  예시를 만들어 사람이 봅니다. 프로젝트에서 실제로 걸린 것이 나오면 그 케이스를 여기 더합니다.

사용법
------
    python core/modules/app-planning-slides/check.py        통과하면 exit 0
"""
import copy
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "base", "scripts"))
import modcheck  # noqa: E402

HERE = modcheck.module_dir(__file__)
sys.path.insert(0, os.path.join(HERE, "scripts"))


def main():
    fails = modcheck.imports(__file__)
    if fails:
        return modcheck.done("app-planning-slides", fails)
    import build_slides as b

    tpl = os.path.join(HERE, "design-template")
    ov = b.load(os.path.join(tpl, "overview.example.json"))
    ft = b.load(os.path.join(tpl, "feature.example.json"))
    tmp = tempfile.mkdtemp()
    try:
        # ② · ③ 예시 둘로 만들고 변환 위험을 봅니다
        for kind, src in (("overview", "overview.example.json"), ("feature", "feature.example.json")):
            out = os.path.join(tmp, kind + ".pptx")
            rc, _ = b.run(kind, os.path.join(tpl, src), out)
            if rc:
                fails.append("%s 예시가 만들어지지 않거나 변환 위험이 있습니다" % kind)
            fails += modcheck.wrote(out, "%s 예시 산출" % kind)

        # ④ all — 기능 ID 대조
        folder = os.path.join(tmp, "planning")
        os.makedirs(os.path.join(folder, "features"))
        with open(os.path.join(folder, "probe-overview.json"), "w", encoding="utf-8") as f:
            json.dump(ov, f, ensure_ascii=False)
        stray = copy.deepcopy(ft)
        stray["feature"]["id"] = "F-NOT-LISTED"
        with open(os.path.join(folder, "features", "F-NOT-LISTED.json"), "w", encoding="utf-8") as f:
            json.dump(stray, f, ensure_ascii=False)
        if b.run_all(folder, None) == 0:
            fails.append("목록에 없는 기능별 문서를 통과시켰습니다")

        # ④ 잘못된 입력을 막는가
        bad = copy.deepcopy(ft)
        bad["screens"][0]["regions"][0]["type"] = "hologram"
        if not b.validate("feature", bad)[0]:
            fails.append("알 수 없는 영역 유형을 통과시켰습니다")
        flow = copy.deepcopy(ft)
        flow["flow"]["edges"].append({"from": "n1", "to": "nowhere"})
        if not b.validate("feature", flow)[0]:
            fails.append("흐름도의 없는 노드 연결을 통과시켰습니다")
        mark = copy.deepcopy(ov)
        mark["ia"]["tree"][0]["children"][0]["change"] = "MAYBE"
        if not b.validate("overview", mark)[0]:
            fails.append("알 수 없는 변경 표시를 통과시켰습니다")
        dup = copy.deepcopy(ov)
        dup["features"].append(dict(dup["features"][0]))
        if not b.validate("overview", dup)[0]:
            fails.append("기능 ID 중복을 통과시켰습니다")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return modcheck.done("app-planning-slides", fails)


if __name__ == "__main__":
    sys.exit(main())
