# simulator — 앱 시뮬레이터의 구조와 조립 규칙

## 1. 구조

시뮬레이터는 **셸 문서 하나 안에 앱 문서 하나**를 iframe으로 넣은 구조입니다.

| 층 | 하는 일 | 누가 만드나 |
|---|---|---|
| 셸 | 기기 틀(크기 · 회전), 개발용 조작 패널, 캡처 · 녹화, 탐색기 연결 전달 | 셸 화면은 프로젝트, 공용 동작은 모듈 실행기(`SimShell`) |
| 앱 문서 | 프로토타입 앱 화면과 동작. 에셋은 data URL로 담습니다 | 프로젝트 |

- 앱 문서는 셸의 `#app` iframe에 문자열로 써 넣습니다(`contentDocument.write`). 파일 하나로 열려야 하므로 앱 문서를 별도 파일로 두지 않습니다.
- 셸과 앱은 `postMessage`로만 대화합니다. 채널 이름은 프로젝트가 정하되 **셸 → 앱 명령 · 앱 → 셸 상태 · 탐색기 연결(앱이 받는 쪽 · 앱이 보내는 쪽)**을 서로 다른 채널로 둡니다.
- 크기가 큰 에셋(영상 · 그림)도 담기 때문에 산출물이 수십 MB가 될 수 있습니다. 앱 코드가 부르지 않는 에셋은 조립할 때 빼는 것을 권합니다(§4 `keep`).

## 2. 탐색기 연결 (`SimShell.wfx` · `SimShell.relay`)

워크플로우 탐색기는 시뮬레이터를 `?wfx`가 붙은 주소의 iframe으로 엽니다.

- `SimShell.wfx()` — 셸 주소에 `?wfx`가 있으면 참입니다. 셸은 이때 앱 문서에 표시(예: `window.{프로젝트}_WFX = true`)를 먼저 넣어, 앱의 연결 코드가 켜지게 합니다. 탐색기 안에서 연 시뮬레이터는 단독으로 연 것과 저장 자리를 나눕니다(탐색기의 상태 이동이 진행 기록을 덮어쓰기 때문).
- `SimShell.relay(frame, {host, app})` — 탐색기(부모 창)의 `wfx-host`를 앱의 `host` 채널로, 앱의 `app` 채널을 탐색기의 `wfx-app`으로 옮깁니다. 셸이 탐색기 안에 있을 때만 동작합니다.
- 메시지 내용(`hello` · `goto` · `press` / `ready` · `goto` · `press` · `action` · `event`와 판정용 상태 요약 `snap`)은 탐색기 규약이 정본입니다(→ `core/modules/workflow-explorer/rules/explorer.md` §4). 앱 쪽 연결 코드(사건 알림 · 상태 이동 준비 · `snap`)는 앱마다 함수가 달라 프로젝트가 씁니다.

## 3. 캡처 · 녹화 (`SimShell.capture`)

브라우저의 탭 화면 공유(`getDisplayMedia` · 「이 탭」)로 **보이는 그대로**(영상 · 흐림 효과 포함) 기기 화면을 저장합니다.

- 셸에는 `#capture`(캡처) · `#capture-stop`(연결 끊기) · `#capture-frame`(기기 틀 포함 체크) · `#capture-status`(안내 문구) · `#record`(녹화 시작 · 종료) 요소가 있어야 합니다.
- `SimShell.capture({frame, device, prefix, screenName})` — `frame`은 앱 iframe, `device`는 기기 틀 요소, `prefix`는 저장 파일 이름 앞부분, `screenName()`은 지금 화면 이름을 돌려주는 함수입니다(실패하면 `screen`). 파일 이름은 `{prefix}-{화면}[-frame]-{날짜시각}.png|mp4|webm`입니다.
- Chrome · Edge는 영역 캡처(`CropTarget`)로 대상 요소만 받고, 못 쓰면 창 전체 장면에서 좌표로 자릅니다. 기기 틀이 창 밖으로 나가 있으면 잠시 스크롤했다가 되돌립니다.
- 화면만 찍으면 실제 스크린샷처럼 모서리를 자르지 않고, 기기 틀 포함이면 둥근 모서리 밖을 투명하게 둡니다. 녹화는 화면만이면 MP4(지원할 때), 틀 포함이면 투명을 담는 WebM입니다.

## 4. 조립 (`scripts/build_simulator.py`)

프로젝트 조립 스크립트는 **어떤 소스를 어떤 순서로 붙일지**만 정하고, 아래 일은 모듈 도구로 합니다.

| 함수 | 하는 일 |
|---|---|
| `inline_assets(css, 에셋 폴더)` | CSS의 `{{asset:이름}}`을 그 파일의 data URL로 바꿉니다 |
| `collect_assets(폴더, keep, assets)` | 에셋을 이름순으로 담습니다. 내용이 같은 파일은 한 번만 담고 나머지는 별칭(`{이름: 원래 이름}`)으로 돌려줍니다. `keep(path)`로 뺄 것을 고릅니다 |
| `js_json(값)` | `<script>` 안에 넣어도 태그가 끊기지 않는 JSON |
| `runtime()` | 셸 공용 실행기 내용 — 셸의 `{{sim-shell-js}}` 자리에 넣습니다. 셸 스크립트에서 `SimShell`을 쓰기 전에 와야 합니다 |
| `fill(문서, 토큰)` | `{{토큰}}`을 채우고, 채우지 못한 토큰이 남으면 멈춥니다 |
| `write_or_check(산출물, 결과, check)` | 산출물을 쓰거나, `--check`면 지금 파일과 같은지만 봅니다(재생성 누락 확인) |

산출물은 자기완결 HTML 한 장이며 네트워크 요청을 하지 않습니다(→ `core/base/rules/html-output.md`). 시뮬레이터는 프로그램이라 문서 디자인 마스터를 따르지 않고 셸 화면은 프로젝트가 정합니다.
