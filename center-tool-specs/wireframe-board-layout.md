# 도구 명세 — 와이어프레임 보드 배치 도구(app-wireframe)

<!-- v1.0 · 2026-10-27: (추가) 설명 상자를 실제 높이로 쌓고 겹침 0을 확인하는 디자인 도구 스크립트 명세 -->

규칙 본문은 `core/modules/app-wireframe/rules/wireframe.md` 「보드 배치 — 설명 상자 쌓기」입니다.

## 1. 형태

app-wireframe 모듈은 Figma API를 직접 부르지 않습니다(module.md 「켜면 따라오는 것」). 그래서 이 도구는 **디자인 도구의
실행 기능(Figma 플러그인 API를 쓰는 코드 실행)에 그대로 넘기는 JavaScript 파일**로 둡니다.

- 자리: `core/modules/app-wireframe/scripts/board-layout.js`
- 맨 앞의 설정 객체(`RULE`)와 마지막 줄의 `apply`만 프로젝트가 바꿉니다. 설정은 프로젝트 입력에 두고 실행할 때 앞에 붙입니다.

```js
const RULE = {
  pageId: '{페이지 ID}',
  excludedSections: [],   // 구조가 다른 섹션(캡션 → 화면 → 설명) — 이유는 프로젝트 설정 옆 주석
  screenName: '^screen-', // 화면 프레임 이름 패턴
  userBox: '^유저 구역', systemBox: '^시스템 구역', linkMarker: '^연결 →',
  firstTop: 80, headGap: 8, headToUser: 20, userToSystem: 24, boxToScreen: 40, headToScreen: 24,
  rowHeaderGap: 16, rowGap: 96, obstacleGap: 48, bottomPad: 80, sidePad: 40,
  linkReach: 150,         // 상자 오른쪽 끝에서 이 거리 안의 연결 표식은 그 상자에 붙은 것으로 봅니다
};
```

수치는 받아 가는 저장소의 한 프로젝트가 쓴 기본값이며, 모듈은 기본값으로만 둡니다.

## 2. 하는 일

1. 섹션마다 화면 프레임을 찾고, 같은 x 위에 쌓인 머리(제목 글자 · 묶음 이름표) · 유저 구역 · 시스템 구역 상자를 그 화면에 묶습니다(스택).
2. 같은 높이에서 시작하는 스택을 한 행으로 묶습니다.
3. 행 안에서 띠(머리 · 유저 · 시스템 · 화면)마다 위끝을 맞추고, 각 띠는 **앞 띠의 실제 바닥 + 간격**에 둡니다(설명 상자가 없으면 머리 → 화면 간격).
4. 다음 행은 가로 범위가 겹치는 위 행의 바닥 + `rowGap`에 둡니다. 고정 상자(제작 범위 · 공통 규칙 메모)와 가로 범위가 겹치면 그 바닥 + `obstacleGap` 아래로 내립니다.
5. 연결 표식과 화살표는 `linkReach` 안에 붙은 상자와 같은 거리만큼 옮깁니다.
6. 제목 없는 화면은 자기 위치를 덮는 행에 넣고 보고서의 `untitled`에 적습니다.
7. 옮긴 뒤 같은 높이가 된 행을 합치고, 더 옮길 것이 없을 때까지 2 ~ 6을 반복합니다(최대 횟수를 두고, 넘으면 실패로 보고).
8. 섹션 크기를 내용 + 여백(`bottomPad` · `sidePad`)으로 맞춥니다.

## 3. 보고서(돌려주는 값)

```json
{"apply": false, "sections": 10, "moved": [{"section": "{ID}", "nodes": 12}],
 "overlaps": 0, "sectionOverlaps": 0, "looseMarkers": 0, "untitled": ["screen-…"], "passes": 2}
```

- `apply: false`이면 계산만 하고 노드를 옮기지 않습니다. 규칙은 계산 → 겹침 확인 → 적용 → 다시 계산의 순서를 요구합니다.
- `overlaps`(상자끼리) · `sectionOverlaps`(섹션끼리) · `looseMarkers`(어느 상자에도 붙지 않은 연결 표식)가 모두 0이어야 통과입니다.
- 적용한 뒤 다시 계산했을 때 `moved`가 비어 있어야 합니다(멱등).

## 4. 확인 방법

디자인 도구 없이 확인할 수 있도록, 배치 계산 부분(`planSection`)은 노드 목록(`{id, name, type, x, y, width, height}`)만 받는 순수 함수로
나눕니다. `check.py`는 Node가 있을 때 고정 높이로 겹치게 만든 예시 노드 목록을 넣어 겹침 0 · 연결 표식 동행 · 반복 적용 시 이동 0을 봅니다.

## 5. 근거

받아 가는 저장소의 한 프로젝트에서 자동 높이 설명 상자를 고정 자리에 두어 상자 · 화면이 겹쳤고, 프로젝트 스크립트로 해결했습니다
(2026-10-15). 열 개 섹션을 다시 배치해 겹침 0 · 섹션 겹침 0 · 떠 있는 연결 표식 0이었고, 다시 계산해도 옮길 것이 없었습니다.
