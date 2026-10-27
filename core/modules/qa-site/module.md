# qa-site — QA 분석 서식과 메뉴를 공통 문서 사이트에 더합니다

<!-- CHANGELOG · v2.1 · 2026-10-27: (추가) 측정 기록 보관 · 비교 규칙(rules/measurement-records.md)과 읽기 게이트 -->
<!-- v2.0 · 2026-10-12: (변경) 공통 디자인·셸·생성 도구를 document-site 책임으로 분리하고 QA 서식·메뉴만 유지 -->

역분석 · 기획서 분석 · 기능 골격과 TC 관계도처럼 **테스트 관점으로 읽는 문서**에 씁니다.
공통 디자인과 문서 사이트는 `document-site`가 맡으며, 이 모듈은 QA 서식과 메뉴만 더합니다.

## 언제 켜나

**공통 문서 사이트에 QA 분석 문서와 TC 관계도 서식이 필요한가?** 그렇다면 켭니다.
저장소 전체에 걸리는 워크스페이스 모듈이므로 `workspace.json`의 `modules`에 적습니다.
문서를 사이트로 묶기 위한 공통 기능만 필요하면 `document-site`를 사용합니다.

## 켜면 따라오는 것

| 구분 | 내용 |
|---|---|
| 서식 | `design-template/01-feature-tree.html` · `02-reverse-analysis.html` · `03-spec-analysis.html` — 기능 골격·TC 관계도, QA 역분석, 테스트 관점의 기획서 분석 |
| 선택 기준 | `design-template/qa-site-template-catalog.md` — QA 서식의 용도와 작업 유형 판별 |
| QA 메뉴 | `navigation.json` — 공통 문서 사이트에서 사용하는 QA 메뉴 정의 |
| 규칙 | `rules/measurement-records.md` — 성능 · 품질 측정 기록의 조건 기록, 비교 범위, 재측정 보관 |
| 공통 디자인 참조 | `../document-site/design-guide/`와 `../document-site/rules/document-design.md` — 마스터·컴포넌트·테마·셸의 기준 |
| 공통 도구 참조 | `document-site`의 셸·진입 페이지·프로젝트 용어집 생성 도구와 재생성 작업 |

범용 기준서와 지원 환경 작성 안내도 `document-site`에서 관리합니다. QA 문서에서 같은 디자인이
필요해도 마스터나 공통 생성기를 이 모듈에 복제하지 않습니다.

## 전제 모듈

`document-site`입니다. 공통 사이트의 적용·등록·재생성 방법은
`../document-site/module.md`를 따릅니다.

## 기획 사양과 QA 분석의 경계

기능 자체의 조건·화면·상태·예외를 작성하는 기준은 `planning-spec`의 책임입니다. 이 모듈은
등록된 기능 정본을 테스트 관점에서 분석하고 검수 내용을 표현합니다. TC와 관계없는 기능 사양을
QA 서식에 넣었다는 이유로 새 정본을 만들지 않습니다. 책임 범위와 승인 상태는
`../../base/rules/canonical-source.md`를 따릅니다.

역분석에서 관찰한 동작과 기획서에서 승인한 규칙을 구분합니다. 분석 결과나 QA 문서의 요약은
원래 기능 사양을 수정할 권한이 없으며, 사양 변경이 필요하면 해당 정본에 제안합니다.

## 읽기 게이트

| 상황 | 읽는 파일 | 멈추는 자리 |
|---|---|---|
| QA 서식을 고르거나 문서를 만들 때 | `design-template/qa-site-template-catalog.md` · `../document-site/module.md` · `../document-site/rules/document-design.md` | 등록 정본의 책임 범위와 승인 상태를 확인하지 못하면 기대값을 확정하지 않습니다 |
| 기능 사양 자체를 작성하거나 바꿀 때 | `../planning-spec/module.md` | 기획 모듈 활성화와 등록 정본을 확인하고 해당 모듈의 읽기 게이트를 따릅니다 |
| 측정 기록을 보관 · 정정하거나 수치를 비교할 때 | `rules/measurement-records.md` | 조건이 다르거나 「미확인」인 기록끼리는 개선 전후 비교로 합치지 않습니다 |

<!-- CHANGELOG · 2026-10-12: (변경) 참조를 항목 제목과 작업 유형 이름으로 표기 -->
