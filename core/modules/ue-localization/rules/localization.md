# localization — 시트를 원본으로 두고 UE 표준 번역으로 넣는 규칙

번역 원본을 코드나 엔진 에셋 안에 흩어 두면 번역하는 사람이 엔진을 열어야 하고, 무엇이 번역됐는지
한눈에 볼 수 없습니다. 그래서 **원본은 시트**, 게임은 **UE 표준 번역 파일**을 읽고, 둘 사이를 도구가
잇습니다.

---

## 1. 흐름

```
코드의 LOCTEXT ──(모으기 · export)──▶ 시트에 붙일 새 행
시트(원본)     ──(CSV 내려받기 · import)──▶ .po ──(컴파일)──▶ Content/Localization/Game/<언어>/Game.locres
```

- 설정 파일: `Config/Localization/Game_Gather.ini`(모으기) · `Game_Import.ini`(가져오기 · 컴파일).
- 배포판에 넣을 언어는 `Config/DefaultGame.ini`의 `+CulturesToStage=`로 적습니다.

## 2. 코드에서 번역 키를 만드는 법

```cpp
// {화면}.cpp — 파일 위에서 이름공간을 정하고, 파일 끝에서 풉니다
#define LOCTEXT_NAMESPACE "Settings"
Label->SetText(LOCTEXT("Disp.World", "월드 크기"));                                  // 키 · 원문
Faint->SetText(FText::Format(LOCTEXT("Trash.More", "더 보기 ({0}건)"), Count));      // 값이 들어가는 문장
#undef LOCTEXT_NAMESPACE
```

- 키와 원문은 **따옴표 안 글자 그대로** 써야 모으기가 찾습니다. `LOCTEXT`를 감싼 매크로 · 변수는
  못 찾습니다.
- 값이 들어가는 문장은 `FString::Printf`가 아니라 `FText::Format`입니다 — Printf의 형식 문자열은
  번역 대상이 아닙니다.
- **사용자가 쓴 값**(이름 · 일지 · 태그 등)은 `FText::FromString` 그대로 두고 번역하지 않습니다.
- 한 화면씩 옮깁니다. 옮긴 범위를 프로젝트 change-log에 적어, 어디까지 키로 바뀌었는지 남깁니다.

## 3. 시트의 모양

첫 줄(머리글)은 `Namespace, Key, {원문 언어}`로 시작하고 그 뒤에 언어 열을 둡니다(`en`, `ja` …).

| Namespace | Key | ko | en |
|---|---|---|---|
| Settings | Disp.World | 월드 크기 | World Size |

- **Namespace · Key는 고치지 않습니다** — 코드의 `LOCTEXT`와 짝입니다.
- `{0}` · `{1}`은 값이 들어갈 자리입니다. 번역에서도 그대로 두되 위치는 그 언어 어순에 맞게 옮깁니다.
- 번역 칸을 비워 두면 그 언어에서 원문이 보입니다.
- 시트의 열 이름을 다르게 쓰고 있다면(예: `Key | Korean | English`) 변환 도구가 그 모양을 읽도록
  맞추고, 어느 모양이 정본인지 프로젝트 현행 기준에 적습니다.

## 4. 순서

**새 문장이 코드에 생겼을 때 (export)** — 에디터를 닫고 내보내기를 돌립니다. 새 행 파일을 시트 맨
아래에 붙이고, 원문이 바뀐 행은 시트의 원문 칸을 고친 뒤 번역을 다시 확인합니다.

**번역을 게임에 넣을 때 (import)** — 시트를 CSV로 내려받아 정해진 이름으로 두고 가져오기를 돌립니다.
게임의 언어 설정에서 고르면 번역 파일이 있는 언어만 목록에 뜹니다.

## 5. 언어를 더할 때

1. 시트에 열을 더합니다(머리글 = 문화권 코드: `ja`, `zh-Hans` …).
2. `Game_Gather.ini` · `Game_Import.ini`에 `CulturesToGenerate=` 줄을 더합니다.
3. 배포판에 넣으려면 `DefaultGame.ini`의 `+CulturesToStage=`도 더합니다.
4. 내보내기 → 시트 채우기 → 가져오기.
