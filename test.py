import requests
from bs4 import BeautifulSoup
import os
import zipfile
import subprocess
import re
import cloudscraper

def fetch_subtitles(url,language="arabic"):
    cookies = {
        'PHPSESSID': 'gahdcn2b6v42i1bk5k7u3t3fmh',
        'ys-sw': '1920',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0',
        'Accept': 'image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5',
        'Accept-Language': 'en-US,en;q=0.5',
        # 'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Connection': 'keep-alive',
        'Referer': 'https://yifysubtitles.ch/movie-imdb/tt9150192',
        # 'Cookie': 'PHPSESSID=gahdcn2b6v42i1bk5k7u3t3fmh; ys-sw=1920',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-origin',
        'Priority': 'u=5, i',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        # Requests doesn't support trailers
        # 'TE': 'trailers',
    }
    base_url = "https://yifysubtitles.ch"
    response = requests.get(url,headers=headers,cookies=cookies)
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
data = fetch_subtitles("https://yifysubtitles.ch/movie-imdb/tt30253473")
print(data)


