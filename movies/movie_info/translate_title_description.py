import os
import time
import random
import json
from google import genai
from google.genai import types

def translate_title_description(title, description, model="gemini-2.0-flash", retries=5):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY") or "AIzaSyCH6qbmbIamMm3ePpBD2Hjq1-HY7rojT6Q")

    prompt = f"""
You are a professional movie translator.

Translate the following **movie title** and **description** from English to Arabic.

🎬 Title:
{title}

📝 Description:
{description}

Rules:
- Make the Arabic translation sound natural and culturally suitable.
- The title should feel like an official Arabic movie title (avoid literal translation if unnatural).
- The description should be fluent, readable, and engaging in Arabic.
- Do NOT include any English in the response.
- **Output JSON only**, in this exact format:

{{
  "title": "<Arabic title here>",
  "description": "<Arabic description here>"
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

            # Try to parse JSON
            parsed = None
            try:
                parsed = json.loads(output.strip())
            except json.JSONDecodeError:
                # Extract JSON block
                start = output.find("{")
                end = output.rfind("}") + 1
                if start != -1 and end != -1:
                    try:
                        parsed = json.loads(output[start:end])
                    except json.JSONDecodeError:
                        pass

            # Validate parsed data
            if isinstance(parsed, dict) and "title" in parsed and "description" in parsed:
                return parsed

            # Fallback if parsing fails
            raise RuntimeError(f"Invalid JSON format from Gemini:\n{output}")

        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"⚠️ Gemini overloaded, retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                raise e

    # If retries fail
    raise RuntimeError("❌ Failed to translate after multiple retries.")