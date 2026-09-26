# qa-site — QA · 역분석 문서를 인디고 마스터와 셸로 한 사이트처럼 엮습니다

역분석 · 기획서 분석 · 기능 골격 · QA 리포트 같은 문서를 **사이드바와 상단 바가 있는 한 사이트**로
만들 때 씁니다. 자기 마스터(인디고 · 라이트 기본 · 다크 토글)와 템플릿, 저장소 진입 페이지 생성기,
프로젝트 용어집 HTML 생성기를 가집니다.

## 언제 켜나

**저장소의 문서를 셸로 묶어 한 사이트처럼 보여 주는가?** 그렇다면 켭니다. 저장소 전체에 걸리는
모듈이라 `workspace.json`의 `modules`에 적습니다.

문서를 한 장씩 완결된 파일로 내고 허브로 잇는 저장소라면 켜지 않습니다 — base 마스터로 충분합니다.

## 켜면 따라오는 것

| | |
|---|---|
| 마스터 | `design-guide/` — 인디고 마스터 CSS · 동작 JS · 시각 규칙서. 이 모듈의 산출물에서는 base 마스터 대신 이것이 정본입니다 |
| 규칙 | `rules/qa-report-design.md` — 색 · 타이포 · 컴포넌트 · 셸 · 차트 · 다이어그램 |
| 서식 | `design-template/` — 기능 골격 · 역분석 · 기획서 분석 · 범용 기준서. 목록은 `qa-site-template-catalog.md` |
| 도구 | `scripts/shell.py`(셸) · `scripts/gen_intro_html.py`(루트 `index.html`) · `scripts/gen_dictionary_html.py`(프로젝트 용어집 HTML) |
| 다시 만드는 것 | 루트 `index.html`, 프로젝트의 dictionary md가 있으면 `docs/{접두}-dictionary.html` (`jobs.py`) |
| 저장소에 두는 것 | 루트 `structure.svg` — 그 저장소의 구조도. 진입 페이지가 읽어 싣습니다(없으면 건너뜁니다) |

## 전제 모듈

없습니다.

## 진입 페이지 문구

진입 페이지의 문장은 그 저장소의 사용자가 정한 문구입니다. `core/base/rules/change-scope.md` §3에
따라 고쳐 달라는 지시가 있을 때만 생성기의 문자열을 바꿉니다. 재생성은 계속합니다.
