# ue-umg-cpp — UMG 화면을 C++ 코드로 만들 때의 규칙

UMG 위젯을 코드로 만들면 편집기의 미리 보기가 없어, 그리기 · 배치 · 입력에서 엔진이 실제로 어떻게
도는지를 모르면 화면을 띄워 봐야 문제를 알게 됩니다. 이 문서는 실제로 겪은 문제마다 **엔진 동작 →
규칙 → 확인 방법**을 정합니다. 클래스 · 파일 이름은 자리 표시자(`{패널}` 등)로 적고, 프로젝트의 값(크기
단위 · 배율 · 언어 목록)은 프로젝트의 change-log 현행 기준이나 UI 사양에 둡니다.

엔진 동작의 근거는 엔진 소스의 함수 이름으로 적습니다. 엔진 판이 바뀌면 그 함수를 다시 열어 같은지
봅니다.

---

## 1. 다시 그리기

**엔진 동작.** 위젯을 지우고 새로 만들면 Slate 쪽 위젯도 새로 생깁니다. 그래서 그 위젯이 갖고 있던
상태가 함께 사라집니다 — 입력칸의 키보드 초점, 끌고 있던 슬라이더의 마우스 캡처, 스크롤 상자의
스크롤 위치입니다. 또 버튼의 클릭은 기본값(`EButtonClickMethod::DownAndUp`)에서 **누른 버튼 위에서
뗄 때** 일어납니다. 누른 뒤 · 떼기 전에 버튼을 새로 만들면, 떼는 순간의 버튼은 누름을 받은 적이 없어
클릭이 어디에도 가지 않습니다.

**규칙.**

1. **바뀐 칸만 갱신합니다.** 처음 만들 때 값이 바뀌는 칸(`UTextBlock` 등)의 포인터를 멤버로 받아 두고,
   값이 바뀌면 그 칸의 `SetText` · `SetPercent` 같은 함수만 부릅니다.
2. **줄 수가 바뀔 때만 다시 만듭니다.** 목록의 줄 수가 같으면 줄 안의 칸만 갱신합니다.
3. **주기적으로 바뀌는 값도 같은 규칙입니다.** 저절로 넘어가는 곡 제목 · 시간마다 늘어나는 숫자처럼
   사용자가 손대지 않아도 바뀌는 값을, 타이머에서 창 전체를 다시 만드는 함수로 갱신하지 않습니다.
   사용자가 그 창의 슬라이더를 끄는 중이면 끌기가 끊깁니다.
4. **마우스 단추가 눌려 있는 동안에는 다시 만들지 않습니다.** 다시 만들 일이 생기면 표시만 해 두고,
   단추가 모두 떨어진 다음 틱에 만듭니다.
5. **틱에서 상태를 비교해 달라졌을 때만 갱신합니다.** 마지막으로 그린 값을 멤버에 남겨 두고, 지금
   값과 다를 때만 칸을 고칩니다. 같은 값으로 `SetText`를 매 틱 부르면 그때마다 다시 그리기와 배치가
   일어납니다.

아래는 1 · 2 · 4 · 5를 한 패널에 넣은 모습입니다. **교육용 압축** — 실전에서는 멤버 선언은 헤더
(`{패널}.h`), 함수 몸통은 구현 파일(`{패널}.cpp`)에 있고, 상태를 읽는 함수(`ReadGold` · `ReadRowCount`)와
줄을 만드는 함수(`RebuildRows`)의 이름은 프로젝트마다 다릅니다.

```cpp
// {패널}.h — 새 파일 아님, 패널 위젯 클래스(UUserWidget 상속)에 더하는 멤버
UPROPERTY() TObjectPtr<UTextBlock> GoldText;   // 처음 만들 때 받아 둔 금액 칸 — 금액이 바뀌면 이 칸의 SetText만 부릅니다
int32 ShownGold = INDEX_NONE;                  // 마지막으로 GoldText에 넣은 금액 — 지금 금액과 다를 때만 SetText를 부릅니다
int32 BuiltRowCount = INDEX_NONE;              // 마지막으로 만든 목록 줄 수 — 줄 수가 달라졌을 때만 목록을 다시 만듭니다
bool bRebuildPending = false;                  // 마우스 단추가 눌려 있어 미뤄 둔 다시 만들기가 있으면 true

// {패널}.cpp — 새 파일 아님, 엔진이 이 위젯이 화면에 있는 동안 매 프레임 부르는 NativeTick
void U{패널}::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
    Super::NativeTick(MyGeometry, InDeltaTime);

    // 1) 금액 칸 — 위젯을 새로 만들지 않고 글자만 바꿉니다. 초점 · 끌기 · 스크롤은 그대로 남습니다
    const int32 Gold = ReadGold();
    if (Gold != ShownGold)
    {
        ShownGold = Gold;
        GoldText->SetText(FText::AsNumber(Gold));
    }

    // 2) 줄 수가 달라졌을 때만 다시 만들 일로 표시합니다
    const int32 Rows = ReadRowCount();
    if (Rows != BuiltRowCount)
    {
        bRebuildPending = true;
    }

    // 3) 눌린 마우스 단추가 하나도 없을 때만 다시 만듭니다
    //    누른 버튼을 지우면 뗄 때의 클릭을 받을 버튼이 없어 그 클릭이 사라집니다
    if (bRebuildPending && FSlateApplication::Get().GetPressedMouseButtons().Num() == 0)
    {
        RebuildRows(Rows);          // 목록 상자를 비우고 줄을 Rows개 만듭니다 — 줄 안의 칸 포인터도 이때 다시 받아 둡니다
        BuiltRowCount = Rows;
        bRebuildPending = false;
    }
}
```

**확인.** 값이 바뀌는 중에 그 창의 슬라이더를 끌고, 입력칸에 글자를 치고, 목록을 스크롤해 봅니다.
셋 다 끊기지 않아야 합니다. 저절로 바뀌는 값이 있으면 그 값이 바뀌는 순간에 버튼을 눌러 봅니다.

## 2. 글자 넘침 · 말줄임

**엔진 동작.** `ETextOverflowPolicy::Ellipsis`의 말줄임은 글자 위젯의 크기가 아니라 **그릴 때의 잘라
내기 사각형**을 기준으로 판정합니다(엔진 `FSlateTextLayout::OnPaint` — 줄과 글자 덩어리가 잘라 내기
사각형 안에 보이는지로 마지막 덩어리를 고릅니다). 그래서 그 글자 위젯에 잘라 내기를 걸지 않으면, 부모의
잘라 내기 사각형 밖으로 나갈 때까지 말줄임이 그려지지 않고 글자가 옆 칸 위로 그대로 그려집니다.
또 한 줄 글자의 말줄임 방향은 맞춤으로 정해집니다 — 왼쪽 맞춤은 끝이, 오른쪽 맞춤은 **앞이** 줄고,
가운데 맞춤은 방향이 없어 **말줄임을 그리지 않습니다.**

**규칙.**

1. **말줄임을 켠 글자에는 늘 잘라 내기를 함께 겁니다** — `SetClipping(EWidgetClipping::ClipToBounds)`.
2. **말줄임 글자는 줄어들 수 있는 칸에 넣습니다.** 내용 폭만큼만 받는 칸(Auto)은 글자가 길면 칸도
   함께 늘어나 줄일 자리가 없습니다. 남는 폭을 받는 칸(Fill)이나, 내용 폭에서 늘고 줄 수 있는 칸
   (Slate의 `FillContentWidth`)에 넣습니다.
3. **한 줄에 제목과 값이 있으면 제목이 먼저 자리를 잡고 값이 줄어듭니다.** 제목은 내용 폭(Auto) 칸,
   값은 줄어드는 칸에 둡니다. 제목도 길어질 수 있으면 제목 칸에 최대 폭을 정합니다.
4. **오른쪽 맞춤 값은 무엇을 남길지 정합니다.** 오른쪽 맞춤 값은 앞부분이 잘리므로, 앞이 중요한 값
   (이름 · 단위가 앞에 붙는 값)이면 왼쪽 맞춤으로 바꾸거나 칸을 넓힙니다.
5. **가운데 맞춤 글자에 말줄임을 기대하지 않습니다.** 넘칠 수 있는 가운데 맞춤 글자는 칸 폭을 넉넉히
   잡거나, 칸 안에서 왼쪽 맞춤으로 바꿉니다.
6. **아이콘을 더하는 버튼은 긴 언어의 글자 폭으로 계산합니다.** 버튼 폭이 정해져 있으면 아이콘이 차지한
   만큼 글자 자리가 줄어듭니다. 프로젝트가 정한 긴 언어(독일어 · 러시아어 · 프랑스어처럼 같은 뜻이
   길어지는 언어)의 문구 폭으로 계산해 넣습니다.

아래는 한 줄에 제목과 값을 넣는 코드입니다. `{패널}.cpp`의 줄을 만드는 함수 안에 있는 코드이며,
`Row`는 그 줄의 `UHorizontalBox`입니다.

```cpp
// {패널}.cpp — 새 파일 아님, 한 줄(제목 + 값)을 만드는 함수 안
UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>();
UHorizontalBoxSlot* LabelSlot = Row->AddChildToHorizontalBox(Label);
LabelSlot->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));  // 제목은 글자 폭만큼 먼저 자리를 받습니다

UTextBlock* Value = WidgetTree->ConstructWidget<UTextBlock>();
Value->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);     // 칸보다 긴 글자의 끝을 말줄임표로 바꿉니다
Value->SetClipping(EWidgetClipping::ClipToBounds);               // 이 칸의 사각형으로 잘라 냅니다 — 없으면 말줄임 판정이 부모의 사각형으로 되어 옆 칸 위로 넘칩니다
UHorizontalBoxSlot* ValueSlot = Row->AddChildToHorizontalBox(Value);
ValueSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));       // 제목이 받고 남은 폭만 받습니다 — 폭이 모자라면 이 칸이 줄어듭니다
```

**확인.** 가장 긴 언어와 가장 큰 UI 배율로 화면을 띄워 봅니다. 자동 플레이 시험에 글자 넘침 검사가
있으면 그 결과의 넘침 줄이 0인지 봅니다(ue-build 모듈을 켰다면 `modules/ue-build/rules/ue-build-test.md`
§4-5). 화면 사진에서 말줄임표가 실제로 보이는지도 봅니다 — 검사는 넘침을 잡아도 말줄임이 그려졌는지는
모를 수 있습니다.

## 3. 자리 재기

**엔진 동작.** `GetCachedGeometry`가 돌려주는 자리는 **그 위젯이 마지막으로 그려질 때** 남긴 값입니다
(엔진 `SWidget::Paint`가 그릴 때마다 저장합니다). 숨긴(Hidden · Collapsed) 위젯은 그려지지 않으므로,
처음부터 숨긴 채 시작한 위젯의 자리는 크기 0 · 위치 0입니다. 한 번 보였다가 숨긴 위젯은 마지막으로
보였을 때의 자리가 남아 있어 지금 자리와 다를 수 있습니다.

**규칙.**

1. **늘 보이는 부모 블록의 자리를 기준으로 잽니다.** 숨긴 위젯의 자리를 기준으로 메뉴 · 말풍선을
   펼치면, 크기 0 · 위치 0이 기준이 되어 화면 모서리 같은 엉뚱한 곳에 나옵니다.
2. **위젯을 크기 상자로 감싸 캔버스에 넣었다면, 위치를 정하는 슬롯은 감싼 상자의 슬롯입니다.** 위젯
   자신의 `Slot`은 상자 안의 슬롯(`USizeBoxSlot` 등)이라 캔버스 위치가 없습니다. `UCanvasPanelSlot`으로
   바꿔 읽으면 `nullptr`이 나오고, 빈 값을 확인하고 건너뛰는 코드라면 아무 일도 일어나지 않습니다.
3. **렌더 변환은 그림만 바꿉니다.** `SetRenderScale` · `SetRenderTranslation`은 그려지는 모습만 바꾸고
   배치 자리는 그대로 둡니다. 크기 자체를 바꾸려면 배율 상자(`UScaleBox`)나 크기 상자로 바꿉니다
   (ue-build 모듈을 켰다면 그 함정 표 `modules/ue-build/rules/ue-build-test.md` §6에 같은 줄이 있습니다).

아래는 2의 코드입니다. HUD를 만드는 함수 안에 있는 코드이며, `Canvas`는 HUD의 `UCanvasPanel`,
`Panel`은 감쌀 위젯입니다.

```cpp
// {HUD}.cpp — 새 파일 아님, HUD 위젯을 만드는 함수 안
USizeBox* Box = WidgetTree->ConstructWidget<USizeBox>();
Box->SetWidthOverride(PanelWidth);                               // 패널 폭을 상자가 정합니다
Box->AddChild(Panel);                                            // 이제 Panel->Slot은 USizeBoxSlot입니다
UCanvasPanelSlot* CanvasSlot = Canvas->AddChildToCanvas(Box);    // 캔버스 위치를 갖는 슬롯은 Box 쪽에 생깁니다
CanvasSlot->SetPosition(FVector2D(PanelX, PanelY));              // 패널을 옮길 때는 이 슬롯(Box->Slot)을 씁니다
// Cast<UCanvasPanelSlot>(Panel->Slot)은 nullptr입니다 — Panel의 슬롯은 상자 안 슬롯이기 때문입니다
```

**확인.** 숨긴 채 시작하는 위젯을 기준으로 무엇을 펼친다면, 게임을 켠 직후 한 번도 그 위젯을 열지 않은
상태에서 펼쳐 봅니다.

## 4. 입력칸

**엔진 동작.** 입력칸(`UEditableTextBox`)의 글자는 Enter를 누르거나 초점이 옮겨질 때 확정
(`OnTextCommitted`)됩니다. 확정에만 기대면, 입력칸에 쓰던 중에 같은 창의 다른 버튼이 눌렸을 때 그 버튼의
처리가 확정보다 먼저 돌아 옛 값을 쓸 수 있습니다.

**규칙.**

1. **그 창의 모든 버튼은 먼저 입력칸 값을 읽어 넣습니다.** 버튼 처리 함수의 맨 앞에서, 입력칸의 지금
   글자(`GetText`)를 읽어 값으로 넣는 함수를 부릅니다. 적용 버튼만이 아니라 탭 바꾸기 · 닫기 · 다른
   항목 고르기 버튼도 같습니다.
2. **읽을 수 없는 값을 쓰는 중에는 적용 버튼을 끕니다.** 글자가 바뀔 때(`OnTextChanged`) 값으로 읽히는지
   보고 적용 버튼을 켜고 끕니다.
3. **숫자가 아닌 글자는 앞 값으로 되돌립니다.** 숫자 칸에 숫자가 아닌 글자가 확정되면, 칸을 마지막으로
   받아들인 값으로 다시 채웁니다.

```cpp
// {설정 창}.cpp — 새 파일 아님, 이 창의 모든 버튼 처리 함수가 맨 앞에서 부르는 함수
void U{설정창}::CommitInputs()
{
    // 입력칸의 지금 글자를 읽습니다 — Enter나 초점 이동으로 확정되기를 기다리지 않습니다
    const FString Typed = CountBox->GetText().ToString();
    if (Typed.IsNumeric())
    {
        Count = FCString::Atoi(*Typed);              // 숫자로 읽히면 값으로 받아들입니다
    }
    else
    {
        CountBox->SetText(FText::AsNumber(Count));   // 숫자가 아니면 칸을 마지막으로 받아들인 값으로 되돌립니다
    }
}
```

**확인.** 입력칸에 값을 친 뒤 Enter 없이 곧바로 적용 · 닫기 · 탭 버튼을 눌러, 친 값이 들어갔는지 봅니다.

## 5. 엔진 위젯의 한계

1. **슬라이더의 채운 쪽 색.** `USlider` · `FSliderStyle`은 막대 그림 하나와 손잡이 그림 하나만 그립니다
   (엔진 `SSlider::OnPaint` — 막대 전체를 한 상자로 그린 뒤 손잡이를 그립니다). 그래서 스타일만으로는
   0부터 지금 값까지를 다른 색으로 칠할 수 없습니다. 채운 쪽 색이 필요하면 `SSlider`를 상속해
   `OnPaint`를 다시 쓰고, **막대 → 채운 쪽(막대 시작부터 `GetNormalizedValue()` 비율까지) → 손잡이** 순서로
   그립니다. 막대 · 손잡이 그림은 상속한 클래스에서 `GetBarImage()` · `GetThumbImage()`로 얻습니다.
   UMG에서 쓰려면 이 Slate 위젯을 만드는 UMG 위젯 클래스를 따로 둡니다.
2. **글자 줄 높이는 합성 글꼴의 기본 글꼴로만 정해집니다.** 줄 높이는 화면에 나온 언어와 상관없이
   합성 글꼴(Composite Font)의 기본 글꼴로 잽니다(엔진 `FSlateFontRenderer::GetMaxHeight` — 기본 글꼴
   데이터의 높이를 씁니다). 다른 언어를 대체 글꼴로 그려도 줄 높이는 바뀌지 않습니다. 그래서 줄 수로
   높이를 정하는 고정 높이 블록은 **기본 글꼴의 줄 높이**로 계산합니다. 줄 높이는 배율마다 픽셀로
   반올림되어 배율에 정비례하지 않으므로, 프로젝트가 정한 UI 배율마다 띄워 봅니다.

## 6. 월드에 붙는 UI와 HUD의 겹침

**겪은 일.** 월드 물체 위에 띄우는 버튼 줄이 화면 가장자리의 HUD 블록이나 열린 패널 밑에 깔려 눌리지
않았습니다. 처음에는 겹치지 않았는데, HUD 블록이 커지면서 새로 생겼습니다. 화면 위치는 물체와 카메라에
따라 계속 바뀌어 한 번 맞춰 둔 자리로는 막을 수 없습니다.

**규칙.**

1. 띄울 자리(예: 물체 위)의 화면 사각형이 **지금 보이는 HUD 블록 · 열린 패널의 사각형**과 겹치는지
   봅니다. 숨긴 블록은 빼고 봅니다 — 숨긴 블록의 자리는 §3처럼 0이거나 옛 값입니다.
2. 겹치면 다른 자리(예: 물체 아래)로 옮깁니다. **둘 다 겹치면 원래 자리**에 둡니다.
3. 비교는 틱마다 하되 **놓을 자리가 바뀔 때만** 옮깁니다. 매 틱 같은 자리로 다시 옮기면 그때마다 배치가
   다시 일어납니다.
4. 모든 사각형을 같은 좌표계(예: 뷰포트 좌표)로 바꾼 뒤 견줍니다. HUD 블록의 자리는 데스크톱 좌표,
   물체를 화면에 투영한 자리는 뷰포트 좌표로 나오기 때문입니다.

아래는 1 ~ 3을 버튼 줄 위젯의 틱에 넣은 모습입니다. **교육용 압축** — 사각형을 구하는 함수
(`RectWhenPlaced` · `VisibleHudRects`)와 옮기는 함수(`MoveTo`)는 프로젝트마다 이름과 자리가 다릅니다.

```cpp
// {월드 버튼 줄}.cpp — 새 파일 아님, 버튼 줄 위젯의 NativeTick 안
const FSlateRect Above = RectWhenPlaced(EPlace::Above);   // 물체 위에 놓을 때 버튼 줄이 차지할 뷰포트 사각형
const FSlateRect Below = RectWhenPlaced(EPlace::Below);   // 물체 아래에 놓을 때의 사각형
const TArray<FSlateRect> Hud = VisibleHudRects();         // 지금 보이는 HUD 블록 · 열린 패널의 뷰포트 사각형(숨긴 것은 뺌)

auto HitsHud = [&Hud](const FSlateRect& R)                // R이 HUD 사각형 하나라도와 겹치면 true
{
    for (const FSlateRect& H : Hud) { if (FSlateRect::DoRectanglesIntersect(R, H)) return true; }
    return false;
};

// 위가 겹치고 아래가 비었을 때만 아래로 — 둘 다 겹치면 원래 자리(위)에 둡니다
const EPlace Want = (HitsHud(Above) && !HitsHud(Below)) ? EPlace::Below : EPlace::Above;
if (Want != CurrentPlace)                                 // 놓을 자리가 바뀔 때만 옮깁니다
{
    CurrentPlace = Want;
    MoveTo(Want);
}
```

**확인.** HUD 블록이 가장 커지는 상태(긴 언어 · 큰 UI 배율 · 패널을 연 상태)에서 물체를 화면 가장자리로
옮겨 버튼 줄이 피해 가는지 봅니다.

## 7. UI 크기 규칙 검사

UI 크기 규칙(예: 틀은 10의 배수 · 그림 칸은 2의 제곱수)을 정하고 그것을 보는 검사 도구를 둔 프로젝트라면,
새 크기 값을 넣은 변경은 **커밋을 제안하기 전에 그 도구를 돌립니다.** 코드에 박힌 크기 값은 눈으로 훑어서는
규칙을 어겨도 걸리지 않습니다. 규칙의 값과 도구의 자리는 프로젝트가 정하며, 이 모듈은 돌리는 시점만
정합니다.
