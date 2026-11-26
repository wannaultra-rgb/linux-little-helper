# -*- coding: utf-8 -*-
"""图形界面的快速冒烟测试（无显示环境会自动跳过）。"""

import tkinter as tk
import unittest

from app import CommandGuideApp
from guide.catalog import TOTAL_COMMANDS


class GuiSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            probe = tk.Tk()
            probe.destroy()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"无图形环境: {exc}")

    def setUp(self):
        self.root = tk.Tk()
        self.app = CommandGuideApp(self.root)
        self.root.update()

    def tearDown(self):
        try:
            self.app._on_close()
        except tk.TclError:
            pass

    def test_initial_state(self):
        self.assertEqual(self.app._results[0]["name"], "ls")
        self.assertEqual(self.app._current["name"], "ls")
        self.assertEqual(self.app.search.get_query(), "")

    def test_chinese_search_and_detail(self):
        self.app._use_suggestion("下载")
        self.root.update()
        self.assertEqual(self.app._results[0]["name"], "wget")
        self.assertEqual(self.app._current["name"], "wget")
        self.assertIn("下载", self.app._current["title"])
        self.assertEqual(self.app.search.get_query(), "下载")
        self.assertEqual(self.app.clear_button.cget("text"), "×")

    def test_editor_search(self):
        self.app._use_suggestion("vi")
        self.root.update()
        self.assertEqual(self.app._current["name"], "vi")
        self.assertIn("模态", self.app._current["summary"])

    def test_category_filter(self):
        self.app._select_category("磁盘与存储")
        self.root.update()
        self.assertTrue(self.app._results)
        self.assertTrue(all(item["category"] == "磁盘与存储" for item in self.app._results))
        self.assertEqual(self.app.result_title.cget("text"), "磁盘与存储")

    def test_copy_and_empty_state(self):
        self.app._copy("wget -c URL")
        self.root.update()
        self.assertEqual(self.root.clipboard_get(), "wget -c URL")
        self.app._use_suggestion("zzzzzz-no-match")
        self.root.update()
        self.assertEqual(self.app._results, [])
        self.assertEqual(self.app.result_count.cget("text"), "0 条")

    def test_small_window_hides_legend(self):
        self.root.geometry("1060x680")
        self.root.update()
        self.assertFalse(self.app.risk_legend.winfo_manager())

    def test_escape_clears_query(self):
        self.app._use_suggestion("vi")
        self.root.update()
        self.app._escape()
        self.root.update()
        self.assertEqual(self.app.search.get_query(), "")
        self.assertEqual(len(self.app._results), TOTAL_COMMANDS)


if __name__ == "__main__":
    unittest.main()
