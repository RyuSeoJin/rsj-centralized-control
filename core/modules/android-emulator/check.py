#!/usr/bin/env python3
"""android-emulator 모듈 자기 점검 — 중앙에서 검증 가능한 모듈 파일만 확인합니다."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent


def main():
    manifest_path = ROOT / "manifests" / "android-studio-windows.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"android-emulator 실패: manifest를 읽지 못했습니다: {error}")
        return 1

    sources = manifest.get("officialSources", {})
    required = ("schema", "platform", "requiredComponents", "license")
    default_avd = manifest.get("defaultAvd", {})
    missing = [key for key in required if key not in manifest]
    missing += [f"officialSources.{key}" for key in ("studioPage", "selectionRule") if not sources.get(key)]
    missing += [f"defaultAvd.{key}" for key in ("deviceProfile", "systemImageSelector", "avdNameTemplate") if not default_avd.get(key)]
    if missing:
        print("android-emulator 실패: 필수 값이 없습니다: " + ", ".join(missing))
        return 1
    for relative in (
        "module.md",
        "android-emulator-install-guide.html",
        "rules/windows-setup.md",
        "rules/environment-record.md",
        "scripts/bootstrap-android.ps1",
        "scripts/get-latest-android-downloads.ps1",
        "scripts/provision-android-sdk.ps1",
        "scripts/verify-android.ps1",
        "templates/env-android-emulator.md",
    ):
        if not (ROOT / relative).is_file():
            print(f"android-emulator 실패: 파일이 없습니다: {relative}")
            return 1
    print("android-emulator 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
