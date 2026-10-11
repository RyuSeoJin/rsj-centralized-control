# app-planning-slides-template-catalog — app-planning-slides 모듈이 더하는 템플릿

`core/base/design-template/template-catalog.md`가 **고르는 법**의 정본이고, 이 문서는
**app-planning-slides를 켠 프로젝트에만 있는 것**의 목록입니다. 두 카탈로그를 함께 보고 고릅니다.

## 목록

| 템플릿 | 용도 | 이런 요청일 때 |
|---|---|---|
| 프로젝트 전체 문서 (`overview.example.json` → `build_slides.py overview`) | 개요서 · 정보 구조도 · 기능 정의서 목록을 한 벌의 슬라이드로 | 「프로젝트 기획서」 · 「앱 개요」 · 「IA」 · 「기능 목록」을 슬라이드로 |
| 기능별 문서 (`feature.example.json` → `build_slides.py feature`) | 기능 하나의 정의 상세 · 와이어프레임 · 화면설계서 · 예외 처리 | 「○○ 기능 기획서」 · 「화면설계서」 · 「스토리보드」 · 「와이어프레임」을 슬라이드로 |

템플릿은 .pptx 파일이 아니라 **입력 형식 + 생성 도구**입니다. 빈 서식 파일을 두면 사람이 그 위에
직접 쓰기 시작해 정본이 갈립니다.

### 부속 문서

| 파일 | 역할 |
|---|---|
| `prompt-guide.md` | 사용자 프롬프트 예시와, 입력을 채우기 전에 물을 것 |
| 견본 덱 (`build_slides.py gallery {폴더}`) | 예시 입력 둘로 **모든 패턴이 들어간** 두 문서를 만듭니다. 어떤 장이 어떻게 생기는지 고르기 전에 이것을 봅니다. 패턴 목록과 한도는 `../rules/slide-patterns.md` §3 |
| `overview.example.json` · `feature.example.json` | 입력 형식의 예시. 선택 자리까지 모두 채워 두었습니다. 모듈 점검(`check.py`)이 이 둘로 만들어 봅니다 |

## 판별 기준 — 여기로 오는 경우

요청의 **산출이 팀이 함께 고치는 슬라이드(Google Slides)**이고 내용이 앱 기획이면 여기입니다.
읽는 HTML 문서는 base 카탈로그가, 시스템 하나를 깊게 합의하는 HTML 기획서는 그 모듈의 카탈로그가
맡습니다. Case A/B/C 판별과 템플릿 공통 규칙은 **base 카탈로그가 정본**입니다.

## 버전

| 템플릿 | 버전 |
|---|---|
| 프로젝트 전체 문서 | v1.1 (`app-planning/overview@1`) — 화면 목록 · 여정 · 용어 · 정책 · 우선순위 · 로드맵 더함 |
| 기능별 문서 | v1.1 (`app-planning/feature@1`) — 화면 정보 띠 · Description · 스토리 · 흐름도 · 비교 · 화면 상태 더함 |
