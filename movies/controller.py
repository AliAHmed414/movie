import sys
import os
import requests
import glob

import re

script_dir = os.path.dirname(os.path.abspath(__file__))
uploader_dir = os.path.dirname(script_dir)

if uploader_dir not in sys.path:
    sys.path.insert(0, uploader_dir)


import uploader.doc
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

async def main():
    api = "http://localhost:8080"
    res = requests.get(f"{api}/movie")
    title = ""
    if res.status_code == 200:
        data = res.json()
        title = data["title"]
        print(title)
        data = await fetch_yts_movie(title)
        
        # Find best torrent: prioritize web over bluray
        web_torrents = [t for t in data.get('torrents', []) if t['codec'] == 'x264' and t['type'] == 'web']
        bluray_torrents = [t for t in data.get('torrents', []) if t['codec'] == 'x264' and t['type'] == 'bluray']
        
        # Choose web if available, otherwise bluray
        chosen_torrents = web_torrents if web_torrents else bluray_torrents
        
        if not chosen_torrents:
            print("No suitable torrents found")
            return
            
        print(f"Using {'web' if web_torrents else 'bluray'} torrents")
        translated = False
        for i, torrent in enumerate(chosen_torrents):
            # Create quality-based folder structure
            base_path = os.path.join("/tmp", data['imdb_id'])
            quality_folder = torrent['quality']  # 720p, 1080p, etc.
            download_path = os.path.join(base_path, quality_folder)
            download_path = await download_libtorrent(download_path, torrent['magnet'], data['imdb_id'])
            if not download_path:
                requests.post(f"{api}/movie/{title}/long")
            if download_path and quality_folder == "1080p":
                # Create subs folder in the same base directory
                subs_path = os.path.join(base_path, "subs")
                os.makedirs(subs_path, exist_ok=True)
                
                subtitle_info = utils.subs_lang.detect_srt_languages(download_path, only_one_lang=True)
                print("Detected Subtitles:", subtitle_info)
                
                
                # Move subtitles to subs folder with imdb-id.{lang}.srt format
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
                            
                            # Clean the subtitle file
                            utils.subs_lang.clean_subtitle_file(new_sub_path)
            
            if not translated:
                eng_sub = os.path.join(subs_path, f"{data['imdb_id']}.eng.srt")
                ara_sub = os.path.join(subs_path, f"{data['imdb_id']}.ara.srt")
                if os.path.exists(eng_sub) and not os.path.exists(ara_sub):
                    await subtitles.translort(eng_sub, ara_sub)
                    translated = True
            
            soft_ubtitles=[
                {'file': os.path.join(subs_path, f"{data['imdb_id']}.ara.srt") ,'language':'ara', 'default': True, 'forced': True},
                {'file': os.path.join(subs_path, f"{data['imdb_id']}.eng.srt"), 'language': 'eng', 'default': False, 'forced': False}
            ]
            mp4_files = glob.glob(os.path.join(download_path, "*.mp4"))
            if not mp4_files:
                print("❌ No MP4 file found to process.")
                return
            input_file = mp4_files[0]
            output_file = os.path.join(download_path, f"{torrent['quality']}_{data['imdb_id']}.mp4")
            encode.add_subtitles_and_audio_only(input_file=input_file,output_file=output_file,subtitles=soft_ubtitles,remove_metadata=True)
            os.remove(input_file)
            third_party_links = []
            subtitles_links = []
            if torrent['quality'] == "1080p" or  i == 0:
                try:
                 dzen_url = uploader.third.dzen.main_with_path(output_file,data['imdb_id'])
                except Exception as e:
                    print(e)
                try:
                    ok_url = uploader.third.ok.main_with_path(output_file)
                except Exception as e:
                    print(e)
                if dzen_url:
                    third_party_links.append(dzen_url)
                if ok_url:
                    third_party_links.append(ok_url)
                

            break
        info = await movie_info.fetch_movie_data_by_imdb(data['imdb_id'])
        ar_id = upload_subtitle(os.path.join(subs_path, f"{data['imdb_id']}.ara.srt"))
        if  ar_id:
            subtitles_links.append(ar_id)
        en_id = upload_subtitle(os.path.join(subs_path, f"{data['imdb_id']}.eng.srt"))
        if en_id:
            subtitles_links.append(en_id)

        doc_result = uploader.doc.upload_doc_to_vk_wall(
            output_file,
            title=data['imdb_id']
        )
        doc_id = ''
        if doc_result["id"]:
            doc_id =  doc_result["id"]
        result = await process_and_upload_movie(
            data=info,
            third_party_links=third_party_links,
            subtitles=subtitles_links,
            doc_id=doc_id
        )
    if result.get("response", {}).get("code") == 201:
        print("✅ Movie uploaded successfully")
        requests.post(f"{api}/movie/{title}")

async def process_and_upload_movie(data,third_party_links=None,subtitles=None,doc_id=None):
    # Step 1: Fetch movie data
    

    # Step 2: Combine title and overview (description) in en|ar format if Arabic exists
    title_en = data.get('title_en', '')
    title_ar = data.get('title_ar', '')
    title = f"{title_en}|{title_ar}" if title_ar else title_en

    overview_en = data.get('overview_en', '')
    overview_ar = data.get('overview_ar', '')
    description = f"{overview_en}|{overview_ar}" if overview_ar else overview_en

    description = re.sub(r"[-]{2,}", " ", description)
    description = re.sub(r"[.]{2,}", " ", description)
    description = description.replace('"', '')

    # Collapse multiple spaces and trim
    description = re.sub(r"\s+", " ", description).strip()

    # Step 3: Merge and deduplicate genres
    genres_en = data.get('genres_en', [])
    genres_ar = data.get('genres_ar', [])
    genres = list(dict.fromkeys(genres_ar + genres_en))

    # Step 4: Normalize age rating to match your DB enum
    tmdb_rating = data.get("age_rating", "")
    rating_map = {
        "G": "G",
        "PG": "PG",
        "PG-13": "PG-12",
        "R": "R-15",
        "NC-17": "R18",
        "TV-MA": "R-16",
        "TV-14": "PG-15",
    }
    age_rating = rating_map.get(tmdb_rating, "")

    
    # Step 5: Other fields
    duration = data.get('runtime', 0)
    release_year = int(data.get('release_date', '')[:4] or 0)
    poster_url = data.get('poster', '')
    backdrop_url = data.get('backdrop', '')
    trailer_url_full = data.get('trailer', '')
    trailer_id = ''
    # Extract video ID from YouTube URL
    match = re.search(r"v=([A-Za-z0-9_-]+)", trailer_url_full)
    if match:
        trailer_id = match.group(1)


    logo_url = data.get('logo', '')
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
    'age_rating': age_rating,
    'subtitles': [],
    'directors': data.get('directors', []),
    'actors': data.get('cast', []),
    'authors': data.get('writers', []),
    'companies': data.get('production_companies', []),
    'countries': data.get('production_countries', []),
    'genres': genres,
    'languages': [data.get('original_language', '')],
    'categories': ['movie'],
    'dubbed': False,
    'free_video_sources': [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': ''
    }],
    'free_download_links': [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': ''
    }],
    'free_third_party_links': third_party_links or [''],
    'paid_video_sources': [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': '', 'url_2160p': '', 'url_4320p': ''
    }],
    'paid_download_links': [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': doc_id if doc_id else ''
    }],
    'paid_third_party_links': [''],
}
    result = await upload_movie(
        **payload
    )

    print("✅ Upload response:", result)

if __name__ == "__main__":
    asyncio.run(main()) 