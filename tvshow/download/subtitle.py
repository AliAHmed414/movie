import requests
import os
import subprocess
import random
import string

def download_subtitle(id, s, e, languages=['ar','en']):
    url = f"https://sub.wyzie.ru/search?id={id}&season={s}&episode={e}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
        "Referer": "https://sub.wyzie.ru/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"❌ Failed to fetch subtitles: {response.status_code}")
            return None
        
        data = response.json()
        return [{lang['language']: lang['url']} for lang in data if lang['language'] in languages]
    except Exception as e:
        print(f"Error downloading subtitle: {e}")
        return None

def download_and_save_subtitles(id, s, e, languages=[ 'ar','en'], path_to_save='./subtitles', base_filename=None):
    print(f"🔍 Searching for subtitles for {id} S{s:02d}E{e:02d}")
    
    subtitle_urls = download_subtitle(id, s, e, languages)
    if not subtitle_urls:
        print("❌ No subtitles found")
        return []
    
    # Create directories for first and all subtitles
    first_path = os.path.join(path_to_save, 'first')
    all_path = os.path.join(path_to_save, 'all')
    os.makedirs(first_path, exist_ok=True)
    os.makedirs(all_path, exist_ok=True)
    
    downloaded_files = []
    
    if not base_filename:
        base_filename = f"{id}_S{s:02d}E{e:02d}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
        "Referer": "https://sub.wyzie.ru/"
    }
    
    # Track first subtitle for each language
    first_downloaded = {lang: False for lang in languages}
    
    for idx, subtitle_dict in enumerate(subtitle_urls):
        for language, url in subtitle_dict.items():
            try:
                random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                filename = f"{random_string}_{base_filename}_{language}_{idx+1}.srt"
                
                # Determine if this is the first subtitle for this language
                is_first = not first_downloaded[language]
                target_path = first_path if is_first else all_path
                filepath = os.path.join(target_path, filename)
                
                print(f"📥 Downloading {language} subtitle ({'first' if is_first else 'additional'})")
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    encoding = 'cp1256' if 'encoding=CP1256' in url else 'utf-8'
                    
                    with open(filepath, 'w', encoding=encoding, errors='ignore') as f:
                        f.write(response.text)
                    
                    # Fix encoding and clean subtitle
                    fix_encoding_if_needed(filepath)
                    clean_srt(filepath)
                    
                    downloaded_files.append(filepath)
                    
                    # Mark this language as having its first subtitle downloaded
                    if is_first:
                        first_downloaded[language] = True
                    
                    print(f"✅ Downloaded and processed: {filepath}")
                else:
                    print(f"❌ Failed to download {language} subtitle: {response.status_code}")
            except Exception as e:
                print(f"❌ Error downloading {language} subtitle: {e}")
    
    return downloaded_files

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

def sub_async(video_path, subtitle_path, output_path):

    command = [
        "ffs",
        video_path,
        "-i", subtitle_path,
        '-o', output_path,
    ]

    try:
        subprocess.run(command, check=True)
        print(f"✅ Subtitles sync ")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to add subtitles to video: {output_path}")
        print(f"Error: {e}")

# Example usage
if __name__ == "__main__":
    show_id = "tt1592154"
    season = 1
    episode = 1
    
    result = download_subtitle(show_id, season, episode)

    downloaded = download_and_save_subtitles(
        id=show_id,
        s=season, 
        e=episode,
        languages=['ar','en'],
        path_to_save='./downloaded_subtitles',
        base_filename=f'{show_id.replace('tt','')}s_{season:02d}_e{episode:02d}'
    )
    
    print(f"\n✅ Downloaded {len(downloaded)} subtitle files:")
    for file in downloaded:
        print(f"   📄 {file}")