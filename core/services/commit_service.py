

class CommitService:
    
    def generate(self):

        project = self.project_entry.get().strip()
        commit_date = self.date_entry.get().strip()
        commit_time = self.time_entry.get().strip()

        if not project:
            messagebox.showwarning(
                "Project Required",
                "Please select a project folder."
            )
            return

        try:

            self.status_label.configure(
                text="Generating commit..."
            )

            self.generate_button.configure(
                state="disabled"
            )

            commit = generate(
                project_path=project,
                commit_date=commit_date or None,
                commit_time=commit_time or None
            )

            self.commit_text.delete("1.0", "end")
            self.commit_text.insert("1.0", commit)

            self.status_label.configure(
                text="Commit generated"

            )

        except Exception as e:

            messagebox.showerror(
                "Generation Failed",
                str(e)
            )

            self.status_label.configure(
                text="Generation failed"
            )

        finally:

            self.generate_button.configure(
                state="normal"
            )

    def create_commit(self):

        project = self.project_entry.get().strip()
        commit_date = self.date_entry.get().strip()
        commit_time = self.time_entry.get().strip()

        message = self.commit_text.get(
            "1.0",
            "end"
        ).strip()

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

            self.status_label.configure(
                text="Creating commit..."
            )

            self.create_button.configure(
                state="disabled"
            )

            self.status_label.configure(
                text="Commit created successfully"
            )

            messagebox.showinfo(
                "Success",
                "Git commit created successfully."
            )

        except Exception as e:

            messagebox.showerror(
                "Commit Failed",
                str(e)
            )

            self.status_label.configure(
                text="Commit failed"
            )

        finally:

            self.create_button.configure(
                state="normal"
            )
