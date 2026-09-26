# Android Emulator 환경 기록

Android Emulator의 실제 기기 조합은 프로젝트 값이므로 중앙 규칙에 쓰지 않습니다. 프로젝트에서
처음 Android Emulator를 쓰기로 정하면 `spec/design/env-android-emulator.md`를 만들고
`../templates/env-android-emulator.md` 형식을 따릅니다.

## 기록하는 값

- 실행 시점에 선택된 Android Studio·Command-line Tools·Android SDK의 버전·설치 경로
- AVD 이름·기기 프로필·Android API 수준·System Image
- 가상화 확인 결과와 첫 부팅 결과
- 이 환경을 쓰는 프로젝트의 테스트 범위

## 기록하지 않는 값

- 계정·비밀번호·토큰·개인 식별 정보
- 프로젝트와 무관한 호스트의 전체 설정
- 중앙 모듈에 프로젝트 이름·앱 ID·기기 선택값

도구를 업데이트하거나 AVD 구성을 바꾸면 환경 기록을 먼저 바꾸고, 그 변경이 테스트 결과에
영향을 주면 프로젝트 change-log에도 한 줄 남깁니다.
