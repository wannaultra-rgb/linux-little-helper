# -*- coding: utf-8 -*-
"""命令数据与中文检索的回归测试。"""

import unittest

from guide.catalog import CATEGORY_ORDER, COMMANDS, COMMANDS_BY_NAME, TOTAL_COMMANDS, category_counts
from guide.search import normalize, search_commands, strip_intent


class CatalogTest(unittest.TestCase):
    def test_catalog_size_and_categories(self):
        self.assertGreaterEqual(TOTAL_COMMANDS, 100)
        self.assertEqual(set(category_counts()), set(CATEGORY_ORDER))
        self.assertEqual(sum(category_counts().values()), TOTAL_COMMANDS)

    def test_unique_names_and_aliases(self):
        aliases = []
        for item in COMMANDS:
            self.assertIn(item["category"], CATEGORY_ORDER)
            self.assertTrue(item["summary"].strip())
            self.assertTrue(item["syntax"].strip())
            self.assertTrue(item["examples"])
            self.assertIn(item["danger"], ("safe", "caution", "danger"))
            aliases.extend(alias.lower() for alias in item["aliases"])
        self.assertEqual(len(aliases), len(set(aliases)), "别名不应重复")

    def test_related_commands_exist(self):
        for item in COMMANDS:
            for related in item["related"]:
                self.assertIn(related, COMMANDS_BY_NAME, f"{item['name']} -> {related}")

    def test_vi_keeps_its_identity(self):
        item = COMMANDS_BY_NAME["vi"]
        self.assertIn("vim", item["aliases"])
        self.assertIn("模态", item["summary"])
        self.assertIn("i", dict(item["options"]))


class SearchTest(unittest.TestCase):
    def names(self, query, limit=6):
        return [item["name"] for item in search_commands(query)[:limit]]

    def test_chinese_to_command(self):
        self.assertEqual(self.names("下载")[0], "wget")
        self.assertIn("curl", self.names("下载"))
        self.assertEqual(self.names("查看端口")[0], "ss")
        self.assertEqual(self.names("磁盘空间")[0], "df")
        self.assertEqual(self.names("删除文件")[0], "rm")
        self.assertEqual(self.names("改权限")[0], "chmod")
        self.assertEqual(self.names("安装软件")[0], "apt")

    def test_editor_queries(self):
        self.assertEqual(self.names("vi")[0], "vi")
        self.assertEqual(self.names("vim")[0], "vi")
        self.assertEqual(self.names("vi是什么")[0], "vi")

    def test_archive_queries(self):
        self.assertIn(self.names("解压")[0], ("unzip", "tar"))
        self.assertIn("tar", self.names("解压"))
        self.assertIn("zip", self.names("压缩"))

    def test_sentence_queries(self):
        top = self.names("如何查看日志", limit=3)
        self.assertIn("tail", top)
        self.assertIn("journalctl", top)
        self.assertEqual(self.names("请问如何下载文件？")[0], "wget")

    def test_category_filter(self):
        results = search_commands("", "磁盘与存储")
        self.assertTrue(results)
        self.assertTrue(all(item["category"] == "磁盘与存储" for item in results))
        results = search_commands("查看", "系统与进程")
        self.assertTrue(all(item["category"] == "系统与进程" for item in results))

    def test_no_results_and_empty_query(self):
        self.assertEqual(search_commands("bulk-unsupported-xyz"), [])
        self.assertEqual(len(search_commands("")), TOTAL_COMMANDS)

    def test_intent_stripping(self):
        self.assertEqual(strip_intent(normalize("vi是什么？")), "vi")
        self.assertEqual(strip_intent(normalize("如何下载文件")), "下载文件")


if __name__ == "__main__":
    unittest.main()
