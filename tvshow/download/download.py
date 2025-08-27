import subprocess
import os
import cloudscraper

def download_video(url, path_to_download, name, referer):
    os.makedirs(path_to_download, exist_ok=True)
    output_template = os.path.join(path_to_download, name)

    cmd = [
        "yt-dlp",
        "--no-part",
        "--restrict-filenames",
        "--referer", referer if referer else "https://player.videasy.net/",
        "-N", "4",
        "--user-agent", "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
        "-o", output_template,
        url
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Download complete: {output_template}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading video: {e}")
