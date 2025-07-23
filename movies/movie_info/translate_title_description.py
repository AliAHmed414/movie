import os
import time
import random
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

def translate_title_description(title, description, model="gemini-2.0-flash", retries=5):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    prompt = f"""
Translate ONLY the following movie title and description from English to Arabic.

Title: {title}
Description: {description}

Return ONLY a JSON object with the Arabic translations. Do not include examples or multiple movies.

Format:
{{
  "title": "Arabic title here",
  "description": "Arabic description here"
}}
"""

    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]

    config = types.GenerateContentConfig(
        temperature=0.9,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )

    for attempt in range(retries):
        try:
            output = ""
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config
            ):
                output += chunk.text

            # Clean and validate output
            output = output.strip()
            if not output:
                raise RuntimeError("Empty response from Gemini")
            
            # Try to parse JSON
            parsed = None
            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                # Try to extract JSON block if wrapped in text
                start = output.find("{")
                end = output.rfind("}") + 1
                if start != -1 and end > start:
                    try:
                        parsed = json.loads(output[start:end])
                    except json.JSONDecodeError:
                        # Check if response was truncated
                        if output.endswith('},') or output.endswith('},{'):
                            raise RuntimeError(f"Response appears truncated from Gemini:\n{output}")
                        pass

            # Handle both single object and array responses
            if isinstance(parsed, list) and len(parsed) > 0:
                parsed = parsed[0]  # Take first item if array
            
            # Validate parsed data
            if isinstance(parsed, dict) and "title" in parsed and "description" in parsed:
                return parsed

            # Fallback if parsing fails
            raise RuntimeError(f"Invalid JSON format from Gemini:\n{output[:500]}...")

        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"⚠️ Gemini overloaded, retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                raise e

    # If retries fail
    raise RuntimeError("❌ Failed to translate after multiple retries.")