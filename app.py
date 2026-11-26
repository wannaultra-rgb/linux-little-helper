#!/usr/bin/env python3
"""Linux 命令指南：用中文需求或命令名，快速找到正确指令。"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk

from guide.catalog import CATEGORY_ORDER, TOTAL_COMMANDS, category_counts
from guide.search import search_commands

# 配色：偏暖的纸白 + 墨绿，强调可读性和长时间使用的舒适度。
BG = "#F3F4EF"
PANEL = "#FFFFFF"
SIDEBAR = "#F3F4EF"
INK = "#20251F"
BODY = "#4B544A"
MUTED = "#7A8378"
FAINT = "#A6AEA1"
BORDER = "#E1E4DA"
HOVER = "#EEF0E9"
STRIPE = "#FAFBF8"
ACCENT = "#2F6B57"
ACCENT_DARK = "#214D3E"
ACCENT_SOFT = "#E7F0EA"
CODE_BG = "#F6F7F2"
CODE_BORDER = "#E4E7DC"
AMBER = "#936015"
AMBER_BG = "#FFF8E7"
AMBER_BORDER = "#EFDFBB"
RED = "#A13A31"
RED_BG = "#FDF1EF"
RED_BORDER = "#F0D3CE"
CHIP_BG = "#EEF0E8"
WHITE = "#FFFFFF"

DANGER_BADGES = {
    "safe": ("常规操作", "#EDF1EA", "#5E6B5B"),
    "caution": ("需谨慎", AMBER_BG, AMBER),
    "danger": ("高风险", RED_BG, RED),
}


class PlaceholderEntry(tk.Entry):
    """带占位提示的输入框，查询时不会把提示文字当成关键词。"""

    def __init__(self, master, placeholder, **kwargs):
        self.var = tk.StringVar(master)
        super().__init__(master, textvariable=self.var, **kwargs)
        self.placeholder = placeholder
        self._showing_placeholder = False
        self._show_placeholder()
        self.bind("<FocusIn>", self._on_focus_in, add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")

    def _show_placeholder(self):
        self._showing_placeholder = True
        self.var.set(self.placeholder)
        self.configure(fg=MUTED)

    def _hide_placeholder(self):
        self._showing_placeholder = False
        self.configure(fg=INK)

    def _on_focus_in(self, _event=None):
        if self._showing_placeholder:
            self._hide_placeholder()
            self.var.set("")

    def _on_focus_out(self, _event=None):
        if not self.var.get().strip():
            self._show_placeholder()

    def is_placeholder(self):
        return self._showing_placeholder

    def get_query(self):
        if self._showing_placeholder:
            return ""
        return self.var.get().strip()

    def set_query(self, value):
        self._hide_placeholder()
        self.var.set(value)
        self.icursor("end")

    def clear(self):
        self._hide_placeholder()
        self.var.set("")


class CommandGuideApp:
    def __init__(self, root):
        self.root = root
        self.category = "全部"
        self._results = []
        self._result_by_iid = {}
        self._current = None
        self._wrap_labels = []
        self._search_job = None
        self._toast_job = None
        self._default_hint = "Ctrl+F 搜索  ·  ↑↓ 浏览  ·  Ctrl+C 复制语法  ·  Esc 清空"

        self.root.title("Linux 命令指南 · 中文双向索引")
        self.root.configure(bg=BG)
        self.root.minsize(1060, 680)
        self._set_initial_geometry()
        self._load_icon()

        self._pick_fonts()
        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._refresh_categories()
        self._do_search(select_first=True)

    # ------------------------------------------------------------------ 字体与外观
    def _pick_fonts(self):
        available = set(tkfont.families(self.root))
        ui_candidates = [
            "Noto Sans CJK SC",
            "Source Han Sans SC",
            "WenQuanYi Micro Hei",
            "Microsoft YaHei UI",
            "Microsoft YaHei",
            "PingFang SC",
            "DejaVu Sans",
        ]
        mono_candidates = [
            "JetBrains Mono",
            "Cascadia Mono",
            "Fira Code",
            "Noto Sans Mono CJK SC",
            "DejaVu Sans Mono",
            "Consolas",
            "Courier New",
        ]
        fallback_ui = tkfont.nametofont("TkDefaultFont").actual("family")
        fallback_mono = tkfont.nametofont("TkFixedFont").actual("family")
        self.ui = next((name for name in ui_candidates if name in available), fallback_ui)
        self.mono = next((name for name in mono_candidates if name in available), fallback_mono)

        self.f_ui = (self.ui, 10)
        self.f_ui_sm = (self.ui, 9)
        self.f_ui_xs = (self.ui, 8)
        self.f_bold = (self.ui, 10, "bold")
        self.f_section = (self.ui, 9, "bold")
        self.f_detail_title = (self.ui, 15, "bold")
        self.f_summary = (self.ui, 10)
        self.f_mono = (self.mono, 10)

    def _configure_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=INK,
            rowheight=34,
            borderwidth=0,
            relief="flat",
            font=self.f_ui,
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT_SOFT)],
            foreground=[("selected", ACCENT_DARK)],
        )
        style.configure(
            "Treeview.Heading",
            background=PANEL,
            foreground=MUTED,
            font=self.f_section,
            relief="flat",
            borderwidth=0,
            padding=(8, 8),
        )
        style.map("Treeview.Heading", background=[("active", PANEL)])
        style.configure(
            "Thin.Vertical.TScrollbar",
            background=BORDER,
            troughcolor=PANEL,
            bordercolor=PANEL,
            darkcolor=BORDER,
            lightcolor=BORDER,
            arrowcolor=MUTED,
            arrowsize=11,
            gripcount=0,
        )
        style.map("Thin.Vertical.TScrollbar", background=[("active", MUTED)])

    def _set_initial_geometry(self):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(1180, max(1000, screen_w - 100))
        height = min(820, max(680, screen_h - 100))
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _load_icon(self):
        icon_path = Path(__file__).resolve().with_name("icon.png")
        if icon_path.exists():
            try:
                self._icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, self._icon)
            except tk.TclError:
                self._icon = None

    # ------------------------------------------------------------------ 构建界面
    def _build_ui(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        header = tk.Frame(self.root, bg=PANEL)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        brand = tk.Frame(header, bg=PANEL)
        brand.grid(row=0, column=0, sticky="w", padx=30, pady=(18, 8))
        logo = tk.Canvas(brand, width=46, height=46, bg=PANEL, highlightthickness=0)
        logo.pack(side="left", padx=(0, 13))
        self._draw_logo(logo)
        titles = tk.Frame(brand, bg=PANEL)
        titles.pack(side="left")
        tk.Label(
            titles,
            text="Linux 命令指南",
            bg=PANEL,
            fg=INK,
            font=(self.ui, 19, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            titles,
            text="中文 ↔ 指令 双向索引 · 说出需求，找到命令",
            bg=PANEL,
            fg=MUTED,
            font=self.f_ui_sm,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        meta = tk.Frame(header, bg=PANEL)
        meta.grid(row=0, column=1, sticky="e", padx=(0, 30), pady=(18, 8))
        tk.Label(meta, text="●", bg=PANEL, fg=ACCENT, font=(self.ui, 8)).pack(side="left", padx=(0, 5))
        tk.Label(
            meta,
            text=f"离线可用  ·  {TOTAL_COMMANDS} 条常用命令",
            bg=PANEL,
            fg=MUTED,
            font=self.f_ui_sm,
        ).pack(side="left")

        search_row = tk.Frame(header, bg=PANEL)
        search_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=30)
        search_row.grid_columnconfigure(0, weight=1)

        self.search_shell = tk.Frame(
            search_row,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.search_shell.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search_shell.grid_columnconfigure(0, weight=1)

        self.search = PlaceholderEntry(
            self.search_shell,
            "搜索中文需求或命令，例如：下载 / vi / 压缩 / 查看端口",
            bg=PANEL,
            fg=INK,
            insertbackground=INK,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(self.ui, 12),
        )
        self.search.grid(row=0, column=0, sticky="ew", padx=(15, 4), pady=7)
        self.search_shell.bind("<Button-1>", lambda _event: self.search.focus_set())

        self.clear_button = tk.Label(
            self.search_shell,
            text="",
            bg=PANEL,
            fg=MUTED,
            font=(self.ui, 14),
            cursor="arrow",
            padx=2,
        )
        self.clear_button.grid(row=0, column=1, padx=(0, 8))
        self.clear_button.bind("<Button-1>", self._clear_search)
        self.clear_button.bind("<Enter>", lambda _e: self.clear_button.configure(fg=INK))
        self.clear_button.bind("<Leave>", lambda _e: self.clear_button.configure(fg=MUTED))

        self.search_button = tk.Button(
            search_row,
            text="搜索",
            command=self._search_now,
            bg=ACCENT,
            fg=WHITE,
            activebackground=ACCENT_DARK,
            activeforeground=WHITE,
            font=self.f_bold,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=22,
            pady=9,
            cursor="hand2",
        )
        self.search_button.grid(row=0, column=1)
        self.search_button.bind("<Enter>", lambda _e: self.search_button.configure(bg=ACCENT_DARK))
        self.search_button.bind("<Leave>", lambda _e: self.search_button.configure(bg=ACCENT))

        self.search.bind("<FocusIn>", self._on_search_focus_in, add="+")
        self.search.bind("<FocusOut>", self._on_search_focus_out, add="+")

        hints = tk.Frame(header, bg=PANEL)
        hints.grid(row=2, column=0, columnspan=2, sticky="w", padx=30, pady=(9, 16))
        tk.Label(hints, text="试试", bg=PANEL, fg=FAINT, font=self.f_ui_sm).pack(side="left", padx=(0, 6))
        for word in ("下载", "vi", "解压", "查看端口", "磁盘空间"):
            self._chip(hints, word, lambda value=word: self._use_suggestion(value)).pack(
                side="left", padx=(0, 6)
            )

        tk.Frame(self.root, bg=BORDER, height=1).grid(row=0, column=0, sticky="sew")

    def _draw_logo(self, canvas):
        color = ACCENT
        points = [
            8, 2, 38, 2, 44, 2, 44, 8, 44, 38, 44, 44, 38, 44,
            8, 44, 2, 44, 2, 38, 2, 8, 2, 2,
        ]
        canvas.create_polygon(points, smooth=True, splinesteps=24, fill=color, outline=color)
        canvas.create_text(23, 22, text=">_", fill=WHITE, font=(self.mono, 14, "bold"))

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=30, pady=(18, 4))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, minsize=206)
        body.grid_columnconfigure(1, weight=1)

        sidebar = tk.Frame(body, bg=SIDEBAR, width=186)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        sidebar.grid_propagate(False)

        tk.Label(
            sidebar,
            text="分类索引",
            bg=SIDEBAR,
            fg=MUTED,
            font=self.f_section,
            anchor="w",
        ).pack(fill="x", pady=(0, 6))
        self.nav_body = tk.Frame(sidebar, bg=SIDEBAR)
        self.nav_body.pack(fill="x")

        legend = tk.Frame(sidebar, bg=SIDEBAR)
        legend.pack(side="bottom", fill="x", pady=(14, 2))
        self.risk_legend = legend
        sidebar.bind("<Configure>", self._toggle_risk_legend, add="+")
        tk.Label(legend, text="风险提示", bg=SIDEBAR, fg=FAINT, font=self.f_ui_xs, anchor="w").pack(fill="x", pady=(0, 3))
        risk_row = tk.Frame(legend, bg=SIDEBAR)
        risk_row.pack(fill="x")
        for color, text in ((ACCENT, "常规"), (AMBER, "谨慎"), (RED, "高风险")):
            item = tk.Frame(risk_row, bg=SIDEBAR)
            item.pack(side="left", padx=(0, 8))
            tk.Label(item, text="●", bg=SIDEBAR, fg=color, font=(self.ui, 6)).pack(side="left", padx=(0, 3))
            tk.Label(item, text=text, bg=SIDEBAR, fg=MUTED, font=self.f_ui_xs).pack(side="left")

        main = tk.Frame(body, bg=BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=0, minsize=382)
        main.grid_columnconfigure(1, weight=1)

        self._build_results(main)
        self._build_detail(main)

    def _toggle_risk_legend(self, event):
        # 小窗口先保证分类列表完整可见，空间足够时再展示图例。
        if event.height < 520:
            if self.risk_legend.winfo_manager():
                self.risk_legend.pack_forget()
        elif not self.risk_legend.winfo_manager():
            self.risk_legend.pack(side="bottom", fill="x", pady=(14, 2))

    def _build_results(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        head = tk.Frame(card, bg=PANEL)
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 8))
        head.grid_columnconfigure(0, weight=1)
        self.result_title = tk.Label(
            head,
            text="全部命令",
            bg=PANEL,
            fg=INK,
            font=(self.ui, 11, "bold"),
            anchor="w",
        )
        self.result_title.grid(row=0, column=0, sticky="w")
        self.result_count = tk.Label(
            head,
            text="",
            bg=ACCENT_SOFT,
            fg=ACCENT_DARK,
            font=self.f_ui_xs,
            padx=7,
            pady=3,
        )
        self.result_count.grid(row=0, column=1, sticky="e")

        self.tree_container = tk.Frame(card, bg=PANEL)
        self.tree_container.grid(row=1, column=0, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.tree_container.grid_rowconfigure(0, weight=1)
        self.tree_container.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self.tree_container,
            columns=("cmd", "title"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("cmd", text="指令", anchor="w")
        self.tree.heading("title", text="中文含义", anchor="w")
        self.tree.column("cmd", width=124, minwidth=100, stretch=False, anchor="w")
        self.tree.column("title", width=244, minwidth=170, stretch=True, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.tag_configure("caution", foreground=AMBER)
        self.tree.tag_configure("danger", foreground=RED)
        self.tree.tag_configure("even", background=STRIPE)

        scrollbar = ttk.Scrollbar(
            self.tree_container,
            orient="vertical",
            command=self.tree.yview,
            style="Thin.Vertical.TScrollbar",
        )
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=(30, 0))
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self.empty_overlay = tk.Frame(self.tree_container, bg=PANEL)
        tk.Label(
            self.empty_overlay,
            text="没有匹配结果",
            bg=PANEL,
            fg=BODY,
            font=(self.ui, 11, "bold"),
        ).pack(pady=(0, 4))
        tk.Label(
            self.empty_overlay,
            text="换一个更短的关键词，或点击左侧「全部」。",
            bg=PANEL,
            fg=MUTED,
            font=self.f_ui_sm,
            wraplength=270,
            justify="center",
        ).pack()

    def _build_detail(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        self.detail_canvas = tk.Canvas(card, bg=PANEL, bd=0, highlightthickness=0, yscrollincrement=18)
        self.detail_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            card,
            orient="vertical",
            command=self.detail_canvas.yview,
            style="Thin.Vertical.TScrollbar",
        )
        scrollbar.grid(row=0, column=1, sticky="ns", pady=6)
        self.detail_canvas.configure(yscrollcommand=scrollbar.set)

        self.detail_inner = tk.Frame(self.detail_canvas, bg=PANEL)
        self._detail_window = self.detail_canvas.create_window(
            (0, 0), window=self.detail_inner, anchor="nw"
        )
        self.detail_inner.bind("<Configure>", self._on_inner_configure)
        self.detail_canvas.bind("<Configure>", self._on_canvas_configure)

    def _build_footer(self):
        tk.Frame(self.root, bg=BORDER, height=1).grid(row=2, column=0, sticky="ew")
        footer = tk.Frame(self.root, bg=BG)
        footer.grid(row=3, column=0, sticky="ew", padx=30, pady=(8, 12))
        footer.grid_columnconfigure(0, weight=1)
        self.status_label = tk.Label(
            footer,
            text="",
            bg=BG,
            fg=MUTED,
            font=self.f_ui_xs,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        self.hint_label = tk.Label(
            footer,
            text=self._default_hint,
            bg=BG,
            fg=FAINT,
            font=self.f_ui_xs,
            anchor="e",
        )
        self.hint_label.grid(row=0, column=1, sticky="e")

    # ------------------------------------------------------------------ 组件辅助
    def _chip(self, parent, text, on_click=None, mono=False, font=None):
        label = tk.Label(
            parent,
            text=text,
            bg=CHIP_BG,
            fg=BODY,
            font=font or ((self.mono, 9) if mono else self.f_ui_sm),
            padx=9,
            pady=4,
            cursor="hand2" if on_click else "arrow",
        )
        if on_click is not None:
            label.bind("<Button-1>", lambda _event: on_click())
            label.bind("<Enter>", lambda _e: label.configure(bg=ACCENT_SOFT, fg=ACCENT_DARK))
            label.bind("<Leave>", lambda _e: label.configure(bg=CHIP_BG, fg=BODY))
        return label

    def _section(self, parent, text, top=18):
        label = tk.Label(
            parent,
            text=text,
            bg=PANEL,
            fg=MUTED,
            font=self.f_section,
            anchor="w",
        )
        label.pack(fill="x", pady=(top, 7))
        return label

    def _badge(self, parent, text, bg, fg):
        return tk.Label(parent, text=text, bg=bg, fg=fg, font=self.f_ui_xs, padx=7, pady=3)

    def _register_wrap(self, label, reserved=0):
        self._wrap_labels.append((label, reserved))
        width = self._current_wrap_width()
        label.configure(wraplength=max(220, width - reserved))

    def _current_wrap_width(self):
        try:
            width = self.detail_canvas.winfo_width()
        except tk.TclError:
            width = 0
        if width <= 1:
            width = 560
        return max(300, width - 52)

    def _apply_wrap(self):
        width = self._current_wrap_width()
        for label, reserved in self._wrap_labels:
            try:
                label.configure(wraplength=max(220, width - reserved))
            except tk.TclError:
                pass

    def _on_canvas_configure(self, event):
        self.detail_canvas.itemconfigure(self._detail_window, width=event.width)
        self._apply_wrap()

    def _on_inner_configure(self, _event=None):
        self.detail_canvas.configure(scrollregion=self.detail_canvas.bbox("all"))

    def _code_box(self, parent, code, top=0):
        outer = tk.Frame(
            parent,
            bg=CODE_BG,
            highlightthickness=1,
            highlightbackground=CODE_BORDER,
        )
        outer.pack(fill="x", pady=(top, 0))
        outer.grid_columnconfigure(0, weight=1)
        label = tk.Label(
            outer,
            text=code,
            bg=CODE_BG,
            fg=INK,
            font=self.f_mono,
            anchor="w",
            justify="left",
            padx=12,
            pady=9,
        )
        label.grid(row=0, column=0, sticky="ew")
        self._register_wrap(label, 64)

        copy = tk.Label(
            outer,
            text="复制",
            bg=CODE_BG,
            fg=ACCENT,
            font=self.f_ui_xs,
            padx=7,
            pady=4,
            cursor="hand2",
        )
        copy.grid(row=0, column=1, sticky="e", padx=(2, 7))
        copy.bind("<Button-1>", lambda _event: self._copy(code))
        copy.bind("<Enter>", lambda _e: copy.configure(bg=ACCENT_SOFT, fg=ACCENT_DARK))
        copy.bind("<Leave>", lambda _e: copy.configure(bg=CODE_BG, fg=ACCENT))
        return outer

    # ------------------------------------------------------------------ 分类导航
    def _refresh_categories(self):
        for child in self.nav_body.winfo_children():
            child.destroy()
        counts = category_counts()
        entries = [("全部", TOTAL_COMMANDS)] + [(name, counts[name]) for name in CATEGORY_ORDER]
        for name, count in entries:
            self._nav_row(self.nav_body, name, count)

    def _nav_row(self, parent, name, count):
        active = name == self.category
        row_bg = ACCENT_SOFT if active else SIDEBAR
        row = tk.Frame(parent, bg=row_bg, cursor="hand2")
        row.pack(fill="x", pady=(0, 1))

        bar = tk.Frame(row, bg=ACCENT if active else row_bg, width=3)
        bar.pack(side="left", fill="y")

        name_label = tk.Label(
            row,
            text=name,
            bg=row_bg,
            fg=ACCENT_DARK if active else BODY,
            font=(self.ui, 9, "bold") if active else self.f_ui_sm,
            anchor="w",
            padx=8,
            pady=5,
            cursor="hand2",
        )
        name_label.pack(side="left", fill="x", expand=True)
        count_label = tk.Label(
            row,
            text=str(count),
            bg=row_bg,
            fg=ACCENT if active else FAINT,
            font=self.f_ui_xs,
            padx=8,
            cursor="hand2",
        )
        count_label.pack(side="right")

        def select(_event=None, category=name):
            self._select_category(category)

        for widget in (row, bar, name_label, count_label):
            widget.bind("<Button-1>", select)

        if not active:
            def enter(_event=None):
                row.configure(bg=HOVER)
                bar.configure(bg=HOVER)
                name_label.configure(bg=HOVER)
                count_label.configure(bg=HOVER)

            def leave(_event=None):
                row.configure(bg=SIDEBAR)
                bar.configure(bg=SIDEBAR)
                name_label.configure(bg=SIDEBAR)
                count_label.configure(bg=SIDEBAR)

            for widget in (row, bar, name_label, count_label):
                widget.bind("<Enter>", enter)
                widget.bind("<Leave>", leave)

    def _select_category(self, category):
        if category == self.category:
            return
        self.category = category
        self._refresh_categories()
        self._do_search(select_first=True)

    def _cancel_jobs(self):
        for job in (self._search_job, self._toast_job):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        self._search_job = None
        self._toast_job = None

    def _on_close(self):
        self._cancel_jobs()
        self.root.destroy()

    # ------------------------------------------------------------------ 搜索与结果
    def _bind_shortcuts(self):
        self.search.var.trace_add("write", self._on_query_changed)
        self.search.bind("<Return>", self._focus_results)
        self.search.bind("<Down>", self._focus_results)
        self.root.bind("<Control-f>", self._focus_search)
        self.root.bind("<Control-F>", self._focus_search)
        self.root.bind("<Control-c>", self._copy_shortcut)
        self.root.bind("<Escape>", self._escape)
        self.tree.bind("<Control-c>", self._copy_shortcut)

    def _on_query_changed(self, *_args):
        if self.search.is_placeholder():
            return
        self._update_clear_button()
        if self._search_job is not None:
            try:
                self.root.after_cancel(self._search_job)
            except tk.TclError:
                pass
        self._search_job = self.root.after(130, self._search_now)

    def _update_clear_button(self):
        has_text = bool(self.search.get_query())
        self.clear_button.configure(text="×" if has_text else "", cursor="hand2" if has_text else "arrow")
        if not has_text:
            self.clear_button.configure(fg=MUTED)

    def _search_now(self):
        if self._search_job is not None:
            try:
                self.root.after_cancel(self._search_job)
            except tk.TclError:
                pass
            self._search_job = None
        self._do_search(select_first=True)

    def _do_search(self, select_first=True):
        query = self.search.get_query()
        items = search_commands(query, self.category)
        self._results = items
        self._result_by_iid.clear()
        self.tree.delete(*self.tree.get_children())

        for index, item in enumerate(items):
            iid = str(index)
            tags = []
            if item["danger"] == "caution":
                tags.append("caution")
            elif item["danger"] == "danger":
                tags.append("danger")
            if index % 2 == 1:
                tags.append("even")
            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(item["name"], item["title"]),
                tags=tuple(tags),
            )
            self._result_by_iid[iid] = item

        if query:
            heading = "搜索结果"
        elif self.category != "全部":
            heading = self.category
        else:
            heading = "全部命令"
        self.result_title.configure(text=heading)
        self.result_count.configure(text=f"{len(items)} 条")
        self.status_label.configure(
            text=f"共 {TOTAL_COMMANDS} 条命令  ·  当前显示 {len(items)} 条"
        )
        self._update_clear_button()

        if items:
            self.empty_overlay.place_forget()
            first = "0"
            self.tree.selection_set(first)
            self.tree.focus(first)
            self.tree.see(first)
            if select_first:
                self._show_detail(items[0])
        else:
            self.empty_overlay.place(relx=0.5, rely=0.28, anchor="center")
            self._show_empty_detail(query)

    def _on_tree_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        item = self._result_by_iid.get(selection[0])
        if item is not None:
            self._show_detail(item)

    def _focus_results(self, _event=None):
        if not self._results:
            return "break"
        if not self.tree.selection():
            self.tree.selection_set("0")
        self.tree.focus("0")
        self.tree.see("0")
        self.tree.focus_set()
        return "break"

    def _focus_search(self, _event=None):
        self.search.focus_set()
        self.search.selection_range(0, "end")
        return "break"

    def _escape(self, _event=None):
        if self.search.get_query():
            self.search.clear()
            self._update_clear_button()
            self._do_search(select_first=True)
        self.search.focus_set()
        return "break"

    def _clear_search(self, _event=None):
        self.search.clear()
        self._update_clear_button()
        self.search.focus_set()
        self._search_now()

    def _use_suggestion(self, word):
        self.search.set_query(word)
        self._update_clear_button()
        self._search_now()
        self.search.focus_set()

    def _on_search_focus_in(self, _event=None):
        self.search_shell.configure(highlightbackground=ACCENT, highlightcolor=ACCENT)

    def _on_search_focus_out(self, _event=None):
        self.search_shell.configure(highlightbackground=BORDER, highlightcolor=BORDER)

    # ------------------------------------------------------------------ 详情渲染
    def _clear_detail(self):
        for child in self.detail_inner.winfo_children():
            child.destroy()
        self._wrap_labels = []
        self._current = None

    def _show_empty_detail(self, query):
        self._clear_detail()
        content = tk.Frame(self.detail_inner, bg=PANEL)
        content.pack(fill="both", expand=True, padx=28, pady=(80, 30))
        tk.Label(content, text="没有找到相关命令", bg=PANEL, fg=INK, font=(self.ui, 16, "bold")).pack(anchor="center")
        message = "试试更短、更日常的中文说法，或直接搜索命令名（例如 vi、tar）。"
        if query:
            message = f"没有找到与「{query}」匹配的命令。试试更短的关键词，或搜索命令名。"
        label = tk.Label(
            content,
            text=message,
            bg=PANEL,
            fg=MUTED,
            font=self.f_summary,
            justify="center",
        )
        label.pack(anchor="center", pady=(8, 18))
        self._wrap_labels.append((label, 80))
        chips = tk.Frame(content, bg=PANEL)
        chips.pack(anchor="center")
        for word in ("下载", "解压", "查看端口"):
            self._chip(chips, word, lambda value=word: self._use_suggestion(value)).pack(side="left", padx=4)
        self.detail_canvas.yview_moveto(0)
        self._bind_detail_wheel()

    def _show_detail(self, item):
        self._clear_detail()
        self._current = item
        content = tk.Frame(self.detail_inner, bg=PANEL)
        content.pack(fill="both", expand=True, padx=26, pady=24)

        meta = tk.Frame(content, bg=PANEL)
        meta.pack(fill="x")
        category = tk.Label(
            meta,
            text=item["category"],
            bg=ACCENT_SOFT,
            fg=ACCENT_DARK,
            font=self.f_ui_xs,
            padx=7,
            pady=3,
        )
        category.pack(side="left")
        danger_text, danger_bg, danger_fg = DANGER_BADGES[item["danger"]]
        danger = self._badge(meta, danger_text, danger_bg, danger_fg)
        danger.pack(side="left", padx=(6, 0))

        name_label = tk.Label(
            content,
            text=item["name"],
            bg=PANEL,
            fg=INK,
            font=(self.mono, 22, "bold"),
            anchor="w",
        )
        name_label.pack(fill="x", pady=(13, 0))
        if item["aliases"]:
            tk.Label(
                content,
                text="别名  " + "  /  ".join(item["aliases"]),
                bg=PANEL,
                fg=MUTED,
                font=(self.mono, 9),
                anchor="w",
            ).pack(fill="x", pady=(2, 0))
        tk.Label(
            content,
            text=item["title"],
            bg=PANEL,
            fg=BODY,
            font=(self.ui, 12, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        tk.Frame(content, bg=BORDER, height=1).pack(fill="x", pady=(18, 0))

        self._section(content, "它是什么", top=16)
        summary = tk.Label(
            content,
            text=item["summary"],
            bg=PANEL,
            fg=BODY,
            font=self.f_summary,
            anchor="w",
            justify="left",
        )
        summary.pack(fill="x")
        self._register_wrap(summary)

        self._section(content, "语法")
        self._code_box(content, item["syntax"])

        if item["caution"]:
            if item["danger"] == "danger":
                box_bg, box_border, title_fg, title = RED_BG, RED_BORDER, RED, "高风险操作"
            elif item["danger"] == "caution":
                box_bg, box_border, title_fg, title = AMBER_BG, AMBER_BORDER, AMBER, "注意"
            else:
                box_bg, box_border, title_fg, title = CODE_BG, CODE_BORDER, MUTED, "提示"
            warning = tk.Frame(
                content,
                bg=box_bg,
                highlightthickness=1,
                highlightbackground=box_border,
            )
            warning.pack(fill="x", pady=(14, 0))
            tk.Label(
                warning,
                text=title,
                bg=box_bg,
                fg=title_fg,
                font=self.f_section,
                anchor="w",
                padx=12,
                pady=0,
            ).pack(fill="x", pady=(9, 2))
            warning_text = tk.Label(
                warning,
                text=item["caution"],
                bg=box_bg,
                fg=BODY,
                font=self.f_ui_sm,
                anchor="w",
                justify="left",
                padx=12,
                pady=0,
            )
            warning_text.pack(fill="x", pady=(0, 9))
            self._register_wrap(warning_text, 18)

        self._section(content, "常用示例")
        for index, (description, command) in enumerate(item["examples"]):
            desc = tk.Label(
                content,
                text=description,
                bg=PANEL,
                fg=MUTED,
                font=self.f_ui_sm,
                anchor="w",
                justify="left",
            )
            desc.pack(fill="x", pady=(0 if index == 0 else 7, 3))
            self._register_wrap(desc)
            self._code_box(content, command)

        if item["options"]:
            self._section(content, item["options_title"])
            for flag, description in item["options"]:
                flag_label = tk.Label(
                    content,
                    text=flag,
                    bg=PANEL,
                    fg=ACCENT_DARK,
                    font=(self.mono, 9),
                    anchor="w",
                    justify="left",
                )
                flag_label.pack(fill="x", pady=(2, 0))
                self._register_wrap(flag_label)
                desc = tk.Label(
                    content,
                    text=description,
                    bg=PANEL,
                    fg=BODY,
                    font=self.f_ui_sm,
                    anchor="w",
                    justify="left",
                )
                desc.pack(fill="x", pady=(1, 2))
                self._register_wrap(desc)

        if item["related"]:
            self._section(content, "相关命令")
            related_row = tk.Frame(content, bg=PANEL)
            related_row.pack(fill="x")
            for related in item["related"]:
                chip = self._chip(
                    related_row,
                    related,
                    lambda name=related: self._use_suggestion(name),
                    mono=True,
                )
                chip.pack(side="left", padx=(0, 6))

        hint = tk.Label(
            content,
            text=f"在终端运行 man {item['name']} 查看完整手册。",
            bg=PANEL,
            fg=FAINT,
            font=self.f_ui_xs,
            anchor="w",
        )
        hint.pack(fill="x", pady=(22, 0))
        self._register_wrap(hint)

        self.detail_canvas.yview_moveto(0)
        self.detail_canvas.after_idle(self._on_inner_configure)
        self.detail_canvas.after_idle(self._apply_wrap)
        self._bind_detail_wheel()

    def _bind_detail_wheel(self):
        def bind(widget):
            widget.bind("<MouseWheel>", self._on_detail_wheel, add="+")
            widget.bind("<Button-4>", self._on_detail_wheel, add="+")
            widget.bind("<Button-5>", self._on_detail_wheel, add="+")
            for child in widget.winfo_children():
                bind(child)

        bind(self.detail_canvas)
        bind(self.detail_inner)

    def _on_detail_wheel(self, event):
        if event.num == 4:
            delta = -3
        elif event.num == 5:
            delta = 3
        elif event.delta:
            delta = -int(event.delta / 120)
            if delta == 0:
                delta = -1 if event.delta > 0 else 1
        else:
            delta = 0
        if delta:
            self.detail_canvas.yview_scroll(delta, "units")
        return "break"

    # ------------------------------------------------------------------ 复制与提示
    def _copy(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
        except tk.TclError:
            self._show_toast("复制失败，请手动选择文本")
            return
        short = text if len(text) <= 28 else "命令"
        self._show_toast(f"已复制{('：' + short) if short != '命令' else '到剪贴板'}")

    def _copy_shortcut(self, _event=None):
        focus = self.root.focus_get()
        if isinstance(focus, (tk.Entry, tk.Text)):
            return None
        if self._current is None:
            return "break"
        self._copy(self._current["syntax"])
        return "break"

    def _show_toast(self, message):
        if self._toast_job is not None:
            try:
                self.root.after_cancel(self._toast_job)
            except tk.TclError:
                pass
        self.hint_label.configure(text=message, fg=ACCENT_DARK)
        self._toast_job = self.root.after(1800, self._reset_hint)

    def _reset_hint(self):
        self._toast_job = None
        self.hint_label.configure(text=self._default_hint, fg=FAINT)


def main():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        sys.stderr.write(
            "无法打开图形界面：%s\n"
            "请确认已安装 python3-tk，并在有桌面环境的会话中运行。\n" % exc
        )
        return 1
    CommandGuideApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
