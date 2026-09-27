# pixel-pipeline — 컬러 그림에서 픽셀 캐릭터와 Spine 파츠까지 가는 제작 절차

등신대 픽셀 캐릭터는 한 픽셀씩 좌표로 찍어서는 얼굴 · 손 · 주름이 나오지 않습니다. 그래서
**고해상도 컬러 그림을 줄여 초안을 얻고, 자동 변환이 약한 자리만 손으로 다시 그리는** 순서로
만듭니다. 이 문서는 그 순서를 정합니다. 절차서이므로 지시가 먼저 오고 이유는 뒤에 붙습니다.

스타일 기준은 `pixel-style.md`, 파츠와 뼈대는 `pixel-rig.md`가 정합니다.

---

## 한눈에 보기

```
사양 파일 확정 (spec/design/pixel-spec.json)
  → ① 입력 그림 준비 (source/)
  → ② 픽셀 변환      scripts/pixelize.py
  → ③ 손으로 다듬기   Aseprite
  → ④ 검수           scripts/lint.py · scripts/lineup.py
  → ⑤ 파츠 나누기     parts/{슬롯}.png
  → ⑥ Aseprite 파일   scripts/sprite_build.py → 호스트 모듈로 실행 → sprites/{캐릭터}.aseprite
  → ⑦ 내보내기       export/{캐릭터}/ · scripts/spine_rig.py
```

## 0. 사양 파일

**작업 전에 사양 파일이 확정되어 있어야 합니다.** 없으면 값을 추측해 채우지 않고 사양부터
확정받습니다 — 캐릭터를 몇 명 만든 뒤 등신이나 캔버스를 바꾸면 전부 다시 맞춰야 합니다.

자리는 프로젝트의 `spec/design/pixel-spec.json`이고, 형식과 예시는 모듈의 `pixel-spec.example.json`
입니다.

| 항목 | 담는 것 |
|---|---|
| `schema_version` | 1 |
| `canvas` | 캔버스 가로 · 세로(px) |
| `center_x` | 몸 중심선 열 |
| `light` | 광원 방향 (기본 `top-left`) |
| `anchors` | 기준선 이름 → y 좌표. `sole`(발바닥)과 `ground`(지면)는 필수 |
| `palette` | `outline` 한 색과 `ramps`(재질 이름 → 밝은 색부터 `#RRGGBB` 목록) |
| `limits` | `colors_max` — 캐릭터 한 명이 쓸 수 있는 색 수 |
| `slots` | 표준 슬롯 이름, 뒤에서 앞 순서 (`pixel-rig.md` §2) |
| `bones` | 뼈 이름 → [부모, x, y] (캔버스 좌표) |
| `slot_bone` | 슬롯 → 붙는 뼈 |

## 0-1. 캐릭터 팔레트 제안

사양 파일의 램프 색이 캐릭터와 맞지 않으면 변환이 가장 가까운 색을 골라도 피부가 창백해지고 옷이
다른 재질 색으로 바뀝니다. 캐릭터 설정 그림이 있으면 먼저 색을 뽑아 램프 후보를 봅니다.

```bash
python core/modules/pixel-art/scripts/palette_suggest.py source/{캐릭터}/full.png     [--bg-key auto] [--native] --spec spec/design/pixel-spec.json --out-spec {검토용 사양}.json
```

- 색조 · 채도가 가까운 색을 군집으로 묶어 밝은 색부터 늘어놓고, 드물지만 뚜렷한 색(눈동자 · 보석)은
  따로 되살립니다.
- 결과는 **후보**입니다. 램프 이름을 재질(SKIN · HAIR …)로 바꾸고 단계를 다듬은 뒤 승인을 받아
  사양 파일에 넣습니다. 모든 캐릭터가 한 팔레트를 쓰므로 캐릭터마다 램프를 **더하는** 방식입니다.

## 1. 입력 그림 준비

- **무엇을:** 목표 등신으로 그린 **채색된 전신 그림**을 `source/{캐릭터}/`에 둡니다.
- **조건:**
  - 배경은 투명합니다. 단색 배경이면 변환 때 `--bg-key auto`로 지웁니다(가장자리에서 이어지는
    배경색만 지우므로 인물 안의 같은 색은 남습니다).
  - 해상도는 목표 키의 8배 이상입니다(키 102px이면 세로 820px 이상).
  - 기본 자세는 `pixel-rig.md` §4를 따릅니다.
  - 파츠를 레이어로 나눠 그렸다면 레이어마다 PNG로 따로 내보내 둡니다. ⑤가 쉬워집니다.
- **저작권:** 남의 그림을 입력으로 쓰지 않습니다. 도구 시험용으로 잠깐 쓴 결과도 저장소에 남기지 않습니다.

## 2. 픽셀 변환

```bash
python core/modules/pixel-art/scripts/pixelize.py source/{캐릭터}/full.png \
    --spec spec/design/pixel-spec.json --height {키} --out source/{캐릭터}/draft.png
```

- 도구가 하는 일: 투명 여백 자르기 → 면적 평균으로 축소 → 팔레트의 가까운 색으로 바꾸기 → 외톨이
  픽셀 정리 → 실루엣 가장자리를 셀아웃으로 → 발바닥 기준선과 중심선에 맞춰 놓기.
- `--ramps`로 쓸 램프를 좁히면 엉뚱한 재질 색이 섞이는 것을 줄입니다(예: 피부 · 머리카락 · 옷 램프만).
- **입력이 이미 도트 그림을 키운 것이면 `--native`를 씁니다.** 격자 간격(소수도 됩니다)을 찾아 칸마다
  한 점씩 읽으므로 원본 도트가 그대로 나옵니다. 자동 탐지는 6배 이상 키운 입력에서 확인했습니다.
  3~5배처럼 작게 키운 입력은 배수 간격을 고를 수 있으니 `--grid {간격}`으로 직접 줍니다. 이때 `--height`는 필요 없고, 원본 도트 키가 사양의
  키와 다르면 사양을 원본에 맞출지 먼저 정합니다 — 다시 줄이면 도트가 번져 원본보다 흐려집니다.
- 외곽선 색은 가까운 색 후보에 들어가지 않습니다. 가장자리 처리에서만 씁니다.
- 결과: 캔버스 크기의 PNG. **초안**입니다.

## 3. 손으로 다듬기

Aseprite에서 초안을 열고 아래 순서로 고칩니다. 앞의 것이 뒤의 판단을 바꾸므로 순서를 지킵니다.

1. **실루엣** — 1배로 보고 몸 윤곽이 읽히는지 봅니다. 튀어나온 픽셀 · 끊긴 윤곽을 먼저 정리합니다.
2. **얼굴** — 눈 · 입 · 코를 `pixel-style.md` §6 기준으로 **다시 그립니다.** 자동 변환된 얼굴은 거의
   항상 뭉개져 있습니다.
3. **손** — 손가락 덩어리를 다시 나눕니다.
4. **외곽선** — 뭉침 · 불규칙 계단 · 끊긴 선을 고칩니다.
5. **머리카락** — 뭉치 경계와 윤기 띠, 끝의 흩어짐을 정리합니다.
6. **재질** — 금속 반짝임 · 주름 방향을 광원에 맞춥니다.
7. **외톨이 픽셀** — `lint.py`의 경고 목록을 보고 의도하지 않은 점을 지웁니다.

⚠️ Aseprite MCP 도구로 다듬을 때는 Indexed 스프라이트에 바로 그리지 않습니다. 호스트 모듈 `aseprite`의
알려진 함정대로 RGB로 바꿔 그린 뒤 Indexed로 되돌립니다.

⚠️ 다듬는 동안 팔레트 밖 색을 쓰지 않도록 Aseprite 팔레트를 사양 파일의 마스터 팔레트로 고정해
둡니다. ⑥이 만든 `.aseprite`에는 이 팔레트가 이미 들어 있습니다.

## 4. 검수

```bash
python core/modules/pixel-art/scripts/lint.py source/{캐릭터}/draft.png --spec spec/design/pixel-spec.json
python core/modules/pixel-art/scripts/lineup.py --spec spec/design/pixel-spec.json \
    --out export/lineup.png export/{캐릭터1}/{캐릭터1}.png export/{캐릭터2}/{캐릭터2}.png
```

실패가 0건이 될 때까지 ③으로 돌아갑니다. 라인업 시트에서 기준선이 어긋난 캐릭터가 있으면 비율부터
고칩니다.

## 5. 파츠 나누기

다듬은 그림을 `pixel-rig.md`의 표준 슬롯으로 나눠 `source/{캐릭터}/parts/{슬롯}.png`에 둡니다.
각 파일은 **캔버스 크기 그대로**이고 자기 파츠만 칠해져 있습니다. 관절 자리는 2~3px 겹치게
그립니다(`pixel-rig.md` §5).

## 6. Aseprite 파일 만들기

```bash
python core/modules/pixel-art/scripts/sprite_build.py --spec spec/design/pixel-spec.json \
    --parts source/{캐릭터}/parts --name {캐릭터} --lua export/{캐릭터}/build.lua \
    --ase sprites/{캐릭터}.aseprite --png export/{캐릭터}/{캐릭터}.png
python core/modules/aseprite/scripts/aseprite_env.py --run export/{캐릭터}/build.lua
```

- 슬롯 순서대로 레이어가 쌓이고, 마스터 팔레트가 들어간 `.aseprite`가 생깁니다.
- 파츠로 나누기 전이면 `--parts` 대신 `--single`로 한 장을 넣습니다.
- 이미 선을 그린 그림에는 `--finalize`를 주지 않습니다. 외곽선이 한 겹 더 생깁니다.
- 실행은 호스트 모듈의 도구가 합니다. Aseprite 설치 자리는 그 모듈이 찾습니다.

## 7. 내보내기

```bash
aseprite -b --split-layers sprites/{캐릭터}.aseprite --save-as export/{캐릭터}/layers/{layer}.png
python core/modules/pixel-art/scripts/spine_rig.py --spec spec/design/pixel-spec.json \
    --root export --out export/skeleton.json {캐릭터1} {캐릭터2}
```

- `aseprite`는 호스트 모듈이 찾은 실행 파일입니다.
- 레이어별 PNG는 캔버스 크기 그대로 나갑니다. Spine이 모든 파츠를 같은 원점에 놓습니다.

## 8. 정본과 파생물

| 자리 | 지위 | 고치는 법 |
|---|---|---|
| `spec/design/pixel-spec.json` | 정본 | 승인을 받아 고치고 change-log 현행 기준에 적습니다 |
| `source/{캐릭터}/` | 입력 정본 | 직접 고칩니다 |
| `sprites/{캐릭터}.aseprite` | 그림 정본 | Aseprite에서 직접 고칩니다 |
| `export/` | 파생물 | 직접 고치지 않습니다. ⑥ · ⑦로 다시 만듭니다 |

Aseprite에서 다듬은 뒤에는 `.aseprite`가 정본입니다. 그 뒤로 ②를 다시 돌리면 손으로 고친 것이
사라지므로, 변환을 다시 할 때는 새 초안을 따로 만들어 비교합니다.
