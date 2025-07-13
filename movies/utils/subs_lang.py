# utils/subs_lang.py

import os
import langdetect

def detect_srt_languages(directory, desired_langs=["ara", "eng"], only_one_lang=True, min_blocks=80):
    lang_map = {"ar": "ara", "en": "eng"}
    srt_files_subs = []
    srt_files_others = []

    # First gather files from Subs and non-Subs
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".srt"):
                full_path = os.path.join(root, file)
                if "subs" in root.lower().split(os.sep):
                    srt_files_subs.append(full_path)
                else:
                    srt_files_others.append(full_path)

    # Prioritize Subs folder files first
    prioritized_files = srt_files_subs + srt_files_others

    srt_data = []
    found_langs = set()

    for path in prioritized_files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

                # Check if the file has enough subtitle blocks (separated by two newlines)
                blocks = [b for b in content.strip().split('\n\n') if b.strip()]
                if len(blocks) < min_blocks:
                    print(f"⚠️ Skipping {path} — too few subtitle blocks ({len(blocks)} found)")
                    continue

                # Detect language
                detected = langdetect.detect(content)
                mapped_lang = lang_map.get(detected)

                if mapped_lang in desired_langs and mapped_lang not in found_langs:
                    srt_data.append({"path": path, "lang": mapped_lang})
                    found_langs.add(mapped_lang)

                    if only_one_lang and found_langs.issuperset(desired_langs):
                        return srt_data
        except Exception as e:
            print(f"❌ Error reading {path}: {e}")

    return srt_data


def clean_subtitle_file(subtitle_path):
    """
    Clean YTS/YIFY ads from subtitle file and replace with halashow.com
    """
    try:
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into subtitle blocks
        blocks = content.strip().split('\n\n')
        cleaned_blocks = []
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # Check if this block contains YTS/YIFY ads
                text_content = ' '.join(lines[2:]).lower()
                
                # Skip blocks with YTS/YIFY content
                if any(keyword in text_content for keyword in [
                    'yts.mx', 'yify', 'yts', 'official yify', 'downloaded from'
                ]):
                    continue
                
                cleaned_blocks.append(block)
        
        # Add halashow.com promotion at the beginning
        halashow_promo = """1
00:00:02,000 --> 00:00:07,000
Downloaded from
halashow.com

2
00:00:08,000 --> 00:00:13,000
Official movies site:
halashow.com"""
        
        # Renumber remaining blocks
        final_blocks = [halashow_promo]
        counter = 3
        
        for block in cleaned_blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # Replace the number with new counter
                lines[0] = str(counter)
                final_blocks.append('\n'.join(lines))
                counter += 1
        
        # Write cleaned content back
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(final_blocks))
        
        print(f"Cleaned subtitle: {subtitle_path}")
        
    except Exception as e:
        print(f"Error cleaning subtitle {subtitle_path}: {e}")
