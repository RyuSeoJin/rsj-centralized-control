# central-rules — 받아 가는 저장소를 위한 안내

이 저장소의 `core/`는 문서 제작 절차 · 작성 원칙 · 이력 · git · HTML 출력 규칙과, 골라 켜는 모듈
(UE 문서 · 기획서 · TC · QA 사이트 등)을 담고 있습니다. 작업 저장소는 `core/`를 복사해 쓰고, 규칙은
이 저장소에서만 고칩니다.

## 처음 받기

1. 받는 저장소 루트에 `workspace.json`을 씁니다(`core/base/rules/site-structure.md` §3).
2. 이 저장소의 도구로 받습니다.

   ```bash
   python {이 저장소 clone}/core/base/scripts/sync_core.py --from https://github.com/RyuSeoJin/rsj-centralized-control --repo-root {받는 저장소}
   ```
3. 받는 저장소 루트에 진입점과 저장소 이력을 둡니다 — 빈 서식은 `core/base/design-template/repo/`.
4. 기존 프로젝트 폴더가 있으면 옮기지 않고 등록합니다(`core/base/rules/project-scaffold.md` §5).
5. `python core/base/scripts/regen.py`로 읽기 게이트(`AGENTS.md` · `CLAUDE.md` 참조 규칙)를 만들고,
   `python core/base/scripts/check_rules.py`로 확인합니다.

## 다시 받기

```bash
python core/base/scripts/sync_core.py --from https://github.com/RyuSeoJin/rsj-centralized-control --check
python core/base/scripts/sync_core.py --from https://github.com/RyuSeoJin/rsj-centralized-control
```

받은 뒤 받는 저장소에서 `core/`를 고친 파일이 있으면 도구가 멈춥니다. 그 수정은 이 저장소로 먼저
옮깁니다(`core/base/rules/central-sync.md` §3).

## 모듈

```bash
python core/base/scripts/module.py list
```

목록은 분야별로 묶여 나옵니다. 하는 일에서 켤 모듈을 찾을 때는 [모듈 지도](core/modules/module-map.md)(분야별
질문 · 함께 쓰는 모듈 · 둘 중 하나를 고르는 기준)를 봅니다 — `regen.py`가 다시 만드는 생성물입니다.
모듈 하나하나의 소개는 그 모듈 폴더의 `module.md`에 있습니다. 모듈이 늘 때마다 어긋나지 않도록 이 파일에는
모듈 목록을 따로 적지 않습니다.
