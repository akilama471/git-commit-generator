import requests
import json
from typing import List, Optional

class DeepSeekClient:
    def __init__(self, api_key: str, model: str = "openrouter/free", 
                 max_diff_len: int = 5000, temperature: float = 0.7):
        self.api_key = api_key
        self.model = model
        self.max_diff_len = max_diff_len
        self.temperature = temperature
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def generate_commit_messages(self, diff: str) -> List[str]:
        """Generate multiple commit message options"""
        
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

Generate 3 different commit message options. Separate each option with '---'"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Git Commit Generator"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates excellent git commit messages following conventional commits format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": 500
        }
        
        try:
            print(f"🔍 Sending request to OpenRouter with model: {self.model}")
            response = requests.post(self.base_url, headers=headers, json=data)
            
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
            
            # SAFELY extract content with multiple fallbacks
            content = None
            
            # Try different response formats
            if 'choices' in result and len(result['choices']) > 0:
                choice = result['choices'][0]
                
                # OpenRouter format
                if 'message' in choice and 'content' in choice['message']:
                    content = choice['message']['content']
                # Alternative format
                elif 'text' in choice:
                    content = choice['text']
            
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
            traceback.print_exc()  # This will show the full error
            return []