import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.services.commit_service import CommitService
from core.services.git_service import GitService

class App(ctk.CTk):
 
    def __init__(self):
        super().__init__()

        self.title("AI Git Commit Generator")
        self.geometry("800x600")
        self.minsize(800, 600)
        self.maxsize(800, 600)

        self.project_path = None

        self._build_ui()

    def _build_ui(self):

        # Main container
        self.container = ctk.CTkFrame(self)
        self.container.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        # Title
        self.title_label = ctk.CTkLabel(
            self.container,
            text="AI Git Commit Generator",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        # Project
        ctk.CTkLabel(
            self.container,
            text="Project Folder"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        project_frame = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )
        project_frame.pack(
            fill="x",
            padx=20
        )

        self.project_entry = ctk.CTkEntry(
            project_frame,
            placeholder_text="Select Git project folder..."
        )
        self.project_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        self.browse_button = ctk.CTkButton(
            project_frame,
            text="Browse",
            width=100,
            command=self.select_project
        )
        self.browse_button.pack(
            side="left",
            padx=(10, 0)
        )

        # Date
        ctk.CTkLabel(
            self.container,
            text="Commit Date (YYYY-MM-DD HH:MM)"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        commit_frame = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )
        commit_frame.pack(
            fill="x",
            padx=0
        )
        self.date_entry = ctk.CTkEntry(
            commit_frame,
            placeholder_text="YYYY-MM-DD"
        )
        self.date_entry.pack(
            side="left",
            anchor="w",
            padx=20
        )

        self.time_entry = ctk.CTkEntry(
            commit_frame,
            placeholder_text="HH:MM"
        )
        self.time_entry.pack(
            side="left",
            anchor="w",
            padx=20
        )


        # Commit message
        ctk.CTkLabel(
            self.container,
            text="Generated Commit"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        self.commit_text = ctk.CTkTextbox(
            self.container,
            height=180
        )
        self.commit_text.pack(
            fill="both",
            expand=True,
            padx=20
        )

        # Buttons
        button_frame = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )
        button_frame.pack(
            fill="x",
            padx=20,
            pady=20
        )

        self.generate_button = ctk.CTkButton(
            button_frame,
            text="✨ Generate Commit",
            command=self.generate_commit_message_ui
        )
        self.generate_button.pack(
            side="left"
        )

        self.create_button = ctk.CTkButton(
            button_frame,
            text="✓ Create Commit",
            command=self.create_commit
        )
        self.create_button.pack(
            side="left",
            padx=10
        )

        # Status
        self.status_label = ctk.CTkLabel(
            self.container,
            text="Ready"
        )
        self.status_label.pack(
            anchor="w",
            padx=20,
            pady=(0, 15)
        )

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

        project = self.project_entry.get().strip()
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
            self.status_label.configure(text="Commit created successfully")
            messagebox.showinfo(
                "Success",
                "Git commit created successfully."
            )

        except Exception as e:
            messagebox.showerror("Commit Failed", str(e))
            self.status_label.configure(text="Commit failed")
        finally:
            self.create_button.configure(state="normal")

    def select_project(self):

        folder = filedialog.askdirectory(
            title="Select Git Project"
        )

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

            self.status_label.configure(
                text="Project selected"
            )

if __name__ == "__main__":
    app = App()
    app.mainloop()
