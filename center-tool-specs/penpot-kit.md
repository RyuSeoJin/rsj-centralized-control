# 도구 명세 — Penpot 그리기 키트(penpot-ux)

<!-- v1.0 · 2026-10-30: (추가) 화면 사양 JSON을 읽어 Components · Wireframes · Flow 세 페이지를 그리는 Penpot 플러그인 키트 명세 -->

규칙 본문은 `core/modules/penpot-ux/rules/penpot.md` 「코드로 그릴 때」이고, `Flow` 페이지의 도형 · 선은
`core/base/rules/flowchart.md`를 따릅니다. 받아 가는 저장소의 한 프로젝트가 화면 21장 · 컴포넌트 18개 · 흐름도를
플러그인 코드 하나로 그린 것이 근거입니다. 그 코드는 범용 부품과 프로젝트 화면 내용이 한 파일에 섞여 있었습니다.

## 1. 형태

- 자리: `core/modules/penpot-ux/scripts/penpot-kit.js`(범용 부품) · `scripts/penpot-build.js`(사양을 읽어 그림) · `scripts/plugin/`(manifest · UI)
- 프로젝트는 화면 사양 JSON(`design/penpot-spec.json`)만 씁니다. 화면 내용을 키트 코드에 적지 않습니다.
- 실행은 Penpot 플러그인 관리자 등록이 기본입니다. 플러그인 파일을 띄우는 작은 로컬 서버 명령을 함께 둡니다.

## 2. 범용 부품(`penpot-kit.js`)

| 함수 | 하는 일 |
|---|---|
| `board(name, opts)` | 보드 만들기 — 크기 · 채우기 · 테두리 · 반경 · 잘라 내기, `dir`가 있으면 Flex(방향 · 간격 · 여백 · 정렬 · 줄바꿈 · 내용에 맞춤), `grid`가 있으면 Grid |
| `text(str, size, weight, color)` | 글자 — 글꼴(프로젝트 설정) · 자동 폭 |
| `add(parent, child, hSizing, vSizing)` | 레이아웃 자식으로 넣고 고정 · 채우기 · 내용에 맞춤 지정 |
| `component(name, board)` · `instance(name, texts)` | 메인 컴포넌트 만들기 · 인스턴스를 놓고 이름으로 글 바꾸기(빈 글이면 그 칸 숨김) |
| `link(shape, destBoard)` | 클릭 → 이동 프로토타입 연결. 실패는 로그로 남기고 멈추지 않음 |
| `onPage(name, fn)` | 페이지가 없으면 만들고 열어서 `fn` 실행 |
| `flow.*` | 흐름도 도형(알약 · 사각형 · 평행사변형 · 마름모 · 공통 처리 · 원 · 오각형 연결자 · 서브루틴)과 직각 연결선 · 라벨 상자. 색과 모양은 `flowchart.md`의 값 |

## 3. 화면 사양 JSON

```json
{
  "board": {"width": 1920, "height": 1080},
  "font": {"family": "{글꼴}"},
  "components": [{"name": "버튼/주", "kind": "button"}],
  "screens": [{"key": "S01", "name": "{화면 이름}", "kind": "full",
               "layout": {"grid": [3, 1], "areas": ["{구역}", "{구역}", "{구역}"]},
               "items": [{"area": "{구역}", "use": "버튼/주", "text": "{버튼}", "to": "S02"}],
               "notes": {"diff": ["{구현과 다른 점}"], "open": ["{정하지 않은 것}"]}}],
  "flow": {"nodes": [{"id": "S01", "type": "output", "lane": "s", "text": "S01 {화면 이름}"}],
           "edges": [{"from": "S01", "to": "A1", "kind": "normal"}]}
}
```

`flow`는 `flowchart.md`의 노드 종류(`type`) · 구역(`lane`) · 연결 종류(`kind`)를 그대로 씁니다.

## 4. 돌려주는 값과 확인

- 그린 뒤 화면 키 → 보드 id 목록을 돌려주고, 이것으로 화면 대응표의 보드 링크를 채웁니다(`screen_map.py`로 검사).
- 프로토타입 연결마다 실제 도착 보드 id를 돌려줍니다. 연결 수만 세지 않습니다(`penpot.md` 「검수」).
- 클립보드를 쓰지 않습니다.

## 5. 시험

- 사양 JSON 검사(키 중복 · 없는 `to` · 흐름 노드의 종류 · 구역 · 연결 종류)를 `check.py`에 둡니다. Penpot 없이 돕니다.
- 그리기 자체는 Penpot이 있어야 하므로 자동 시험에 넣지 않고, 첫 프로젝트에서 사람이 보드 · 흐름도 PNG로 확인합니다.
