import requests
import json
from typing import List, Optional

class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-lite",
                 max_diff_len: int = 5000, temperature: float = 0.7):
        self.api_key = api_key
        self.model = model  # gemini-2.0-flash-lite, gemini-2.0-flash, or gemini-1.5-pro
        self.max_diff_len = max_diff_len
        self.temperature = temperature
        # Gemini API endpoint
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def generate_commit_messages(self, diff: str) -> List[str]:
        """Generate multiple commit message options using Gemini API"""

        # Truncate diff if too long
        if len(diff) > self.max_diff_len:
            diff = diff[:self.max_diff_len] + "\n... (truncated)"

        prompt = f"""Generate git commit messages for these code changes:

{diff}

Requirements:
- Format: <type>(<scope>): <description>
- Types: feat, fix, docs, style, refactor, perf, test, chore, build, ci
- First line: max 72 characters
- If needed, add blank line then bullet points for details
- Focus on WHY the change was made
- Use imperative mood ("add" not "added")
- No line breaks in the first line

CRITICAL OUTPUT FORMAT REQUIREMENTS:
- Generate EXACTLY 3 different commit message options.
- Separate each option with exactly three dashes: '---'
- Output strictly the commit messages and separators. DO NOT include any introductory greetings, markdown code blocks (like ```), or concluding conversational text.
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
                        "text": "You are a helpful assistant that generates excellent git commit messages following conventional commits format."
                    }
                ]
            },
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": 500,
                "topP": 0.95,
                "topK": 40
            }
        }

        try:
            print(f"🔍 Sending request to Gemini with model: {self.model}")
            response = requests.post(url, headers=headers, json=data)

            # Check if request was successful
            if response.status_code != 200:
                print(f"❌ API returned status {response.status_code}")
                print(f"Response: {response.text}")
                return []

            result = response.json()

            # Check for API errors
            if 'error' in result:
                print(f"❌ API Error: {result['error']['message']}")
                return []

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

            # Split into options
            options = []
            if '---' in content:
                options = [opt.strip() for opt in content.split('---') if opt.strip()]
            else:
                # If no separators, treat as single option
                options = [content.strip()]

            # Filter out any empty options
            options = [opt for opt in options if opt]

            if not options:
                print("❌ No valid commit messages generated")
                return []

            return options

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
