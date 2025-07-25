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
    
    max_retries = 6
    
    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, json={"text": prompt, "tab": 1}, timeout=30)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    # Check if API returned available: false in success response
                    if result.get("available") == False:
                        print(f"🚫 API not available (attempt {attempt + 1}/{max_retries}). Quick retry...")
                        time.sleep(2)
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
                        print(f"🚫 API not available (attempt {attempt + 1}/{max_retries}). Quick retry...")
                        time.sleep(2)
                        continue
                except json.JSONDecodeError:
                    pass
                print(f"❌ Server error (attempt {attempt + 1}/{max_retries}): {response.text}")
                time.sleep(1)
            else:
                print(f"❌ HTTP {response.status_code} (attempt {attempt + 1}/{max_retries}): {response.text}")
                time.sleep(1)
                
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout (attempt {attempt + 1}/{max_retries}). Quick retry...")
            time.sleep(1)
        except requests.exceptions.ConnectionError:
            print(f"🔌 Connection error (attempt {attempt + 1}/{max_retries}). Quick retry...")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error: {e} (attempt {attempt + 1}/{max_retries}). Quick retry...")
            time.sleep(1)
    
    # Return None instead of raising error - let caller handle skipping
    print(f"⏭️ Skipping batch after {max_retries} failed attempts")
    return None

async def translort(input_path, output_path, batch_size=15, api_url=""):
    sub_port = os.getenv("SUB_PORT")
    api_url = f"http://193.181.211.153:{sub_port}/api/text"
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
            
            # Skip if batch failed after all retries
            if result is None:
                print(f"⏭️ Skipping batch {i//batch_size + 1}")
                continue
            
            with open(output_path, "a", encoding="utf-8") as f:
                for block in result:
                    if block.strip():
                        f.write(block + "\n\n")
                        
        except Exception as e:
            print(f"❌ Failed batch {i//batch_size + 1}: {e}")
            continue
    
    print(f"✅ Translation completed! Output: {output_path}")