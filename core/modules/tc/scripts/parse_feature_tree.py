# -*- coding: utf-8 -*-
"""
feature-tree.md (정본) -> 트리 구조 JSON

파이프라인에서의 위치
--------------------
  spec/{프로젝트}-feature-tree.md       (정본 — 손으로 고치는 유일한 파일)
    │  이 스크립트
    ▼
  nodes.json                            (트리 구조 데이터)
    │  케이스 전개(정상·경계·예외·우회)를 거쳐 tcs 배열 작성
    ▼
  input.json  ->  build_tc_template_xlsx.py  ->  TC 시트(xlsx)

이 스크립트는 기계적 변환만 담당한다. 케이스 전개·TN 부여는
rules/case-expansion.md, rules/depth-and-tn.md 규칙에 따라 별도로 수행한다.

정본 md 형식 v2 (2026-08-01 — 출처·범위 태그 추가, 지원은 선택으로)
---------------
    # {프로젝트} 기능 골격 v{X.Y}

    ## 트리
    - 대화 세션 [범위: 구현]
      - 재시도 [유형: 결정적] [P: High] [출처: REF] [범위: 구현] — 비고 텍스트
        - PRE: 로그인 상태
      - 백로그 [유형: 결정적] [P: Low] [출처: REF] [범위: 보류]
    - 외부 연동 [범위: 제외] — 사유 텍스트

    ## 미확인 목록
    - 목록 > 불러오기 | 한 번에 받는 개수 | design에서 확정

규칙:
  * 들여쓰기 2칸 = Depth 1단 (불릿 "- " 기준).
  * 태그는 대괄호 [키: 값] — 유형(검증유형), P(우선순위), 출처(REF/ADD),
    범위(구현/보류/제외), 지원(O/X/△/? — 역분석 트리용, 자사 기획 트리에서는 선택),
    상태(2026-08-04 신설 — 그 기능 단위를 확인해야 하는 게이팅·세션 상태를 `·` 구분으로 나열.
    선언된 상태마다 최소 한 케이스가 요구된다. **값은 프로젝트가 정합니다** — 그 서비스에
    어떤 게이팅이 있는지는 그 서비스의 사정이라 중앙에 목록을 두지 않습니다.
    정본은 TC 입력 json의 `gate_states`이고, 선언 배치 규칙은 rules/depth-and-tn.md §상태 축).
  * "PRE: "로 시작하는 자식 불릿은 노드가 아니라 부모의 Pre-Condition.
  * "— " 뒤는 비고. 미확인 목록은 "경로 | 값 | 확인 방법".
  * 형식이 바뀌면 이 독스트링과 파서를 함께 갱신한다(여기가 형식의 정본).

사용법:
    python parse_feature_tree.py feature-tree.md -o nodes.json
"""
import argparse
import json
import re
import sys

TAG_RE = re.compile(r"\[(유형|P|지원|출처|범위|상태):\s*([^\]]+)\]")
HEAD_RE = re.compile(r"^#\s+(.+?)\s+기능 골격\s+v([\d.]+)", re.M)


def parse(md_text):
    md_text = md_text.lstrip("﻿")  # BOM 제거
    project, version = "", ""
    m = HEAD_RE.search(md_text)
    if m:
        project, version = m.group(1).strip(), m.group(2)

    nodes, unknowns = [], []
    stack = []  # (depth, node) 경로 추적
    section = ""

    for raw in md_text.splitlines():
        if raw.startswith("## "):
            section = raw[3:].strip()
            continue
        m = re.match(r"^(\s*)-\s+(.*)$", raw)
        if not m:
            continue
        indent, text = len(m.group(1)), m.group(2).strip()

        if section == "미확인 목록":
            parts = [p.strip() for p in text.split("|")]
            unknowns.append({
                "path": parts[0] if parts else "",
                "value": parts[1] if len(parts) > 1 else "",
                "how": parts[2] if len(parts) > 2 else "",
            })
            continue
        if section != "트리":
            continue

        depth = indent // 2 + 1

        if text.startswith("PRE:"):
            # 부모 노드의 Pre-Condition
            if stack:
                stack[-1][1]["pre"].append(text[4:].strip())
            continue

        tags = dict(TAG_RE.findall(text))
        name = TAG_RE.sub("", text)
        note = ""
        if "—" in name:
            name, note = [s.strip() for s in name.split("—", 1)]
        name = name.strip()

        while stack and stack[-1][0] >= depth:
            stack.pop()
        path = [n["name"] for _, n in stack] + [name]

        node = {
            "name": name,
            "depth": depth,
            "path": path,
            "type": tags.get("유형", ""),
            "priority": tags.get("P", ""),
            "support": tags.get("지원", ""),
            "source": tags.get("출처", ""),
            "scope": tags.get("범위", ""),
            # 상태 선언 — 이 기능 단위를 확인해야 하는 상태 목록("·" 구분 원문 그대로).
            # 커버리지 대조(check_tc_coverage.py)가 기능 단위×상태 조합을 요구하는 근거다
            "states": tags.get("상태", ""),
            "pre": [],
            "note": note,
        }
        nodes.append(node)
        stack.append((depth, node))

    return {"project": project, "version": version,
            "nodes": nodes, "unknowns": unknowns}


def main():
    # 한글 출력이 콘솔 기본 인코딩으로 나가면, 다른 도구가 받아 읽을 때 깨집니다.
    # 오류는 stderr로 나가므로 둘 다 맞춥니다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default="nodes.json")
    args = ap.parse_args()
    # 없는 파일이면 스택을 쏟지 않고 한 줄로 알립니다 — 대개 경로를 잘못 친 경우입니다
    if not os.path.exists(args.input):
        sys.exit("그런 파일이 없습니다: %s" % args.input)

    with open(args.input, encoding="utf-8") as f:
        data = parse(f.read())

    if not data["nodes"]:
        sys.exit("트리 노드를 찾지 못함 — '## 트리' 섹션과 불릿 들여쓰기(2칸) 확인")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{len(data['nodes'])} nodes, {len(data['unknowns'])} unknowns -> {args.output}")


if __name__ == "__main__":
    main()
