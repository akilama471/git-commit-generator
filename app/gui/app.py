import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime, timezone, timedelta

from core.config.config_manager import ConfigManager
from core.services.commit_service import CommitService
from core.services.git_service import GitService


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("AI Git Commit Generator")
        self.geometry("960x640")
        self.minsize(900, 600)
        self.maxsize(1200, 900)

        self.project_path = None
        self.current_view = "Commits"

        self._build_ui()

    def _build_ui(self):
        self.root_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.root_frame.pack(fill="both", expand=True, padx=18, pady=18)

        self.sidebar = ctk.CTkFrame(self.root_frame, width=180, corner_radius=14)
        self.sidebar.pack(side="left", fill="y", padx=(0, 16))

        self.nav_label = ctk.CTkLabel(
            self.sidebar,
            text="Navigation",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.nav_label.pack(anchor="w", padx=16, pady=(18, 12))

        self.nav_buttons = {}
        for nav_name in ["Commits", "Config"]:
            button = ctk.CTkButton(
                self.sidebar,
                text=nav_name,
                height=38,
                corner_radius=10,
                command=lambda name=nav_name: self.show_view(name),
            )
            button.pack(fill="x", padx=12, pady=(0, 10))
            self.nav_buttons[nav_name] = button

        self.content_area = ctk.CTkFrame(self.root_frame, fg_color="transparent")
        self.content_area.pack(side="left", fill="both", expand=True)

        self.commits_view = self._build_commits_view()
        self.config_view = self._build_config_view()

        self.show_view("Commits")

    def _build_commits_view(self):
        frame = ctk.CTkFrame(self.content_area, corner_radius=14)

        self.title_label = ctk.CTkLabel(
            frame,
            text="AI Git Commit Generator",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(anchor="w", padx=20, pady=(20, 5))

        ctk.CTkLabel(frame, text="Project Folder").pack(anchor="w", padx=20, pady=(20, 5))

        project_frame = ctk.CTkFrame(frame, fg_color="transparent")
        project_frame.pack(fill="x", padx=20)

        self.project_entry = ctk.CTkEntry(
            project_frame,
            placeholder_text="Select Git project folder..."
        )
        self.project_entry.pack(side="left", fill="x", expand=True)

        self.browse_button = ctk.CTkButton(
            project_frame,
            text="Browse",
            width=100,
            command=self.select_project
        )
        self.browse_button.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(frame, text="Commit Date (YYYY-MM-DD HH:MM)").pack(anchor="w", padx=20, pady=(20, 5))

        commit_frame = ctk.CTkFrame(frame, fg_color="transparent")
        commit_frame.pack(fill="x", padx=0)

        self.date_entry = ctk.CTkEntry(commit_frame, placeholder_text="YYYY-MM-DD")
        self.date_entry.pack(side="left", anchor="w", padx=20)

        self.time_entry = ctk.CTkEntry(commit_frame, placeholder_text="HH:MM")
        self.time_entry.pack(side="left", anchor="w", padx=20)

        ctk.CTkLabel(frame, text="Generated Commit").pack(anchor="w", padx=20, pady=(20, 5))

        self.commit_text = ctk.CTkTextbox(frame, height=180)
        self.commit_text.pack(fill="both", expand=True, padx=20)

        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=20)

        self.generate_button = ctk.CTkButton(
            button_frame,
            text="✨ Generate Commit",
            command=self.generate_commit_message_ui
        )
        self.generate_button.pack(side="left")

        self.create_button = ctk.CTkButton(
            button_frame,
            text="✓ Create Commit",
            command=self.create_commit
        )
        self.create_button.pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(frame, text="Ready")
        self.status_label.pack(anchor="w", padx=20, pady=(0, 15))

        return frame

    def _build_config_view(self):
        frame = ctk.CTkFrame(self.content_area, corner_radius=14)

        ctk.CTkLabel(
            frame,
            text="Configuration",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        ctk.CTkLabel(frame, text="API Key").pack(anchor="w", padx=20, pady=(20, 5))
        self.api_key_entry = ctk.CTkEntry(frame, width=500, placeholder_text="your-api-key-here")
        self.api_key_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(frame, text="Model").pack(anchor="w", padx=20, pady=(20, 5))
        self.model_entry = ctk.CTkEntry(frame, width=500, placeholder_text="gemini-2.0-flash-lite")
        self.model_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(frame, text="GitHub Token").pack(anchor="w", padx=20, pady=(20, 5))
        self.github_token_entry = ctk.CTkEntry(frame, width=500, placeholder_text="optional")
        self.github_token_entry.pack(fill="x", padx=20)

        self.config_save_button = ctk.CTkButton(frame, text="Save Config", command=self.save_config)
        self.config_save_button.pack(anchor="w", padx=20, pady=(24, 10))

        self.config_status_label = ctk.CTkLabel(frame, text="Ready")
        self.config_status_label.pack(anchor="w", padx=20, pady=(0, 10))

        self._load_config_values()
        return frame

    def show_view(self, view_name):
        self.current_view = view_name

        for name, button in self.nav_buttons.items():
            if name == view_name:
                button.configure(fg_color=("#3B8ED0", "#1F6AA5"), hover_color=("#3B8ED0", "#1F6AA5"))
            else:
                button.configure(fg_color="transparent", hover_color=("#3B8ED0", "#1F6AA5"))

        self.commits_view.pack_forget()
        self.config_view.pack_forget()

        if view_name == "Commits":
            self.commits_view.pack(fill="both", expand=True)
        elif view_name == "Config":
            self.config_view.pack(fill="both", expand=True)

    def _load_config_values(self):
        try:
            config = ConfigManager._load_config()
        except Exception:
            config = {}

        self.api_key_entry.delete(0, "end")
        self.model_entry.delete(0, "end")
        self.github_token_entry.delete(0, "end")

        self.api_key_entry.insert(0, config.get("api_key", ""))
        self.model_entry.insert(0, config.get("model", "gemini-2.0-flash-lite"))
        self.github_token_entry.insert(0, config.get("github_token", ""))

    def save_config(self):
        api_key = self.api_key_entry.get().strip()
        model = self.model_entry.get().strip()
        github_token = self.github_token_entry.get().strip()

        if not api_key:
            messagebox.showwarning("API Key Required", "Please enter an API key before saving.")
            return

        try:
            ConfigManager.save_api_key(api_key)
            ConfigManager.save_model(model or "gemini-2.0-flash-lite")
            ConfigManager.save_github_token(github_token)
            self.config_status_label.configure(text="Configuration saved")
            messagebox.showinfo("Config Saved", "Settings saved successfully.")
        except Exception as exc:
            self.config_status_label.configure(text="Save failed")
            messagebox.showerror("Config Save Failed", str(exc))

    def generate_commit_message_ui(self):
        project = (self.project_entry.get() or "").strip() or self.project_path
        if not project:
            messagebox.showwarning(
                "Project Required",
                "Please select a project folder."
            )
            return

        try:
            self.status_label.configure(text="Generating commit...")
            self.generate_button.configure(state="disabled")

            result = CommitService.generate_commit_message(project, None)
            if isinstance(result, str) and (result.startswith("No staged") or result.startswith("Failed") or result.startswith("Please select")):
                messagebox.showwarning("Generation warning", result)
                self.status_label.configure(text="No commit generated")
                return

            self.commit_text.delete("1.0", "end")
            self.commit_text.insert("1.0", result)
            self.status_label.configure(text="Commit generated")
        except Exception as e:
            messagebox.showerror("Generation Failed", str(e))
            self.status_label.configure(text="Generation failed")
        finally:
            self.generate_button.configure(state="normal")

    def create_commit(self):

        project = (self.project_entry.get() or "").strip() or self.project_path
        message = self.commit_text.get("1.0", "end").strip()

        if not project:
            messagebox.showwarning(
                "Project Required",
                "Please select a project folder."
            )
            return

        if not message:
            messagebox.showwarning(
                "Commit Required",
                "Generate or enter a commit message first."
            )
            return

        try:
            self.status_label.configure(text="Creating commit...")
            self.create_button.configure(state="disabled")

            # date_entry & time_entry
            status_code, commit_datetime = self.get_commit_datetime()

            if status_code != 200:
                return

            status = GitService.commit_with_message(message, project, commit_datetime)

            if status is False:
                messagebox.showerror(
                    "Commit Failed",
                    "Failed to create the commit. Please check the project folder and try again."
                )
                self.status_label.configure(text="Commit failed")
                return
            
            self.status_label.configure(text="Commit created successfully")
            messagebox.showinfo(
                "Success",
                "Git commit created successfully."
            )
            self.commit_text.delete("1.0", "end")

        except Exception as e:
            messagebox.showerror("Commit Failed", str(e))
            self.status_label.configure(text="Commit failed")
        finally:
            self.create_button.configure(state="normal")

    def select_project(self):
        folder = filedialog.askdirectory(title="Select Git Project")

        if folder:
            repo_root = GitService.get_repository_root(folder)
            if not repo_root:
                messagebox.showwarning(
                    "Project Required",
                    "A .git repository cannot be found in this folder. Please select a valid Git project folder."
                )
                return

            self.project_path = repo_root

            self.project_entry.delete(0, "end")
            self.project_entry.insert(0, repo_root)

            self.status_label.configure(text="Project selected")

    def get_commit_datetime(self):
        date_value = self.date_entry.get().strip()

        # Both empty -> skip
        if not date_value:
            return 200, None

        # Validate date + time
        try:
            dt = datetime.strptime(
                f"{date_value}",
                "%Y-%m-%d"
            )
        except ValueError:
            messagebox.showerror(
                "Invalid Date",
                "Please enter a valid date.\n\n"
                "Date format: YYYY-MM-DD\n\n"
                "Example:\n"
                "2026-06-13"
            )
            return 400, None

        # Automatically use the computer's local timezone
        local_timezone = datetime.now().astimezone().tzinfo

        # Automatically set time to 01:00 AM
        dt = dt.replace(
            hour=1,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=local_timezone
        )

        # Result: 2026-06-13 18:30:00 +0530
        return 200, dt.strftime("%Y-%m-%d %H:%M:%S %z")

if __name__ == "__main__":
    app = App()
    app.mainloop()
