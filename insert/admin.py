import requests



# BASE_URL = 'https://swag.halashow.com/ddtank/admin'
BASE_URL = 'http://127.0.0.1:6090/ddtank/admin'
HEADERS = {
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

COOCKIES = {
    'auth_token': 'add0b66970af70d798d57e973f701a78e99fe835da256a287d5d9db2a2a6f9b5',
}

async def upload_movie(
    title,
    imdb_id,
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
        'imdb_id': imdb_id,
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



    response = requests.post(
        f'{BASE_URL}/movie',
        cookies=COOCKIES,
        headers=HEADERS,
        json=json_data
    )

    return response.json()



async def upload_subtitle(file_path: str, language: str = "ar") -> str:
    url = f'{BASE_URL}/subs'

    files = {
        'file': ('w.srt', open(file_path, 'rb'), 'application/x-subrip'),
    }

    data = {
        'language': language,
    }

    response = requests.post(url, headers=HEADERS, cookies=COOCKIES, data=data, files=files)

    if response.ok:
        result = response.json()
        return result.get("data") 
    else:
        print("Failed:", response.status_code, response.text)
        return None


async def create_three(
    type_,
    imdb_id,
    title,
    age_rating="",
    directors=None,
    actors=None,
    authors=None,
    countries=None,
    languages=None,
    categories=None,
    companies=None,
    genres=None,
    status=None,
):
    directors = directors or []
    actors = actors or []
    authors = authors or []
    countries = countries or []
    languages = languages or []
    categories = categories or []
    companies = companies or []
    genres = genres or []

    json_data = {
        'title': title,
        'imdb_id': imdb_id,
        'age_rating': age_rating,
        'directors': directors,
        'actors': actors,
        'authors': authors,
        'countries': countries,
        'languages': languages,
        'categories': categories,
        'companies': companies,
        'genres': genres,
        'status':status
    }
    response = requests.post(
        f'{BASE_URL}/three/{type_}',
        cookies=COOCKIES,
        headers=HEADERS,
        json=json_data
    )

    return response.json()


async def create_season(
    type_,
    series_id,
    title,
    description="",
    season=1,
    status="",
    logo_url="",
    poster_url="",
    backdrop_url="",
    mobile_backdrop="",
    trailer_url="",
    release_year=None,
    episode_count=None,
    hot_video_url="",
    dubbed=False
):
    json_data = {
        'title': title,
        'description': description,
        'season': season,
        'status': status,
        'logo_url': logo_url,
        'poster_url': poster_url,
        'backdrop_url': backdrop_url,
        'mobile_backdrop': mobile_backdrop,
        'trailer_url': trailer_url,
        'release_year': release_year,
        'episode_count': episode_count,
        'hot_video_url': hot_video_url,
        'dubbed': dubbed,
    }
    response = requests.post(
        f'{BASE_URL}/season/{type_}?id={series_id}',
        cookies=COOCKIES,
        headers=HEADERS,
        json=json_data
    )

    return response.json()


async def create_episode(
    type_,
    season_id,
    episode,
    title,
    description="",
    image="",
    air_date=None,
    duration=0,
    subtitles=None,
    free_video_sources=None,
    free_download_links=None,
    free_third_party_links=None,
    free_pixel_videos=None,
    paid_video_sources=None,
    paid_download_links=None,
    paid_third_party_links=None,
    paid_pixel_videos=None
):
    subtitles = subtitles or []
    
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
        'episode': episode,
        'title': title,
        'description': description,
        'image': image,
        'air_date': air_date,
        'duration': duration,
        'subtitles': subtitles,
        'free': {
            'video_sources': free_video_sources,
            'download_links': free_download_links,
            'third_party_video_links': free_third_party_links,
            'pixel_videos': free_pixel_videos,
        },
        'paid': {
            'video_sources': paid_video_sources,
            'download_links': paid_download_links,
            'third_party_video_links': paid_third_party_links,
            'pixel_videos': paid_pixel_videos,
        },
    }

    response = requests.post(
        f'{BASE_URL}/episode/{type_}?id={season_id}',
        cookies=COOCKIES,
        headers=HEADERS,
        json=json_data
    )

    return response.json()


async def search(query: str):
    """Search for content using the admin API"""
    url = f'{BASE_URL}/search?q={query}'
    
    response = requests.get(
        url,
        cookies=COOCKIES,
        headers=HEADERS
    )
    
    return response.json()


