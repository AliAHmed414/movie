import os
import time
import random
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

# MODEL = 'learnlm-2.0-flash-experimental'
MODEL = 'gemma-3-27b-it'

def translate_title_description(title, description, model=MODEL, retries=5):
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

    generate_content_config = types.GenerateContentConfig(
        top_p=1.0,
        temperature=1,       
    )

    for attempt in range(retries):
        try:
            output = ""
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config
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


def translate_title_only(title, model=MODEL, retries=5):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    prompt = f"""
Translate ONLY the following movie title from English to Arabic.
Title: {title}
Return ONLY a JSON object with the Arabic translation. Do not include examples or multiple movies.
Format:
{{
 "title": "Arabic title here"
}}
"""


    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        top_p=1.0,
        temperature=1,       
    )

    for attempt in range(retries):
        try:
            output = ""
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config
            ):
                # chunk.text may be None for some chunks; concatenate safely
                output += chunk.text or ""

            output = output.strip()
            if not output:
                raise RuntimeError("Empty response from model")

            # Try direct JSON parse; if fails, try to extract JSON block
            parsed = None
            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                start = output.find("{")
                end = output.rfind("}") + 1
                if start != -1 and end > start:
                    try:
                        parsed = json.loads(output[start:end])
                    except json.JSONDecodeError:
                        # If truncated, raise a helpful error
                        if output.endswith('},') or output.endswith('},{'):
                            raise RuntimeError(f"Response appears truncated:\n{output}")
                        parsed = None

            # Support array-wrapped responses
            if isinstance(parsed, list) and parsed:
                parsed = parsed[0]

            if isinstance(parsed, dict) and "title" in parsed:
                return parsed

            raise RuntimeError(f"Invalid JSON format from model:\n{output[:1000]}")

        except Exception as e:
            # retry on transient server errors
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"⚠️ Model overloaded, retrying in {wait_time:.2f}s... (attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
            else:
                # bubble up other errors (including invalid argument for model)
                raise e

    raise RuntimeError("❌ Failed to translate title after multiple retries.")


def translate_description_only(description, model=MODEL, retries=3):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    description = "The fascinating story of the early life of England’s most iconic Queen, Elizabeth Tudor, an orphaned teenager who became embroiled in the political and sexual politics of the English court on her journey to obtain the crown."


    prompt = f"'\\nTranslate ONLY the following movie description from English to Arabic.\\nDescription: {description}\\nReturn ONLY a JSON object with the Arabic translation. Do not include examples or multiple movies.\\nFormat:\\n{{\\n \"description\": \"Arabic description here\"\\n}}\\n'"


    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=prompt 
                )
            ],
    )
]

    generate_content_config = types.GenerateContentConfig(
        top_p=1.0,
        temperature=1,
    )

    for attempt in range(retries):
        try:
            # Call non-streaming API
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )

            output = ""
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        output += part.text
            output = output.strip()

            # Remove Markdown fences if present
            if output.startswith("```") and output.endswith("```"):
                lines = output.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                output = "\n".join(lines).strip()

            # Try JSON parsing
            parsed = None
            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                start = output.find("{")
                end = output.rfind("}") + 1
                if start != -1 and end > start:
                    parsed = json.loads(output[start:end])

            if isinstance(parsed, list) and len(parsed) > 0:
                parsed = parsed[0]

            if isinstance(parsed, dict) and "description" in parsed:
                return parsed

            raise RuntimeError(f"Invalid JSON format from Gemini:\n{output[:500]}...")

        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"⚠️ Gemini overloaded, retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                raise e

    raise RuntimeError("❌ Failed to translate description after multiple retries.")