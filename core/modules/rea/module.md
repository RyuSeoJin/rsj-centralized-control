# rea — 이 컴퓨터에 REA(역분석 MCP 서버)를 설치하고 연결 상태를 점검합니다

REA(Reverse Engineer Anything)는 에이전트가 소스 코드 없이 실행 파일 · 앱 · 웹사이트를 분석하게
해 주는 MCP 서버이자 명령줄 도구입니다. 결과마다 근거(Evidence)와 모르는 것(한계)을 함께 돌려줍니다.
Node.js 버전 · MCP 등록 · 분석 엔진(Ghidra · Hopper · IDA) 설치 자리는 컴퓨터마다 다르므로, 환경의
일은 이 호스트 모듈이 맡습니다. **무엇을 어떻게 분석하는가는 이 모듈이 다루지 않습니다.**

## 언제 켜나

켜지 않습니다. 호스트 모듈이라 프로젝트에 붙지 않고, REA로 역분석할 컴퓨터에서 점검 도구로 설치
상태만 확인합니다.

## 공식 출처

REA는 아래 세 곳에서만 받습니다. 이름이 비슷한 저장소 · README를 베낀 저장소 · 미러가 여럿 있고,
악성 코드를 심은 사칭본이 돈 적이 있습니다. 다른 곳의 설치 안내 · 릴리스 링크는 따르지 않습니다.

| 출처 | 자리 |
|---|---|
| 원본 저장소 | `https://github.com/morluto/rea` (MIT) |
| 웹사이트 | `https://rea.tools/` |
| npm 패키지 | `rea-agents` |

## 무엇을 점검하나

```bash
python core/modules/rea/scripts/rea_env.py
```

| 항목 | 통과 조건 |
|---|---|
| Node.js | `node`가 PATH에 있고 22.x(22.23.4 이상) · 24.x(24.22.1 이상) · 26.x(26.12.1 이상) · 27 이상 중 하나입니다. REA 자신은 22.19 · 24.11 · 26부터 돌지만, Brotli 해제기 결함(CVE-2026-111497)을 고친 보안 릴리스를 하한으로 둡니다 |
| npx | PATH에 있습니다 |
| MCP 서버 | Claude Code CLI가 있으면 `rea` 이름의 서버가 연결 상태인지 봅니다(없으면 건너뜁니다) |
| `rea` 명령 | 전역 설치가 있으면 버전을 찍습니다. 없어도 실패가 아닙니다 — npx로 씁니다 |
| 분석 엔진 | `GHIDRA_INSTALL_DIR` · PATH의 `ghidraRun` · `HOPPER_LAUNCHER_PATH`를 알려 줍니다. 없어도 실패가 아닙니다 — JavaScript/Electron · .NET 정적 분석은 엔진 없이 됩니다 |

더 깊은 진단은 REA 자신의 점검(읽기 전용)으로 합니다. 도구에 `--doctor`를 주면 이것을 함께 돌립니다.
npm에서 패키지를 받으므로 네트워크가 필요합니다.

```bash
npx -y rea-agents@latest doctor --client claude_code --json
npx -y rea-agents@latest doctor --provider ghidra --json
```

## 새 컴퓨터 설치

점검이 실패하는 컴퓨터(처음 쓰는 컴퓨터)에서 한 번 합니다.

1. **Node.js 설치** — 위 버전 조건을 맞춥니다.
2. **설치 계획 보기 · 승인** — REA의 설치 도구가 고칠 설정 파일 경로와 설치할 것을 먼저 보여 주고,
   승인해야 씁니다. 기존 설정은 백업됩니다. 에이전트 고르기에서 Claude Code를 고릅니다.

   ```bash
   npx rea-agents@latest setup
   ```

   - 승인 전에 계획의 경로가 이 컴퓨터의 Claude 설정 자리인지 확인합니다.
   - Claude Desktop을 쓰고 있으면 승인 전에 완전히 종료합니다 — 켜져 있으면 등록을 덮어쓸 수 있습니다.
   - Hopper 설치는 별도 승인입니다. 필요 없으면 거절합니다(Windows에서는 Hopper를 설치할 수 없습니다).
3. **Claude Code 다시 시작** — 등록한 MCP 도구는 새 세션부터 보입니다.
4. **(선택) 네이티브 분석 엔진** — 실행 파일 · DLL을 의사코드로 보려면 Ghidra 12.1.x와 그 Ghidra가
   요구하는 64비트 JDK를 직접 설치하고 `GHIDRA_INSTALL_DIR`를 지정합니다. 설치 도구는 Ghidra · Java를
   설치하지 않습니다. Windows의 Ghidra 연결은 아직 실험 단계입니다.
5. **점검** — `rea_env.py`를 다시 돌립니다.

**한 프로젝트에서만 쓰려면** 전역 등록 대신 그 프로젝트 폴더에서 local 범위로 등록합니다. 저장소에
`.mcp.json`을 쓰는 `--scope project`는 쓰지 않습니다 — 커밋되어 다른 곳으로 퍼질 수 있습니다.

```powershell
claude mcp add --scope local rea -- cmd.exe /d /c npx -y rea-agents@{버전} mcp
```

local 범위 등록은 `rea doctor` · `rea update` · `rea uninstall`이 보지 못합니다. 버전을 올리거나 지울
때는 같은 폴더에서 `claude mcp remove --scope local rea` 뒤 다시 등록합니다.

## 업데이트 · 제거

REA는 릴리스가 잦고 버그 수정이 많습니다. 문제가 생기면 먼저 업데이트합니다.

| 할 일 | 명령 |
|---|---|
| npx로 등록한 경우 업데이트 | `npx rea-agents@latest setup` 뒤 Claude Code 다시 시작 |
| 전역 설치(`npm install --global rea-agents`)의 업데이트 | `rea update` |
| 제거 | `rea uninstall` — REA가 만든 등록 · 지침 파일만 지웁니다. 분석 근거 · 캡처 · Hopper는 남깁니다 |

## 알려진 함정

- ⚠️ **Windows에서 `npx`를 MCP 명령으로 바로 등록하면 서버가 뜨지 않습니다.** `npx`가 실행 파일이 아닌
  셸 스크립트라 stdio 클라이언트가 띄우지 못합니다. `cmd.exe /d /c npx …`로 감쌉니다.
- ⚠️ **Windows 예시는 PowerShell로 돌립니다.** 문서의 `NAME=값 명령` 꼴(POSIX 환경변수 지정)은 cmd.exe ·
  PowerShell에서 그대로 되지 않습니다. PowerShell에서는 `$env:NAME = '값'`으로 씁니다.
- ⚠️ **`rea doctor`의 전체 `healthy`가 false여도 지금 할 분석은 될 수 있습니다.** 쓰지 않는 엔진 · 에이전트까지
  감사하기 때문입니다. `--provider` · `--client`로 범위를 좁혀 그 항목만 봅니다.
- ⚠️ **한글을 찍는 도구가 Windows 콘솔(cp949)에서 멈출 수 있습니다.** 도구 첫머리에서 표준 출력을
  UTF-8로 맞춥니다.

## 전제 모듈

없습니다.
