# {프로젝트} — Penpot 화면 대응표

화면 키와 Penpot 보드를 잇는 표입니다. planning-spec의 「외부 디자인 도구의 화면 대응표」에 해당합니다.
링크 글자는 화면 키를 그대로 씁니다.

- **지위**: 파생 · 제안입니다. 기대값의 정본은 {기획 정본 경로}와 {구현 정본 경로}입니다. 이 표와 Penpot 파일은 정본을 바꾸지 않습니다.
- **기준**: {가로}×{세로} {기기}, 저충실도 와이어프레임. {YYYY-MM-DD} 사용자 확인 — {화면 수}개 화면, {설계 방향}.
- **파일**: Penpot {Penpot 프로젝트 이름}의 [{파일 이름}](https://design.penpot.app/#/workspace?team-id={team-id}&file-id={file-id}&page-id={page-id})
  - `Components` — 공통 컴포넌트 {수}개({부품 이름 나열})
  - `Wireframes` — 화면 보드 {수}장, 보드마다 아래에 설계 메모. 프로토타입 연결 {수}개, 시작 보드 {화면 키}
  - `Flow` — 전체 화면 흐름도. 표기는 중앙 흐름도 규칙(`core/base/rules/flowchart.md`)을 따르고, 〔추정〕은 정본에 없어 추정한 도형 · 연결입니다

## 구현 스택 판단

{무엇으로 화면을 만드는지와 그 근거}. {검사 탭의 코드를 쓰는지, 보드의 Flex · Grid 값을 사양으로 읽어 옮기는지}.

## 화면 대응표

| 화면 키 | 화면 | 종류 | 들어오는 곳 | 지금 구현(참고) |
|---|---|---|---|---|
| [S01](https://design.penpot.app/#/workspace?team-id={team-id}&file-id={file-id}&page-id={page-id}&board-id={board-id}) | {화면 이름} | 전체 화면 | {진입 버튼 · 조건} | {구현 파일 · 함수} |
| [S02](https://design.penpot.app/#/workspace?team-id={team-id}&file-id={file-id}&page-id={page-id}&board-id={board-id}) | {화면 이름} | 창 | S01 [{버튼}] | {구현 파일 · 함수} |

## 흐름 요약

- **진입**: S01 → [{버튼}] S02
- **종료**: S02 → [{버튼}] S01

## 정하지 않은 것

- {정본에 근거가 없어 추정한 연결 · 배치}
- {「구현과 다른 점」으로 제안한 것 중 반영 여부를 정하지 않은 것}
