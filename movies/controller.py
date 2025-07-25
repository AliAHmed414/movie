import json
import subprocess
import sys
import os
import requests
import glob
import shutil
import re
import random
import string
script_dir = os.path.dirname(os.path.abspath(__file__))
uploader_dir = os.path.dirname(script_dir)

if uploader_dir not in sys.path:
    sys.path.insert(0, uploader_dir)


import uploader.third
import utils.subs_lang
from yts import fetch_yts_movie
from movie_info import fetch_movie_data_by_imdb
from download.download import download_libtorrent
import utils
import subtitles
import encode
import movie_info
import asyncio
import uploader
import uploader.third.dzen
import uploader.third.ok
import uploader.third.vk
from insert.admin import upload_movie,upload_subtitle
import yts.sub  as yts_sub
from langdetect import detect
from movie_info.translate_title_description import translate_title_description
import traceback
from uploader import media
import time 


def resolve_imdb_redirect(imdb_id: str) -> str:
    url = f"https://www.imdb.com/title/{imdb_id}/"

    headers = {
        "User-Agent": "Mozilla/5.0"  # IMDb behaves differently without this
    }

    response = requests.get(url, headers=headers, allow_redirects=False)

    # Case 1: Standard redirect
    location = response.headers.get("Location")
    if location:
        match = re.search(r'tt\d+', location)
        if match:
            return match.group(0)

    # Case 2: Meta refresh
    refresh = response.headers.get("Refresh")
    if refresh:
        match = re.search(r'tt\d+', refresh)
        if match:
            return match.group(0)

    # Case 3: Check body manually
    match = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+url=/title/(tt\d+)', response.text, re.IGNORECASE)
    if match:
        return match.group(1)

    # No redirect, return original
    return imdb_id

async def main():
    try:
        api = "http://47.237.25.164:8080"
        res = requests.get(f"{api}/movie")
        title = ""
        if res.status_code == 200:
            data = res.json()
            title = data["title"]
            print(title)
            data = await fetch_yts_movie(title)

            if 'imdb_id' not in data:
                print("❌ imdb_id not found in data")
                return

            data['imdb_id'] = resolve_imdb_redirect(data['imdb_id'])
            

            web_torrents = [t for t in data.get('torrents', []) if t['codec'] == 'x264' and t['type'] == 'web']
            bluray_torrents = [t for t in data.get('torrents', []) if t['codec'] == 'x264' and t['type'] == 'bluray']

            chosen_torrents = web_torrents if web_torrents else bluray_torrents

            if not chosen_torrents:
                print("No suitable torrents found")
                return

            print(f"Using {'web' if web_torrents else 'bluray'} torrents")
            translated = False
            subs_path = None  # Define subs_path in outer scope

            for i, torrent in enumerate(chosen_torrents):
                base_path = os.path.join("/tmp", data['imdb_id'])
                quality_folder = torrent['quality']
                download_path = os.path.join(base_path, quality_folder)

                download_path = await download_libtorrent(download_path, torrent['magnet'], data['imdb_id'])

                if not download_path:
                    requests.post(f"{api}/movie/{title}/long")

                if download_path and quality_folder == "1080p":
                    subs_path = os.path.join(base_path, "subs")
                    os.makedirs(subs_path, exist_ok=True)

                    subtitle_info = utils.subs_lang.detect_srt_languages(download_path, only_one_lang=True)
                    print("Detected Subtitles:", subtitle_info)

                    for sub_info in subtitle_info:
                        sub_file = sub_info['path']
                        lang = sub_info['lang']

                        if sub_file.endswith('.srt'):
                            old_sub_path = sub_file
                            new_sub_name = f"{data['imdb_id']}.{lang}.srt"
                            new_sub_path = os.path.join(subs_path, new_sub_name)

                            if os.path.exists(old_sub_path):
                                os.rename(old_sub_path, new_sub_path)
                                print(f"Moved subtitle: {os.path.basename(sub_file)} -> {new_sub_name}")
                                utils.subs_lang.clean_subtitle_file(new_sub_path)

                if not translated:
                    if not subs_path:
                        print("❌ subs_path is not defined. Skipping subtitles processing.")
                        return

                    eng_sub = os.path.join(subs_path, f"{data['imdb_id']}.eng.srt")
                    ara_sub = os.path.join(subs_path, f"{data['imdb_id']}.ara.srt")

                    # Enhanced English subtitle processing
                    if not os.path.exists(eng_sub):
                        print(f"🔍 Fetching English subtitles for {data['imdb_id']}...")
                        subtitles_yts_query = f"https://yifysubtitles.ch/movie-imdb/{data['imdb_id']}"
                        
                        try:
                            subtitles_yts = yts_sub.fetch_subtitles(subtitles_yts_query) 
                            if subtitles_yts:
                                print(f"✅ Found {len(subtitles_yts)} English subtitle(s)")
                                yts_sub.download_and_extract_subtitle(
                                    subtitles_yts[0], save_path=subs_path, new_name=f"{data['imdb_id']}.eng.srt"
                                )
                                
                                # Post-processing with error handling
                                if os.path.exists(eng_sub):
                                    yts_sub.fix_encoding_if_needed(eng_sub)
                                    yts_sub.clean_srt(eng_sub)
                                    print("✅ English subtitle processed successfully")
                                else:
                                    print("❌ English subtitle file not found after download")
                            else:
                                print("❌ No English subtitles found on YTS")
                        except Exception as e:
                            print(f"❌ Error fetching English subtitles: {e}")

                    # Enhanced Arabic subtitle processing
                    if os.path.exists(eng_sub) and not os.path.exists(ara_sub):
                        print(f"🔍 Processing Arabic subtitles for {data['imdb_id']}...")
                        
                        # Try to fetch Arabic subtitles from YTS first
                        try:
                            subtitles_yts_query = f"https://yifysubtitles.ch/movie-imdb/{data['imdb_id']}"
                            subtitles_yts = yts_sub.fetch_subtitles(subtitles_yts_query, language="arabic")
                            
                            if subtitles_yts:
                                print(f"✅ Found {len(subtitles_yts)} Arabic subtitle(s) on YTS")
                                yts_sub.download_and_extract_subtitle(
                                    subtitles_yts[0], save_path=subs_path, new_name=f"{data['imdb_id']}.ara.srt"
                                )
                                
                                # Post-processing with error handling
                                if os.path.exists(ara_sub):
                                    yts_sub.fix_encoding_if_needed(ara_sub)
                                    yts_sub.clean_srt(ara_sub)
                                    yts_sub.remove_blocks_with_phrase(ara_sub, "ترجمة")  # Remove translator credits
                                    print("✅ Arabic subtitle from YTS processed successfully")
                                    translated = True
                                else:
                                    print("❌ Arabic subtitle file not found after YTS download")
                                    raise Exception("YTS Arabic subtitle download failed")
                            else:
                                print("ℹ️ No Arabic subtitles found on YTS, falling back to translation")
                                raise Exception("No Arabic subtitles on YTS")
                                
                        except Exception as yts_error:
                            print(f"⚠️ YTS Arabic subtitle failed: {yts_error}")
                            print("🔄 Falling back to translation service...")
                            
                            # try:
                            #     await subtitles.translort(eng_sub, ara_sub)
                            #     if os.path.exists(ara_sub):
                            #         print("✅ Arabic subtitle translated successfully")
                            #         translated = True
                            #     else:
                            #         print("❌ Translation service failed to create Arabic subtitle")
                            # except Exception as trans_error:
                            #     print(f"❌ Translation service error: {trans_error}")
                            #     print("⚠️ Continuing without Arabic subtitles...")
                    
                    elif not os.path.exists(eng_sub):
                        print("⚠️ No English subtitle available for Arabic processing")

                soft_subtitles = []
                
                ara_sub_path = os.path.join(subs_path, f"{data['imdb_id']}.ara.srt")
                if os.path.exists(ara_sub_path):
                    soft_subtitles.append({'file': ara_sub_path, 'language': 'ara', 'default': True, 'forced': True})
                
                eng_sub_path = os.path.join(subs_path, f"{data['imdb_id']}.eng.srt")
                if os.path.exists(eng_sub_path):
                    soft_subtitles.append({'file': eng_sub_path, 'language': 'eng', 'default': False, 'forced': False})

                mp4_files = glob.glob(os.path.join(download_path, "*.mp4"))
                if not mp4_files:
                    print("❌ No MP4 file found to process.")
                    return

                input_file = mp4_files[0]
                random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                output_file = os.path.join(download_path, f"{random_string}_{data['imdb_id'].replace('tt','')}.mp4")
                encode.add_subtitles_and_audio_only(input_file=input_file, output_file=output_file, subtitles=soft_subtitles, remove_metadata=True)
                os.remove(input_file)

                third_party_links = []
                subtitles_links = []

                if torrent['quality'] == "1080p" or i == 0:
                    try:
                        ok_url = uploader.third.ok.main_with_path(output_file)
                        third_party_links.append(ok_url)
                    except Exception as e:
                        print(e)
                    try:
                        subprocess.run(["pkill", "-f", "chrome"])
                        time.sleep(3)
                        dzen_url = uploader.third.dzen.main_with_path(output_file, f"{random_string}_{data['imdb_id'].replace('tt','')}.mp4")
                        third_party_links.append(dzen_url)
                    except Exception as e:
                        print(e)

                break

            # doc_id = None

            # try:
            #     url = 'http://193.181.211.153:3000/upload'
            #     cmd = [
            #         'curl',
            #         '-X', 'POST',
            #         '-F', f'file=@{output_file}',
            #         url
            #     ]
            #     result = subprocess.run(cmd, capture_output=True, text=True)
            #     response_json = json.loads(result.stdout)
            #     if response_json.get('success'):
            #         doc_url = response_json.get('url')
            #         doc_id = doc_url.split('/')[-1]

            # except Exception as e:
            #     print(f"DOCERROR: {e}")

            info = await movie_info.fetch_movie_data_by_imdb(data['imdb_id'])

            ara_sub_file = os.path.join(subs_path, f"{data['imdb_id']}.ara.srt")
            if os.path.exists(ara_sub_file):
                ar_id = await upload_subtitle(ara_sub_file, f"ar_{data['imdb_id']}")
                if ar_id:
                    subtitles_links.append(ar_id)

            eng_sub_file = os.path.join(subs_path, f"{data['imdb_id']}.eng.srt")
            if os.path.exists(eng_sub_file):
                en_id = await upload_subtitle(eng_sub_file, f"en_{data['imdb_id']}")
                if en_id:
                    subtitles_links.append(en_id)
            doc_id = None
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    # Get file size in GB and add 1GB buffer for space requirement
                    file_size_bytes = os.path.getsize(output_file)
                    file_size_gb = file_size_bytes / (1024 ** 3)  # Convert bytes to GB
                    required_space = max(3, int(file_size_gb + 1))  # Minimum 3GB or file size + 1GB buffer (rounded up)
                
                    print(f"📁 File size: {file_size_gb:.2f} GB, requesting {required_space} GB space (Attempt {attempt + 1}/{max_attempts})")
                    
                    mediafire = requests.get(f"http://47.237.25.164:9090/mediafire/with_space?space={required_space}")
                    mediafire.raise_for_status()  # Raise exception for HTTP errors
                    
                    mediafire_data = mediafire.json()
                    cookie = mediafire_data["cookie"]
                    entry_id = mediafire_data["id"]
                    
                    doc_id, free_space = media.upload_to_mediafire(output_file, cookie)
                    free_space = int(free_space / (1024**3))
                    # Update free space on server
                    update_response = requests.put(
                        f"http://47.237.25.164:9090/mediafire/{entry_id}/free_space",
                        json={"free_space": free_space}
                    )
                    update_response.raise_for_status()
                    
                    print(f"✅ MediaFire upload successful: {doc_id}")
                    print(f"📊 Updated free space: {free_space} GB")
                    break  # Success, exit the retry loop
                
                except requests.exceptions.RequestException as e:
                    print(f"❌ MediaFire API request failed (Attempt {attempt + 1}/{max_attempts}): {e}")
                    if attempt == max_attempts - 1:
                        print("⚠️ All MediaFire upload attempts failed, continuing without MediaFire upload...")
                except KeyError as e:
                    print(f"❌ MediaFire response missing key (Attempt {attempt + 1}/{max_attempts}): {e}")
                    if attempt == max_attempts - 1:
                        print("⚠️ All MediaFire upload attempts failed, continuing without MediaFire upload...")
                except FileNotFoundError:
                    print(f"❌ Output file not found: {output_file}")
                    break  # No point retrying if file doesn't exist
                except Exception as e:
                    print(f"❌ MediaFire upload failed (Attempt {attempt + 1}/{max_attempts}): {e}")
                    if attempt == max_attempts - 1:
                        print("⚠️ All MediaFire upload attempts failed, continuing without MediaFire upload...")

            result = await process_and_upload_movie(
                data=info,
                third_party_links=third_party_links,
                subtitles=subtitles_links,
                doc_id=doc_id
            )

        if result.get("response", {}).get("code") == 201:
            print("✅ Movie uploaded successfully")
            requests.post(f"{api}/movie/{title}")
        else:
            print(result)

    except:
        traceback.print_exc()

    finally:
        try:
            if 'data' in locals() and 'imdb_id' in data:
                file_path = f"/tmp/{data['imdb_id']}"
                if os.path.exists(file_path):
                    shutil.rmtree(file_path)
                    print(f"🧹 Cleaned up: {file_path}")
        except Exception as cleanup_err:
            print(f"⚠️ Failed to remove path: {cleanup_err}")

async def process_and_upload_movie(data,third_party_links=None,subtitles=None,doc_id=None):

    title_en = data.get('title_en', '')
    title_ar = data.get('title_ar', '')
    overview_en = data.get('overview_en', '')
    overview_ar = data.get('overview_ar', '')

    # Collapse multiple spaces and trim before translating
    title_en = re.sub(r"\s+", " ", title_en).strip()
    overview_en = re.sub(r"\s+", " ", overview_en).strip()

    # Fallback translation if Arabic is missing or incorrect
    if not title_ar or detect(title_ar.strip()) != "ar":
        title_description = translate_title_description(title_en, overview_en)

        # ✅ Ensure it's a dictionary
        if isinstance(title_description, dict):
            title_ar = title_description.get('title', '')
            if not overview_ar or detect(overview_ar.strip()) != 'ar':
                overview_ar = title_description.get('description', '')
        else:
            print(f"❌ Unexpected response from translate_title_description: {title_description}")
            title_ar = title_ar or ''
            overview_ar = overview_ar or ''

    # Construct the final values
    title = f"{title_en}|{title_ar}" if title_ar else title_en
    description = f"{overview_en}|{overview_ar}" if overview_ar else overview_en

    # Clean up final description
    description = re.sub(r"\s+", " ", description).strip()
    description = re.sub(r"[-]{2,}", " ", description)
    description = re.sub(r"[.]{2,}", " ", description)
    description = description.replace('"', '')
        # Step 3: Merge and deduplicate genres
    genres_en = data.get('genres_en', [])
    genres_ar = data.get('genres_ar', [])
    genres = list(dict.fromkeys(genres_ar + genres_en))


    rating_map = {
        # --- G ---
        "0": "G", "0+": "G", "All": "G", "ALL": "G", "AA": "G", "A": "G", "AL": "G", "ATP": "G",
        "Genel İzleyici Kitlesi": "G", "U": "G", "E": "G", "SU": "G", "Btl": "G",
        "G": "G", "P": "G", "6": "G", "7": "G", "6+": "G", "7+": "G", "6A": "G", "6A+": "G",
        "Públicos": "G", "AP": "G",

        # --- PG ---
        "PG": "PG", "PG12": "PG", "PG-12": "PG", "PG13": "PG-12", "PG-13": "PG-12",
        "7-9PG": "PG", "10-12PG": "PG", "UA": "PG", "U/A 7+": "PG", "U/A 13+": "PG",

        # --- PG-12 ---
        "12": "PG-12", "12A": "PG-12", "12+": "PG-12", "K-12": "PG-12", "I": "PG-12", "N-13": "PG-12",

        # --- PG-15 ---
        "13": "PG-15", "13+": "PG-15", "14": "PG-15", "14A": "PG-15", "15": "PG-15", "15+": "PG-15",
        "B": "PG-15", "B-15": "PG-15", "M": "PG-15", "TV-14": "PG-15", "U/A 16+": "PG-15",

        # --- R-15 ---
        "R": "R-15", "R13": "R-15", "R15": "R-15", "RP13": "R-15", "RP16": "R-15", "IIA": "R-15",
        "II": "R-15", "R15+": "R-15", "TV-MA": "R-15",

        # --- R-16 ---
        "16": "R-16", "16+": "R-16", "M/16": "R-16", "K-16": "R-16", "K15": "R-16", "K16": "R-16",
        "RP18": "R-16", "R16": "R-16", "R-16": "R-16",

        # --- R18 ---
        "18": "R18", "18+": "R18", "M/18": "R18", "K-18": "R18", "K18": "R18", "R18": "R18",
        "R-18": "R18", "R18+": "R18", "NC16": "R18", "NC-17": "R18", "18SG": "R18", "18SX": "R18",
        "18PA": "R18", "18PL": "R18", "III": "R18", "X": "R18", "X18": "R18", "XX": "R18",
        "20": "R18", "21+": "R18", "MA 15+": "R18", "Restricted Screening": "R18", "D": "R18",
        "TV-MA": "R18", "R21": "R18", "S": "R18",
        "Banned": "R18"
    }
        

    
    # Step 5: Other fields
    duration = data.get('runtime', 0)
    release_year = int(data.get('release_date', '')[:4] or 2030)
    poster_url = data.get('poster', '')
    backdrop_url = data.get('backdrop', '')
    trailer_url_full = data.get('trailer', '')
    trailer_id = trailer_url_full
    # if trailer_url_full :
    #     # Extract video ID from YouTube URL
    #     match = re.search(r"v=([A-Za-z0-9_-]+)", trailer_url_full)
    #     if match:
    #         trailer_id = match.group(1)

    # # Extract video ID from YouTube URL
    # match = re.search(r"v=([A-Za-z0-9_-]+)", trailer_url_full)
    # if match:
    #     trailer_id = match.group(1)

    logo_url = data.get('logo', '')
    if data.get("age_rating") == "" or not data.get("age_rating"):
        data["age_rating"] = "G"
    payload = {
    'title': title,
    'description': description,
    'duration': duration,
    'release_year': release_year,
    'poster_url': poster_url,
    'backdrop_url': backdrop_url,
    'mobile_url': poster_url,
    'trailer_url': trailer_id,
    'logo_url': logo_url,
    'hot_video_url': '',
    'status': "released",
    'age_rating': rating_map.get(data.get('age_rating', 'G'), 'G'),
    'subtitles': subtitles,
    'directors': list(dict.fromkeys(data.get('directors', []))),
    'actors': list(dict.fromkeys(data.get('cast', []))),
    'authors': list(dict.fromkeys(data.get('writers', []))),
    'companies': list(dict.fromkeys(data.get('production_companies', []))),
    'countries': list(dict.fromkeys(data.get('production_countries', []))),
    'genres': list(dict.fromkeys(genres)),
    'languages': list(dict.fromkeys([data.get('original_language', '')])),
    'categories': ['movie'],
    'dubbed': False,
    'free_video_sources': [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': ''
    }],
    'free_download_links': [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': doc_id if doc_id else ''
    }],
    'free_third_party_links': third_party_links or [''],
    'paid_video_sources': [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': '', 'url_2160p': '', 'url_4320p': ''
    }],
    'paid_download_links': [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p':  ''
    }],
    'paid_third_party_links': [''],
}
    print(payload)
    result = await upload_movie(
        **payload
    )

    return result

if __name__ == "__main__":
    for i in range(20000):
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"❌ Unhandled exception: {e}")
            traceback.print_exc()
            continue

