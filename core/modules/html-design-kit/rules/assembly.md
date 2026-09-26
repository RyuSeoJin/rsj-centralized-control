# HTML 디자인 킷 조립 규칙

## 역할

이 모듈은 프로젝트 고유 콘텐츠를 갖지 않습니다. 중앙에는 공용 토큰·부품·조립기만 두고, 제목·본문·이미지·페이지 전용 부품은 프로젝트 안에 둡니다.

## 입력과 산출물

- `choice.json`이 페이지 구성의 정본입니다. 프레임·영역·슬롯·속성·테마와 페이지 전용 덮어쓰기를 기록합니다.
- `page.html`과 `DESIGN.md`는 파생물입니다. `python core/modules/html-design-kit/scripts/assemble.py {choice.json 경로} --final`로 함께 만듭니다.
- 페이지 전용 부품은 `choice.json`과 같은 폴더의 `parts/`에 둡니다. 공용 부품보다 먼저 읽습니다.
- 페이지 전용 이미지는 그 HTML이 있는 `docs/` 아래에 두고, 본문이 이미지 없이도 성립하도록 대체 텍스트와 설명을 둡니다.

## 자기완결

- 완성 HTML의 CSS와 JavaScript는 모두 인라인합니다. CDN·외부 스크립트·상대 경로 JavaScript 참조를 두지 않습니다.
- 페이지에 별도 JavaScript가 필요하면 `choice.json`의 `scripts` 배열에 페이지 폴더 기준 경로를 순서대로 적습니다. 조립기가 내용을 인라인합니다.
- 래스터 이미지만 문서와 같은 `docs/` 아래에서 상대 경로로 참조할 수 있습니다.

## 공용 부품 관리

- 공용 부품을 추가하거나 수정한 뒤에는 `python core/modules/html-design-kit/scripts/lint.py`와 `python core/modules/html-design-kit/scripts/build.py`를 실행합니다.
- 자체 제작 또는 재배포 조건이 확인된 출처만 공용 부품에 넣습니다. 라이선스가 없거나 재배포 조건이 불명확하거나 강한 카피레프트 조건이 있는 디자인은 넣지 않습니다.
- 공용 변경은 프로젝트 이름·콘텐츠·실제 값을 포함하지 않습니다.
