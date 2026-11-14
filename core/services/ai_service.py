import json
from typing import List, Optional, Tuple, Union

import requests


DEFAULT_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash",
]


class GeminiClient:
    _session = requests.Session()

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-lite",
        max_diff_len: int = 5000,
        temperature: float = 0.7,
        timeout: int = 25,
    ):
        self.api_key = (api_key or "").strip()
        self.model = model
        self.max_diff_len = max_diff_len
        self.temperature = temperature
        self.timeout = timeout
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    def _call_generate_content(
        self,
        prompt: str,
        system_instruction: str,
        max_output_tokens: int = 600,
        timeout: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Execute a Gemini generateContent call with connection pooling and timeout."""
        if not self.api_key or self.api_key == "your-api-key-here":
            return False, "Gemini API key is not configured."

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [
                {
                    "parts": [{"text": prompt}],
                    "role": "user",
                }
            ],
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": max_output_tokens,
                "topP": 0.95,
                "topK": 40,
            },
        }

        try:
            response = self._session.post(
                url,
                headers=headers,
                json=data,
                timeout=timeout or self.timeout,
            )

            if response.status_code != 200:
                err_msg = f"API Error (HTTP {response.status_code})"
                try:
                    err_json = response.json()
                    if isinstance(err_json, dict) and "error" in err_json:
                        err_msg = f"API Error ({response.status_code}): {err_json['error'].get('message', response.text)}"
                except Exception:
                    if response.text:
                        err_msg = f"API Error ({response.status_code}): {response.text[:300]}"
                return False, err_msg

            result = response.json()
            if "error" in result:
                return False, f"API Error: {result['error'].get('message', 'Unknown error')}"

            content = None
            candidates = result.get("candidates") or []
            if candidates:
                parts = (candidates[0].get("content") or {}).get("parts") or []
                if parts and "text" in parts[0]:
                    content = parts[0]["text"]

            if not content:
                return False, "No content returned by Gemini API."

            cleaned = self._strip_code_fences(content)
            if not cleaned:
                return False, "Generated response was empty."

            return True, cleaned

        except requests.exceptions.Timeout:
            return False, f"Request timed out after {timeout or self.timeout}s. Check your internet connection or try a faster model."
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {e}"
        except json.JSONDecodeError:
            return False, "Invalid JSON response from Gemini API."
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def generate_commit_messages_safe(
        self, diff: str, files: Optional[List[str]] = None
    ) -> Tuple[bool, Union[List[str], str]]:
        """Generate a conventional commit message, returning (success, [message] | error_message)."""
        if len(diff) > self.max_diff_len:
            diff = diff[: self.max_diff_len] + "\n... (truncated)"

        files_section = ""
        if files:
            listed = "\n".join(f"- {f}" for f in files[:40])
            if len(files) > 40:
                listed += f"\n- ... and {len(files) - 40} more files"
            files_section = f"\nCHANGED FILES ({len(files)}):\n{listed}\n"

        prompt = f"""You are an expert software developer and Git specialist.
Analyze the following staged files and git diff, and generate a single, high-quality, professional Git commit message following the Conventional Commits specification.
{files_section}
GIT DIFF:
```diff
{diff}
```

CONVENTIONAL COMMITS SPECIFICATION:
1. Format: <type>(<optional-scope>): <description>
2. Types:
   - feat: A new feature or capability
   - fix: A bug fix
   - refactor: Code refactoring without changing functionality or fixing bugs
   - perf: Code change that improves performance
   - docs: Documentation changes only
   - style: Formatting, missing semicolons, whitespace (no logic changes)
   - test: Adding or updating test cases
   - build: Changes affecting build systems, dependencies, or packaging
   - ci: CI/CD configuration files and automation scripts
   - chore: Maintenance, tooling, or housekeeping tasks
3. Scope: Specify the affected module or component in parentheses if appropriate (e.g., auth, ui, core, config, api, git).
4. Subject line rules:
   - Maximum 72 characters (aim for 50-60 characters for crisp readability).
   - Use lowercase for the type and description.
   - Use imperative present mood ("add feature", "fix bug", NOT "added", "fixes", "fixing").
   - Do NOT end the subject line with a period.
5. Body rules (include only when changes are non-trivial or multi-part):
   - Leave exactly ONE blank line after the subject line.
   - Use concise bullet points starting with `- ` explaining WHAT changed and WHY (not how).
   - Wrap body lines at 72 characters.

CRITICAL OUTPUT CONSTRAINTS:
- Output ONLY the single commit message.
- Do NOT include markdown code blocks (no ```).
- Do NOT include introductory greetings, explanations, alternative options, or closing text.
"""
        system_instruction = (
            "You are an expert Git commit assistant. You generate concise, accurate, and professional "
            "conventional git commit messages based on diffs. You output strictly the single raw commit "
            "message with no conversational text or markdown code fences."
        )

        success, result = self._call_generate_content(prompt, system_instruction, max_output_tokens=600)
        if not success:
            return False, result
        return True, [result]

    def generate_commit_messages(self, diff: str, files: Optional[List[str]] = None) -> List[str]:
        """Generate commit message list; returns [] on error (logging error to stdout)."""
        success, result = self.generate_commit_messages_safe(diff, files=files)
        if not success:
            print(f"❌ {result}")
            return []
        return result if isinstance(result, list) else [str(result)]

    @staticmethod
    def list_available_models(api_key: Optional[str] = None) -> List[str]:
        """Fetch all available models that support generateContent from the Gemini API."""
        if not api_key or api_key.strip() in ("", "your-api-key-here"):
            return list(DEFAULT_MODELS)

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
            response = GeminiClient._session.get(url, timeout=8)
            if response.status_code == 200:
                data = response.json()
                models = []
                for m in data.get("models", []):
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        raw_name = m.get("name", "")
                        clean_name = raw_name.replace("models/", "").strip()
                        if clean_name.startswith("gemini"):
                            models.append(clean_name)
                if models:
                    return sorted(
                        list(dict.fromkeys(models)),
                        key=lambda x: (
                            "2.5" not in x and "2.0" not in x,
                            "lite" not in x,
                            "flash" not in x,
                            x,
                        ),
                    )
            return list(DEFAULT_MODELS)
        except Exception as e:
            print(f"⚠️ Could not fetch remote models: {e}")
            return list(DEFAULT_MODELS)

    def generate_readme(self, prompt: str) -> Optional[str]:
        """Generate a complete README.md string using Gemini API."""
        print(f"🔍 Sending request to Gemini for README generation with model: {self.model}")
        system_instruction = (
            "You are an expert technical writer and developer. Generate a highly structured, accurate, "
            "and visually appealing README.md based on the provided project context. Output ONLY the raw "
            "markdown content without any prepended conversational text or ```markdown wrapper."
        )
        success, result = self._call_generate_content(prompt, system_instruction, max_output_tokens=2000)
        if not success:
            print(f"❌ Error generating README: {result}")
            return None
        return result

    def generate_issue(self, context: str) -> Optional[str]:
        """Generate a complete Issue markdown string using Gemini API."""
        print(f"🔍 Sending request to Gemini for Issue generation with model: {self.model}")
        prompt = f"Please generate a well-structured GitHub/GitLab issue using this context: {context}"
        system_instruction = (
            "You are an expert technical writer and developer. Generate a highly structured, accurate, "
            "and visually appealing GitHub/GitLab Issue template based on the provided context. If it sounds "
            "like a bug, format as a Bug Report (with Steps to Reproduce, Expected vs Actual). If it sounds "
            "like a feature, format as a Feature Request (with Problem, Proposed Solution). Output ONLY the "
            "raw markdown content without any prepended conversational text or ```markdown wrapper."
        )
        success, result = self._call_generate_content(prompt, system_instruction, max_output_tokens=2000)
        if not success:
            print(f"❌ Error generating Issue: {result}")
            return None
        return result
