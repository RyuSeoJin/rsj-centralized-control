# -*- coding: utf-8 -*-
"""이 컴퓨터에서 Aseprite를 찾고 배치 모드로 돌려 보며 MCP 등록까지 점검합니다

왜 따로 있나
----------
  Aseprite 설치 자리와 Python 환경은 컴퓨터마다 다릅니다. 이 값을 그림 규칙 쪽 도구에 넣으면
  컴퓨터를 바꿀 때마다 그림 규칙을 고쳐야 합니다. 그래서 찾기 · 실행 · 점검을 이 호스트 모듈
  한 곳에 두고, 다른 도구는 `run_script()`만 부릅니다.

찾는 순서
--------
  1. 환경변수 ASEPRITE_PATH
  2. PATH의 `aseprite`
  3. 운영체제별 흔한 설치 자리 (Steam · 기본 설치 폴더)

사용법
------
    python aseprite_env.py                 점검 보고 (없으면 exit 1)
    python aseprite_env.py --run 파일.lua  Lua를 배치 모드로 실행합니다
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMMON = {
    "win32": [
        r"C:\Program Files\Aseprite\Aseprite.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Aseprite\Aseprite.exe",
        r"C:\Program Files\Steam\steamapps\common\Aseprite\Aseprite.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Aseprite\Aseprite.exe"),
    ],
    "darwin": [
        "/Applications/Aseprite.app/Contents/MacOS/aseprite",
        os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Aseprite/"
                           "Aseprite.app/Contents/MacOS/aseprite"),
    ],
    "linux": [
        "/usr/bin/aseprite",
        os.path.expanduser("~/.steam/steam/steamapps/common/Aseprite/aseprite"),
    ],
}


def find_exe():
    """Aseprite 실행 파일 경로. 못 찾으면 None."""
    env = os.environ.get("ASEPRITE_PATH")
    if env and os.path.isfile(env):
        return env
    on_path = shutil.which("aseprite")
    if on_path:
        return on_path
    key = "win32" if sys.platform.startswith("win") else "darwin" if sys.platform == "darwin" else "linux"
    for p in COMMON[key]:
        for hit in glob.glob(p):
            if os.path.isfile(hit):
                return hit
    return None


def run_script(lua_path, sprite=None, exe=None, timeout=300):
    """Lua 스크립트를 배치 모드로 실행하고 (성공 여부, 표준 출력)을 돌려줍니다.

    Lua 안의 오류는 종료 코드에 드러나지 않을 수 있어, 스크립트가 `ERROR:`로 시작하는 줄을
    찍으면 실패로 봅니다.
    """
    exe = exe or find_exe()
    if not exe:
        return False, "Aseprite를 찾지 못했습니다 — ASEPRITE_PATH를 지정합니다"
    args = [exe, "--batch"] + ([sprite] if sprite else []) + ["--script", lua_path]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    bad = r.returncode != 0 or any(l.startswith("ERROR:") for l in out.splitlines())
    return not bad, out


def version(exe=None):
    """배치 모드에서 app.version을 찍어 봅니다. Windows의 --version은 아무것도 찍지 않을 때가 있습니다."""
    with tempfile.TemporaryDirectory() as tmp:
        lua = os.path.join(tmp, "v.lua")
        with open(lua, "w", encoding="utf-8") as f:
            f.write("print('ASEPRITE ' .. tostring(app.version))\n")
        ok, out = run_script(lua, exe=exe, timeout=120)
    for line in out.splitlines():
        if line.startswith("ASEPRITE "):
            return line.split(" ", 1)[1].strip()
    return None


def mcp_status(name="aseprite"):
    """Claude Code에 MCP 서버가 등록 · 연결되어 있는지. CLI가 없으면 None."""
    cli = shutil.which("claude")
    if not cli:
        return None
    try:
        r = subprocess.run([cli, "mcp", "get", name], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (r.stdout or "") + (r.stderr or "")
    if "Connected" in text or "✓" in text:
        return "연결됨"
    if "No MCP server" in text or r.returncode != 0:
        return "등록 안 됨"
    return "등록됨 · 연결 실패"


def report():
    exe = find_exe()
    print("Aseprite 실행 파일 — %s" % (exe or "찾지 못함 (ASEPRITE_PATH 지정 필요)"))
    if not exe:
        return 1
    v = version(exe)
    print("배치 모드 실행      — %s" % ("버전 " + v if v else "실패 (Lua가 돌지 않음)"))
    m = mcp_status()
    print("MCP 서버(aseprite)  — %s" % (m or "claude CLI 없음 · 건너뜀"))
    return 0 if v else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", help="배치 모드로 실행할 Lua 파일")
    a = ap.parse_args(argv)
    if a.run:
        ok, out = run_script(a.run)
        print(out.strip())
        return 0 if ok else 1
    return report()


if __name__ == "__main__":
    sys.exit(main())
