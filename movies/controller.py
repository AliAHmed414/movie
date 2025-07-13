import sys
import os
import requests
import glob





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
        for torrent in chosen_torrents:
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
            if torrent['quality'] == "1080p":
                dzen_url = uploader.third.dzen.main_with_path(output_file,data['imdb_id'])
                print(dzen_url)
                vk_url = uploader.third.vk.main_with_path(output_file)
                print(vk_url)
                ok_url = uploader.third.ok.main_with_path(output_file)
                print(ok_url)
        info =await movie_info.fetch_movie_data_by_imdb(data['imdb_id'])
        print(info)
        requests.post(f"{api}/movie/{title}")
if __name__ == "__main__":
    asyncio.run(main()) 