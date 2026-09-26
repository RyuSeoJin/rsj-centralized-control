# Android Emulator Windows 설치와 확인

이 문서는 Windows에서 Android Emulator를 설치하고 기본 AVD를 만드는 절차의 정본입니다.
설치 정책은 `../manifests/android-studio-windows.json`을 읽습니다. 각 새 설치에서는 공식 Android
다운로드 페이지를 다시 읽어 당시의 최신 Windows 권장 설치 파일과 Command-line Tools의 URL·SHA-256을
함께 확인합니다. 설치 프로그램의 라이선스는 설치하는 사람이 직접 확인하고 동의합니다.

## 1. 설치 전 확인

- 64비트 Windows와 CPU 가상화가 필요합니다.
- Android Studio와 Emulator에는 최소 16GiB의 빈 공간이 필요합니다.
- 기존 Android SDK가 있다면 설치 위치와 SDK 버전을 환경 기록에 먼저 남깁니다. 다른 위치에
  새 SDK를 섞어 설치하지 않습니다.

## 2. Android Studio 설치

다음 명령은 실행 시점에 Android 공식 다운로드 표에서 최신 Windows 권장 `.exe`와 그 SHA-256을
가져옵니다. 내려받은 파일의 SHA-256이 그 공식 값과 일치할 때만 설치 프로그램을 엽니다. 이미
Android Studio가 설치된 컴퓨터에서는 설치 마법사를 다시 열지 않고 상태만 점검합니다.

```powershell
powershell -ExecutionPolicy Bypass -File core/modules/android-emulator/scripts/bootstrap-android.ps1
```

설치 마법사에서는 표준 설치를 고릅니다. Android SDK 라이선스는 설치하는 사람이 직접 확인하고
동의합니다.

새 컴퓨터에 설치할 때마다 이 절차를 그대로 실행합니다. 수동으로 URL이나 체크섬을 문서에
복사하지 않습니다. 공식 페이지의 구조가 바뀌어 자동 확인을 할 수 없으면 스크립트는 중단하며,
그때 중앙 모듈의 선택 규칙을 수정·검토한 뒤 다시 실행합니다.

## 3. SDK 구성과 기본 AVD 만들기

Android Studio 설치가 끝난 뒤 다음 명령을 실행합니다. 이 명령은 명령줄 도구를 체크섬으로
검증해 설치하고, SDK 라이선스를 수락한 뒤 Platform-Tools·Emulator·실행 시점에 제공되는 가장 높은
숫자 Android API의 Google APIs x86_64 System Image를 구성합니다. AVD 이름은
`Pixel_8_API_{API}` 형식으로 자동 생성됩니다.

```powershell
powershell -ExecutionPolicy Bypass -File core/modules/android-emulator/scripts/provision-android-sdk.ps1 -AcceptSdkLicenses
```

`-AcceptSdkLicenses`는 Android SDK 라이선스를 직접 확인한 사람이 명시적으로 붙입니다.
기본 AVD의 기기 프로필은 Pixel 8이고, API 수준은 설치 시점의 공식 SDK 목록이 정합니다. 실제 선택된
System Image와 AVD 이름은 설치 결과 및 프로젝트 환경 기록에 남깁니다. 프로젝트가 다른 기기 조합을
필요로 하면 추가 AVD를 프로젝트 환경 기록에 남깁니다.

`sdkmanager`가 Android CLI 관련 호환 경고를 내더라도, 명령이 실패하지 않았다면 경고만으로 설치를
멈추지 않습니다. AVD 생성 경로는 `--sdk_root` 인수가 아니라 `ANDROID_SDK_ROOT` 환경 변수로 전달합니다.

## 4. 추가 AVD 만들기

1. Android Studio에서 Device Manager를 열고 새 Virtual Device를 만듭니다.
2. 프로젝트가 `env-android-emulator.md`에 정한 기기 프로필과 Android API 수준을 고릅니다.
3. System Image는 필요한 Google APIs 또는 Google Play 변형을 고르고, 이름은 프로젝트 기록과
   같은 값으로 정합니다.
4. 처음 실행한 뒤 잠금 화면까지 부팅되는지 확인합니다.

기기 모델·API 수준·해상도·네트워크 조건은 중앙에 고정하지 않습니다. 앱의 지원 범위와 테스트
목적에 따라 달라지는 프로젝트 값이기 때문입니다.

## 5. 설치 뒤 점검

설치 후 점검만 따로 다시 실행해야 하면 다음 명령을 씁니다.

```powershell
powershell -ExecutionPolicy Bypass -File core/modules/android-emulator/scripts/verify-android.ps1
```

특정 AVD까지 확인할 때는 이름을 함께 넘깁니다.

```powershell
powershell -ExecutionPolicy Bypass -File core/modules/android-emulator/scripts/verify-android.ps1 -AvdName {AVD이름}
```

점검이 통과하면 프로젝트의 환경 기록에 SDK 경로·도구 버전·AVD 이름·System Image를 적습니다.
