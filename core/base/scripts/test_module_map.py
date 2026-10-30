# -*- coding: utf-8 -*-
"""모듈 분야 묶음과 모듈 지도 생성을 검사합니다."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_module_map  # noqa: E402
import module as modlib  # noqa: E402


def make_module(core, name, title, needs="", meta=None):
    d = os.path.join(core, "modules", name)
    os.makedirs(d)
    md = ["# %s — %s" % (name, title), "", "## 언제 켜나", "", "**%s를 하는가?**" % name, ""]
    if needs:
        md += ["## 전제 모듈", "", "`%s` — %s가 먼저 있어야 합니다." % (needs, needs), ""]
    with io.open(os.path.join(d, "module.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    if meta is not None:
        with io.open(os.path.join(d, "module.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)


class ModuleMapTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        core = self.core = self.tmp.name
        os.makedirs(os.path.join(core, "modules"))
        with io.open(os.path.join(core, "modules", "groups.json"), "w", encoding="utf-8") as f:
            json.dump({"groups": [
                {"id": "beta", "label": "둘째 분야", "ask": "둘째 일을 하나요?"},
                {"id": "alpha", "label": "첫째 분야", "ask": "첫째 일을 하나요?"},
                {"id": "empty", "label": "빈 분야", "ask": "아무도 없나요?"},
            ]}, f, ensure_ascii=False)
        # beta 안에서 이름 순이면 aa · mm · zz지만, 전제 사슬 zz → mm → aa 순이 맞습니다
        make_module(core, "zz", "바닥", meta={"group": "beta"})
        make_module(core, "mm", "가운데", needs="zz", meta={"group": "beta"})
        make_module(core, "aa", "꼭대기", needs="mm", meta={
            "group": "beta",
            "instead": [{"name": "kk", "why": "kk 쪽 일이면"}]})
        make_module(core, "bb", "곁가지", needs="zz", meta={
            "group": "beta", "pairs": [{"name": "kk", "why": "같이 쓰면 좋음"}],
            "external": [{"name": "Tool", "kind": "program", "use": "그림 그리기"},
                         {"name": "lib", "kind": "library", "use": "읽기", "required": False}]})
        make_module(core, "kk", "다른 분야", meta={
            "group": "alpha", "scope": "workspace",
            "instead": [{"name": "aa", "why": "aa 쪽 일이면"}]})
        make_module(core, "nogroup", "분야 없음", meta=None)
        make_module(core, "lost", "없는 분야", meta={"group": "nowhere", "scope": "host"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_grouping_and_order(self):
        g = modlib.grouped(self.core)
        labels = [x[0]["label"] for x in g]
        # groups.json 순서, 빈 분야는 빠지고, 분류 없음은 맨 끝
        self.assertEqual(labels, ["둘째 분야", "첫째 분야", "분류 없음"])
        beta = [m[0] for m in g[0][1]]
        # 사슬이 끊기지 않습니다 — zz 다음에 그것을 전제로 삼는 bb · mm(이름 순), mm 다음에 aa
        self.assertEqual(beta, ["zz", "bb", "mm", "aa"])
        self.assertEqual([m[0] for m in g[2][1]], ["lost", "nogroup"])

    def test_non_dirs_are_not_modules(self):
        names = [m[0] for m in modlib.modules(self.core)]
        self.assertNotIn("groups.json", names)

    def test_links(self):
        self.assertEqual(modlib.pairs("bb", self.core), [("kk", "같이 쓰면 좋음")])
        self.assertEqual(modlib.instead("nogroup", self.core), [])
        self.assertEqual(modlib.module_group("nogroup", self.core), "")

    def test_render(self):
        text = gen_module_map.render(self.core)
        self.assertIn("### 둘째 분야 — 둘째 일을 하나요?", text)
        self.assertNotIn("빈 분야", text)
        self.assertIn("### 분류 없음", text)
        self.assertIn("`aa` ← `mm` ← `zz`", text)
        self.assertIn("`kk` (워크스페이스)", text)
        # instead는 양쪽이 적어도 한 번만, 양쪽 이유가 제자리에
        rows = [l for l in text.split("\n") if "| `kk` |" in l and "`aa`" in l]
        self.assertEqual(rows, ["| `aa` | aa 쪽 일이면 | `kk` | kk 쪽 일이면 |"])
        self.assertIn("| `bb` | `kk` | 같이 쓰면 좋음 |", text)
        # 결정적 출력
        self.assertEqual(text, gen_module_map.render(self.core))

    def test_external(self):
        ext = modlib.external("bb", self.core)
        self.assertEqual([(x["name"], x["required"]) for x in ext], [("Tool", True), ("lib", False)])
        self.assertEqual(modlib.external("zz", self.core), [])
        text = gen_module_map.render(self.core)
        self.assertIn("| Tool | 설치 프로그램 | `bb` | 예 | 그림 그리기 |", text)
        self.assertIn("| lib | 라이브러리 | `bb` | 선택 | 읽기 |", text)

    def test_group_graphs(self):
        groups, order, info = gen_module_map.collect(self.core)
        group_of = dict((m[0], g["label"]) for g, mods in groups for m in mods)
        beta = "\n".join(gen_module_map.group_graph(groups[0][1], order, info, group_of))
        self.assertIn("  m_zz --> m_mm", beta)       # 전제: mm을 켜려면 zz가 먼저
        self.assertIn("  m_bb -.- m_kk", beta)       # 함께 쓰는 짝
        self.assertIn("  m_aa <-.-> m_kk", beta)     # 고르는 짝 — 양쪽이 적어도 한 줄
        # 다른 분야 모듈은 이어진 것만, 분야 이름을 붙인 회색 상자로
        self.assertIn('  m_kk["kk<br/>(첫째 분야)"]:::other', beta)
        self.assertNotIn("m_lost", beta)
        alpha = "\n".join(gen_module_map.group_graph(groups[1][1], order, info, group_of))
        self.assertIn('  m_bb["bb<br/>(둘째 분야)"]:::other', alpha)
        self.assertNotIn("m_zz", alpha)               # kk와 직접 이어지지 않은 모듈은 그리지 않습니다
        # 이어진 것이 없는 분야는 그림이 없습니다
        self.assertEqual(gen_module_map.group_graph(groups[2][1], order, info, group_of), [])
        text = gen_module_map.render(self.core)
        self.assertEqual(text.count("```mermaid"), 2)

    def test_readme_block(self):
        readme = os.path.join(self.core, "README.md")
        with io.open(readme, "w", encoding="utf-8") as f:
            f.write("# 제목\n\n앞글\n\n%s\n낡은 것\n%s\n\n뒷글\n"
                    % (gen_module_map.README_START, gen_module_map.README_END))
        self.assertTrue(gen_module_map.has_block(readme))
        self.assertEqual(gen_module_map.main(["--core", self.core, "--readme", readme, "--check"]), 1)
        self.assertEqual(gen_module_map.main(["--core", self.core, "--readme", readme]), 0)
        with io.open(readme, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("낡은 것", text)
        self.assertTrue(text.startswith("# 제목\n\n앞글\n\n"))
        self.assertTrue(text.endswith("\n\n뒷글\n"))
        self.assertIn("### 둘째 분야\n\n**둘째 일을 하나요?**\n\n| 모듈 | 하는 일 | 외부 도구 |", text)
        self.assertIn("| `zz` | 바닥 | — |", text)
        self.assertIn("| Tool | 설치 프로그램 | `bb` |", text)
        self.assertIn("| lib | 라이브러리 | `bb`(선택) |", text)
        self.assertIn("| Tool, lib(선택) |", text)
        self.assertEqual(gen_module_map.main(["--core", self.core, "--readme", readme, "--check"]), 0)
        # 표시가 없는 README는 건드리지 않습니다
        plain = os.path.join(self.core, "PLAIN.md")
        with io.open(plain, "w", encoding="utf-8") as f:
            f.write("# 받는 저장소\n")
        self.assertFalse(gen_module_map.has_block(plain))
        self.assertEqual(gen_module_map.main(["--core", self.core, "--readme", plain]), 0)
        with io.open(plain, encoding="utf-8") as f:
            self.assertEqual(f.read(), "# 받는 저장소\n")

    def test_without_groups_file(self):
        os.remove(os.path.join(self.core, "modules", "groups.json"))
        g = modlib.grouped(self.core)
        self.assertEqual([x[0]["label"] for x in g], ["분류 없음"])
        self.assertIn("### 분류 없음", gen_module_map.render(self.core))

    def test_write_and_check(self):
        out = os.path.join(self.core, "modules", "module-map.md")
        self.assertEqual(gen_module_map.main(["--core", self.core, "--check"]), 1)
        self.assertEqual(gen_module_map.main(["--core", self.core]), 0)
        self.assertTrue(os.path.isfile(out))
        self.assertEqual(gen_module_map.main(["--core", self.core, "--check"]), 0)
        # 지도 파일이 생겨도 모듈로 세지 않습니다
        self.assertNotIn("module-map.md", [m[0] for m in modlib.modules(self.core)])


if __name__ == "__main__":
    unittest.main()
