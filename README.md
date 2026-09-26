# central-rules — 받아 가는 저장소를 위한 안내

이 저장소의 `core/`는 문서 제작 절차 · 작성 원칙 · 이력 · git · HTML 출력 규칙과, 골라 켜는 모듈
(UE 문서 · 기획서 · TC · QA 사이트 등)을 담고 있습니다. 작업 저장소는 `core/`를 복사해 쓰고, 규칙은
이 저장소에서만 고칩니다.

## 처음 받기

1. 받는 저장소 루트에 `workspace.json`을 씁니다(`core/base/rules/site-structure.md` §3).
2. 이 저장소의 도구로 받습니다.

   ```bash
   python {이 저장소}/core/base/scripts/sync_core.py --from {이 저장소} --repo-root {받는 저장소}
   ```
3. 받는 저장소 루트에 진입점과 저장소 이력을 둡니다 — 빈 서식은 `core/base/design-template/repo/`.
4. 기존 프로젝트 폴더가 있으면 옮기지 않고 등록합니다(`core/base/rules/project-scaffold.md` §5).
5. `python core/base/scripts/regen.py`로 읽기 게이트(`AGENTS.md` · `CLAUDE.md` 참조 규칙)를 만들고,
   `python core/base/scripts/check_rules.py`로 확인합니다.

## 다시 받기

```bash
python core/base/scripts/sync_core.py --from {이 저장소} --check
python core/base/scripts/sync_core.py --from {이 저장소}
```

받은 뒤 받는 저장소에서 `core/`를 고친 파일이 있으면 도구가 멈춥니다. 그 수정은 이 저장소로 먼저
옮깁니다(`core/base/rules/central-sync.md` §3).

## 모듈

```bash
python core/base/scripts/module.py list
```

| 모듈 | 무엇 |
|---|---|
| `ue-doc` | 언리얼 엔진 문서 — 지식 위키 · 프로젝트 트랙, 에셋 분석 · 아키텍처 · 로드맵 · 데이터 지도 템플릿 |
| `gdd` | 코드 전 시스템 기획서 · 콘텐츠 총괄표 · 기획서 → 프로토타입 → 구현 순서 |
| `ue-build` | UE C++ 명령 빌드 · 게임 창 조작 점검 절차와 함정 |
| `ue-localization` | 시트 원본 → UE 표준 번역 |
| `qa-site` | QA · 역분석 문서를 인디고 마스터와 셸로 엮는 사이트 (워크스페이스 모듈) |
| `tc` · `automation` · `sut` · `llm` | 테스트 케이스 설계 · 자동화 · 검증 대상 제작 · LLM 출력 검증 |
| `html-design-kit` · `app-preview` | 부품 조립형 HTML · 앱 화면 흐름 미리보기 |
| `android-emulator` | Android 에뮬레이터 설치 · 점검 (호스트 모듈) |
