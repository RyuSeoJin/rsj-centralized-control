# -*- coding: utf-8 -*-
"""결함 주입 매트릭스 — 내 테스트가 결함을 실제로 잡는지 증명합니다
(rules/sut-build.md §2 · 프로젝트의 fault-injection 사양)

무엇을 하는가
------------
  같은 스위트를 **주입 키만 바꿔** 반복 실행한다. 케이스는 한 줄도 고치지 않는다 —
  바뀌는 것은 SUT에 켜 둔 고장뿐이다.

      주입 없음 1회   전부 PASS여야 한다 (기준선)
      결함별 1회      **담당 영역만** FAIL이어야 한다

  행=주입 결함, 열=영역으로 접어 표를 만든다. 읽을 것은 하나, **대각선만 FAIL인가**다.

      대각선이 PASS      결함을 심었는데 아무도 못 잡았다 = 그 TC가 부실하다.
                         결함이 아니라 케이스로 되돌아간다
      대각선 밖이 FAIL   결함끼리 간섭한다 = 주입 지점이 넓다. 결함은 서로 독립이어야
                         매트릭스가 읽힌다

  영역은 TC ID의 영역코드다. 테스트 이름이 `test_tc_{영역코드}_{번호}_{요약}` 규약을
  따르므로(automation 모듈의 케이스명 규칙) 이름에서 그대로 접는다. 규약 밖 이름은 스모크로
  본다 — 스모크는 어느 영역도 담당하지 않으므로 기준선에서만 의미가 있다.

담당은 어떻게 정하나
------------------
  「돌려 보니 깨졌다」는 기준이 아니다. 그건 관측이라 항상 통과하고, 그 순간 매트릭스는
  아무것도 증명하지 않는다. 담당은 결함의 **주입 지점을 지나고 그 오동작을 판정하는**
  케이스이며, 지나가기만 하고 결과를 보지 않는 케이스는 담당이 아니다.

  담당을 영역(TC ID의 영역코드)으로 두면 판정이 무뎌진다 — 한 영역에 22건이 있어도 1건만
  깨지면 「FAIL」로 보이므로, 나머지 21건이 안 깨진 게 맞는지 표에 남지 않는다. 그래서
  담당은 **TC 단위**로 적고, 표만 영역으로 접어 읽는다.

  이 목록은 낡아도 스스로 드러난다. 매트릭스가 양방향으로 보기 때문이다 — 담당인데 안
  깨지면 그 TC가 부실하거나 담당 지정이 틀린 것이고, 담당이 아닌데 깨지면 주입이 넓거나
  담당을 빠뜨린 것이다.

기대 대응표는 어디서 오나
------------------------
  프로젝트의 `automation/{프로젝트}-fault-matrix.json`이며, 정본은 그 프로젝트의
  fault-injection 사양 §2다. 기대를 코드에 박으면 사양과 어긋나도 아무도 모른다.

      {"areas": [...],
       "faults": [{"key": "save-leak", "point": "슬롯 저장의 복사 계층",
                   "expect": [{"tc": "TC-SAV-001", "why": "..."}]}]}

사용법
------
    python run_fault_matrix.py --tests <tests 디렉터리> --map <fault-matrix.json> \
        --out <결과 디렉터리> [--python <파이썬 실행기>] [--only <키>]

  대각선이 어긋나면 종료 코드 1로 끝난다.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

BASELINE = ""                       # 주입 없음 — 표에서는 「(주입 없음)」 행
BASELINE_LABEL = "(주입 없음)"
SMOKE = "SMOKE"

# 테스트 이름 → TC ID. `test_tc_sav_003_슬롯_간_격리[chromium]` → SAV, TC-SAV-003
NAME_RE = re.compile(r"^test_tc_([a-z]+)_(\d+)_")


def run_suite(python, tests_dir, inject, xml_path):
    """스위트를 한 번 돌리고 junit xml을 남긴다. 실패는 정상 결과이므로 예외로 보지 않는다."""
    cmd = [python, "-m", "pytest", tests_dir, "-q", "--junitxml=" + xml_path]
    if inject:
        cmd.append("--inject=" + inject)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = proc.stdout.decode("utf-8", "replace")
    if not os.path.exists(xml_path):
        # 수집 자체가 깨진 경우 — 결과가 없으므로 매트릭스를 만들 수 없다
        raise SystemExit("[중단] 결과 파일이 없습니다: %s\n%s" % (xml_path, out[-3000:]))
    return out


def parse_results(xml_path):
    """({영역코드: {"pass": n, "fail": [이름, ...]}}, 깨진 TC ID 집합)"""
    root = ET.parse(xml_path).getroot()
    areas, failed_tcs = {}, set()
    for case in root.iter("testcase"):
        name = case.get("name") or ""
        m = NAME_RE.match(name)
        area = m.group(1).upper() if m else SMOKE
        slot = areas.setdefault(area, {"pass": 0, "fail": []})
        failed = any(child.tag in ("failure", "error") for child in case)
        if failed:
            slot["fail"].append(name)
            if m:
                failed_tcs.add("TC-%s-%s" % (m.group(1).upper(), m.group(2)))
        elif any(child.tag == "skipped" for child in case):
            pass                    # 건너뛴 것은 PASS로도 FAIL로도 세지 않는다
        else:
            slot["pass"] += 1
    return areas, failed_tcs


def cell(slot):
    if slot is None or (slot["pass"] == 0 and not slot["fail"]):
        return "-"
    return "**FAIL** %d" % len(slot["fail"]) if slot["fail"] else "PASS"


def judge(baseline, failed, faults):
    """대각선 판정 — TC 단위로 양방향을 본다. 어긋난 것만 사유와 함께 낸다."""
    problems = []
    for area, slot in sorted(baseline.items()):
        if slot["fail"]:
            problems.append("기준선(주입 없음) %s 영역에서 %d건 FAIL — 주입 이전에 이미 깨져 "
                            "있어 매트릭스를 읽을 수 없습니다: %s"
                            % (area, len(slot["fail"]), ", ".join(slot["fail"][:5])))
    for fault in faults:
        got = failed[fault["key"]]
        want = {e["tc"] for e in fault["expect"]}
        why = {e["tc"]: e.get("why", "") for e in fault["expect"]}
        for tc in sorted(want - got):
            problems.append("%s × %s — 결함을 켰는데 담당 TC가 통과했습니다. 담당으로 적은 "
                            "근거는 「%s」이므로, 그 케이스가 결함을 못 잡거나 담당 지정이 "
                            "틀렸습니다" % (fault["key"], tc, why.get(tc, "")))
        for tc in sorted(got - want):
            problems.append("%s × %s — 담당이 아닌 TC가 깨졌습니다. 주입 지점(%s)이 넓거나 "
                            "담당을 빠뜨린 것이므로 둘 중 어느 쪽인지 판단해 고칩니다"
                            % (fault["key"], tc, fault.get("point", "?")))
    return problems


def render(baseline, runs, failed, faults, areas, problems):
    lines = []
    header = ["주입 \\ 영역"] + areas + [SMOKE]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))

    def row(label, res):
        cells = [cell(res.get(a)) for a in areas] + [cell(res.get(SMOKE))]
        return "| " + " | ".join([label] + cells) + " |"

    lines.append(row(BASELINE_LABEL, baseline))
    for fault in faults:
        lines.append(row("`%s`" % fault["key"], runs[fault["key"]]))
    lines.append("")
    lines.append("표는 읽기 위해 영역으로 접은 것이고, **판정은 TC 단위**로 합니다 — "
                 "한 영역에 케이스가 여럿이면 하나만 깨져도 영역은 FAIL로 보입니다.")
    lines.append("")
    if problems:
        lines.append("## 어긋난 자리")
        lines.append("")
        for p in problems:
            lines.append("- " + p)
    else:
        lines.append("대각선만 FAIL입니다 — 각 결함을 담당 영역의 TC가 실제로 잡아냈고, "
                     "담당 밖은 흔들리지 않았습니다.")
    lines.append("")
    lines.append("## 담당 TC — 무엇을 근거로 담당인가")
    lines.append("")
    lines.append("담당은 실행 결과가 아니라 **주입 지점을 지나고 그 오동작을 판정하는가**로 "
                 "정합니다. 지나가기만 하는 케이스는 담당이 아닙니다.")
    for fault in faults:
        got = failed[fault["key"]]
        lines.append("")
        lines.append("**`%s`** — 주입 지점: %s" % (fault["key"], fault.get("point", "?")))
        lines.append("")
        lines.append("| TC | 잡았나 | 담당 근거 |")
        lines.append("|---|---|---|")
        for e in fault["expect"]:
            mark = "잡음" if e["tc"] in got else "**놓침**"
            lines.append("| %s | %s | %s |" % (e["tc"], mark, e.get("why", "")))
        extra = sorted(got - {e["tc"] for e in fault["expect"]})
        for tc in extra:
            lines.append("| %s | 잡음 | **담당 밖** — 주입이 넓거나 담당을 빠뜨렸습니다 |" % tc)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--only", help="이 키 하나만 실행 (기준선 포함). 진단용")
    args = ap.parse_args()

    # 콘솔 기본 인코딩(cp949)으로는 표의 문장부호가 깨진다 — 결과를 다 만들어 놓고
    # 출력에서 죽으면 판정을 못 본다
    # 한글 출력이 콘솔 기본 인코딩으로 나가면, 다른 도구가 받아 읽을 때 깨집니다.
    # 오류는 stderr로 나가므로 둘 다 맞춥니다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    with open(args.map, encoding="utf-8") as f:
        conf = json.load(f)
    faults = [x for x in conf["faults"] if not args.only or x["key"] == args.only]
    areas = conf["areas"]

    os.makedirs(args.out, exist_ok=True)

    keys = [BASELINE] + [x["key"] for x in faults]
    results, failed = {}, {}
    for key in keys:
        label = key or BASELINE_LABEL
        print("[실행] %s" % label, flush=True)
        xml_path = os.path.join(args.out, "junit-%s.xml" % (key or "none"))
        out = run_suite(args.python, args.tests, key, xml_path)
        summary = [ln for ln in out.strip().splitlines()
                   if " passed" in ln or " failed" in ln]
        print("       " + (summary[-1] if summary else ""), flush=True)
        results[key], failed[key] = parse_results(xml_path)

    baseline = results[BASELINE]
    problems = judge(baseline, failed, faults)
    body = render(baseline, results, failed, faults, areas, problems)

    md_path = os.path.join(args.out, "fault-matrix.md")
    # newline 고정 — 위와 같은 이유(플랫폼 줄바꿈 차이가 낡음 검사에서 거짓 신호가 됨)
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 결함 주입 매트릭스\n\n")
        f.write("행=주입 결함 · 열=영역. **대각선만 FAIL이 정상**입니다.\n\n")
        f.write(body + "\n")
    print("\n" + body)
    print("\n[산출] %s" % md_path)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
