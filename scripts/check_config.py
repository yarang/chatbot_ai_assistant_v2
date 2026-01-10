import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import os

from core.config import get_settings

try:
    settings = get_settings()
    api_key = settings.gemini.api_key
    print(f"API Key present: {bool(api_key)}")
    if api_key:
        print(f"API Key length: {len(api_key)}")
        print(f"API Key start: {api_key[:4]}...")
    else:
        print("API Key is missing or empty.")
        
    print(f"Env GEMINI_API_KEY: {bool(os.getenv('GEMINI_API_KEY'))}")
except Exception as e:
    print(f"Error loading config: {e}")
