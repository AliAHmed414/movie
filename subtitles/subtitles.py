import os
import time
import chardet
import requests
import json
import re
from dotenv import load_dotenv
load_dotenv()

async def load_srt_file(file_path):
    with open(file_path, "rb") as f:
        raw_data = f.read()
        encoding_result = chardet.detect(raw_data)
        detected_encoding = encoding_result['encoding']

    for encoding in [detected_encoding, 'utf-8', 'latin-1', 'cp1252']:
        if encoding is None:
            continue
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def extract_arabic_text(text):
    """Extract Arabic text from response"""
    if not text:
        return ""
    
    # Remove formatting artifacts
    text = re.sub(r'^srtCopyEdit\d+', '', text)
    text = re.sub(r'^\d+$', '', text)
    text = re.sub(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$', '', text)
    text = text.strip()
    
    # Return if contains Arabic
    if re.search(r'[\u0600-\u06FF]', text):
        return text
    return ""

def fix_structure(original_blocks, translated_response):
    """Extract Arabic and rebuild proper SRT structure"""
    print("🔧 Fixing structure...")
    
    # Extract all Arabic text from response
    all_arabic = []
    for block in translated_response.strip().split("\n\n"):
        for line in block.split('\n'):
            arabic = extract_arabic_text(line)
            if arabic:
                all_arabic.append(arabic)
    
    print(f"🔍 Found {len(all_arabic)} Arabic translations")
    
    # Rebuild with original structure
    fixed_blocks = []
    arabic_index = 0
    
    for orig_block in original_blocks:
        lines = orig_block.strip().split('\n')
        if len(lines) >= 3:
            number = lines[0].strip()
            timestamp = lines[1].strip()
            orig_text = '\n'.join(lines[2:]).strip()
            
            # Check if has dialogue (not just sound effects)
            has_dialogue = orig_text and not re.match(r'^\[.*\]$', orig_text.strip())
            
            if has_dialogue and arabic_index < len(all_arabic):
                arabic_text = all_arabic[arabic_index]
                fixed_block = f"{number}\n{timestamp}\n{arabic_text}"
                arabic_index += 1
            else:
                fixed_block = f"{number}\n{timestamp}\n"
            
            fixed_blocks.append(fixed_block)
    
    print(f"✅ Fixed: {len(fixed_blocks)} blocks, {arabic_index} translations used")
    return fixed_blocks

def translate_batch(blocks, api_url):
    """Translate batch and fix structure directly"""
    headers = {"Content-Type": "application/json", "Cookie": "tstc=p"}
    
    # Simple translation prompt
    prompt = f"""Translate these subtitles to Arabic. Keep dialogue only, remove sound effects:

{chr(10).join(blocks)}"""
    
    max_retries = 10
    base_wait_time = 30
    
    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, json={"text": prompt, "tab": 1}, timeout=60)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    # Check if API returned available: false in success response
                    if result.get("available") == False:
                        wait_time = base_wait_time * (attempt + 1)
                        print(f"🚫 API not available (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    
                    translated_text = result.get("received_text", response.text)
                except json.JSONDecodeError:
                    translated_text = response.text
                
                # Always use structure fix (no validation)
                return fix_structure(blocks, translated_text)
            
            elif response.status_code == 500:
                try:
                    error_data = response.json()
                    if error_data.get("available") == False:
                        wait_time = base_wait_time * (attempt + 1)
                        print(f"🚫 API not available (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                except json.JSONDecodeError:
                    pass
                raise RuntimeError(f"Server error: {response.text}")
            else:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            wait_time = 5 * (attempt + 1)
            print(f"⏰ Timeout (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
            time.sleep(wait_time)
        except requests.exceptions.ConnectionError:
            wait_time = 5 * (attempt + 1)
            print(f"🔌 Connection error (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = 5 * (attempt + 1)
            print(f"❌ Error: {e} (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    raise RuntimeError("Max retries exceeded")

async def translort(input_path, output_path, batch_size=15, api_url="http://193.181.211.153:5000/api/text"):
    srt_content = await load_srt_file(input_path)
    blocks = srt_content.strip().split("\n\n")
    total_blocks = len(blocks)
    
    print(f"📊 Total blocks: {total_blocks}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("")
    
    for i in range(0, total_blocks, batch_size):
        batch = blocks[i:i + batch_size]
        progress = (i / total_blocks) * 100
        
        print(f"🔁 Batch {i//batch_size + 1} ({progress:.1f}% complete)...")
        
        try:
            result = translate_batch(batch, api_url)
            
            with open(output_path, "a", encoding="utf-8") as f:
                for block in result:
                    if block.strip():
                        f.write(block + "\n\n")
                        
        except Exception as e:
            print(f"❌ Failed batch {i//batch_size + 1}: {e}")
            if "not available" in str(e).lower():
                print("🚫 API server not available.")
                return
            continue
    
    print(f"✅ Translation completed! Output: {output_path}")