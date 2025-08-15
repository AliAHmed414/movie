import argparse
import requests
import json

async def fetch_series_data_by_title_year(title: str, year: str = None):
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
    }

    def get_json(url):
        resp = requests.get(url, headers=headers)
        return resp.json() if resp.ok else {}

    # Search for TV series by title and year
    search_url = f"{TMDB_API_BASE}/search/tv?query={title}"
    if year:
        search_url += f"&first_air_date_year={year}"
    
    search_resp = get_json(search_url)
    tv_results = search_resp.get("results", [])
    
    if not tv_results:
        return {"error": "No TV series found with this title and year."}

    # Get the first (most relevant) result
    series = tv_results[0]
    series_id = series["id"]

    # Fetch detailed information
    ext = get_json(f"{TMDB_API_BASE}/tv/{series_id}/external_ids")
    en = get_json(f"{TMDB_API_BASE}/tv/{series_id}?language=en-US")
    ar = get_json(f"{TMDB_API_BASE}/tv/{series_id}?language=ar")
    credits = get_json(f"{TMDB_API_BASE}/tv/{series_id}/credits")
    vids = get_json(f"{TMDB_API_BASE}/tv/{series_id}/videos").get("results", [])
    images = get_json(f"{TMDB_API_BASE}/tv/{series_id}/images")
    content_ratings = get_json(f"{TMDB_API_BASE}/tv/{series_id}/content_ratings").get("results", [])

    # Age Rating / Content Rating
    age_rating = None
    for rating in content_ratings:
        if rating["iso_3166_1"] == "US":
            age_rating = rating["rating"]
            break

    # Logo
    en_logos = [l for l in images.get("logos", []) if l.get("iso_639_1") == "en"]
    logo_url = IMAGE_BASE_URL + en_logos[0]["file_path"] if en_logos else None

    # Get seasons information
    seasons_info = []
    for season in en.get("seasons", []):
        if season["season_number"] > 0:  # Skip specials (season 0)
            seasons_info.append({
                "season_number": season["season_number"],
                "episode_count": season["episode_count"],
                "air_date": season.get("air_date"),
                "name": season.get("name"),
                "overview": season.get("overview")
            })

    # Final result dict
    entry = {
        "name_en": en.get("name"),
        "name_ar": ar.get("name"),
        "overview_en": en.get("overview"),
        "overview_ar": ar.get("overview"),
        "number_of_seasons": en.get("number_of_seasons"),
        "number_of_episodes": en.get("number_of_episodes"),
        "seasons": seasons_info,
        "genres_en": [g["name"] for g in en.get("genres", [])],
        "genres_ar": [g["name"] for g in ar.get("genres", [])],
        "imdb_id": ext.get("imdb_id"),
        "first_air_date": en.get("first_air_date", "").split("-")[0] if en.get("first_air_date") else None,
        "last_air_date": en.get("last_air_date", "").split("-")[0] if en.get("last_air_date") else None,
        "status": en.get("status"),
        "original_language": en.get("original_language"),
        "production_companies": [c["name"] for c in en.get("production_companies", [])],
        "production_countries": [c["iso_3166_1"] for c in en.get("production_countries", [])],
        "networks": [n["name"] for n in en.get("networks", [])],
        "age_rating": age_rating,
        "trailer": next(
            (f"https://www.youtube.com/watch?v={v['key']}"
             for v in vids if v["site"] == "YouTube" and v["type"] == "Trailer"),
            None
        ),
        "creators": [c["name"] for c in en.get("created_by", [])],
        "cast": [c["name"] for c in credits.get("cast", [])[:10]],
        "backdrop": IMAGE_BASE_URL + images["backdrops"][0]["file_path"] if images.get("backdrops") else None,
        "poster": IMAGE_BASE_URL + images["posters"][0]["file_path"] if images.get("posters") else None,
        "logo": logo_url,
        "episode_run_time": en.get("episode_run_time", []),
        "in_production": en.get("in_production"),
        "type": en.get("type")
    }

    return entry


def fetch_series_data_by_title_year_sync(title: str, year: str = None):
    """Synchronous version for command line usage"""
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
    }

    def get_json(url):
        resp = requests.get(url, headers=headers)
        return resp.json() if resp.ok else {}

    # Search for TV series by title and year
    search_url = f"{TMDB_API_BASE}/search/tv?query={title}"
    if year:
        search_url += f"&first_air_date_year={year}"
    
    search_resp = get_json(search_url)
    tv_results = search_resp.get("results", [])
    
    if not tv_results:
        return {"error": "No TV series found with this title and year."}

    # Get the first (most relevant) result
    series = tv_results[0]
    series_id = series["id"]

    # Fetch detailed information
    ext = get_json(f"{TMDB_API_BASE}/tv/{series_id}/external_ids")
    en = get_json(f"{TMDB_API_BASE}/tv/{series_id}?language=en-US")
    ar = get_json(f"{TMDB_API_BASE}/tv/{series_id}?language=ar")
    credits = get_json(f"{TMDB_API_BASE}/tv/{series_id}/credits")
    vids = get_json(f"{TMDB_API_BASE}/tv/{series_id}/videos").get("results", [])
    images = get_json(f"{TMDB_API_BASE}/tv/{series_id}/images")
    content_ratings = get_json(f"{TMDB_API_BASE}/tv/{series_id}/content_ratings").get("results", [])

    # Age Rating / Content Rating
    age_rating = None
    for rating in content_ratings:
        if rating["iso_3166_1"] == "US":
            age_rating = rating["rating"]
            break

    # Logo
    en_logos = [l for l in images.get("logos", []) if l.get("iso_639_1") == "en"]
    logo_url = IMAGE_BASE_URL + en_logos[0]["file_path"] if en_logos else None

    # Get seasons information
    seasons_info = []
    for season in en.get("seasons", []):
        if season["season_number"] > 0:  # Skip specials (season 0)
            seasons_info.append({
                "season_number": season["season_number"],
                "episode_count": season["episode_count"],
                "air_date": season.get("air_date"),
                "name": season.get("name"),
                "overview": season.get("overview")
            })

    # Final result dict
    entry = {
        "name_en": en.get("name"),
        "name_ar": ar.get("name"),
        "overview_en": en.get("overview"),
        "overview_ar": ar.get("overview"),
        "number_of_seasons": en.get("number_of_seasons"),
        "number_of_episodes": en.get("number_of_episodes"),
        "seasons": seasons_info,
        "genres_en": [g["name"] for g in en.get("genres", [])],
        "genres_ar": [g["name"] for g in ar.get("genres", [])],
        "imdb_id": ext.get("imdb_id"),
        "first_air_date": en.get("first_air_date", "").split("-")[0] if en.get("first_air_date") else None,
        "last_air_date": en.get("last_air_date", "").split("-")[0] if en.get("last_air_date") else None,
        "status": en.get("status"),
        "original_language": en.get("original_language"),
        "production_companies": [c["name"] for c in en.get("production_companies", [])],
        "production_countries": [c["iso_3166_1"] for c in en.get("production_countries", [])],
        "networks": [n["name"] for n in en.get("networks", [])],
        "age_rating": age_rating,
        "trailer": next(
            (f"https://www.youtube.com/watch?v={v['key']}"
             for v in vids if v["site"] == "YouTube" and v["type"] == "Trailer"),
            None
        ),
        "creators": [c["name"] for c in en.get("created_by", [])],
        "cast": [c["name"] for c in credits.get("cast", [])[:10]],
        "backdrop": IMAGE_BASE_URL + images["backdrops"][0]["file_path"] if images.get("backdrops") else None,
        "poster": IMAGE_BASE_URL + images["posters"][0]["file_path"] if images.get("posters") else None,
        "logo": logo_url,
        "episode_run_time": en.get("episode_run_time", []),
        "in_production": en.get("in_production"),
        "type": en.get("type")
    }

    return entry


async def fetch_episode_by_imdb(imdb_id: str, season: int, episode: int):
    """Fetch episode data using IMDB ID - returns title, overview, image, duration in both English and Arabic"""
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
    }

    def get_json(url):
        resp = requests.get(url, headers=headers)
        return resp.json() if resp.ok else {}

    # Find series by IMDB ID
    find_url = f"{TMDB_API_BASE}/find/{imdb_id}?external_source=imdb_id"
    find_resp = get_json(find_url)
    
    tv_results = find_resp.get("tv_results", [])
    if not tv_results:
        return {"error": "No TV series found with this IMDB ID."}

    series_id = tv_results[0]["id"]

    # Fetch episode details in both languages
    episode_url_en = f"{TMDB_API_BASE}/tv/{series_id}/season/{season}/episode/{episode}?language=en-US"
    episode_url_ar = f"{TMDB_API_BASE}/tv/{series_id}/season/{season}/episode/{episode}?language=ar"
    
    episode_data_en = get_json(episode_url_en)
    episode_data_ar = get_json(episode_url_ar)

    if not episode_data_en or episode_data_en.get("success") == False:
        return {"error": f"Episode S{season}E{episode} not found."}

    # Return episode info in both languages
    return {
        "title_en": episode_data_en.get("name"),
        "title_ar": episode_data_ar.get("name"),
        "overview_en": episode_data_en.get("overview"),
        "overview_ar": episode_data_ar.get("overview"),
        "image": IMAGE_BASE_URL + episode_data_en["still_path"] if episode_data_en.get("still_path") else None,
        "duration": episode_data_en.get("runtime")
    }


def fetch_episode_by_imdb_sync(imdb_id: str, season: int, episode: int):
    """Synchronous version for command line usage"""
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
    }

    def get_json(url):
        resp = requests.get(url, headers=headers)
        return resp.json() if resp.ok else {}

    # Find series by IMDB ID
    find_url = f"{TMDB_API_BASE}/find/{imdb_id}?external_source=imdb_id"
    find_resp = get_json(find_url)
    
    tv_results = find_resp.get("tv_results", [])
    if not tv_results:
        return {"error": "No TV series found with this IMDB ID."}

    series_id = tv_results[0]["id"]

    # Fetch episode details in both languages
    episode_url_en = f"{TMDB_API_BASE}/tv/{series_id}/season/{season}/episode/{episode}?language=en-US"
    episode_url_ar = f"{TMDB_API_BASE}/tv/{series_id}/season/{season}/episode/{episode}?language=ar"
    
    episode_data_en = get_json(episode_url_en)
    episode_data_ar = get_json(episode_url_ar)

    if not episode_data_en or episode_data_en.get("success") == False:
        return {"error": f"Episode S{season}E{episode} not found."}

    # Return episode info in both languages
    return {
        "title_en": episode_data_en.get("name"),
        "title_ar": episode_data_ar.get("name"),
        "overview_en": episode_data_en.get("overview"),
        "overview_ar": episode_data_ar.get("overview"),
        "image": IMAGE_BASE_URL + episode_data_en["still_path"] if episode_data_en.get("still_path") else None,
        "duration": episode_data_en.get("runtime")
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch TMDB TV series or episode data")
    parser.add_argument("--title", help="TV series title to search for")
    parser.add_argument("--year", help="First air date year (optional)")
    parser.add_argument("--imdb", help="IMDB ID for episode query (e.g., tt0903747)")
    parser.add_argument("--season", type=int, help="Season number for episode query")
    parser.add_argument("--episode", type=int, help="Episode number for episode query")
    args = parser.parse_args()

    if args.imdb and args.season is not None and args.episode is not None:
        # Fetch episode data by IMDB ID
        result = fetch_episode_by_imdb_sync(args.imdb, args.season, args.episode)
    elif args.title:
        # Fetch series data by title
        result = fetch_series_data_by_title_year_sync(args.title, args.year)
    else:
        parser.error("Either --title or (--imdb --season --episode) is required")
    
    print(json.dumps(result, ensure_ascii=False, indent=2))