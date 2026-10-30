# -*- coding: utf-8 -*-
"""base 규칙 지도 생성을 검사합니다."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_base_map  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)


class BaseMapTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        b = self.base = self.tmp.name
        write(os.path.join(b, "base-groups.json"), json.dumps({
            "groups": [
                {"id": "a", "label": "첫째 일", "rules": ["rules/read-gates.md", "rules/alpha.md", "rules/gone.md"]},
                {"id": "b", "label": "둘째 일", "rules": ["rules/beta.md", "guide.md"]},
            ],
            "hubs": ["rules/read-gates.md"]}, ensure_ascii=False))
        write(os.path.join(b, "rules", "read-gates.md"),
              "# read-gates — 무엇을 읽는가\n\n## 읽기 게이트\n\n| 상황 | 읽는 파일 | 멈추는 자리 |\n|---|---|---|\n"
              "| 알파를 할 때 | `core/base/rules/alpha.md` | — |\n"
              "| 둘 다 할 때 | `core/base/rules/alpha.md` · `core/base/rules/beta.md` | — |\n\n"
              "## 다른 절\n\n| 상황 | 읽는 파일 |\n|---|---|\n| 무시할 줄 | `core/base/rules/beta.md` |\n\n"
              "alpha.md · beta.md · guide.md를 모두 가리킵니다.\n")
        write(os.path.join(b, "rules", "alpha.md"),
              "<!-- 주석 -->\n# alpha — 첫째 규칙\n\n## 1. 시작\n\n`beta.md`를 따릅니다.\n\n```\n## 코드 안 제목\n```\n\n## §2 끝\n")
        write(os.path.join(b, "rules", "beta.md"), "# beta — 둘째 규칙\n\n## 절\n\nalpha-old.md는 다른 파일입니다.\n")
        write(os.path.join(b, "rules", "stray.md"), "# stray — 분야에 없는 규칙\n")
        write(os.path.join(b, "guide.md"), "# guide — 안내\n\n`rules/alpha.md`를 봅니다.\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_collect(self):
        groups, hubs, info = gen_base_map.collect(self.base)
        self.assertEqual([g["label"] for g in groups], ["첫째 일", "둘째 일", "분류 없음"])
        self.assertNotIn("rules/gone.md", groups[0]["rules"])        # 없는 파일은 뺍니다
        self.assertEqual(groups[2]["rules"], ["rules/stray.md"])     # 분야에 없는 규칙은 끝으로
        a = info["rules/alpha.md"]
        self.assertEqual(a["title"], "첫째 규칙")
        self.assertEqual(a["sections"], ["시작", "끝"])              # 번호를 떼고 코드 블록 안은 건너뜀
        self.assertEqual(a["gates"], ["알파를 할 때", "둘 다 할 때"])
        self.assertEqual(info["rules/beta.md"]["gates"], ["둘 다 할 때"])   # 다른 절의 표는 읽지 않음
        self.assertEqual(a["refs"], ["rules/beta.md"])
        self.assertEqual(info["rules/beta.md"]["refs"], [])          # alpha-old.md는 alpha.md가 아님
        self.assertEqual(info["guide.md"]["refs"], ["rules/alpha.md"])

    def test_render(self):
        text = gen_base_map.render(self.base)
        self.assertIn("## 첫째 일", text)
        self.assertIn("| [alpha](rules/alpha.md) | 첫째 규칙 | 알파를 할 때 / 둘 다 할 때 | 시작 · 끝 | beta |", text)
        # 색인 문서는 그림에서 빠지고, 가리키는 규칙 칸은 「색인」으로 줄입니다
        self.assertNotIn("r_read_gates -->", text)
        self.assertIn("| [read-gates](rules/read-gates.md) | 무엇을 읽는가 | 모든 작업 — 무엇을 더 읽을지 정합니다 | "
                      "읽기 게이트 · 다른 절 | 색인 — base 규칙 대부분 |", text)
        # 나가는 선만 — beta를 가리키는 alpha 선은 첫째 일 그림에만 있습니다
        self.assertEqual(text.count("r_alpha --> r_beta"), 1)
        self.assertIn("  r_alpha --> r_beta", text)
        self.assertIn('  r_beta["beta<br/>(둘째 일)"]:::other', text)
        self.assertEqual(text, gen_base_map.render(self.base))      # 결정적 출력

    def test_readme_block(self):
        readme = os.path.join(self.base, "README.md")
        write(readme, "앞\n\n%s\n옛\n%s\n\n뒤\n" % (gen_base_map.README_START, gen_base_map.README_END))
        self.assertEqual(gen_base_map.main(["--base", self.base, "--readme", readme, "--check"]), 1)
        self.assertEqual(gen_base_map.main(["--base", self.base, "--readme", readme]), 0)
        with io.open(readme, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("옛", text)
        self.assertIn("| 첫째 일 | [read-gates](core/base/rules/read-gates.md) | 무엇을 읽는가 | "
                      "모든 작업 — 무엇을 더 읽을지 정합니다 |\n"
                      "|  | [alpha](core/base/rules/alpha.md) | 첫째 규칙 | 알파를 할 때 / 둘 다 할 때 |", text)
        self.assertTrue(text.endswith("\n\n뒤\n"))
        self.assertEqual(gen_base_map.main(["--base", self.base, "--readme", readme, "--check"]), 0)
        plain = os.path.join(self.base, "PLAIN.md")
        write(plain, "# 받는 저장소\n")
        self.assertEqual(gen_base_map.main(["--base", self.base, "--readme", plain]), 0)
        with io.open(plain, encoding="utf-8") as f:
            self.assertEqual(f.read(), "# 받는 저장소\n")

    def test_write_and_check(self):
        self.assertEqual(gen_base_map.main(["--base", self.base, "--check"]), 1)
        self.assertEqual(gen_base_map.main(["--base", self.base]), 0)
        self.assertEqual(gen_base_map.main(["--base", self.base, "--check"]), 0)


if __name__ == "__main__":
    unittest.main()
