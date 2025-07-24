import requests
from bs4 import BeautifulSoup
import os
import zipfile
import subprocess
import re
import cloudscraper



def fetch_subtitles(url, language="arabic"):
    cookies = {
        'PHPSESSID': 'gahdcn2b6v42i1bk5k7u3t3fmh',
        'ys-sw': '1920',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0',
        'Accept': 'image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Referer': 'https://yifysubtitles.ch/movie-imdb/tt9150192',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-origin',
        'Priority': 'u=5, i',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    base_url = "https://yifysubtitles.ch"

    # Create cloudscraper instance
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url, headers=headers, cookies=cookies)
    
    soup = BeautifulSoup(response.content, "html.parser")

    arabic_links = []

    # Find all <tr> rows
    for row in soup.find_all("tr"):
        lang_cell = row.find("span", class_="sub-lang")
        if lang_cell and lang_cell.text.strip().lower() == language:
            link_tag = row.find("a", href=True)
            if link_tag:
                href = link_tag["href"]
                if href.startswith("/subtitles/"):
                    # Convert /subtitles/... ➜ /subtitle/....zip
                    slug = href.replace("/subtitles/", "")
                    final_url = f"{base_url}/subtitle/{slug}.zip"
                    arabic_links.append(final_url)

    return arabic_links
    
def download_and_extract_subtitle(url: str, save_path: str, new_name: str = "subtitle.srt"):
    os.makedirs(save_path, exist_ok=True)
    filename = url.split("/")[-1]
    zip_path = os.path.join(save_path, filename)

    # Use wget with custom headers
    wget_command = [
        "wget", "--quiet", "--show-progress",
        "--header", "User-Agent: Mozilla/5.0",
        "--referer", "https://yifysubtitles.ch/",
        "-O", zip_path,
        url
    ]

    print(f"⬇️ Downloading with wget: {url}")
    result = subprocess.run(wget_command, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Failed to download {url} (wget error)\n{result.stderr}")
        return

    print(f"✅ Downloaded: {zip_path}")

    # Extract the ZIP file
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(save_path)
            print(f"📂 Extracted to: {save_path}")

            # Rename the first .srt file found
            for name in zip_ref.namelist():
                if name.lower().endswith(".srt"):
                    original_path = os.path.join(save_path, name)
                    renamed_path = os.path.join(save_path, new_name)
                    os.rename(original_path, renamed_path)
                    print(f"✏️ Renamed {original_path} ➜ {renamed_path}")
                    break
    except zipfile.BadZipFile:
        print(f"❌ Invalid ZIP file: {zip_path}")
        return

    # Remove the ZIP file
    os.remove(zip_path)
    print(f"🗑️ Removed ZIP file: {zip_path}")
    
def fix_encoding_if_needed(filepath: str):
    """
    Automatically detect if a file is not UTF-8 encoded.
    If needed, converts it from Windows-1256 (common for Arabic subs) to UTF-8.
    """
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    try:
        # Use the `file` command to check encoding
        result = subprocess.check_output(["file", filepath], text=True)
        if "UTF-8" in result:
            print(f"✅ Encoding already UTF-8. No need to fix.")
            return
        else:
            print(f"🛠️ Detected non-UTF-8 encoding ({result.strip()}), converting...")

        # Fix encoding: read as windows-1256 and write as utf-8
        with open(filepath, 'r', encoding='windows-1256', errors='ignore') as f_in:
            content = f_in.read()

        with open(filepath, 'w', encoding='utf-8') as f_out:
            f_out.write(content)

        print(f"✅ Converted and saved to: {filepath}")

    except Exception as e:
        print(f"❌ Error processing file encoding: {e}")




def clean_srt(input_path: str, tags=None):
    """
    Clean an .srt subtitle file using `cleanit` CLI.
    
    Parameters:
    - input_path: Path to the .srt file to clean.
    - tags: List of cleanit tags (default: no-style, no-spam, tidy)
    """
    if tags is None:
        tags = ["no-style", "no-spam", "tidy"]

    if not os.path.exists(input_path):
        print(f"❌ File not found: {input_path}")
        return

    command = ["cleanit"]
    for tag in tags:
        command += ["-t", tag]

    command += [input_path]

    try:
        subprocess.run(command, check=True)
        print(f"✅ Subtitle cleaned: {input_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to clean: {input_path}")
        print(f"Error: {e}")


def remove_blocks_with_phrase(input_file, phrase="ترجمة"):
    """
    Removes subtitle blocks containing translator credits or specific Arabic phrases.
    """
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"❌ Error reading file: {input_file}")
        return

    # Split content into blocks (separated by double newlines)
    blocks = re.split(r'\n\s*\n', content)
    
    filtered_blocks = []
    removed_count = 0
    
    for block in blocks:
        # Check for translator credit patterns (various forms of "ترجمة")
        translator_patterns = [
            r'#\s*ت[ـ]*ر[ـ]*ج[ـ]*م[ـ]*ة\s*#',  # # ترجمة # with optional connecting chars
            r'تـرجـمـة',  # تـرجـمـة with connecting chars
            r'ترجمة',    # Regular ترجمة
            r'\|\s*.*\s*-\s*.*\s*\|',  # Translator names pattern like | Name - Name |
        ]
        
        is_translator_block = any(re.search(pattern, block) for pattern in translator_patterns)
        
        if is_translator_block:
            removed_count += 1
            print(f"🗑️ Removing translator credit block")
            continue
        
        # Keep all other blocks
        if block.strip():  # Only keep non-empty blocks
            filtered_blocks.append(block)
    
    # Join the filtered blocks back
    cleaned_content = '\n\n'.join(filtered_blocks)
    
    # Write back to file
    try:
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"✅ Removed {removed_count} translator credit blocks")
        print(f"✅ Total blocks remaining: {len(filtered_blocks)}")
        print(f"✅ Cleaned subtitle saved to: {input_file}")
        
    except Exception as e:
        print(f"❌ Error writing file: {input_file}")
        print(f"Error: {e}")


if __name__ == "__main__":
    url = "https://yifysubtitles.ch/movie-imdb/tt23149780"

    subtitle_links = fetch_subtitles(url,language="arabic")
    download_and_extract_subtitle(subtitle_links[0], save_path="/home/kda/uploader", new_name="sq.srt")
    fix_encoding_if_needed("/home/kda/uploader/sq.srt")
    clean_srt("/home/kda/uploader/sq.srt")
