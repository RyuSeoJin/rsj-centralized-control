# aseprite — 이 컴퓨터에서 Aseprite를 배치 모드로 돌리고 MCP로 연결하는 환경을 점검합니다

Aseprite 설치 자리 · Python 환경 · MCP 서버 등록은 컴퓨터마다 다릅니다. 이 값을 그림 규칙 쪽에
넣으면 컴퓨터를 바꿀 때마다 그림 규칙을 고쳐야 하므로, 환경의 일은 이 호스트 모듈이 맡습니다.
그림을 어떻게 그리는가는 이 모듈이 다루지 않습니다.

## 언제 켜나

켜지 않습니다. 호스트 모듈이라 프로젝트에 붙지 않고, Aseprite로 작업할 컴퓨터에서 점검 도구로 설치 상태만 확인합니다.

## 무엇을 점검하나

```bash
python core/modules/aseprite/scripts/aseprite_env.py
```

| 항목 | 통과 조건 |
|---|---|
| 실행 파일 | 환경변수 `ASEPRITE_PATH` → PATH의 `aseprite` → 운영체제별 흔한 설치 자리 순으로 찾아집니다 |
| 배치 모드 | Lua 한 줄을 실행해 `app.version`이 찍힙니다 |
| MCP 서버 | Claude Code CLI가 있으면 `aseprite` 이름의 서버가 연결 상태인지 봅니다 (없으면 건너뜁니다) |

다른 도구는 Lua를 이 모듈로 실행합니다 — `aseprite_env.py --run {파일}.lua`.

## 설치 절차

1. **Aseprite 설치** — 1.3 이상. 설치 자리가 흔한 자리가 아니면 환경변수 `ASEPRITE_PATH`에 실행
   파일 전체 경로를 적습니다.
2. **점검** — 위 명령으로 배치 모드까지 통과하는지 봅니다.
3. **(선택) MCP 서버** — Claude가 Aseprite를 도구로 부르게 하려면 Aseprite용 MCP 서버를 하나
   골라 설치하고 Claude Code에 등록합니다.

   ```bash
   claude mcp add --scope user aseprite \
       -e PYTHONPATH={서버 저장소 경로} -- {서버의 파이썬 실행 파일} -m {서버 패키지}
   claude mcp get aseprite
   ```

   고를 때 봅니다 — 원본 저장소인지(포크가 아닌지), 관리가 이어지는지, 외부로 데이터를 보내는
   코드가 없는지(설치 전에 네트워크 호출 · 임의 명령 실행 · 파일 삭제를 훑습니다).

## 알려진 함정

- ⚠️ **Windows의 `--version`은 아무것도 찍지 않을 때가 있습니다.** GUI 실행 파일이라 콘솔 출력이
  붙지 않습니다. 그래서 점검 도구는 배치 모드로 Lua를 돌려 버전을 읽습니다.
- ⚠️ **Windows의 `python` 명령이 Microsoft Store 바로가기일 수 있습니다.** 실행하면 `Python`만
  찍고 아무것도 돌리지 않습니다. 가상 환경의 파이썬 실행 파일을 전체 경로로 부릅니다.
- ⚠️ **uv가 Python을 받은 뒤 「Missing expected target directory for Python minor version link」로
  멈출 수 있습니다.** 받은 폴더는 멀쩡합니다. `uv sync --python {받은 폴더의 python 실행 파일}`로
  경로를 직접 주면 지나갑니다.
- ⚠️ **MCP 서버가 「Failed to connect」로 뜰 수 있습니다.** `-m {패키지}`로 띄우는 서버는 실행 위치가
  저장소 밖이면 패키지를 못 찾습니다. 등록할 때 `-e PYTHONPATH={서버 저장소 경로}`를 줍니다.
- ⚠️ **Lua 문자열에 픽셀 데이터를 넣을 때 특수 문자가 섞이면 스크립트가 깨집니다.** 역슬래시 등이
  이스케이프로 읽히기 때문입니다. 픽셀 값은 16진 두 글자처럼 특수 문자가 없는 인코딩으로 넣습니다.
- ⚠️ **한글을 찍는 도구가 Windows 콘솔(cp949)에서 멈출 수 있습니다.** 도구 첫머리에서 표준 출력을
  UTF-8로 맞춥니다.

## 전제 모듈

없습니다.
