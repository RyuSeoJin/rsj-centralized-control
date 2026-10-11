# -*- coding: utf-8 -*-
# v1.3 · 2026-10-12: 흐름 ID와 분기·복귀 구조 경고 회귀 검사 추가
# v1.2 · 2026-10-12: 미등록 이동·처리 노드 혼입·연결 화면 ID 검사와 기존 예시 호환 점검 추가
"""app-planning-slides 모듈 자기 점검 — 도구가 뜨고 두 문서가 만들어지는지 봅니다

무엇을 보나
----------
  ① scripts/의 도구를 실제로 불러 봅니다.
  ② design-template/의 예시 둘로 전체 문서 · 기능별 문서를 만들어 봅니다.
  ③ 만든 파일에 Google Slides 변환 때 굳는 요소(차트 · SmartArt · 그라데이션 · 그림자 ·
     허용하지 않은 글꼴)가 없는지 봅니다.
  ④ `all`이 기능 ID를 대조하는지, 잘못된 입력(영역 유형 · ID 중복 · 흐름도 연결 · 변경 표시 ·
     범위 밖 MoSCoW 충돌 · 경로 밖 예외 갈래)을 막는지 봅니다.

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
        clash = copy.deepcopy(ov)
        clash["features"][0]["scope"] = "out"           # 범위 밖인데 moscow는 must
        if not b.validate("overview", clash)[0]:
            fails.append("범위 밖 기능의 MoSCoW 충돌을 통과시켰습니다")
        branch = copy.deepcopy(ov)
        branch["ia"]["flows"][0].setdefault("exceptions", []).append({"from": "S9-99", "when": "?", "to": "S1-01"})
        if not b.validate("overview", branch)[0]:
            fails.append("흐름 경로에 없는 예외 갈래를 통과시켰습니다")

        # 화면 사이 처리 노드를 화면처럼 그리던 실제 누락을 일반화한 회귀 사례입니다.
        for target in ("n4", "UNREGISTERED", None, "", 7):
            move = copy.deepcopy(ft)
            move["screens"][0]["next"][0]["to"] = target
            errors, _ = b.validate("feature", move)
            if not any("이동" in e for e in errors):
                fails.append("잘못된 화면 이동 대상을 통과시켰습니다: %r" % target)
        disguised = copy.deepcopy(ft)
        disguised["linked_screens"].append({"id": "n4", "name": "처리 노드"})
        disguised["screens"][0]["next"][0]["to"] = "n4"
        if not any("화면이 아닌" in e for e in b.validate("feature", disguised)[0]):
            fails.append("처리 노드를 연결 화면으로 등록해 검사를 우회했습니다")
        for sid in ("S2-02", "S1-01", None, ""):
            catalog = copy.deepcopy(ft)
            catalog["linked_screens"].append({"id": sid, "name": "중복 또는 빈 ID"})
            if not b.validate("feature", catalog)[0]:
                fails.append("잘못된 연결 화면 ID를 통과시켰습니다: %r" % sid)
        shared = copy.deepcopy(ft)
        shared["flow"]["nodes"].append({"id": "S2-02", "type": "screen", "label": "모임 상세", "lane": "앱"})
        if b.validate("feature", shared)[0]:
            fails.append("실제 화면 노드의 기존 ID 재사용을 막았습니다")
        for sid in ("n1", None, "", 7):
            bad_id = copy.deepcopy(ft)
            bad_id["flow"]["nodes"].append({"id": sid, "type": "process", "label": "검사", "lane": "앱"})
            if not any("노드 ID" in e for e in b.validate("feature", bad_id)[0]):
                fails.append("빈 값 또는 중복 흐름 ID를 통과시켰습니다: %r" % sid)
        branch = copy.deepcopy(ft)
        branch["flow"]["edges"] = [e for e in branch["flow"]["edges"] if not (e["from"] == "n2" and e.get("label") == "아니오")]
        if not any("조건 출구" in w for w in b.validate("feature", branch)[1]):
            fails.append("조건 출구 누락을 알리지 않았습니다")
        unlabeled = copy.deepcopy(ft)
        for edge in unlabeled["flow"]["edges"]:
            if edge["from"] == "n2": edge.pop("label", None)
        if not any("분기 라벨" in w for w in b.validate("feature", unlabeled)[1]):
            fails.append("분기 라벨 누락을 알리지 않았습니다")
        dead = copy.deepcopy(ft)
        dead["flow"]["edges"] = [e for e in dead["flow"]["edges"] if e["from"] != "n4"]
        warnings = b.validate("feature", dead)[1]
        if not any("n4: 출구" in w for w in warnings) or any("n7: 출구" in w for w in warnings):
            fails.append("처리 출구 누락과 정상 종료를 구분하지 못했습니다")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return modcheck.done("app-planning-slides", fails)


if __name__ == "__main__":
    sys.exit(main())
