import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import List, Optional

import customtkinter as ctk

from core.config.config_manager import ConfigManager
from core.services.commit_service import CommitService
from core.services.git_service import GitService

# Appearance & Theme Configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """Modern, clean, and compact AI Git Commit Generator GUI."""

    FONT_FAMILY = "Segoe UI"
    MONO_FONT = "Consolas"

    COLOR_PRIMARY = ("#2563EB", "#3B82F6")
    COLOR_PRIMARY_HOVER = ("#1D4ED8", "#60A5FA")
    COLOR_SUCCESS = ("#059669", "#10B981")
    COLOR_SUCCESS_HOVER = ("#047857", "#34D399")
    COLOR_DANGER = ("#DC2626", "#EF4444")
    COLOR_CARD_BG = ("#F3F4F6", "#1E2026")
    COLOR_INNER_BG = ("#E5E7EB", "#181A1F")
    COLOR_BORDER = ("#D1D5DB", "#2D3139")
    COLOR_TEXT_MUTED = ("#6B7280", "#9CA3AF")

    def __init__(self):
        super().__init__()

        self.title("AI Git Commit Generator")
        self.geometry("940x630")
        self.minsize(860, 540)

        self.project_path: Optional[str] = None
        self.current_view: str = "Generator"
        self.generated_options: List[str] = []
        self.selected_option_idx: int = 0
        self.show_api_key: bool = False
        self.show_github_token: bool = False

        # Load initial config
        self._load_config_cache()

        # Build UI layout
        self._build_ui()

        # Auto-detect git repo from current working directory if available
        self.after(100, self._auto_detect_current_directory)

    def _load_config_cache(self):
        try:
            self.config_data = ConfigManager._load_config()
        except Exception:
            self.config_data = {}

    def _auto_detect_current_directory(self):
        cwd = GitService.get_current_directory()
        repo_root = GitService.get_repository_root(cwd)
        if repo_root:
            self._set_project(repo_root)

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
            width=200,
            corner_radius=0,
            fg_color=("gray92", "#131519"),
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)  # spacer

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
            text="v1.2 • AI Generator",
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

        # Bottom section in sidebar
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.grid(row=6, column=0, sticky="sew", padx=12, pady=14)

        # Active Model Pill Badge
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
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.model_status_badge.pack(padx=8, pady=4, fill="x")

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
            "Settings": self._build_settings_view(),
        }

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
            placeholder_text="Select a Git repository folder...",
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
        )
        self.project_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=(10, 4))

        actions_frame = ctk.CTkFrame(repo_card, fg_color="transparent")
        actions_frame.grid(row=0, column=2, padx=(0, 10), pady=(10, 4), sticky="e")

        self.browse_btn = ctk.CTkButton(
            actions_frame,
            text="Browse",
            width=70,
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self.select_project,
        )
        self.browse_btn.pack(side="left", padx=2)

        self.stage_all_btn = ctk.CTkButton(
            actions_frame,
            text="+ Stage All",
            width=80,
            height=30,
            corner_radius=6,
            fg_color=("gray75", "#2C313C"),
            hover_color=("gray65", "#3A4150"),
            text_color=("gray10", "gray95"),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self.stage_all_changes_ui,
        )
        self.stage_all_btn.pack(side="left", padx=2)

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

        self.branch_badge = self._create_badge(self.badge_strip, "🌿 Branch: None", "#3B82F6")
        self.branch_badge.pack(side="left", padx=(0, 6))

        self.staged_badge = self._create_badge(self.badge_strip, "● 0 staged", "#6B7280")
        self.staged_badge.pack(side="left", padx=(0, 6))

        self.unstaged_badge = self._create_badge(self.badge_strip, "● 0 modified", "#6B7280")
        self.unstaged_badge.pack(side="left", padx=(0, 6))

        self.repo_name_label = ctk.CTkLabel(
            self.badge_strip,
            text="",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            text_color=self.COLOR_TEXT_MUTED,
        )
        self.repo_name_label.pack(side="right")

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
        action_inner.pack(fill="x", padx=12, pady=8)

        self.generate_button = ctk.CTkButton(
            action_inner,
            text="✨ Generate AI Commit",
            height=34,
            width=170,
            corner_radius=8,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
            fg_color=self.COLOR_PRIMARY,
            hover_color=self.COLOR_PRIMARY_HOVER,
            command=self.generate_commit_message_async,
        )
        self.generate_button.pack(side="left", padx=(0, 8))

        self.create_button = ctk.CTkButton(
            action_inner,
            text="✓ Commit to Git",
            height=34,
            width=140,
            corner_radius=8,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=12, weight="bold"),
            fg_color=self.COLOR_SUCCESS,
            hover_color=self.COLOR_SUCCESS_HOVER,
            command=self.create_commit,
        )
        self.create_button.pack(side="left", padx=(0, 10))

        # Real-time Status Indicator Label
        self.status_label = ctk.CTkLabel(
            action_inner,
            text="● Ready",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        return view

    def _create_badge(self, parent, text: str, color_hex: str) -> ctk.CTkFrame:
        badge = ctk.CTkFrame(
            parent,
            fg_color=self.COLOR_INNER_BG,
            corner_radius=5,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        lbl = ctk.CTkLabel(
            badge,
            text=text,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10, weight="bold"),
            text_color=color_hex,
        )
        lbl.pack(padx=6, pady=2)
        badge.label = lbl
        return badge

    def _set_badge_text(self, badge: ctk.CTkFrame, text: str, color_hex: Optional[str] = None):
        badge.label.configure(text=text)
        if color_hex:
            badge.label.configure(text_color=color_hex)

    # -------------------------------------------------------------------------
    # 2. Changes & Diff View (Dedicated Tab)
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
            text="📁 Staged & Working Changes",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=13, weight="bold"),
        ).pack(side="left")

        diff_actions = ctk.CTkFrame(diff_header_inner, fg_color="transparent")
        diff_actions.pack(side="right")

        ctk.CTkButton(
            diff_actions,
            text="+ Stage All",
            width=80,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
            command=self.stage_all_changes_ui,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            diff_actions,
            text="- Unstage All",
            width=90,
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

        # Main Diff Content Area
        diff_card = ctk.CTkFrame(
            view,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        diff_card.grid(row=1, column=0, sticky="nsew")
        diff_card.grid_rowconfigure(0, weight=1)
        diff_card.grid_columnconfigure(0, weight=1)

        self.diff_textbox = ctk.CTkTextbox(
            diff_card,
            corner_radius=6,
            font=ctk.CTkFont(family=self.MONO_FONT, size=11),
            wrap="none",
        )
        self.diff_textbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.diff_textbox.insert("1.0", "Select a repository to view Git diff and staged changes.")

        return view

    def _refresh_diff_view(self):
        if not self.project_path:
            self.diff_textbox.delete("1.0", "end")
            self.diff_textbox.insert("1.0", "No Git repository selected.")
            return

        git_diff = GitService.get_staged_diff(self.project_path)
        status_summary = GitService.get_repo_status_summary(self.project_path)

        lines = []
        lines.append(f"# Repository: {Path(self.project_path).name}")
        lines.append(f"# Active Branch: {status_summary.get('branch', 'unknown')}\n")

        lines.append("## Staged Files (will be analyzed for commit):")
        staged = status_summary.get("staged_files", [])
        if staged:
            for s in staged:
                lines.append(f"  [{s['status']}] {s['file']}")
        else:
            lines.append("  (No staged files - click '+ Stage All' or run 'git add')")

        lines.append("\n## Unstaged Changes:")
        unstaged = status_summary.get("unstaged_files", [])
        if unstaged:
            for u in unstaged:
                lines.append(f"  [{u['status']}] {u['file']}")
        else:
            lines.append("  (None)")

        lines.append("\n" + "=" * 60 + "\n## Staged Diff Preview:\n" + "=" * 60 + "\n")
        if git_diff and git_diff.diff:
            lines.append(git_diff.diff)
        else:
            lines.append("No staged diff content available.")

        self.diff_textbox.delete("1.0", "end")
        self.diff_textbox.insert("1.0", "\n".join(lines))

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

        self.model_options = [
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
        self.model_dropdown = ctk.CTkOptionMenu(
            model_frame,
            values=self.model_options,
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=11),
        )
        self.model_dropdown.pack(side="left", fill="x", expand=True)

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
        if model in self.model_options:
            self.model_dropdown.set(model)
        else:
            self.model_dropdown.set("gemini-2.0-flash-lite")

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
            repo_root = GitService.get_repository_root(folder)
            if not repo_root:
                messagebox.showwarning(
                    "Invalid Repository",
                    "No .git repository found in the selected folder.\nPlease select a valid Git repository.",
                )
                return
            self._set_project(repo_root)

    def _set_project(self, repo_root: str):
        self.project_path = repo_root
        self.project_entry.delete(0, "end")
        self.project_entry.insert(0, repo_root)
        self.repo_name_label.configure(text=Path(repo_root).name)
        self.refresh_git_status()

    def refresh_git_status(self):
        path = (self.project_entry.get() or "").strip() or self.project_path
        if not path:
            return

        summary = GitService.get_repo_status_summary(path)
        if not summary.get("is_repo"):
            self._set_badge_text(self.branch_badge, "🌿 None", "#EF4444")
            self._set_badge_text(self.staged_badge, "● 0 staged", "#6B7280")
            self._set_badge_text(self.unstaged_badge, "● 0 modified", "#6B7280")
            return

        branch = summary.get("branch", "unknown")
        staged_count = len(summary.get("staged_files", []))
        unstaged_count = len(summary.get("unstaged_files", []))

        self._set_badge_text(self.branch_badge, f"🌿 {branch}", "#3B82F6")
        self._set_badge_text(
            self.staged_badge,
            f"● {staged_count} staged",
            self.COLOR_SUCCESS[1] if staged_count > 0 else "#6B7280",
        )
        self._set_badge_text(
            self.unstaged_badge,
            f"● {unstaged_count} modified",
            "#F59E0B" if unstaged_count > 0 else "#6B7280",
        )

        self.status_label.configure(
            text=f"● Ready • {staged_count} file(s) staged for commit",
            text_color=self.COLOR_SUCCESS[1] if staged_count > 0 else self.COLOR_TEXT_MUTED,
        )

    def stage_all_changes_ui(self):
        path = (self.project_entry.get() or "").strip() or self.project_path
        if not path:
            messagebox.showwarning("Project Required", "Please select a project folder first.")
            return

        success = GitService.stage_all_changes(path)
        if success:
            self.refresh_git_status()
            if self.current_view == "Diff":
                self._refresh_diff_view()
            self.status_label.configure(text="✓ All changes staged", text_color=self.COLOR_SUCCESS[1])
        else:
            messagebox.showerror("Error", "Failed to stage changes.")

    def unstage_all_changes_ui(self):
        path = (self.project_entry.get() or "").strip() or self.project_path
        if not path:
            return

        success = GitService.unstage_all_changes(path)
        if success:
            self.refresh_git_status()
            if self.current_view == "Diff":
                self._refresh_diff_view()
            self.status_label.configure(text="✓ All changes unstaged", text_color=self.COLOR_TEXT_MUTED)

    # -------------------------------------------------------------------------
    # AI Generation (Threaded Async)
    # -------------------------------------------------------------------------
    def generate_commit_message_async(self):
        project = (self.project_entry.get() or "").strip() or self.project_path
        if not project:
            messagebox.showwarning("Project Required", "Please select a project folder.")
            return

        self.status_label.configure(text="⏳ Analyzing diff & generating...", text_color="#3B82F6")
        self.generate_button.configure(state="disabled", text="✨ Generating...")

        def _worker():
            success, result = CommitService.generate_commit_options(project, None)
            self.after(0, lambda: self._on_generation_complete(success, result))

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
            self.status_label.configure(
                text="✓ Commit generated",
                text_color=self.COLOR_SUCCESS[1],
            )
        elif isinstance(result, str):
            self.generated_options = [result]
            self.selected_option_idx = 0
            self.commit_text.delete("1.0", "end")
            self.commit_text.insert("1.0", result)
            self._render_option_pills()
            self._on_text_change()
            self.status_label.configure(text="✓ Commit generated", text_color=self.COLOR_SUCCESS[1])

    # -------------------------------------------------------------------------
    # Commit Execution
    # -------------------------------------------------------------------------
    def create_commit(self):
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
            success = GitService.commit_with_message(message, project, commit_datetime)
            self.after(0, lambda: self._on_commit_complete(success))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_commit_complete(self, success: bool):
        self.create_button.configure(state="normal")
        if success:
            self.status_label.configure(
                text="✓ Commit created successfully!",
                text_color=self.COLOR_SUCCESS[1],
            )
            messagebox.showinfo("Success", "Git commit created successfully.")
            self.commit_text.delete("1.0", "end")
            self.generated_options = []
            self._render_option_pills()
            self._on_text_change()
            self.refresh_git_status()
            if self.current_view == "Diff":
                self._refresh_diff_view()
        else:
            self.status_label.configure(text="❌ Commit failed", text_color=self.COLOR_DANGER[1])
            messagebox.showerror(
                "Commit Failed",
                "Failed to create the commit. Please ensure there are staged changes and try again.",
            )


if __name__ == "__main__":
    app = App()
    app.mainloop()
