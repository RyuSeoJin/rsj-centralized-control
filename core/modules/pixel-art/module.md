# pixel-art — 픽셀 아트 그림을 같은 규칙으로 만들고 화면에 매끄럽게 올립니다

캐릭터를 한 장씩 따로 그리면 등신 · 눈높이 · 선 처리 · 색이 캐릭터마다 조금씩 갈리고, 그렇게
갈린 캐릭터들은 같은 애니메이션 뼈대에 얹을 수 없습니다. 이 모듈은 **방법**(비율 재는 법 · 팔레트
구조 · 외곽선과 셰이딩 규칙 · 제작 절차 · 검수 · 리깅 규약)과 그 방법을 도는 **도구**를 담고,
캔버스 크기 · 등신 · 팔레트 색 · 관절 좌표 같은 **값**은 켠 프로젝트의 사양 파일이 정합니다.

캐릭터에서 시작해 타일 · 배경, UI · 아이콘, 이펙트 · 오브젝트까지 같은 팔레트 · 광원 규칙으로 묶고, 그 그림을
게임 화면에 올릴 때의 해상도 · 카메라 · 움직임 규칙까지 다룹니다. 그림을 잘 그려도 소수배 확대나 소수
좌표 카메라에서는 도트가 흔들려 보이기 때문입니다.

## 언제 켜나

픽셀 아트로 게임 · 앱의 그림(캐릭터 · 타일 · 배경 · UI · 이펙트)을 만들거나, 픽셀 아트를 화면에 올리는 규칙(해상도 · 카메라 · 움직임)을 정하는가? 그렇다면 켭니다.

## 켜면 따라오는 것

| 갈래 | 무엇 |
|---|---|
| 규칙 | `rules/pixel-style.md`(스타일 · 치비 §9 · 레퍼런스 세트 §10) · `rules/pixel-pipeline.md`(제작 절차) · `rules/pixel-rig.md`(Spine 리깅) · `rules/pixel-anim.md`(프레임 애니메이션) · `rules/pixel-motion.md`(움직임 원리) · `rules/pixel-render.md`(화면에 올리기 · 카메라) · `rules/pixel-tile.md`(타일 · 배경) · `rules/pixel-ui.md`(UI · 아이콘 · 글꼴) · `rules/pixel-fx.md`(이펙트 · 오브젝트) |
| 용어 | `pixel-art-dictionary.md` |
| 도구 | `scripts/`의 변환(`pixelize.py`) · 팔레트 제안(`palette_suggest.py`) · 레이어 쌓기(`sprite_build.py`) · 동작 합성(`anim_build.py`) · 검사(`lint.py`) · 라인업 시트(`lineup.py`) · Spine 뼈대(`spine_rig.py`) · 타일셋 검사(`tile_check.py`) · 아이콘 시트 검사(`icon_check.py`) · 기준 해상도 배율 계획(`scale_plan.py`). 검사 도구는 결함을 일부러 넣은 그림으로 스스로를 시험합니다 |
| 프로젝트 폴더 | `source/`(입력 그림) · `sprites/`(원본 `.aseprite`) · `export/`(다시 만들 수 있는 파생물). 타일은 각 폴더의 `tiles/` 아래, 이펙트 · 오브젝트는 `export/fx/` · `export/objects/` |
| 프로젝트가 쓰는 정본 | 사양 파일 `spec/design/pixel-spec-{용도}.json` — 켠 뒤 사람이 씁니다. 예시는 `pixel-spec.example.json`(등신대) · `pixel-spec-field.example.json`(치비 · 동작) · `pixel-spec-tile.example.json`(타일 · 배경) |
| 의존성 | `requirements.txt` (Pillow) |

사양 파일은 켤 때 만들지 않습니다. 빈 사양이 있으면 도구가 그 값으로 그림을 찍어 내고, 그것이
「값이 정해졌다」는 신호로 읽히기 때문입니다.

## 전제 모듈

없습니다.

## 작업 환경

Aseprite 실행 파일을 찾고 배치 모드로 돌리는 일은 컴퓨터마다 다른 환경의 일이라, 호스트 모듈
`aseprite`가 맡습니다. 호스트 모듈은 켜는 대상이 아니므로 위 전제 절에 적지 않고, 아래 읽기
게이트의 첫 줄로 부릅니다. 이 모듈을 켠 프로젝트에서만 환경 점검이 작업 흐름에 들어오고, 다른
프로젝트나 저장소 진입점(`CLAUDE.md`)은 이 정보를 싣지 않습니다.

```bash
python core/modules/aseprite/scripts/aseprite_env.py
```

## 읽기 게이트

| 상황 | 읽는 파일 | 멈추는 자리 |
|---|---|---|
| 이 모듈로 작업을 시작할 때 (세션마다 한 번) | `core/modules/aseprite/module.md` — 위 점검 명령을 돌립니다 | 점검이 실패하면 그 문서의 「새 컴퓨터 설치」를 먼저 끝냅니다. 설치는 컴퓨터를 바꾸는 일이라 사용자 승인 뒤에만 합니다 |
| 캐릭터를 새로 만들거나 다듬을 때 | `rules/pixel-style.md` · `rules/pixel-pipeline.md` · 프로젝트의 사양 파일 | 사양 파일이 없으면 값을 추측하지 않고 사양부터 확정받습니다 |
| 파츠를 나누거나 Spine으로 보낼 때 | `rules/pixel-rig.md` | 사양 파일의 슬롯 · 뼈대를 캐릭터마다 바꾸지 않습니다 |
| 동작(프레임 애니메이션)을 만들 때 | `rules/pixel-anim.md` | 동작은 공통 몸체에만 그리고, 캐릭터별로 동작 프레임을 새로 그리지 않습니다 |
| 동작의 타이밍 · 이동 속도 · 타격감을 정할 때 | `rules/pixel-motion.md` (나눠 얹는 규약은 `rules/pixel-anim.md`) | 오래 유지되는 이동 속도가 §7-1 표의 「좋음 · 쓸 만함」 밖이면 멈추고 확인받습니다 |
| 게임 화면 · 카메라 · 해상도를 정하거나 떨림을 고칠 때 | `rules/pixel-render.md` · 사양 파일의 `render` 절 | 기준 해상도와 `scale_mode`가 정해지지 않았으면 값을 추측하지 않고 `scripts/scale_plan.py` 표를 보여 확정받습니다. 소수배(`fractional`)는 change-log 현행 기준에 예외로 적힌 경우에만 씁니다 |
| 타일 · 배경 · 패럴랙스용 그림을 만들 때 | `rules/pixel-tile.md` · 프로젝트의 타일 사양 파일 · 캐릭터 사양(캐릭터 상자 · 광원 · 공유 램프) | 타일 사양이 없으면 타일 크기 · 시점을 추측하지 않고 사양부터 확정받습니다. 이미 쓰는 시트 칸은 옮기지 않습니다 |
| UI · 아이콘 · 패널 · 픽셀 글꼴을 만들 때 | `rules/pixel-ui.md` · 프로젝트의 UI 사양 파일 | 아이콘을 축소해 다른 크기를 만들지 않습니다. 한글 글꼴 크기 · 글꼴 라이선스가 정해지기 전에는 글을 얹지 않습니다 |
| 이펙트 · 오브젝트를 만들 때 | `rules/pixel-fx.md` (타이밍은 `rules/pixel-motion.md`, 화면 처리는 `rules/pixel-render.md`) | 앵커 · 원점 · 혼합 방식을 사양에 적기 전에는 내보내지 않습니다 |
| 등신 · 캔버스 · 팔레트를 바꿀 때 | 프로젝트 change-log의 현행 기준 | 이미 만든 캐릭터를 모두 다시 맞춰야 하므로 승인 전에는 바꾸지 않습니다 |

## 자기 점검

```bash
python core/modules/pixel-art/check.py
```

예시 사양으로 「변환 → 검사 → Lua → Spine 뼈대」 한 벌을 돌려 보고, 검사 도구 넷(`lint` · `tile_check` ·
`icon_check` · `scale_plan`)의 자기 시험을 돌립니다. Aseprite 실행은 컴퓨터
환경이라 점검에 넣지 않습니다.
