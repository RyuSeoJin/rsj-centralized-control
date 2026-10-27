# document-site — 공통 HTML 디자인과 문서 탐색을 제공합니다

<!-- CHANGELOG · v1.1 · 2026-10-27: (추가) 주제별 문서 허브와 묶음 허브의 규칙 위치 · 허브 생성기의 경계 -->
<!-- CHANGELOG · v1.0 · 2026-10-12: 공통 HTML 기반을 QA 서식에서 분리 -->

저장소 문서를 공통 디자인 · 사이드바 · 상단 바 · 테마로 연결합니다. 기획 내용과 QA 판정은
각 담당 모듈이 정하고, 이 모듈은 표현과 탐색을 제공합니다.

## 언제 켜나

**저장소의 문서를 공통 셸과 디자인으로 연결할 때** 켭니다. workspace.json의 modules에 등록합니다.

## 켜면 따라오는 것

| 구분 | 내용 |
|---|---|
| 마스터 | `design-guide/` — 공통 CSS · 동작 JS · 시각 규칙서 |
| 규칙 | `rules/document-design.md` — 디자인 · 셸 · 차트 · 다이어그램 표현, 주제별 문서 허브와 묶음 허브 |
| 서식 | `design-template/document-site-template-catalog.md` — 범용 기준서와 지원 환경 안내 |
| 도구 | `scripts/shell.py` · `scripts/gen_intro_html.py` · `scripts/gen_dictionary_html.py` |
| 재생성 | `jobs.py` — 루트 index.html과 정본이 있는 프로젝트의 용어집 HTML |
| 분야별 확장 | 켠 모듈의 navigation.json에서 프로젝트 메뉴를 읽습니다 |

## 전제 모듈

없습니다.

## 경계와 확장

정본 관리는 `../../base/rules/canonical-source.md`, 공통 출력은 `../../base/rules/html-output.md`를
따릅니다. HTML의 기획 내용은 등록된 정본을 참조합니다. 범용 표 · 칩 · 트리의 표현은 제공하지만
검증 유형의 뜻이나 테스트 집계는 정의하지 않습니다. 부품 조립 도구와 문서 사이트 셸은 별개입니다.

분야별 모듈은 navigation.json의 project_items에 id · label · path · order를 선언합니다.
path는 projects/로 시작하는 저장소 상대 경로이며 {slug} · {prefix}를 사용할 수 있습니다.
기본 메뉴와 ID가 겹치거나 상위 경로 이동이 있으면 오류입니다. 활성 모듈만 읽고 order 순으로
정렬합니다. 공통 셸에 특정 분야 메뉴를 직접 추가하지 않습니다.

진입 페이지의 사용자 확정 문구는 그대로 유지합니다. 재생성과 문구 변경은 구분합니다.

프로젝트 허브는 파일 목록이 아니라 주제 탭으로 묶고, 여러 프로젝트를 한 묶음으로 운영하면 통합
허브와 업무별 허브를 함께 만듭니다(`rules/document-design.md` 「주제별 문서 허브」 · 「묶음 허브 —
통합 허브와 업무별 허브」). 묶음이 무엇이고 모듈 설정을 어떻게 물려받는지는 base의
`../../base/rules/site-structure.md`가 정하며, 이 모듈은 허브의 모양과 생성 계약만 정합니다.
