import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Dict, List, Optional

import customtkinter as ctk

from core.config.config_manager import ConfigManager
from core.services.ai_service import DEFAULT_MODELS, GeminiClient
from core.services.commit_service import CommitService
from core.services.git_service import GitService

# Appearance & Theme Configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """Lightweight, responsive AI Git Commit Generator GUI with Pull, Push, and Selective Staging."""

    FONT_FAMILY = "Segoe UI"
    MONO_FONT = "Consolas"
    MAX_FILE_ROWS = 60
    MAX_DIFF_PREVIEW_CHARS = 40000

    COLOR_PRIMARY = ("#2563EB", "#3B82F6")
    COLOR_PRIMARY_HOVER = ("#1D4ED8", "#60A5FA")
    COLOR_SUCCESS = ("#059669", "#10B981")
    COLOR_SUCCESS_HOVER = ("#047857", "#34D399")
    COLOR_PURPLE = ("#7C3AED", "#8B5CF6")
    COLOR_PURPLE_HOVER = ("#6D28D9", "#A78BFA")
    COLOR_TEAL = ("#0D9488", "#14B8A6")
    COLOR_TEAL_HOVER = ("#0F766E", "#2DD4BF")
    COLOR_DANGER = ("#DC2626", "#EF4444")
    COLOR_CARD_BG = ("#F3F4F6", "#1E2026")
    COLOR_INNER_BG = ("#E5E7EB", "#181A1F")
    COLOR_BORDER = ("#D1D5DB", "#2D3139")
    COLOR_TEXT_MUTED = ("#6B7280", "#9CA3AF")

    def __init__(self):
        super().__init__()

        self.title("AI Git Commit Generator")
        self.geometry("1040x680")
        self.minsize(920, 580)

        self.project_path: Optional[str] = None
        self.current_view: str = "Generator"
        self.generated_options: List[str] = []
        self.selected_option_idx: int = 0
        self.show_api_key: bool = False
        self.show_github_token: bool = False
        self.selected_diff_file: Optional[str] = None

        # Async request sequence guards & UI caches
        self._status_req_id: int = 0
        self._diff_req_id: int = 0
        self._diff_text_req_id: int = 0
        self._repos_view_req_id: int = 0
        self._latest_status_summary: Optional[Dict] = None
        self._file_row_widgets: Dict[str, ctk.CTkFrame] = {}
        self._repo_row_widgets: Dict[str, ctk.CTkButton] = {}
        self._repo_status_labels: Dict[str, ctk.CTkLabel] = {}
        self._repo_display_map: Dict[str, str] = {}
        self._is_closing: bool = False

        self.model_options = list(DEFAULT_MODELS)

        # Load initial config
        self._load_config_cache()
        self.saved_repositories: List[str] = list(self.config_data.get("repositories", []))

        # Build UI layout
        self._build_ui()

        # Keyboard shortcuts for fast workflow
        self.bind("<Control-g>", lambda e: self.generate_commit_message_async())
        self.bind("<Control-G>", lambda e: self.generate_commit_message_async())
        self.bind("<Control-Return>", lambda e: self.create_commit())
        self.bind("<F5>", lambda e: self._refresh_active_view())

        # Auto-detect git repo asynchronously after UI renders
        self.after(50, self._auto_detect_current_directory)

    def _load_config_cache(self):
        try:
            self.config_data = ConfigManager._load_config()
        except Exception:
            self.config_data = {}

    def _post_ui(self, callback):
        """Schedule a UI callback on the main thread safely, ignoring shutdown races."""
        if getattr(self, "_is_closing", False):
            return

        def _safe_run():
            if not getattr(self, "_is_closing", False):
                callback()

        try:
            self.after(0, _safe_run)
        except (RuntimeError, tk.TclError):
            pass

    def destroy(self):
        self._is_closing = True
        super().destroy()

    def _auto_detect_current_directory(self):
        saved_path = (self.config_data.get("last_repo_path") or "").strip()
        saved_repos = list(self.saved_repositories)

        def _worker():
            cwd = GitService.get_current_directory()
            repo_root = GitService.get_repository_root(cwd)
            if not repo_root and saved_path and Path(saved_path).exists():
                repo_root = GitService.get_repository_root(saved_path)
            if not repo_root:
                for candidate in saved_repos:
                    if Path(candidate).exists():
                        repo_root = GitService.get_repository_root(candidate)
                        if repo_root:
                            break
            if repo_root:
                self._post_ui(lambda r=repo_root: self._set_project(r, save_last=False))

        threading.Thread(target=_worker, daemon=True).start()

    def _refresh_active_view(self):
        self.refresh_git_status()
        if self.current_view == "Diff" and self.project_path:
            self._refresh_diff_view()
        elif self.current_view == "Repositories":
            self._refresh_repositories_view()

    def _update_model_dropdown_options(self, models: List[str]):
        if models:
            self.model_options = models
            current = self.model_dropdown.get()
            self.model_dropdown.configure(values=self.model_options)
            if current in self.model_options:
                self.model_dropdown.set(current)
            elif self.model_options:
                self.model_dropdown.set(self.model_options[0])
                self.model_status_badge.configure(text=f"🤖 {self.model_options[0]}")

    # -------------------------------------------------------------------------
    # UI Skeleton & Navigation
    # -------------------------------------------------------------------------
    def _build_ui(self):
        # Master grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Left Sidebar
        self.sidebar = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0,
            fg_color=("gray92", "#131519"),
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(7, weight=1)  # repo switcher list expands

        # App Brand Header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=14, pady=(16, 12), sticky="w")

        title_icon = ctk.CTkLabel(
            brand_frame,
            text="⚡",
            font=ctk.CTkFont(size=20),
        )
        title_icon.pack(side="left", padx=(0, 6))

        title_text_frame = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_text_frame.pack(side="left")

        brand_title = ctk.CTkLabel(
            title_text_frame,
            text="GitAI Commit",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=15, weight="bold"),
        )
        brand_title.pack(anchor="w")

        brand_sub = ctk.CTkLabel(
            title_text_frame,
            text="v1.4 • Multi-Repo",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            text_color=self.COLOR_TEXT_MUTED,
        )
        brand_sub.pack(anchor="w")

        # Nav separator
        ctk.CTkFrame(
            self.sidebar,
            height=1,
            fg_color=self.COLOR_BORDER,
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        # Nav Buttons
        self.nav_buttons = {}
        nav_items = [
            ("Generator", "⚡  Generator"),
            ("Diff", "📁  Changes & Diff"),
            ("Repositories", "🗂️  Repositories"),
            ("Settings", "⚙️  Settings"),
        ]

        for idx, (view_key, label_text) in enumerate(nav_items, start=2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label_text,
                anchor="w",
                height=34,
                corner_radius=8,
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="normal"),
                fg_color="transparent",
                text_color=("gray20", "gray85"),
                hover_color=("gray85", "#1E222A"),
                command=lambda vk=view_key: self.show_view(vk),
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=10, pady=3)
            self.nav_buttons[view_key] = btn

        # Sidebar Quick Repositories Switcher
        repos_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        repos_header.grid(row=6, column=0, sticky="ew", padx=12, pady=(12, 4))

        ctk.CTkLabel(
            repos_header,
            text="REPOSITORIES",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
            text_color=self.COLOR_TEXT_MUTED,
        ).pack(side="left")

        ctk.CTkButton(
            repos_header,
            text="+ Add",
            width=46,
            height=22,
            corner_radius=5,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
            fg_color=("gray80", "#232730"),
            hover_color=("gray70", "#2E3440"),
            text_color=("gray15", "gray90"),
            command=self.select_project,
        ).pack(side="right")

        self.sidebar_repo_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            corner_radius=6,
            height=130,
        )
        self.sidebar_repo_scroll.grid(row=7, column=0, sticky="nsew", padx=8, pady=(0, 6))

        # Bottom section in sidebar
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.grid(row=8, column=0, sticky="sew", padx=12, pady=12)

        # Active Model Pill Badge in Left Navigation Panel
        model_pill_frame = ctk.CTkFrame(
            bottom_frame,
            fg_color=self.COLOR_INNER_BG,
            corner_radius=6,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        model_pill_frame.pack(fill="x", pady=(0, 10))

        self.model_status_badge = ctk.CTkLabel(
            model_pill_frame,
            text=f"🤖 {self.config_data.get('model', 'gemini-2.0-flash-lite')}",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
            text_color=("gray20", "#93C5FD"),
            anchor="w",
            wraplength=185,
        )
        self.model_status_badge.pack(padx=8, pady=5, fill="x")

        # Appearance Theme Switcher
        theme_label = ctk.CTkLabel(
            bottom_frame,
            text="Appearance",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        )
        theme_label.pack(fill="x", pady=(0, 4))

        self.theme_segment = ctk.CTkSegmentedButton(
            bottom_frame,
            values=["Dark", "Light", "System"],
            height=26,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            command=self._change_appearance_mode,
        )
        self.theme_segment.set("Dark")
        self.theme_segment.pack(fill="x")

        # 2. Main Content Container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=14, pady=12)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Build View Frames
        self.views = {
            "Generator": self._build_generator_view(),
            "Diff": self._build_diff_view(),
            "Repositories": self._build_repositories_view(),
            "Settings": self._build_settings_view(),
        }

        self._render_sidebar_repos()
        self._sync_repo_switcher_menu()

        # Show default view
        self.show_view("Generator")

    def show_view(self, view_name: str):
        self.current_view = view_name
        for name, btn in self.nav_buttons.items():
            if name == view_name:
                btn.configure(
                    fg_color=self.COLOR_PRIMARY,
                    text_color="#FFFFFF",
                    font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray20", "gray85"),
                    font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="normal"),
                )

        for name, frame in self.views.items():
            if name == view_name:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_forget()

        if view_name == "Diff" and self.project_path:
            self._refresh_diff_view()
        elif view_name == "Repositories":
            self._refresh_repositories_view()

    def _change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode.lower())

    # -------------------------------------------------------------------------
    # 1. Generator View (Main Tab)
    # -------------------------------------------------------------------------
    def _build_generator_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        view.grid_rowconfigure(2, weight=1)  # Commit Editor gets expandable area
        view.grid_columnconfigure(0, weight=1)

        # --- Top Card: Repository & Git Info ---
        repo_card = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        repo_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        repo_card.grid_columnconfigure(1, weight=1)

        # Row 1: Path + Action Buttons
        folder_lbl = ctk.CTkLabel(
            repo_card,
            text="📁 Repo",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
        )
        folder_lbl.grid(row=0, column=0, padx=(12, 6), pady=(10, 4), sticky="w")

        self.project_entry = ctk.CTkEntry(
            repo_card,
            placeholder_text="Select a Git repository folder (press Enter to load)...",
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
        )
        self.project_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=(10, 4))
        self.project_entry.bind("<Return>", lambda e: self._on_project_entry_submit())

        actions_frame = ctk.CTkFrame(repo_card, fg_color="transparent")
        actions_frame.grid(row=0, column=2, padx=(0, 10), pady=(10, 4), sticky="e")

        self.browse_btn = ctk.CTkButton(
            actions_frame,
            text="+ Add Repo",
            width=82,
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self.select_project,
        )
        self.browse_btn.pack(side="left", padx=2)

        self.stage_all_btn = ctk.CTkButton(
            actions_frame,
            text="+ Stage All",
            width=72,
            height=30,
            corner_radius=6,
            fg_color=("gray75", "#2C313C"),
            hover_color=("gray65", "#3A4150"),
            text_color=("gray10", "gray95"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self.stage_all_changes_ui,
        )
        self.stage_all_btn.pack(side="left", padx=2)

        self.top_pull_btn = ctk.CTkButton(
            actions_frame,
            text="📥 Pull",
            width=60,
            height=30,
            corner_radius=6,
            fg_color=self.COLOR_TEAL,
            hover_color=self.COLOR_TEAL_HOVER,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
            command=self.pull_commits_async,
        )
        self.top_pull_btn.pack(side="left", padx=2)

        self.top_push_btn = ctk.CTkButton(
            actions_frame,
            text="🚀 Push",
            width=62,
            height=30,
            corner_radius=6,
            fg_color=self.COLOR_PURPLE,
            hover_color=self.COLOR_PURPLE_HOVER,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
            command=self.push_commits_async,
        )
        self.top_push_btn.pack(side="left", padx=2)

        self.refresh_repo_btn = ctk.CTkButton(
            actions_frame,
            text="🔄",
            width=32,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            hover_color=("gray85", "#2C313C"),
            text_color=("gray20", "gray85"),
            command=self.refresh_git_status,
        )
        self.refresh_repo_btn.pack(side="left", padx=2)

        # Row 2: Status Badges Strip
        self.badge_strip = ctk.CTkFrame(repo_card, fg_color="transparent")
        self.badge_strip.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 8))

        self.branch_badge = self._create_badge(
            self.badge_strip,
            "🌿 Branch: None",
            "#3B82F6",
            on_click=self._open_branch_switcher_menu,
        )
        self.branch_badge.pack(side="left", padx=(0, 6))

        self.staged_badge = self._create_badge(
            self.badge_strip,
            "● 0 staged",
            "#6B7280",
            on_click=lambda: self.show_view("Diff"),
        )
        self.staged_badge.pack(side="left", padx=(0, 6))

        self.unstaged_badge = self._create_badge(
            self.badge_strip,
            "● 0 modified",
            "#6B7280",
            on_click=lambda: self.show_view("Diff"),
        )
        self.unstaged_badge.pack(side="left", padx=(0, 6))

        self.unpushed_badge = self._create_badge(self.badge_strip, "↑ 0 unpushed", "#6B7280")
        self.unpushed_badge.pack(side="left", padx=(0, 6))

        self.repo_switcher_menu = ctk.CTkOptionMenu(
            self.badge_strip,
            values=["No repositories"],
            width=170,
            height=24,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
            fg_color=self.COLOR_INNER_BG,
            button_color=("gray75", "#2C313C"),
            button_hover_color=("gray65", "#3A4150"),
            text_color=("gray15", "gray90"),
            command=self._on_repo_switcher_select,
        )
        self.repo_switcher_menu.pack(side="right")

        # --- Middle Card: Commit Date & Options ---
        date_card = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        date_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        date_header_frame = ctk.CTkFrame(date_card, fg_color="transparent")
        date_header_frame.pack(fill="x", padx=12, pady=6)

        date_icon = ctk.CTkLabel(
            date_header_frame,
            text="📅 Timestamp:",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
        )
        date_icon.pack(side="left", padx=(0, 8))

        self.date_mode_btn = ctk.CTkSegmentedButton(
            date_header_frame,
            values=["Current Time", "Custom Timestamp"],
            height=26,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            command=self._on_date_mode_change,
        )
        self.date_mode_btn.set("Current Time")
        self.date_mode_btn.pack(side="left", padx=4)

        # Custom Date Inputs Container
        self.custom_date_frame = ctk.CTkFrame(date_header_frame, fg_color="transparent")

        self.date_entry = ctk.CTkEntry(
            self.custom_date_frame,
            placeholder_text="YYYY-MM-DD",
            width=100,
            height=26,
            corner_radius=5,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
        )
        self.date_entry.pack(side="left", padx=3)

        self.time_entry = ctk.CTkEntry(
            self.custom_date_frame,
            placeholder_text="HH:MM",
            width=70,
            height=26,
            corner_radius=5,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
        )
        self.time_entry.pack(side="left", padx=3)

        self.today_btn = ctk.CTkButton(
            self.custom_date_frame,
            text="Today",
            width=46,
            height=26,
            corner_radius=5,
            fg_color=("gray75", "#2C313C"),
            hover_color=("gray65", "#3A4150"),
            text_color=("gray10", "gray95"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            command=self._set_date_today,
        )
        self.today_btn.pack(side="left", padx=2)

        # --- Main Card: Generated Commit Message Editor ---
        msg_card = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        msg_card.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        msg_card.grid_rowconfigure(1, weight=1)
        msg_card.grid_columnconfigure(0, weight=1)

        # Editor Toolbar Header
        editor_toolbar = ctk.CTkFrame(msg_card, fg_color="transparent")
        editor_toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))

        commit_title_lbl = ctk.CTkLabel(
            editor_toolbar,
            text="💬 Commit Message",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
        )
        commit_title_lbl.pack(side="left")

        # Option switch pills container (shown if multiple options exist)
        self.options_container = ctk.CTkFrame(editor_toolbar, fg_color="transparent")
        self.options_container.pack(side="left", padx=12)

        # Action Buttons on Right
        self.copy_btn = ctk.CTkButton(
            editor_toolbar,
            text="📋 Copy",
            width=65,
            height=26,
            corner_radius=5,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            command=self.copy_commit_message,
        )
        self.copy_btn.pack(side="right", padx=2)

        self.clear_btn = ctk.CTkButton(
            editor_toolbar,
            text="🧹 Clear",
            width=60,
            height=26,
            corner_radius=5,
            fg_color="transparent",
            hover_color=("gray85", "#2C313C"),
            text_color=("gray20", "gray85"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            command=self.clear_commit_message,
        )
        self.clear_btn.pack(side="right", padx=2)

        # Commit Message Textbox
        self.commit_text = ctk.CTkTextbox(
            msg_card,
            corner_radius=6,
            border_width=1,
            border_color=self.COLOR_BORDER,
            font=ctk.CTkFont(family=self.MONO_FONT, size=12),
            wrap="word",
            undo=True,
        )
        self.commit_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 4))
        self.commit_text.bind("<KeyRelease>", self._on_text_change)

        # Editor Footer: Character Counter & Rules info
        editor_footer = ctk.CTkFrame(msg_card, fg_color="transparent")
        editor_footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))

        self.char_count_badge = ctk.CTkLabel(
            editor_footer,
            text="Line 1: 0 / 72 chars",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            text_color=self.COLOR_TEXT_MUTED,
        )
        self.char_count_badge.pack(side="left")

        self.total_lines_badge = ctk.CTkLabel(
            editor_footer,
            text="0 lines",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            text_color=self.COLOR_TEXT_MUTED,
        )
        self.total_lines_badge.pack(side="left", padx=10)

        shortcut_hint = ctk.CTkLabel(
            editor_footer,
            text="Ctrl+G Generate • Ctrl+Enter Commit • F5 Refresh",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            text_color=self.COLOR_TEXT_MUTED,
        )
        shortcut_hint.pack(side="right")

        # --- Bottom Card: Action Controls & Status Bar ---
        action_card = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        action_card.grid(row=3, column=0, sticky="ew")

        action_inner = ctk.CTkFrame(action_card, fg_color="transparent")
        action_inner.pack(fill="x", padx=12, pady=(8, 4))

        self.generate_button = ctk.CTkButton(
            action_inner,
            text="✨ Generate AI Commit",
            height=34,
            width=155,
            corner_radius=8,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
            fg_color=self.COLOR_PRIMARY,
            hover_color=self.COLOR_PRIMARY_HOVER,
            command=self.generate_commit_message_async,
        )
        self.generate_button.pack(side="left", padx=(0, 6))

        self.create_button = ctk.CTkButton(
            action_inner,
            text="✓ Commit to Git",
            height=34,
            width=125,
            corner_radius=8,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
            fg_color=self.COLOR_SUCCESS,
            hover_color=self.COLOR_SUCCESS_HOVER,
            command=self.create_commit,
        )
        self.create_button.pack(side="left", padx=(0, 6))

        self.pull_button = ctk.CTkButton(
            action_inner,
            text="📥 Pull",
            height=34,
            width=72,
            corner_radius=8,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
            fg_color=self.COLOR_TEAL,
            hover_color=self.COLOR_TEAL_HOVER,
            command=self.pull_commits_async,
        )
        self.pull_button.pack(side="left", padx=(0, 6))

        self.push_button = ctk.CTkButton(
            action_inner,
            text="🚀 Push",
            height=34,
            width=88,
            corner_radius=8,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
            fg_color=self.COLOR_PURPLE,
            hover_color=self.COLOR_PURPLE_HOVER,
            command=self.push_commits_async,
        )
        self.push_button.pack(side="left", padx=(0, 10))

        self.auto_stage_var = ctk.BooleanVar(value=True)
        self.auto_stage_cb = ctk.CTkCheckBox(
            action_inner,
            text="Auto-stage all",
            variable=self.auto_stage_var,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            width=105,
        )
        self.auto_stage_cb.pack(side="left", padx=(0, 8))

        self.auto_push_var = ctk.BooleanVar(value=False)
        self.auto_push_cb = ctk.CTkCheckBox(
            action_inner,
            text="Auto-push",
            variable=self.auto_push_var,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            width=85,
        )
        self.auto_push_cb.pack(side="left")

        # Real-time Status Indicator Bar
        status_bar = ctk.CTkFrame(action_card, fg_color="transparent")
        status_bar.pack(fill="x", padx=12, pady=(0, 6))

        self.status_label = ctk.CTkLabel(
            status_bar,
            text="● Ready",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        return view

    def _create_badge(self, parent, text: str, color_hex: str, on_click=None) -> ctk.CTkFrame:
        badge = ctk.CTkFrame(
            parent,
            fg_color=self.COLOR_INNER_BG,
            corner_radius=5,
            border_width=1,
            border_color=self.COLOR_BORDER,
            cursor="hand2" if on_click else "",
        )
        lbl = ctk.CTkLabel(
            badge,
            text=text,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
            text_color=color_hex,
            cursor="hand2" if on_click else "",
        )
        lbl.pack(padx=6, pady=2)
        if on_click:
            badge.bind("<Button-1>", lambda e: on_click())
            lbl.bind("<Button-1>", lambda e: on_click())
        badge.label = lbl
        return badge

    def _set_badge_text(self, badge: ctk.CTkFrame, text: str, color_hex: Optional[str] = None):
        badge.label.configure(text=text)
        if color_hex:
            badge.label.configure(text_color=color_hex)

    # -------------------------------------------------------------------------
    # 2. Changes & Diff View (Dedicated Tab with Interactive File Checklist)
    # -------------------------------------------------------------------------
    def _build_diff_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        view.grid_rowconfigure(1, weight=1)
        view.grid_columnconfigure(0, weight=1)

        # Header Toolbar
        diff_header = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        diff_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        diff_header_inner = ctk.CTkFrame(diff_header, fg_color="transparent")
        diff_header_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            diff_header_inner,
            text="📁 Changes & Selective Staging",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=13, weight="bold"),
        ).pack(side="left")

        diff_actions = ctk.CTkFrame(diff_header_inner, fg_color="transparent")
        diff_actions.pack(side="right")

        ctk.CTkButton(
            diff_actions,
            text="+ Stage All",
            width=75,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self.stage_all_changes_ui,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            diff_actions,
            text="- Unstage All",
            width=85,
            height=28,
            corner_radius=6,
            fg_color=("gray75", "#2C313C"),
            hover_color=("gray65", "#3A4150"),
            text_color=("gray10", "gray95"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self.unstage_all_changes_ui,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            diff_actions,
            text="📥 Pull",
            width=60,
            height=28,
            corner_radius=6,
            fg_color=self.COLOR_TEAL,
            hover_color=self.COLOR_TEAL_HOVER,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
            command=self.pull_commits_async,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            diff_actions,
            text="🚀 Push",
            width=65,
            height=28,
            corner_radius=6,
            fg_color=self.COLOR_PURPLE,
            hover_color=self.COLOR_PURPLE_HOVER,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
            command=self.push_commits_async,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            diff_actions,
            text="🔄 Refresh",
            width=70,
            height=28,
            corner_radius=6,
            fg_color="transparent",
            hover_color=("gray85", "#2C313C"),
            text_color=("gray20", "gray85"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self._refresh_diff_view,
        ).pack(side="left", padx=2)

        # Split Content Area: Left = File Checklist, Right = Diff Viewer
        split_card = ctk.CTkFrame(view, fg_color="transparent")
        split_card.grid(row=1, column=0, sticky="nsew")
        split_card.grid_rowconfigure(0, weight=1)
        split_card.grid_columnconfigure(0, weight=4)  # Left checklist (40%)
        split_card.grid_columnconfigure(1, weight=6)  # Right diff preview (60%)

        # --- Left Panel: Selective Files Checklist ---
        left_panel = ctk.CTkFrame(
            split_card,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left_panel.grid_rowconfigure(1, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        left_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        left_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))

        self.file_count_label = ctk.CTkLabel(
            left_header,
            text="Changed Files (0)",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
        )
        self.file_count_label.pack(side="left")

        self.view_all_diff_btn = ctk.CTkButton(
            left_header,
            text="Show All Diff",
            width=80,
            height=22,
            corner_radius=5,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            fg_color=("gray75", "#2C313C"),
            hover_color=("gray65", "#3A4150"),
            text_color=("gray10", "gray95"),
            command=lambda: self._select_file_for_diff(None),
        )
        self.view_all_diff_btn.pack(side="right")

        # Scrollable file list container
        self.file_checklist_frame = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="transparent",
            corner_radius=0,
        )
        self.file_checklist_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        # --- Right Panel: Diff Preview ---
        right_panel = ctk.CTkFrame(
            split_card,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        right_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        right_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))

        self.diff_preview_title = ctk.CTkLabel(
            right_header,
            text="Diff Preview: All Staged Changes",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
        )
        self.diff_preview_title.pack(side="left")

        self.diff_textbox = ctk.CTkTextbox(
            right_panel,
            corner_radius=6,
            font=ctk.CTkFont(family=self.MONO_FONT, size=11),
            wrap="none",
        )
        self.diff_textbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.diff_textbox.insert("1.0", "Select a repository to view Git diff and staged changes.")

        return view

    def _refresh_diff_view(self):
        if not self.project_path:
            self.diff_textbox.delete("1.0", "end")
            self.diff_textbox.insert("1.0", "No Git repository selected.")
            self._render_file_checklist([])
            return

        self._diff_req_id += 1
        req_id = self._diff_req_id
        path = self.project_path

        def _worker():
            files_status = GitService.get_detailed_file_status(path)
            self._post_ui(lambda: self._on_diff_list_loaded(req_id, files_status))

        threading.Thread(target=_worker, daemon=True).start()
        self._update_diff_textbox()

    def _on_diff_list_loaded(self, req_id: int, files_status: List[Dict]):
        if req_id != self._diff_req_id:
            return
        self._render_file_checklist(files_status)

    def _render_file_checklist(self, files_status: List[Dict]):
        for widget in self.file_checklist_frame.winfo_children():
            widget.destroy()
        self._file_row_widgets.clear()

        total_files = len(files_status)
        self.file_count_label.configure(text=f"Changed Files ({total_files})")

        if not files_status:
            no_files_lbl = ctk.CTkLabel(
                self.file_checklist_frame,
                text="Working tree is clean.\nNo modified or untracked files.",
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
                text_color=self.COLOR_TEXT_MUTED,
                justify="center",
            )
            no_files_lbl.pack(pady=30)
            return

        visible_files = files_status[: self.MAX_FILE_ROWS]
        for item in visible_files:
            file_path = item["file"]
            is_staged = item["staged"]
            status_type = item["status_type"]

            row_frame = ctk.CTkFrame(
                self.file_checklist_frame,
                fg_color=self.COLOR_INNER_BG if file_path == self.selected_diff_file else "transparent",
                corner_radius=6,
            )
            row_frame.pack(fill="x", pady=2, padx=2)
            self._file_row_widgets[file_path] = row_frame

            var = ctk.BooleanVar(value=is_staged)
            cb = ctk.CTkCheckBox(
                row_frame,
                text="",
                variable=var,
                width=20,
                height=20,
                command=lambda fp=file_path, v=var: self._on_file_checkbox_toggle(fp, v),
            )
            cb.pack(side="left", padx=(6, 4))

            badge_color = "#3B82F6"
            badge_char = item.get("index_status", "") or item.get("work_status", "M")
            if "Added" in status_type or "Untracked" in status_type:
                badge_color = self.COLOR_SUCCESS[1]
                badge_char = "A" if "Added" in status_type else "?"
            elif "Deleted" in status_type:
                badge_color = self.COLOR_DANGER[1]
                badge_char = "D"
            elif "Modified" in status_type:
                badge_color = "#F59E0B"
                badge_char = "M"

            tag_lbl = ctk.CTkLabel(
                row_frame,
                text=f"[{badge_char}]",
                font=ctk.CTkFont(family=self.MONO_FONT, size=10, weight="bold"),
                text_color=badge_color,
                width=24,
            )
            tag_lbl.pack(side="left")

            file_btn = ctk.CTkButton(
                row_frame,
                text=file_path,
                anchor="w",
                height=24,
                fg_color="transparent",
                hover_color=("gray80", "#2C313C"),
                text_color=("gray15", "gray90"),
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
                command=lambda fp=file_path: self._select_file_for_diff(fp),
            )
            file_btn.pack(side="left", fill="x", expand=True, padx=(2, 6))

        if total_files > self.MAX_FILE_ROWS:
            more_lbl = ctk.CTkLabel(
                self.file_checklist_frame,
                text=f"... and {total_files - self.MAX_FILE_ROWS} more file(s)",
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
                text_color=self.COLOR_TEXT_MUTED,
            )
            more_lbl.pack(pady=(6, 4))

    def _on_file_checkbox_toggle(self, file_path: str, var: ctk.BooleanVar):
        if not self.project_path:
            return

        should_stage = var.get()
        path = self.project_path
        self.status_label.configure(
            text=f"⏳ {'Staging' if should_stage else 'Unstaging'} {file_path}...",
            text_color="#3B82F6",
        )

        def _worker():
            if should_stage:
                ok = GitService.stage_single_file(file_path, path)
            else:
                ok = GitService.unstage_single_file(file_path, path)
            self._post_ui(lambda: self._on_file_stage_complete(file_path, should_stage, ok))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_file_stage_complete(self, file_path: str, staged: bool, ok: bool):
        if ok:
            verb = "Staged" if staged else "Unstaged"
            color = self.COLOR_SUCCESS[1] if staged else self.COLOR_TEXT_MUTED
            self.status_label.configure(text=f"✓ {verb}: {file_path}", text_color=color)
        else:
            self.status_label.configure(text=f"❌ Failed to update {file_path}", text_color=self.COLOR_DANGER[1])
        self.refresh_git_status()
        self._update_diff_textbox()

    def _select_file_for_diff(self, file_path: Optional[str]):
        old_file = self.selected_diff_file
        self.selected_diff_file = file_path

        if old_file and old_file in self._file_row_widgets:
            old_widget = self._file_row_widgets[old_file]
            if old_widget.winfo_exists():
                old_widget.configure(fg_color="transparent")

        if file_path and file_path in self._file_row_widgets:
            new_widget = self._file_row_widgets[file_path]
            if new_widget.winfo_exists():
                new_widget.configure(fg_color=self.COLOR_INNER_BG)

        self._update_diff_textbox()

    def _update_diff_textbox(self):
        if not self.project_path:
            return

        self._diff_text_req_id += 1
        req_id = self._diff_text_req_id
        path = self.project_path
        selected_file = self.selected_diff_file

        if selected_file:
            self.diff_preview_title.configure(text=f"Diff Preview: {selected_file}")
        else:
            self.diff_preview_title.configure(text="Diff Preview: All Staged Changes")

        def _worker():
            if selected_file:
                diff_text = GitService.get_file_diff(selected_file, path)
                if not diff_text.strip():
                    diff_text = f"# No diff changes found for {selected_file}."
            else:
                git_diff = GitService.get_staged_diff(path)
                status_summary = GitService.get_repo_status_summary(path)

                lines = [
                    f"# Repository: {Path(path).name}",
                    f"# Active Branch: {status_summary.get('branch', 'unknown')}",
                    f"# Unpushed Commits: {status_summary.get('unpushed_count', 0)}\n",
                    "## Staged Files (will be analyzed for commit):",
                ]
                staged = status_summary.get("staged_files", [])
                if staged:
                    for s in staged:
                        lines.append(f"  [{s['status']}] {s['file']}")
                else:
                    lines.append("  (No staged files - check boxes or click '+ Stage All')")

                lines.append("\n" + "=" * 60 + "\n## Staged Unified Diff Preview:\n" + "=" * 60 + "\n")
                if git_diff and git_diff.diff:
                    lines.append(git_diff.diff)
                else:
                    lines.append("No staged diff content available.")
                diff_text = "\n".join(lines)

            if len(diff_text) > self.MAX_DIFF_PREVIEW_CHARS:
                diff_text = (
                    diff_text[: self.MAX_DIFF_PREVIEW_CHARS]
                    + "\n\n... [Diff preview truncated at 40,000 chars for UI performance]"
                )

            self._post_ui(lambda: self._apply_diff_textbox(req_id, diff_text))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_diff_textbox(self, req_id: int, diff_text: str):
        if req_id != self._diff_text_req_id:
            return
        self.diff_textbox.delete("1.0", "end")
        self.diff_textbox.insert("1.0", diff_text)

    # -------------------------------------------------------------------------
    # 3. Repositories Manager View & Multi-Repo Switcher Helpers
    # -------------------------------------------------------------------------
    def _build_repositories_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        view.grid_rowconfigure(1, weight=1)
        view.grid_columnconfigure(0, weight=1)

        header_card = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        header_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        header_inner = ctk.CTkFrame(header_card, fg_color="transparent")
        header_inner.pack(fill="x", padx=12, pady=8)

        title_box = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="🗂️ Repositories Manager",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=13, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Add, scan, switch, pull, or push multiple Git repositories from one place",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            text_color=self.COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        btn_box = ctk.CTkFrame(header_inner, fg_color="transparent")
        btn_box.pack(side="right")

        ctk.CTkButton(
            btn_box,
            text="+ Add Repository",
            width=115,
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
            fg_color=self.COLOR_PRIMARY,
            hover_color=self.COLOR_PRIMARY_HOVER,
            command=self.select_project,
        ).pack(side="left", padx=3)

        self.scan_repos_btn = ctk.CTkButton(
            btn_box,
            text="📂 Scan Folder",
            width=105,
            height=30,
            corner_radius=6,
            fg_color=("gray75", "#2C313C"),
            hover_color=("gray65", "#3A4150"),
            text_color=("gray10", "gray95"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self.scan_workspace_repos_ui,
        )
        self.scan_repos_btn.pack(side="left", padx=3)

        ctk.CTkButton(
            btn_box,
            text="🔄 Refresh All",
            width=95,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            hover_color=("gray85", "#2C313C"),
            text_color=("gray20", "gray85"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self._refresh_repositories_view,
        ).pack(side="left", padx=3)

        list_card = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        list_card.grid(row=1, column=0, sticky="nsew")
        list_card.grid_rowconfigure(0, weight=1)
        list_card.grid_columnconfigure(0, weight=1)

        self.repos_list_frame = ctk.CTkScrollableFrame(
            list_card,
            fg_color="transparent",
            corner_radius=6,
        )
        self.repos_list_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        return view

    def _render_sidebar_repos(self):
        for widget in self.sidebar_repo_scroll.winfo_children():
            widget.destroy()
        self._repo_row_widgets.clear()

        if not self.saved_repositories:
            ctk.CTkLabel(
                self.sidebar_repo_scroll,
                text="No repos saved yet.\nClick '+ Add' above.",
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
                text_color=self.COLOR_TEXT_MUTED,
                justify="left",
            ).pack(anchor="w", padx=8, pady=6)
            return

        active_norm = os.path.normcase(self.project_path) if self.project_path else ""
        for repo_path in self.saved_repositories:
            is_active = os.path.normcase(repo_path) == active_norm
            repo_name = Path(repo_path).name or repo_path
            btn = ctk.CTkButton(
                self.sidebar_repo_scroll,
                text=f"{'● ' if is_active else '📦 '}{repo_name}",
                anchor="w",
                height=28,
                corner_radius=6,
                font=ctk.CTkFont(
                    family=self.FONT_FAMILY,
                    size=11,
                    weight="bold" if is_active else "normal",
                ),
                fg_color=self.COLOR_INNER_BG if is_active else "transparent",
                text_color=("#1D4ED8", "#93C5FD") if is_active else ("gray25", "gray80"),
                hover_color=("gray85", "#1E222A"),
                command=lambda rp=repo_path: self._set_project(rp),
            )
            btn.pack(fill="x", padx=2, pady=1)
            self._repo_row_widgets[os.path.normcase(repo_path)] = btn

    def _sync_repo_switcher_menu(self):
        self._repo_display_map.clear()
        if not self.saved_repositories:
            self.repo_switcher_menu.configure(values=["No repositories"])
            self.repo_switcher_menu.set("No repositories")
            return

        name_counts: Dict[str, int] = {}
        for rp in self.saved_repositories:
            name = Path(rp).name or rp
            name_counts[name] = name_counts.get(name, 0) + 1

        display_values: List[str] = []
        active_display = ""
        active_norm = os.path.normcase(self.project_path) if self.project_path else ""

        for rp in self.saved_repositories:
            p = Path(rp)
            name = p.name or rp
            if name_counts.get(name, 0) > 1 and p.parent.name:
                label = f"{name} ({p.parent.name})"
            else:
                label = name
            while label in self._repo_display_map:
                label = f"{label} *"
            self._repo_display_map[label] = rp
            display_values.append(label)
            if os.path.normcase(rp) == active_norm:
                active_display = label

        self.repo_switcher_menu.configure(values=display_values)
        if active_display:
            self.repo_switcher_menu.set(active_display)
        elif display_values:
            self.repo_switcher_menu.set(display_values[0])

    def _on_repo_switcher_select(self, choice: str):
        target_path = self._repo_display_map.get(choice)
        if target_path and os.path.normcase(target_path) != os.path.normcase(self.project_path or ""):
            self._set_project(target_path)

    def _open_branch_switcher_menu(self):
        if not self.project_path:
            return
        path = self.project_path
        current_branch = (self._latest_status_summary or {}).get("branch", "")

        def _worker():
            branches = GitService.get_local_branches(path)
            self._post_ui(lambda: self._show_branch_menu(path, branches, current_branch))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_branch_menu(self, repo_path: str, branches: List[str], current_branch: str):
        if not branches:
            self.status_label.configure(text="⚠️ No local branches found", text_color=self.COLOR_TEXT_MUTED)
            return

        menu = tk.Menu(self, tearoff=0)
        for branch in branches:
            label = f"✓ {branch}" if branch == current_branch else f"   {branch}"
            menu.add_command(
                label=label,
                command=lambda b=branch: self._checkout_branch_async(repo_path, b),
            )

        x = self.branch_badge.winfo_rootx()
        y = self.branch_badge.winfo_rooty() + self.branch_badge.winfo_height() + 2
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _checkout_branch_async(self, repo_path: str, branch_name: str):
        self.status_label.configure(text=f"⏳ Switching to branch '{branch_name}'...", text_color="#3B82F6")

        def _worker():
            ok, msg = GitService.checkout_branch(repo_path, branch_name)
            self._post_ui(lambda: self._on_checkout_complete(ok, branch_name, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_checkout_complete(self, ok: bool, branch_name: str, msg: str):
        if ok:
            self.status_label.configure(text=f"✓ Switched to branch '{branch_name}'", text_color=self.COLOR_SUCCESS[1])
            self.refresh_git_status()
            if self.current_view == "Diff":
                self._refresh_diff_view()
        else:
            self.status_label.configure(text="❌ Branch switch failed", text_color=self.COLOR_DANGER[1])
            messagebox.showerror("Branch Checkout Failed", msg)

    def _refresh_repositories_view(self):
        self._render_repositories_cards()
        if not self.saved_repositories:
            return

        self._repos_view_req_id += 1
        req_id = self._repos_view_req_id
        repos = list(self.saved_repositories)

        def _worker():
            from concurrent.futures import ThreadPoolExecutor

            def _check_one(rp: str):
                summary = GitService.get_repo_status_summary(rp)
                self._post_ui(lambda p=rp, s=summary: self._update_repo_card_status(req_id, p, s))

            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(_check_one, repos))

        threading.Thread(target=_worker, daemon=True).start()

    def _render_repositories_cards(self):
        for widget in self.repos_list_frame.winfo_children():
            widget.destroy()
        self._repo_status_labels.clear()

        if not self.saved_repositories:
            ctk.CTkLabel(
                self.repos_list_frame,
                text="No repositories added yet.\nClick '+ Add Repository' or '📂 Scan Folder' to add multiple Git projects.",
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=12),
                text_color=self.COLOR_TEXT_MUTED,
                justify="center",
            ).pack(pady=60)
            return

        active_norm = os.path.normcase(self.project_path) if self.project_path else ""
        for repo_path in self.saved_repositories:
            is_active = os.path.normcase(repo_path) == active_norm
            card = ctk.CTkFrame(
                self.repos_list_frame,
                fg_color=self.COLOR_INNER_BG,
                corner_radius=8,
                border_width=1,
                border_color=self.COLOR_PRIMARY if is_active else self.COLOR_BORDER,
            )
            card.pack(fill="x", padx=4, pady=4)

            info_col = ctk.CTkFrame(card, fg_color="transparent")
            info_col.pack(side="left", fill="x", expand=True, padx=12, pady=8)

            top_line = ctk.CTkFrame(info_col, fg_color="transparent")
            top_line.pack(fill="x")

            ctk.CTkLabel(
                top_line,
                text=f"📦 {Path(repo_path).name or repo_path}",
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
                anchor="w",
            ).pack(side="left")

            if is_active:
                ctk.CTkLabel(
                    top_line,
                    text="ACTIVE",
                    font=ctk.CTkFont(family=self.FONT_FAMILY, size=9, weight="bold"),
                    fg_color=self.COLOR_SUCCESS,
                    text_color="#FFFFFF",
                    corner_radius=4,
                    padx=6,
                    pady=1,
                ).pack(side="left", padx=8)

            ctk.CTkLabel(
                info_col,
                text=repo_path,
                font=ctk.CTkFont(family=self.MONO_FONT, size=10),
                text_color=self.COLOR_TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", pady=(1, 2))

            status_lbl = ctk.CTkLabel(
                info_col,
                text="⏳ Checking repository status...",
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
                text_color=self.COLOR_TEXT_MUTED,
                anchor="w",
            )
            status_lbl.pack(fill="x")
            self._repo_status_labels[os.path.normcase(repo_path)] = status_lbl

            actions_col = ctk.CTkFrame(card, fg_color="transparent")
            actions_col.pack(side="right", padx=10, pady=8)

            ctk.CTkButton(
                actions_col,
                text="Open",
                width=60,
                height=28,
                corner_radius=6,
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
                fg_color=self.COLOR_PRIMARY,
                hover_color=self.COLOR_PRIMARY_HOVER,
                command=lambda rp=repo_path: self._open_repo_from_manager(rp),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                actions_col,
                text="📥 Pull",
                width=60,
                height=28,
                corner_radius=6,
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
                fg_color=self.COLOR_TEAL,
                hover_color=self.COLOR_TEAL_HOVER,
                command=lambda rp=repo_path: self._pull_repo_from_manager(rp),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                actions_col,
                text="🚀 Push",
                width=60,
                height=28,
                corner_radius=6,
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
                fg_color=self.COLOR_PURPLE,
                hover_color=self.COLOR_PURPLE_HOVER,
                command=lambda rp=repo_path: self._push_repo_from_manager(rp),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                actions_col,
                text="✕",
                width=28,
                height=28,
                corner_radius=6,
                fg_color="transparent",
                hover_color=("#FEE2E2", "#3B1D1D"),
                text_color=self.COLOR_DANGER,
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
                command=lambda rp=repo_path: self._remove_repository(rp),
            ).pack(side="left", padx=(4, 0))

    def _update_repo_card_status(self, req_id: int, repo_path: str, summary: Dict):
        if req_id != self._repos_view_req_id:
            return
        lbl = self._repo_status_labels.get(os.path.normcase(repo_path))
        if not lbl or not lbl.winfo_exists():
            return

        if not summary.get("is_repo"):
            err = summary.get("error") or "Invalid Git repository"
            lbl.configure(text=f"⚠️ {err}", text_color=self.COLOR_DANGER[1])
            return

        branch = summary.get("branch", "unknown")
        staged = len(summary.get("staged_files", []))
        unstaged = len(summary.get("unstaged_files", [])) + len(summary.get("untracked_files", []))
        unpushed = summary.get("unpushed_count", 0)
        parts = [f"🌿 {branch}", f"● {staged} staged", f"● {unstaged} unstaged"]
        if unpushed > 0:
            parts.append(f"↑ {unpushed} unpushed")
        color = self.COLOR_SUCCESS[1] if staged > 0 else ("#F59E0B" if unstaged > 0 else self.COLOR_TEXT_MUTED)
        lbl.configure(text="   •   ".join(parts), text_color=color)

    def _open_repo_from_manager(self, repo_path: str):
        self._set_project(repo_path)
        self.show_view("Generator")

    def _pull_repo_from_manager(self, repo_path: str):
        self.status_label.configure(text=f"⏳ Pulling {Path(repo_path).name}...", text_color=self.COLOR_TEAL[1])

        def _worker():
            ok, msg = GitService.pull_commits(repo_path)
            self._post_ui(lambda: self._on_manager_git_action_complete("Pull", repo_path, ok, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _push_repo_from_manager(self, repo_path: str):
        self.status_label.configure(text=f"⏳ Pushing {Path(repo_path).name}...", text_color=self.COLOR_PURPLE[1])

        def _worker():
            ok, msg = GitService.push_commits(repo_path)
            self._post_ui(lambda: self._on_manager_git_action_complete("Push", repo_path, ok, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_manager_git_action_complete(self, action: str, repo_path: str, ok: bool, msg: str):
        name = Path(repo_path).name
        if ok:
            self.status_label.configure(text=f"✓ {action} complete ({name})", text_color=self.COLOR_SUCCESS[1])
        else:
            self.status_label.configure(text=f"❌ {action} failed ({name})", text_color=self.COLOR_DANGER[1])
            messagebox.showerror(f"{action} Failed ({name})", msg)
        if os.path.normcase(repo_path) == os.path.normcase(self.project_path or ""):
            self.refresh_git_status()
        if self.current_view == "Repositories":
            self._refresh_repositories_view()

    def _remove_repository(self, repo_path: str):
        self.saved_repositories = ConfigManager.remove_repository(repo_path)
        if self.project_path and os.path.normcase(self.project_path) == os.path.normcase(repo_path):
            self.project_path = None
            self.project_entry.delete(0, "end")
            if self.saved_repositories:
                self._set_project(self.saved_repositories[0], save_last=False)
            else:
                self._set_badge_text(self.branch_badge, "🌿 Branch: None", "#3B82F6")
                self._set_badge_text(self.staged_badge, "● 0 staged", "#6B7280")
                self._set_badge_text(self.unstaged_badge, "● 0 modified", "#6B7280")
                self._set_badge_text(self.unpushed_badge, "↑ 0 unpushed", "#6B7280")
        self._render_sidebar_repos()
        self._sync_repo_switcher_menu()
        if self.current_view == "Repositories":
            self._refresh_repositories_view()

    def scan_workspace_repos_ui(self):
        folder = filedialog.askdirectory(title="Select Parent Workspace Folder to Scan for Git Repositories")
        if not folder:
            return
        self.scan_repos_btn.configure(state="disabled", text="⏳ Scanning...")
        self.status_label.configure(text=f"⏳ Scanning {folder} for Git repositories...", text_color="#3B82F6")

        def _worker():
            discovered = GitService.scan_for_repositories(folder, max_depth=3)
            self._post_ui(lambda: self._on_workspace_scanned(discovered))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_workspace_scanned(self, discovered: List[str]):
        self.scan_repos_btn.configure(state="normal", text="📂 Scan Folder")
        if not discovered:
            self.status_label.configure(text="⚠️ No Git repositories found in folder", text_color=self.COLOR_TEXT_MUTED)
            messagebox.showinfo("Scan Complete", "No Git repositories were found within 3 directory levels.")
            return

        existing_keys = {os.path.normcase(r) for r in self.saved_repositories}
        added_count = 0
        for repo in discovered:
            if os.path.normcase(repo) not in existing_keys:
                self.saved_repositories.append(repo)
                existing_keys.add(os.path.normcase(repo))
                added_count += 1

        self.saved_repositories = ConfigManager._dedupe_repositories(self.saved_repositories)
        ConfigManager.save_settings({"repositories": self.saved_repositories})

        self._render_sidebar_repos()
        self._sync_repo_switcher_menu()
        if not self.project_path and self.saved_repositories:
            self._set_project(self.saved_repositories[0])
        elif self.current_view == "Repositories":
            self._refresh_repositories_view()

        self.status_label.configure(
            text=f"✓ Found {len(discovered)} repo(s), added {added_count} new",
            text_color=self.COLOR_SUCCESS[1],
        )

    # -------------------------------------------------------------------------
    # 3. Settings View
    # -------------------------------------------------------------------------
    def _build_settings_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        view.grid_rowconfigure(2, weight=1)
        view.grid_columnconfigure(0, weight=1)

        # Card 1: AI Provider & Model Configuration
        ai_card = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        ai_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            ai_card,
            text="🤖 Gemini AI Settings",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=13, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # API Key Row
        key_frame = ctk.CTkFrame(ai_card, fg_color="transparent")
        key_frame.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(
            key_frame,
            text="Gemini API Key",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            width=120,
            anchor="w",
        ).pack(side="left")

        self.api_key_entry = ctk.CTkEntry(
            key_frame,
            placeholder_text="Enter your Gemini API key...",
            show="*",
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
        )
        self.api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.toggle_key_btn = ctk.CTkButton(
            key_frame,
            text="👁",
            width=36,
            height=30,
            corner_radius=6,
            fg_color=("gray75", "#2C313C"),
            hover_color=("gray65", "#3A4150"),
            text_color=("gray10", "gray95"),
            command=self._toggle_api_key_visibility,
        )
        self.toggle_key_btn.pack(side="left")

        # Model Selection Row
        model_frame = ctk.CTkFrame(ai_card, fg_color="transparent")
        model_frame.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(
            model_frame,
            text="AI Model",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            width=120,
            anchor="w",
        ).pack(side="left")

        self.model_dropdown = ctk.CTkOptionMenu(
            model_frame,
            values=self.model_options,
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self._on_model_dropdown_change,
        )
        self.model_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.fetch_models_btn = ctk.CTkButton(
            model_frame,
            text="🔄 Fetch Models",
            width=100,
            height=30,
            corner_radius=6,
            fg_color=("gray75", "#2C313C"),
            hover_color=("gray65", "#3A4150"),
            text_color=("gray10", "gray95"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
            command=self.fetch_available_models_async,
        )
        self.fetch_models_btn.pack(side="left")

        # Temperature Slider Row
        temp_frame = ctk.CTkFrame(ai_card, fg_color="transparent")
        temp_frame.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(
            temp_frame,
            text="Temperature",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            width=120,
            anchor="w",
        ).pack(side="left")

        self.temp_slider = ctk.CTkSlider(
            temp_frame,
            from_=0.0,
            to=1.0,
            number_of_steps=20,
            height=16,
            command=self._on_temp_slider_change,
        )
        self.temp_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.temp_value_label = ctk.CTkLabel(
            temp_frame,
            text="0.70",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
            width=36,
            anchor="w",
        )
        self.temp_value_label.pack(side="left")

        # Card 2: Git & Integration Settings
        git_card = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        git_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            git_card,
            text="🐙 GitHub & Git Integration",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=13, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(12, 6))

        token_frame = ctk.CTkFrame(git_card, fg_color="transparent")
        token_frame.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(
            token_frame,
            text="GitHub Token",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            width=120,
            anchor="w",
        ).pack(side="left")

        self.github_token_entry = ctk.CTkEntry(
            token_frame,
            placeholder_text="Optional: Personal Access Token (for issues/PRs)",
            show="*",
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
        )
        self.github_token_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.toggle_token_btn = ctk.CTkButton(
            token_frame,
            text="👁",
            width=36,
            height=30,
            corner_radius=6,
            fg_color=("gray75", "#2C313C"),
            hover_color=("gray65", "#3A4150"),
            text_color=("gray10", "gray95"),
            command=self._toggle_token_visibility,
        )
        self.toggle_token_btn.pack(side="left")

        # Card 3: Save Actions Footer
        settings_actions = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        settings_actions.grid(row=2, column=0, sticky="new")

        actions_inner = ctk.CTkFrame(settings_actions, fg_color="transparent")
        actions_inner.pack(fill="x", padx=14, pady=10)

        self.save_settings_btn = ctk.CTkButton(
            actions_inner,
            text="💾 Save Settings",
            height=32,
            width=130,
            corner_radius=7,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11, weight="bold"),
            fg_color=self.COLOR_PRIMARY,
            hover_color=self.COLOR_PRIMARY_HOVER,
            command=self.save_config,
        )
        self.save_settings_btn.pack(side="left", padx=(0, 8))

        self.reset_settings_btn = ctk.CTkButton(
            actions_inner,
            text="🔄 Reset Defaults",
            height=32,
            width=120,
            corner_radius=7,
            fg_color="transparent",
            hover_color=("gray85", "#2C313C"),
            text_color=("gray20", "gray85"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self.reset_config,
        )
        self.reset_settings_btn.pack(side="left", padx=(0, 12))

        self.config_status_label = ctk.CTkLabel(
            actions_inner,
            text="",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            text_color=self.COLOR_TEXT_MUTED,
        )
        self.config_status_label.pack(side="left")

        # Populate settings fields
        self._populate_config_fields()

        return view

    def _on_model_dropdown_change(self, choice: str):
        """Immediately update the sidebar active model badge when dropdown selection changes."""
        self.model_status_badge.configure(text=f"🤖 {choice}")

    def fetch_available_models_async(self):
        """Fetch all available Gemini models from Google AI API."""
        api_key = self.api_key_entry.get().strip() or self.config_data.get("api_key", "")
        if not api_key or api_key == "your-api-key-here":
            messagebox.showwarning("API Key Required", "Please enter a valid Gemini API key first.")
            return

        self.fetch_models_btn.configure(state="disabled", text="⏳ Loading...")
        self.config_status_label.configure(text="Fetching available models...", text_color="#3B82F6")

        def _worker():
            models = GeminiClient.list_available_models(api_key)
            self._post_ui(lambda: self._on_models_fetched(models))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_models_fetched(self, models: List[str]):
        self.fetch_models_btn.configure(state="normal", text="🔄 Fetch Models")
        if models:
            self._update_model_dropdown_options(models)
            self.config_status_label.configure(
                text=f"✓ Loaded {len(models)} available model(s)",
                text_color=self.COLOR_SUCCESS[1],
            )
            self.after(3000, lambda: self.config_status_label.configure(text=""))
        else:
            self.config_status_label.configure(text="⚠️ Failed to fetch models", text_color=self.COLOR_DANGER[1])

    def _toggle_api_key_visibility(self):
        self.show_api_key = not self.show_api_key
        self.api_key_entry.configure(show="" if self.show_api_key else "*")
        self.toggle_key_btn.configure(text="🔒" if self.show_api_key else "👁")

    def _toggle_token_visibility(self):
        self.show_github_token = not self.show_github_token
        self.github_token_entry.configure(show="" if self.show_github_token else "*")
        self.toggle_token_btn.configure(text="🔒" if self.show_github_token else "👁")

    def _on_temp_slider_change(self, value):
        self.temp_value_label.configure(text=f"{value:.2f}")

    def _populate_config_fields(self):
        cfg = self.config_data
        self.api_key_entry.delete(0, "end")
        self.api_key_entry.insert(0, cfg.get("api_key", ""))

        model = cfg.get("model", "gemini-2.0-flash-lite")
        if model not in self.model_options:
            self.model_options.insert(0, model)
            self.model_dropdown.configure(values=self.model_options)

        self.model_dropdown.set(model)
        self.model_status_badge.configure(text=f"🤖 {model}")

        temp = float(cfg.get("temperature", 0.7))
        self.temp_slider.set(temp)
        self.temp_value_label.configure(text=f"{temp:.2f}")

        self.github_token_entry.delete(0, "end")
        self.github_token_entry.insert(0, cfg.get("github_token", ""))

    def save_config(self):
        api_key = self.api_key_entry.get().strip()
        model = self.model_dropdown.get().strip()
        temperature = round(float(self.temp_slider.get()), 2)
        github_token = self.github_token_entry.get().strip()

        if not api_key:
            messagebox.showwarning("API Key Required", "Please enter a valid Gemini API key.")
            return

        settings = {
            "api_key": api_key,
            "model": model or "gemini-2.0-flash-lite",
            "temperature": temperature,
            "github_token": github_token,
        }

        try:
            ConfigManager.save_settings(settings)
            self._load_config_cache()
            self.model_status_badge.configure(text=f"🤖 {model}")
            self.config_status_label.configure(text="✓ Saved successfully", text_color=self.COLOR_SUCCESS[1])
            self.after(3000, lambda: self.config_status_label.configure(text=""))
        except Exception as exc:
            self.config_status_label.configure(text="❌ Save failed", text_color=self.COLOR_DANGER[1])
            messagebox.showerror("Save Failed", str(exc))

    def reset_config(self):
        if messagebox.askyesno("Reset Configuration", "Reset settings to default values?"):
            ConfigManager.reset_to_default()
            self._load_config_cache()
            self._populate_config_fields()
            self.model_status_badge.configure(text=f"🤖 {self.config_data.get('model', 'gemini-2.0-flash-lite')}")
            self.config_status_label.configure(text="✓ Reset to defaults", text_color=self.COLOR_SUCCESS[1])

    # -------------------------------------------------------------------------
    # Date/Time Logic
    # -------------------------------------------------------------------------
    def _on_date_mode_change(self, value):
        if value == "Custom Timestamp":
            self.custom_date_frame.pack(side="left", padx=4)
            if not self.date_entry.get():
                self._set_date_today()
        else:
            self.custom_date_frame.pack_forget()

    def _set_date_today(self):
        now = datetime.now()
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, now.strftime("%Y-%m-%d"))
        self.time_entry.delete(0, "end")
        self.time_entry.insert(0, now.strftime("%H:%M"))

    def get_commit_datetime(self):
        if self.date_mode_btn.get() == "Current Time":
            return 200, None

        date_val = self.date_entry.get().strip()
        time_val = self.time_entry.get().strip() or "01:00"

        if not date_val:
            return 200, None

        try:
            if ":" in time_val:
                dt_str = f"{date_val} {time_val}"
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            else:
                dt = datetime.strptime(date_val, "%Y-%m-%d")
                dt = dt.replace(hour=1, minute=0)

            local_tz = datetime.now().astimezone().tzinfo
            dt = dt.replace(tzinfo=local_tz)
            return 200, dt.strftime("%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            messagebox.showerror(
                "Invalid Date/Time",
                "Please enter a valid format:\nDate: YYYY-MM-DD (e.g. 2026-08-27)\nTime: HH:MM (e.g. 14:30)",
            )
            return 400, None

    # -------------------------------------------------------------------------
    # Editor & Option Switching
    # -------------------------------------------------------------------------
    def _on_text_change(self, event=None):
        content = self.commit_text.get("1.0", "end-1c")
        lines = content.splitlines() if content else []
        first_line = lines[0] if lines else ""
        first_len = len(first_line)

        color = self.COLOR_TEXT_MUTED
        if first_len > 72:
            color = self.COLOR_DANGER[1]
        elif first_len > 50:
            color = "#F59E0B"

        self.char_count_badge.configure(
            text=f"Line 1: {first_len} / 72 chars",
            text_color=color,
        )
        self.total_lines_badge.configure(text=f"{len(lines)} line(s)")

    def _render_option_pills(self):
        for widget in self.options_container.winfo_children():
            widget.destroy()

        if len(self.generated_options) <= 1:
            return

        for idx, _ in enumerate(self.generated_options):
            is_active = idx == self.selected_option_idx
            btn = ctk.CTkButton(
                self.options_container,
                text=f"Opt {idx + 1}",
                width=50,
                height=24,
                corner_radius=5,
                font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold" if is_active else "normal"),
                fg_color=self.COLOR_PRIMARY if is_active else ("gray80", "#2C313C"),
                text_color="#FFFFFF" if is_active else ("gray10", "gray85"),
                hover_color=self.COLOR_PRIMARY_HOVER if is_active else ("gray70", "#3A4150"),
                command=lambda i=idx: self._select_option(i),
            )
            btn.pack(side="left", padx=2)

    def _select_option(self, idx: int):
        if 0 <= idx < len(self.generated_options):
            self.selected_option_idx = idx
            self.commit_text.delete("1.0", "end")
            self.commit_text.insert("1.0", self.generated_options[idx])
            self._render_option_pills()
            self._on_text_change()

    def copy_commit_message(self):
        msg = self.commit_text.get("1.0", "end-1c").strip()
        if not msg:
            return
        self.clipboard_clear()
        self.clipboard_append(msg)
        self.copy_btn.configure(text="✓ Copied!", fg_color=self.COLOR_SUCCESS)
        self.after(2000, lambda: self.copy_btn.configure(text="📋 Copy", fg_color=self.COLOR_PRIMARY))

    def clear_commit_message(self):
        self.commit_text.delete("1.0", "end")
        self.generated_options = []
        self._render_option_pills()
        self._on_text_change()

    # -------------------------------------------------------------------------
    # Git & Project Actions
    # -------------------------------------------------------------------------
    def select_project(self):
        folder = filedialog.askdirectory(title="Select Git Project Folder")
        if folder:
            self._validate_and_load_project_async(folder)

    def _on_project_entry_submit(self):
        folder = (self.project_entry.get() or "").strip()
        if folder:
            self._validate_and_load_project_async(folder)

    def _validate_and_load_project_async(self, folder: str):
        self.status_label.configure(text="⏳ Opening repository...", text_color="#3B82F6")

        def _worker():
            repo_root = GitService.get_repository_root(folder)
            self._post_ui(lambda: self._on_project_validated(repo_root))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_project_validated(self, repo_root: Optional[str]):
        if not repo_root:
            self.status_label.configure(text="❌ Not a valid Git repository", text_color=self.COLOR_DANGER[1])
            messagebox.showwarning(
                "Invalid Repository",
                "No .git repository found in the selected folder.\nPlease select a valid Git repository.",
            )
            return
        self._set_project(repo_root)

    def _set_project(self, repo_root: str, save_last: bool = True):
        norm_root = ConfigManager._normalize_repo_path(repo_root)
        self.project_path = norm_root
        self.selected_diff_file = None
        self.project_entry.delete(0, "end")
        self.project_entry.insert(0, norm_root)

        norm_key = os.path.normcase(norm_root)
        already_saved = any(os.path.normcase(r) == norm_key for r in self.saved_repositories)
        if not already_saved:
            self.saved_repositories.append(norm_root)
            self.saved_repositories = ConfigManager._dedupe_repositories(self.saved_repositories)

        self._render_sidebar_repos()
        self._sync_repo_switcher_menu()

        if save_last or not already_saved or norm_root != self.config_data.get("last_repo_path"):
            self.config_data["last_repo_path"] = norm_root
            threading.Thread(
                target=lambda: ConfigManager.add_repository(norm_root),
                daemon=True,
            ).start()

        self.refresh_git_status()
        if self.current_view == "Diff":
            self._refresh_diff_view()
        elif self.current_view == "Repositories":
            self._refresh_repositories_view()

    def refresh_git_status(self):
        path = (self.project_entry.get() or "").strip() or self.project_path
        if not path:
            return

        self._status_req_id += 1
        req_id = self._status_req_id

        def _worker():
            summary = GitService.get_repo_status_summary(path)
            self._post_ui(lambda: self._apply_git_status(req_id, summary))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_git_status(self, req_id: int, summary: Dict):
        if req_id != self._status_req_id:
            return

        self._latest_status_summary = summary
        if not summary.get("is_repo"):
            self._set_badge_text(self.branch_badge, "🌿 None", "#EF4444")
            self._set_badge_text(self.staged_badge, "● 0 staged", "#6B7280")
            self._set_badge_text(self.unstaged_badge, "● 0 modified", "#6B7280")
            self._set_badge_text(self.unpushed_badge, "↑ 0 unpushed", "#6B7280")
            return

        branch = summary.get("branch", "unknown")
        staged_count = len(summary.get("staged_files", []))
        unstaged_count = len(summary.get("unstaged_files", []))
        untracked_count = len(summary.get("untracked_files", []))
        unpushed_count = summary.get("unpushed_count", 0)
        pending_count = unstaged_count + untracked_count

        self._set_badge_text(self.branch_badge, f"🌿 {branch}", "#3B82F6")
        self._set_badge_text(
            self.staged_badge,
            f"● {staged_count} staged",
            self.COLOR_SUCCESS[1] if staged_count > 0 else "#6B7280",
        )
        self._set_badge_text(
            self.unstaged_badge,
            f"● {pending_count} unstaged" if untracked_count else f"● {unstaged_count} modified",
            "#F59E0B" if pending_count > 0 else "#6B7280",
        )
        self._set_badge_text(
            self.unpushed_badge,
            f"↑ {unpushed_count} unpushed",
            self.COLOR_PURPLE[1] if unpushed_count > 0 else "#6B7280",
        )

        status_txt = f"● Ready • {staged_count} staged"
        if pending_count > 0:
            status_txt += f" • {pending_count} unstaged"
        if unpushed_count > 0:
            status_txt += f" • {unpushed_count} unpushed commit(s)"

        self.status_label.configure(
            text=status_txt,
            text_color=self.COLOR_SUCCESS[1] if staged_count > 0 else self.COLOR_TEXT_MUTED,
        )

    def stage_all_changes_ui(self):
        path = (self.project_entry.get() or "").strip() or self.project_path
        if not path:
            messagebox.showwarning("Project Required", "Please select a project folder first.")
            return

        self.status_label.configure(text="⏳ Staging all changes...", text_color="#3B82F6")

        def _worker():
            success = GitService.stage_all_changes(path)
            self._post_ui(lambda: self._on_stage_all_complete(success, staged=True))

        threading.Thread(target=_worker, daemon=True).start()

    def unstage_all_changes_ui(self):
        path = (self.project_entry.get() or "").strip() or self.project_path
        if not path:
            return

        self.status_label.configure(text="⏳ Unstaging all changes...", text_color="#3B82F6")

        def _worker():
            success = GitService.unstage_all_changes(path)
            self._post_ui(lambda: self._on_stage_all_complete(success, staged=False))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_stage_all_complete(self, success: bool, staged: bool):
        if success:
            self.refresh_git_status()
            if self.current_view == "Diff":
                self._refresh_diff_view()
            if staged:
                self.status_label.configure(text="✓ All changes staged", text_color=self.COLOR_SUCCESS[1])
            else:
                self.status_label.configure(text="✓ All changes unstaged", text_color=self.COLOR_TEXT_MUTED)
        else:
            self.status_label.configure(text="❌ Staging action failed", text_color=self.COLOR_DANGER[1])
            messagebox.showerror("Error", f"Failed to {'stage' if staged else 'unstage'} changes.")

    # -------------------------------------------------------------------------
    # AI Generation (Threaded Async)
    # -------------------------------------------------------------------------
    def generate_commit_message_async(self):
        if self.generate_button.cget("state") == "disabled":
            return

        project = (self.project_entry.get() or "").strip() or self.project_path
        if not project:
            messagebox.showwarning("Project Required", "Please select a project folder.")
            return

        auto_stage = self.auto_stage_var.get()
        summary = self._latest_status_summary
        if not auto_stage and summary and summary.get("is_repo"):
            staged_count = len(summary.get("staged_files", []))
            pending_count = len(summary.get("unstaged_files", [])) + len(summary.get("untracked_files", []))
            if staged_count == 0 and pending_count > 0:
                if not messagebox.askyesno(
                    "No Staged Changes",
                    f"No files are staged, but {pending_count} change(s) exist.\n"
                    "Stage all changes and generate commit message?",
                ):
                    return
                auto_stage = True

        selected_model = (self.model_dropdown.get() or "").strip() or None
        self.status_label.configure(text="⏳ Analyzing diff & generating...", text_color="#3B82F6")
        self.generate_button.configure(state="disabled", text="✨ Generating...")

        def _worker():
            success, result = CommitService.generate_commit_options(
                project, selected_model, auto_stage=auto_stage
            )
            self._post_ui(lambda: self._on_generation_complete(success, result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_generation_complete(self, success: bool, result):
        self.generate_button.configure(state="normal", text="✨ Generate AI Commit")

        if not success:
            self.status_label.configure(text="❌ Generation failed", text_color=self.COLOR_DANGER[1])
            messagebox.showwarning("Generation Warning", str(result))
            return

        if isinstance(result, list) and result:
            self.generated_options = result
            self.selected_option_idx = 0
            self.commit_text.delete("1.0", "end")
            self.commit_text.insert("1.0", result[0])
            self._render_option_pills()
            self._on_text_change()
        elif isinstance(result, str):
            self.generated_options = [result]
            self.selected_option_idx = 0
            self.commit_text.delete("1.0", "end")
            self.commit_text.insert("1.0", result)
            self._render_option_pills()
            self._on_text_change()

        self.refresh_git_status()
        if self.current_view == "Diff":
            self._refresh_diff_view()
        self.status_label.configure(text="✓ Commit message generated", text_color=self.COLOR_SUCCESS[1])

    # -------------------------------------------------------------------------
    # Commit Execution
    # -------------------------------------------------------------------------
    def create_commit(self):
        if self.create_button.cget("state") == "disabled":
            return

        project = (self.project_entry.get() or "").strip() or self.project_path
        message = self.commit_text.get("1.0", "end-1c").strip()

        if not project:
            messagebox.showwarning("Project Required", "Please select a project folder.")
            return

        if not message:
            messagebox.showwarning("Commit Required", "Generate or enter a commit message first.")
            return

        status_code, commit_datetime = self.get_commit_datetime()
        if status_code != 200:
            return

        self.status_label.configure(text="⏳ Creating commit...", text_color="#3B82F6")
        self.create_button.configure(state="disabled")

        def _worker():
            success, details = GitService.commit_with_message_detailed(
                message, project, commit_datetime
            )
            self._post_ui(lambda: self._on_commit_complete(success, details))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_commit_complete(self, success: bool, details: str):
        self.create_button.configure(state="normal")
        if success:
            self.commit_text.delete("1.0", "end")
            self.generated_options = []
            self._render_option_pills()
            self._on_text_change()
            self.refresh_git_status()
            if self.current_view == "Diff":
                self._refresh_diff_view()

            self.status_label.configure(
                text="✓ Commit created successfully!",
                text_color=self.COLOR_SUCCESS[1],
            )

            if self.auto_push_var.get():
                self.push_commits_async()
        else:
            self.status_label.configure(text="❌ Commit failed", text_color=self.COLOR_DANGER[1])
            messagebox.showerror(
                "Commit Failed",
                f"Failed to create commit:\n\n{details}",
            )

    # -------------------------------------------------------------------------
    # Pull Execution
    # -------------------------------------------------------------------------
    def pull_commits_async(self):
        project = (self.project_entry.get() or "").strip() or self.project_path
        if not project:
            messagebox.showwarning("Project Required", "Please select a project folder.")
            return

        self.status_label.configure(text="⏳ Pulling latest changes from remote...", text_color=self.COLOR_TEAL[1])
        self.pull_button.configure(state="disabled", text="⏳ Pulling...")
        self.top_pull_btn.configure(state="disabled")

        def _worker():
            success, msg = GitService.pull_commits(project)
            self._post_ui(lambda: self._on_pull_complete(success, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_pull_complete(self, success: bool, msg: str):
        self.pull_button.configure(state="normal", text="📥 Pull")
        self.top_pull_btn.configure(state="normal")
        self.refresh_git_status()
        if self.current_view == "Diff":
            self._refresh_diff_view()

        if success:
            short_msg = msg.splitlines()[0][:80] if msg else "Already up to date."
            self.status_label.configure(
                text=f"✓ Pull complete: {short_msg}",
                text_color=self.COLOR_SUCCESS[1],
            )
        else:
            self.status_label.configure(text="❌ Pull failed", text_color=self.COLOR_DANGER[1])
            messagebox.showerror("Pull Failed", f"Failed to pull from remote:\n\n{msg}")

    # -------------------------------------------------------------------------
    # Push Execution
    # -------------------------------------------------------------------------
    def push_commits_async(self):
        project = (self.project_entry.get() or "").strip() or self.project_path
        if not project:
            messagebox.showwarning("Project Required", "Please select a project folder.")
            return

        self.status_label.configure(text="⏳ Pushing commits to remote...", text_color=self.COLOR_PURPLE[1])
        self.push_button.configure(state="disabled", text="🚀 Pushing...")
        self.top_push_btn.configure(state="disabled")

        def _worker():
            success, msg = GitService.push_commits(project)
            self._post_ui(lambda: self._on_push_complete(success, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_push_complete(self, success: bool, msg: str):
        self.push_button.configure(state="normal", text="🚀 Push")
        self.top_push_btn.configure(state="normal")
        self.refresh_git_status()
        if self.current_view == "Diff":
            self._refresh_diff_view()

        if success:
            self.status_label.configure(
                text="✓ Pushed to remote successfully!",
                text_color=self.COLOR_SUCCESS[1],
            )
        else:
            self.status_label.configure(text="❌ Push failed", text_color=self.COLOR_DANGER[1])
            messagebox.showerror("Push Failed", f"Failed to push commits to remote:\n\n{msg}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
