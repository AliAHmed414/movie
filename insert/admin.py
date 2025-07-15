import requests



async def upload_movie(
    title,
    description,
    duration,
    release_year,
    poster_url,
    backdrop_url,
    mobile_url,
    trailer_url,
    logo_url='',
    hot_video_url='',
    status='',
    age_rating='',
    subtitles=None,
    directors=None,
    actors=None,
    authors=None,
    companies=None,
    countries=None,
    genres=None,
    languages=None,
    categories=None,
    dubbed=False,
    free_video_sources=None,
    free_download_links=None,
    free_third_party_links=None,
    paid_video_sources=None,
    paid_download_links=None,
    paid_third_party_links=None
):
    subtitles = subtitles or []
    directors = directors or []
    actors = actors or []
    authors = authors or []
    companies = companies or []
    countries = countries or []
    genres = genres or []
    languages = languages or []
    categories = categories or []

    free_video_sources = free_video_sources or [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': ''
    }]
    free_download_links = free_download_links or [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': ''
    }]
    free_third_party_links = free_third_party_links or ['']

    paid_video_sources = paid_video_sources or [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': '', 'url_2160p': '', 'url_4320p': ''
    }]
    paid_download_links = paid_download_links or [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': ''
    }]
    paid_third_party_links = paid_third_party_links or ['']

    json_data = {
        'title': title,
        'description': description,
        'duration': duration,
        'release_year': release_year,
        'poster_url': poster_url,
        'backdrop_url': backdrop_url,
        'mobile': mobile_url,
        'trailer_url': trailer_url,
        'logo_url': logo_url,
        'hot_video_url': hot_video_url,
        'status': status,
        'age_rating': age_rating,
        'subtitles': subtitles,
        'directors': directors,
        'actors': actors,
        'authors': authors,
        'companies': companies,
        'countries': countries,
        'genres': genres,
        'languages': languages,
        'categories': categories,
        'dubbed': dubbed,
        'free': {
            'video_sources': free_video_sources,
            'download_links': free_download_links,
            'third_party_video_links': free_third_party_links,
            'pixel_videos': {
                'url_360p': ['undefined'],
                'url_480p': ['undefined'],
                'url_720p': ['undefined'],
                'url_1080p': ['undefined'],
            },
        },
        'paid': {
            'video_sources': paid_video_sources,
            'download_links': paid_download_links,
            'third_party_video_links': paid_third_party_links,
            'pixel_videos': {
                'url_360p': ['undefined'],
                'url_480p': ['undefined'],
                'url_720p': ['undefined'],
                'url_1080p': ['undefined'],
                'url_2160p': ['undefined'],
                'url_4320p': ['undefined'],
            },
        },
    }

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Access': 'yatki',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'https://ddtank.halashow.com',
        'Pragma': 'no-cache',
        'Referer': 'https://ddtank.halashow.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not.A/Brand";v="99", "Chromium";v="136"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
    }

    cookies = {
        'auth_token': '26a3c99ca55a006dca854cb8af4c3756cdc20c99b3f836e4b621bd78348cee07',
    }

    response = requests.post(
        'https://swag.halashow.com/ddtank/admin/movie',
        cookies=cookies,
        headers=headers,
        json=json_data
    )

    return response.json()



async def upload_subtitle(file_path: str, language: str = "ar") -> str:
    url = 'https://swag.halashow.com/ddtank/admin/subs'

    cookies = {
        'auth_token': '26a3c99ca55a006dca854cb8af4c3756cdc20c99b3f836e4b621bd78348cee07',
    }
    headers = {
        'Accept': '*/*',
        'Access': 'yatki',
        'Origin': 'https://ddtank.halashow.com',
        'Referer': 'https://ddtank.halashow.com/',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not.A/Brand";v="99", "Chromium";v="136"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
    }

    files = {
        'file': ('w.srt', open(file_path, 'rb'), 'application/x-subrip'),
    }

    data = {
        'language': language,
    }

    response = requests.post(url, headers=headers, cookies=cookies, data=data, files=files)

    if response.ok:
        result = response.json()
        return result.get("data") 
    else:
        print("Failed:", response.status_code, response.text)
        return None