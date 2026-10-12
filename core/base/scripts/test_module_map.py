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
            "group": "beta", "pairs": [{"name": "kk", "why": "같이 쓰면 좋음"}]})
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
