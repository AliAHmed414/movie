import os
import time
import random
import json
from google import genai
from google.genai import types

# Translate English title and description to Arabic and return as JSON
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
            # parse to ensure valid JSON
            return json.loads(output.strip())
        except json.JSONDecodeError:
            # If the model added any stray text, try to extract the JSON block
            start = output.find("{")
            end = output.rfind("}") + 1
            if start != -1 and end != -1:
                try:
                    return json.loads(output[start:end])
                except Exception:
                    pass
            raise RuntimeError(f"Failed to parse JSON from response:\n{output}")
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"⚠️ Gemini overloaded, retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                raise e

    raise RuntimeError("❌ Failed to translate after multiple retries.")

# Example usage
if __name__ == "__main__":
    english_title = "The Last Voyage of the Demeter"
    english_description = (
        "A terrifying journey aboard the merchant ship Demeter as it transports mysterious cargo. "
        "Unexplained events unfold, and the crew begins to suspect an evil presence is stalking them."
    )

    result = translate_title_description(english_title, english_description)
    print(json.dumps(result, ensure_ascii=False, indent=2))