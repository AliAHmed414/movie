import os
import time
import random
import chardet
from google import genai
from google.genai import types

# Load and detect encoding of SRT file
async def load_srt_file(file_path):
    with open(file_path, "rb") as f:
        raw_data = f.read()
        encoding_result = chardet.detect(raw_data)
        detected_encoding = encoding_result['encoding']
        confidence = encoding_result['confidence']

    print(f"🔍 Detected encoding: {detected_encoding} (confidence: {confidence:.2f})")

    encodings_to_try = [detected_encoding, 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    for encoding in encodings_to_try:
        if encoding is None:
            continue
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
                print(f"✅ Successfully loaded file with {encoding} encoding")
                return content
        except (UnicodeDecodeError, LookupError):
            print(f"❌ Failed to decode with {encoding}")
            continue

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            print("⚠️ Loaded with UTF-8 and replaced invalid characters")
            return content
    except Exception as e:
        raise RuntimeError(f"Could not load file {file_path}: {e}")


# Split SRT into blocks
def split_srt_blocks(srt_text):
    return srt_text.strip().split("\n\n")


# Translate a batch of subtitle blocks (generic for any SRT)
def translate_block_batch(blocks, client, model, max_retries=5):
    srt_batch = "\n\n".join(blocks)

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"""
                    You are a professional subtitle translator for movies and TV shows.
                
                    Translate the following SRT subtitles from English to Arabic.

Rules:
- This is for cinematic subtitles (movies and TV shows).
- Keep the format: index numbers, timestamps, and line breaks.
- Only include the Arabic translation of spoken dialogue.
- Completely remove the English lines.
- Do NOT include or translate sound cues (e.g. [music], [screaming], etc).
- If a block contains only non-dialogue (like sound effects), return the block empty except for its number and timestamps.
- Make the Arabic translation natural and suitable for viewers watching dubbed or subtitled Arabic content

Subtitles:
{srt_batch}"""
                )
            ],
        )
    ]

    config = types.GenerateContentConfig(
        temperature=1,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(
                text="You are a professional subtitle translator for movies and TV shows . Translate English SRT subtitles to Arabic while preserving the SRT format. Do not include English text or non-dialogue cues like [music], [screaming], etc."
            ),
        ],
    )

    for attempt in range(max_retries):
        try:
            output = ""
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            ):
                output += chunk.text
            return output.strip().split("\n\n")

        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"⚠️ Model overloaded. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                raise e

    raise RuntimeError("❌ Max retries exceeded: model still unavailable.")


# Re-number translated blocks after branding
def renumber_blocks(translated_blocks, start_index=3):
    result = []
    count = start_index
    for block in translated_blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 2:
            lines[0] = str(count)
            result.append("\n".join(lines))
            count += 1
    return result


# Main translation entry
async def translort(input_path, output_path, batch_size=100):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY") or "AIzaSyCH6qbmbIamMm3ePpBD2Hjq1-HY7rojT6Q")
    model = "gemini-2.0-flash"

    srt_content = await load_srt_file(input_path)
    blocks = split_srt_blocks(srt_content)

    translated_blocks = []

    for i in range(0, len(blocks), batch_size):
        batch = blocks[i:i + batch_size]
        print(f"🔁 Translating batch {i} to {min(i + batch_size, len(blocks))}...")

        try:
            result = translate_block_batch(batch, client, model)
            translated_blocks.extend(result)
        except Exception as e:
            print(f"❌ Failed to translate batch {i}: {e}")

    # Re-number translated blocks starting from 3
    translated_blocks = renumber_blocks(translated_blocks, start_index=3)

    # Branding blocks (1 and 2)
    branding = [
        "1",
        "00:00:02,000 --> 00:00:07,000",
        "ترجمة حصرية بواسطة",
        "halashow.com",
        "",
        "2",
        "00:00:08,000 --> 00:00:13,000",
        "لمزيد من الأفلام والمسلسلات زوروا",
        "halashow.com",
        ""
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(branding))
        f.write("\n\n")
        f.write("\n\n".join(translated_blocks))
        f.write("\n")