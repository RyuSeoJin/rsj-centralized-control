# app-planning-slides — 앱 기획 문서를 프롬프트로 채워 Google Slides로 냅니다

앱 기획의 다섯 문서(프로젝트 개요서 · 정보 구조도 · 기능 정의서 · 와이어프레임 · 화면설계서)를
두 종류의 슬라이드로 만듭니다. **프로젝트 전체 문서** 한 벌과 **기능별 문서** 여러 벌입니다.
사용자가 프롬프트로 앱과 기능을 설명하면 정해진 입력(JSON)을 채우고, 도구가 그 입력에서 .pptx를
만듭니다. .pptx는 Google Drive에 올릴 때 Google Slides로 변환해 그대로 고칠 수 있게 만듭니다.

## 언제 켜나

**기획자 · 디자이너 · 개발자가 함께 보는 앱 기획 문서를 슬라이드로 공유하는가?** 그렇다면 켭니다.
구현 전 시스템 하나를 깊게 합의하는 HTML 기획서가 목적이면 `gdd` 모듈이 맞습니다.

## 켜면 따라오는 것

| 구분 | 내용 |
|---|---|
| 규칙 | `rules/planning-slides.md` — 두 문서의 구성, 정본과 공유본, 프롬프트로 채우는 순서, 입력 형식, Google Slides 변환 규칙 · `rules/slide-patterns.md` — 화면설계서 프레임, 장 구성 순서, 패턴 카탈로그, 가독성 · 일관성 규칙, 참고 자료 |
| 서식 | `design-template/` — 입력 예시 둘과 프롬프트 안내. 목록은 `app-planning-slides-template-catalog.md`이며, 고르는 법은 base 카탈로그가 정본입니다 |
| 도구 | `scripts/build_slides.py` — 입력 검증 · .pptx 생성 · 기능 ID 대조 · 변환 위험 점검(`lint`) · 견본 덱(`gallery`). 패턴은 `scripts/patterns.py`, 부품은 `scripts/slidekit.py` |
| 점검 | `check.py` — 도구가 뜨는가, 예시 둘로 만들어지는가, 변환 위험 요소가 없는가, 잘못된 입력을 막는가 |
| 프로젝트에 생기는 것 | `planning/` (모듈을 켤 때 `module.py`가 만듭니다) |
| 프로젝트가 정하는 값 | 입력 JSON의 모든 내용, Google Slides 공유본의 자리(링크는 프로젝트 change-log에 적습니다) |
| 필요한 것 | `python-pptx` — `requirements.txt` |

## 전제 모듈

없습니다.

## 읽기 게이트

| 상황 | 읽는 파일 | 멈추는 자리 |
|---|---|---|
| 기획 슬라이드를 만들거나 고칠 때 | `rules/planning-slides.md` · `rules/slide-patterns.md` · `design-template/prompt-guide.md` | 모르는 값은 묻거나 `?`로 남깁니다. 추측으로 채우지 않습니다 |
| Google Slides 공유본을 직접 고치기 시작할 때 | `rules/planning-slides.md` §2 | 정본이 공유본으로 넘어갔다는 사실을 change-log에 적기 전에는 입력에서 다시 만들지 않습니다 |
