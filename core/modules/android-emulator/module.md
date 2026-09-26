# android-emulator — Android Emulator 환경을 재현 가능하게 관리합니다

Android 앱 또는 모바일 웹을 Android 가상 기기에서 확인할 때, 설치 원본·AVD 생성·점검 절차를
한곳에서 관리합니다. 이 모듈은 한 컴퓨터에 설치되어 여러 프로젝트가 함께 쓰는 **호스트 환경
모듈**입니다.

## 적용 범위

컴퓨터에 Android Studio·SDK·AVD를 설치하고 관리할 때 적용합니다. 프로젝트의
`{프로젝트}-modules.json`에는 넣지 않으며, 실제 설치 상태는 `verify-android.ps1`로 확인합니다.

프로젝트가 특정 AVD를 써야 하면 기기 조합과 테스트 범위만
`spec/design/env-android-emulator.md`에 기록합니다. 설치 자체는 그 프로젝트에 귀속되지 않습니다.

## 제공하는 것

| | |
|---|---|
| 규칙 | `rules/windows-setup.md` — Windows 설치·AVD 생성·점검 / `rules/environment-record.md` — 프로젝트별 환경 기록 |
| 설치 안내 | `android-emulator-install-guide.html` — Install Type 선택과 설치·AVD 생성 과정을 따라 읽는 자기완결 안내서 |
| 설치 기준 | `manifests/android-studio-windows.json` — 공식 배포 페이지·최신판 선택 규칙·기본 AVD 정책 / `scripts/get-latest-android-downloads.ps1` — 실행 시점의 파일명·URL·SHA-256 확인 |
| 도구 | `scripts/bootstrap-android.ps1` — 최신 Android Studio 설치 / `scripts/provision-android-sdk.ps1` — 최신 숫자 API System Image·AVD 구성 / `scripts/verify-android.ps1` — SDK·Emulator·AVD 상태 점검 |
| 프로젝트에 생기는 것 | 없습니다. 실제 기기 조합은 필요할 때 `spec/design/env-android-emulator.md`에 기록합니다 |

## 전제 모듈

없습니다.

이 모듈은 수동 확인에도 쓸 수 있으므로, TC나 자동화 모듈을 먼저 켜지 않습니다.
