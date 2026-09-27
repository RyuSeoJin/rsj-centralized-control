# pixel-art-dictionary — pixel-art 모듈의 용어

정의는 새로 쓰지 않고 한 줄 요약과 정의가 사는 자리만 적습니다.

| 용어 | 한 줄 요약 | 정의가 사는 자리 |
|---|---|---|
| 등신 | 키가 머리 길이의 몇 배인가 | `rules/pixel-style.md` §1 |
| 머리 단위 (H) | 정수리에서 턱까지의 길이. 기준선을 이 배수로 잽니다 | `rules/pixel-style.md` §2-1 |
| 치비 | 2~3등신 작은 캐릭터. 등신대와 규칙이 다릅니다 | `rules/pixel-style.md` §1 |
| 기준선 (anchors) | 모든 캐릭터가 공유하는 눈 · 턱 · 어깨 · 발바닥 등의 y 좌표 | `rules/pixel-style.md` §2 |
| 마스터 팔레트 | 모든 캐릭터가 함께 쓰는 번호 고정 팔레트 | `rules/pixel-style.md` §3-1 |
| 램프 | 한 재질의 밝은 색부터 어두운 색까지의 단계 | `rules/pixel-style.md` §3-2 |
| 색조 이동 | 밝을수록 따뜻하게, 어두울수록 차갑게 색조를 옮기는 것 | `rules/pixel-style.md` §3-2 |
| 셀아웃 | 외곽선을 닿는 재질의 어두운 단계로 칠하는 방식 | `rules/pixel-style.md` §4 |
| 뭉침 | 외곽선 색 2×2 덩어리. 선이 두꺼워 보입니다 | `rules/pixel-style.md` §4 |
| 접촉 그림자 | 위 파츠 바로 아래 1px을 한 단계 어둡게 하는 것 | `rules/pixel-style.md` §5 |
| 외톨이 픽셀 | 여덟 이웃과 색이 모두 다른 점 | `rules/pixel-style.md` §7 |
| 라인업 시트 | 캐릭터들을 기준선과 함께 나란히 놓은 검수용 그림 | `rules/pixel-style.md` §7 |
| 사양 파일 | 프로젝트의 캔버스 · 기준선 · 팔레트 · 슬롯 · 뼈대 값을 담은 JSON | `rules/pixel-pipeline.md` §0 |
| 슬롯 | 파츠 하나가 들어가는 자리. 이름과 앞뒤 순서가 고정됩니다 | `rules/pixel-rig.md` §2 |
| 스킨 | 같은 슬롯들에 끼우는 캐릭터별 그림 묶음 | `rules/pixel-rig.md` |
| 기본 자세 | 모든 캐릭터가 같은 뼈대를 쓰기 위해 공유하는 자세 | `rules/pixel-rig.md` §4 |
| 포즈 일러스트 | 규약 밖에서 따로 그리는 특정 포즈 그림. 파츠로 나누지 않습니다 | `rules/pixel-rig.md` §4 |
| 필드 스프라이트 · 초상화 | 게임 안을 움직이는 작은 그림(치비) · 정보 화면의 큰 그림(등신대) — 용도별 사양 | `rules/pixel-style.md` §1 · §9 |
| 기준 방향 | 캐릭터를 그리는 한 방향. 반대쪽은 좌우 반전 | `rules/pixel-anim.md` §2 |
| 동작 태그 | 동작 하나에 해당하는 Aseprite 태그(`idle` · `walk` …) | `rules/pixel-anim.md` §3 |
| 공통 몸체 | 모든 캐릭터가 함께 쓰는 민무늬 몸. 동작 프레임은 여기에만 그립니다 | `rules/pixel-anim.md` §4-1 |
| 앵커 · 이동량 | 파츠가 따라 움직이는 기준점과, 프레임마다 그 점이 기본 자세에서 움직인 도트 수 | `rules/pixel-anim.md` §4-2 |
| 파츠 | 캐릭터마다 다른 머리카락 · 옷 · 소품. 기본 자세 한 장으로 그립니다 | `rules/pixel-anim.md` §4-3 |
