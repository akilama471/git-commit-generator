import requests
import json
from typing import List, Optional

class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-lite", max_diff_len: int = 5000, temperature: float = 0.7):
        self.api_key = api_key
        self.model = model  # gemini-2.0-flash-lite, gemini-2.0-flash, or gemini-1.5-pro
        self.max_diff_len = max_diff_len
        self.temperature = temperature
        # Gemini API endpoint
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def generate_commit_messages(self, diff: str) -> List[str]:
        """Generate a single high-quality conventional git commit message using Gemini API"""

        # Truncate diff if too long
        if len(diff) > self.max_diff_len:
            diff = diff[:self.max_diff_len] + "\n... (truncated)"

        prompt = f"""You are an expert software developer and Git specialist.
Analyze the following git diff and generate a single, high-quality, professional Git commit message following the Conventional Commits specification.

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

        # Gemini API request format
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ],
                    "role": "user"
                }
            ],
            "system_instruction": {
                "parts": [
                    {
                        "text": "You are an expert Git commit assistant. You generate concise, accurate, and professional conventional git commit messages based on diffs. You output strictly the single raw commit message with no conversational text or markdown code fences."
                    }
                ]
            },
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": 600,
                "topP": 0.95,
                "topK": 40
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data)

            # Check if request was successful
            if response.status_code != 200:
                return f"Response: {response.text}"

            result = response.json()

            # Check for API errors
            if 'error' in result:
                return f"❌ API Error: {result['error']['message']}"

            # Extract content from Gemini response
            content = None
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if len(parts) > 0 and 'text' in parts[0]:
                        content = parts[0]['text']

            # If no content found
            if not content:
                print("❌ No content in API response")
                print(f"Raw response: {result}")
                return []

            # Strip markdown code blocks if model returned them
            content = content.strip()
            if content.startswith("```"):
                lines = content.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()

            if not content:
                print("❌ No valid commit messages generated")
                return []

            return [content]


        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response details: {e.response.text}")
            return []
        except json.JSONDecodeError:
            print("❌ Invalid JSON response from API")
            return []
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def list_available_models(api_key: Optional[str] = None) -> List[str]:
        """Fetch all available models that support generateContent from the Gemini API."""
        default_models = [
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-thinking-exp-01-21",
            "gemini-2.0-pro-exp-02-05",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-exp-1206",
        ]
        if not api_key or api_key.strip() in ("", "your-api-key-here"):
            return default_models

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
            response = requests.get(url, timeout=5)
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
                    # Sort prioritizing 2.0 / flash models first
                    return sorted(
                        list(dict.fromkeys(models)),
                        key=lambda x: (not "2.0" in x, not "flash" in x, x),
                    )
            return default_models
        except Exception as e:
            print(f"⚠️ Could not fetch remote models: {e}")
            return default_models


    def generate_readme(self, prompt: str) -> Optional[str]:
        """Generate a complete README.md string using Gemini API"""
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [
                {
                    "parts": [{"text": prompt}],
                    "role": "user"
                }
            ],
            "system_instruction": {
                "parts": [
                    {
                        "text": "You are an expert technical writer and developer. Generate a highly structured, accurate, and visually appealing README.md based on the provided project context. Output ONLY the raw markdown content without any prepended conversational text or ```markdown wrapper."
                    }
                ]
            },
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": 2000,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        try:
            print(f"🔍 Sending request to Gemini for README generation with model: {self.model}")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code != 200:
                print(f"❌ API returned status {response.status_code}")
                return None
                
            result = response.json()
            
            if 'error' in result:
                print(f"❌ API Error: {result['error']['message']}")
                return None
                
            content = None
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if len(parts) > 0 and 'text' in parts[0]:
                        content = parts[0]['text']
                        
            if not content:
                print("❌ No content in API response")
                return None
                
            # Strip markdown block wrappers if model still returns them
            content = content.strip()
            if content.startswith("```markdown"):
                content = content[11:]
            elif content.startswith("```md"):
                content = content[5:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            return content.strip()
            
        except Exception as e:
            print(f"❌ Error generating README: {e}")
            return None

    def generate_issue(self, context: str) -> Optional[str]:
        """Generate a complete Issue markdown string using Gemini API"""
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        prompt = f"Please generate a well-structured GitHub/GitLab issue using this context: {context}"
        
        data = {
            "contents": [
                {
                    "parts": [{"text": prompt}],
                    "role": "user"
                }
            ],
            "system_instruction": {
                "parts": [
                    {
                        "text": "You are an expert technical writer and developer. Generate a highly structured, accurate, and visually appealing GitHub/GitLab Issue template based on the provided context. If it sounds like a bug, format as a Bug Report (with Steps to Reproduce, Expected vs Actual). If it sounds like a feature, format as a Feature Request (with Problem, Proposed Solution). Output ONLY the raw markdown content without any prepended conversational text or ```markdown wrapper."
                    }
                ]
            },
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": 2000,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        try:
            print(f"🔍 Sending request to Gemini for Issue generation with model: {self.model}")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code != 200:
                print(f"❌ API returned status {response.status_code}")
                return None
                
            result = response.json()
            
            if 'error' in result:
                print(f"❌ API Error: {result['error']['message']}")
                return None
                
            content = None
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if len(parts) > 0 and 'text' in parts[0]:
                        content = parts[0]['text']
                        
            if not content:
                print("❌ No content in API response")
                return None
                
            # Strip markdown block wrappers if model still returns them
            content = content.strip()
            if content.startswith("```markdown"):
                content = content[11:]
            elif content.startswith("```md"):
                content = content[5:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            return content.strip()
            
        except Exception as e:
            print(f"❌ Error generating Issue: {e}")
            return None
