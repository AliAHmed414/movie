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
            error_str = str(e)
            
            # Handle quota exhaustion (429 RESOURCE_EXHAUSTED)
            if "429" in error_str and "RESOURCE_EXHAUSTED" in error_str:
                if "retryDelay" in error_str:
                    # Extract retry delay from error message
                    import re
                    delay_match = re.search(r"'retryDelay': '(\d+)s'", error_str)
                    if delay_match:
                        retry_delay = int(delay_match.group(1))
                        print(f"🚫 Quota exceeded. Waiting {retry_delay} seconds before retry...")
                        time.sleep(retry_delay + 5)  # Add 5 seconds buffer
                    else:
                        # Default wait for quota reset (24 hours for daily quota)
                        print("🚫 Daily quota exceeded. Waiting 1 hour before retry...")
                        time.sleep(3600)  # Wait 1 hour
                else:
                    wait_time = min(300, 60 * (attempt + 1))  # Progressive wait up to 5 minutes
                    print(f"🚫 Quota exceeded. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
            
            # Handle server overload (503 UNAVAILABLE)
            elif "503" in error_str or "UNAVAILABLE" in error_str:
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"⚠️ Model overloaded. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            
            # Handle other errors
            else:
                print(f"❌ Translation error: {error_str}")
                if attempt == max_retries - 1:
                    raise e
                wait_time = 10 * (attempt + 1)
                print(f"⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    raise RuntimeError("❌ Max retries exceeded: translation still failing.")


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


# Save progress to resume later
def save_progress(output_path, translated_blocks, current_batch):
    progress_file = f"{output_path}.progress"
    progress_data = {
        'translated_blocks': translated_blocks,
        'current_batch': current_batch,
        'timestamp': time.time()
    }
    
    import json
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)
    print(f"� ProgTress saved to {progress_file}")

# Load progress to resume translation
def load_progress(output_path):
    progress_file = f"{output_path}.progress"
    if not os.path.exists(progress_file):
        return None, 0
    
    try:
        import json
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        
        translated_blocks = progress_data.get('translated_blocks', [])
        current_batch = progress_data.get('current_batch', 0)
        timestamp = progress_data.get('timestamp', 0)
        
        # Check if progress is recent (within 24 hours)
        if time.time() - timestamp < 86400:
            print(f"📂 Resuming from batch {current_batch} ({len(translated_blocks)} blocks completed)")
            return translated_blocks, current_batch
        else:
            print("⚠️ Progress file is too old, starting fresh")
            return None, 0
            
    except Exception as e:
        print(f"⚠️ Could not load progress: {e}")
        return None, 0

# Main translation entry
async def translort(input_path, output_path, batch_size=100):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    model = "gemini-2.0-flash"

    srt_content = await load_srt_file(input_path)
    blocks = split_srt_blocks(srt_content)
    total_blocks = len(blocks)
    
    print(f"📊 Total subtitle blocks to translate: {total_blocks}")

    # Try to resume from previous progress
    translated_blocks, start_batch = load_progress(output_path)
    if translated_blocks is None:
        translated_blocks = []
        start_batch = 0

    failed_batches = []
    
    for i in range(start_batch, total_blocks, batch_size):
        batch = blocks[i:i + batch_size]
        batch_end = min(i + batch_size, total_blocks)
        progress_pct = (i / total_blocks) * 100
        
        print(f"🔁 Translating batch {i} to {batch_end} ({progress_pct:.1f}% complete)...")

        try:
            result = translate_block_batch(batch, client, model)
            translated_blocks.extend(result)
            
            # Save progress every 5 batches
            if (i // batch_size) % 5 == 0:
                save_progress(output_path, translated_blocks, i + batch_size)
                
        except Exception as e:
            error_str = str(e)
            print(f"❌ Failed to translate batch {i}: {e}")
            
            # If quota exceeded, save progress and exit gracefully
            if "429" in error_str and "RESOURCE_EXHAUSTED" in error_str:
                print("🚫 Quota exhausted. Saving progress...")
                save_progress(output_path, translated_blocks, i)
                print(f"💡 Resume later by running the same command. Progress: {len(translated_blocks)} blocks completed.")
                return
            
            failed_batches.append(i)
            
            # Continue with next batch for other errors
            continue

    # Report failed batches
    if failed_batches:
        print(f"⚠️ Failed to translate {len(failed_batches)} batches: {failed_batches}")
        print("💡 You may want to retry these batches manually or with a smaller batch size.")

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

    # Write final output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(branding))
        f.write("\n\n")
        f.write("\n\n".join(translated_blocks))
        f.write("\n")
    
    # Clean up progress file on successful completion
    progress_file = f"{output_path}.progress"
    if os.path.exists(progress_file):
        os.remove(progress_file)
        print("🧹 Progress file cleaned up")
    
    print(f"✅ Translation completed! Output saved to {output_path}")
    print(f"📊 Translated {len(translated_blocks)} subtitle blocks")