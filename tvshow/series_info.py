import argparse
import requests
import json





def fetch_series_data_by_tmdb(tmdb_id: str):
    """Fetch TV series data by TMDB ID using append_to_response for efficiency"""
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

    # It's recommended to store your API key securely, e.g., in an environment variable
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
    }

    def get_json(url):
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return {}

    # Single request with all main data appended - reduces from 7 requests to 2!
    append_params = "external_ids,credits,videos,images,content_ratings"
    en = get_json(f"{TMDB_API_BASE}/tv/{tmdb_id}?language=en-US&append_to_response={append_params}")
    ar = get_json(f"{TMDB_API_BASE}/tv/{tmdb_id}?language=ar")
    epsiode_info = get_json(f"{TMDB_API_BASE}/tv/{tmdb_id}/season/1/episode/1?language=en-US")
    

    if not en: # If the primary API call fails, exit early
        return None

    # Extract data from the single response
    ext = en.get("external_ids", {})
    credits = en.get("credits", {})
    vids = en.get("videos", {}).get("results", [])
    images = en.get("images", {})
    content_ratings = en.get("content_ratings", {}).get("results", [])

    # Age Rating / Content Rating
    age_rating = None
    for rating in content_ratings:
        if rating.get("iso_3166_1") == "US":
            age_rating = rating.get("rating")
            break

    # Logo - comprehensive approach to find series logo
    logo_url = None
    all_logos = images.get("logos", [])
    if all_logos:
        en_logos = [l for l in all_logos if l.get("iso_639_1") == "en"]
        chosen_logo = en_logos[0] if en_logos else all_logos[0]
        if chosen_logo.get("file_path"):
            logo_url = IMAGE_BASE_URL + chosen_logo["file_path"]

    if not logo_url:
        alternative_images = get_json(f"{TMDB_API_BASE}/tv/{tmdb_id}/images?include_image_language=en,null")
        alt_logos = alternative_images.get("logos", [])
        if alt_logos and alt_logos[0].get("file_path"):
            logo_url = IMAGE_BASE_URL + alt_logos[0]["file_path"]

    if not logo_url and en.get("networks"):
        network = en["networks"][0]
        if network.get("logo_path"):
            logo_url = IMAGE_BASE_URL + network["logo_path"]

    # Get seasons information with detailed data
    seasons_info = []
    for season in en.get("seasons", []):
        if season.get("season_number", 0) > 0:
            season_num = season["season_number"]
            season_append_params = "images,videos"
            season_en = get_json(f"{TMDB_API_BASE}/tv/{tmdb_id}/season/{season_num}?language=en-US&append_to_response={season_append_params}")
            season_ar = get_json(f"{TMDB_API_BASE}/tv/{tmdb_id}/season/{season_num}?language=ar")
            
            season_images = season_en.get("images", {})
            season_videos = season_en.get("videos", {}).get("results", [])
            
            season_en_logos = [l for l in season_images.get("logos", []) if l.get("iso_639_1") == "en"]
            season_logo_url = IMAGE_BASE_URL + season_en_logos[0]["file_path"] if season_en_logos and season_en_logos[0].get("file_path") else None
            
            season_poster = None
            if season_images.get("posters") and season_images["posters"][0].get("file_path"):
                season_poster = IMAGE_BASE_URL + season_images["posters"][0]["file_path"]
            elif season.get("poster_path"):
                season_poster = IMAGE_BASE_URL + season["poster_path"]

            season_backdrop = None
            if season_images.get("backdrops") and season_images["backdrops"][0].get("file_path"):
                season_backdrop = IMAGE_BASE_URL + season_images["backdrops"][0]["file_path"]

            seasons_info.append({
                "season_number": season.get("season_number"),
                "episode_count": season.get("episode_count"),
                "air_date": season.get("air_date"),
                "name": season_en.get("name"),
                "overview_en": season_en.get("overview"),
                "overview_ar": season_ar.get("overview"),
                "backdrop": season_backdrop,
                "poster": season_poster,
                "logo": season_logo_url,
                "trailer": next(
                    (f"{v['key']}"
                     for v in season_videos if v.get("site") == "YouTube" and v.get("type") == "Trailer"),
                    None
                )
            })

    # Get main series trailer URL
    trailer_key = next(
        (v['key'] for v in vids if v.get("site") == "YouTube" and v.get("type") == "Trailer"),
        None
    )
    trailer_url = f"{trailer_key}" if trailer_key else None
    print()
    # **NEW:** Extract directors from the crew list
    directors = [
        person["name"] for person in credits.get("crew", []) if person.get("job") == "Director"
    ]
    if not directors:
        directors = [person["name"] for person in epsiode_info.get("crew", []) if person.get("job") == "Director"]

    # Final result dictionary
    return {
        "tmdb_id": int(tmdb_id),
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
        "production_companies": [company["name"] for company in en.get("production_companies", [])],
        "production_countries": [country["iso_3166_1"] for country in en.get("production_countries", [])],
        "networks": [network["name"] for network in en.get("networks", [])],
        "age_rating": age_rating,
        "trailer": trailer_url,
        "creators": [creator["name"] for creator in en.get("created_by", [])],
        "directors": directors,  # Added directors here
        "cast": [cast.get("name") for cast in credits.get("cast", [])[:10]],
        "backdrop": IMAGE_BASE_URL + en["backdrop_path"] if en.get("backdrop_path") else None,
        "poster": IMAGE_BASE_URL + en["poster_path"] if en.get("poster_path") else None,
        "logo": logo_url,
        "episode_run_time": en.get("episode_run_time", []),
        "in_production": en.get("in_production"),
        "type": en.get("type"),
        'tagline': en.get("tagline", ""),
    }


def fetch_series_data_by_title_year(title: str, year: str = None):
    """Synchronous version for command line usage - optimized with append_to_response"""
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

    # Single request with all main data appended - optimized!
    append_params = "external_ids,credits,videos,images,content_ratings"
    en = get_json(f"{TMDB_API_BASE}/tv/{series_id}?language=en-US&append_to_response={append_params}")
    ar = get_json(f"{TMDB_API_BASE}/tv/{series_id}?language=ar")

    # Extract data from the single response
    ext = en.get("external_ids", {})
    credits = en.get("credits", {})
    vids = en.get("videos", {}).get("results", [])
    images = en.get("images", {})
    content_ratings = en.get("content_ratings", {}).get("results", [])

    # Age Rating / Content Rating
    age_rating = None
    for rating in content_ratings:
        if rating["iso_3166_1"] == "US":
            age_rating = rating["rating"]
            break

    # Logo
    en_logos = [l for l in images.get("logos", []) if l.get("iso_639_1") == "en"]
    logo_url = IMAGE_BASE_URL + en_logos[0]["file_path"] if en_logos else None

    # Get seasons information with detailed data - optimized with append_to_response
    seasons_info = []
    for season in en.get("seasons", []):
        if season["season_number"] > 0:  # Skip specials (season 0)
            season_num = season["season_number"]
            
            # Optimized: get season data with appended responses
            season_append_params = "images,videos"
            season_en = get_json(f"{TMDB_API_BASE}/tv/{series_id}/season/{season_num}?language=en-US&append_to_response={season_append_params}")
            season_ar = get_json(f"{TMDB_API_BASE}/tv/{series_id}/season/{season_num}?language=ar")
            
            season_images = season_en.get("images", {})
            season_videos = season_en.get("videos", {}).get("results", [])
            
            # Season logo
            season_en_logos = [l for l in season_images.get("logos", []) if l.get("iso_639_1") == "en"]
            season_logo_url = IMAGE_BASE_URL + season_en_logos[0]["file_path"] if season_en_logos else None
            
            # Get season poster and backdrop with fallbacks
            season_poster = None
            season_backdrop = None
            
            # Try to get from season images first
            if season_images.get("posters"):
                season_poster = IMAGE_BASE_URL + season_images["posters"][0]["file_path"]
            elif season.get("poster_path"):  # Fallback to basic season data
                season_poster = IMAGE_BASE_URL + season["poster_path"]
            
            if season_images.get("backdrops"):
                season_backdrop = IMAGE_BASE_URL + season_images["backdrops"][0]["file_path"]
            
            seasons_info.append({
                "season_number": season["season_number"],
                "episode_count": season["episode_count"],
                "air_date": season.get("air_date"),
                "name": season.get("name"),
                "overview": season_en.get("overview"),
                "overview_ar": season_ar.get("overview"),
                "backdrop": season_backdrop,
                "poster": season_poster,
                "logo": season_logo_url,
                "trailer": next(
                    (v['key']
                     for v in season_videos if v["site"] == "YouTube" and v["type"] == "Trailer"),
                    None
                )
            })

    # Get trailer URL (full YouTube URL instead of just key)
    trailer_key = next(
        (v['key'] for v in vids if v["site"] == "YouTube" and v["type"] == "Trailer"),
        None
    )
    trailer_url = f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else None

    # Final result dict - use series data for poster/backdrop, not images endpoint
    entry = {
        "tmdb_id": series_id,
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
        "trailer": trailer_url,
        "creators": [c["name"] for c in en.get("created_by", [])],
        "cast": [c["name"] for c in credits.get("cast", [])[:10]],
        "backdrop": IMAGE_BASE_URL + en["backdrop_path"] if en.get("backdrop_path") else None,
        "poster": IMAGE_BASE_URL + en["poster_path"] if en.get("poster_path") else None,
        "logo": logo_url,
        "episode_run_time": en.get("episode_run_time", []),
        "in_production": en.get("in_production"),
        "type": en.get("type")
    }

    return entry

def fetch_episode_by_imdb(imdb_id: str, season: int, episode: int):
    """Synchronous version for command line usage with optimized API calls"""
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
    
    if not (tv_results := find_resp.get("tv_results")):
        return {"error": "No TV series found with this IMDB ID."}

    series_id = tv_results[0]["id"]
    
    # Single optimized API call with append_to_response
    episode_url = (
        f"{TMDB_API_BASE}/tv/{series_id}/season/{season}/episode/{episode}?"
        "language=en-US&"
        "append_to_response=translations,images,videos"
    )
    
    episode_data = get_json(episode_url)
    if not episode_data or episode_data.get("success") is False:
        return {"error": f"Episode S{season}E{episode} not found."}

    # Extract Arabic title and overview from translations
    title_ar = overview_ar = None
    if translations := episode_data.get("translations", {}).get("translations", []):
        ar_translation = next((t for t in translations if t.get("iso_639_1") == "ar"), None)
        if ar_translation:
            title_ar = ar_translation.get("data", {}).get("name")
            overview_ar = ar_translation.get("data", {}).get("overview")

    return {
        "title_en": episode_data.get("name"),
        "title_ar": title_ar,
        "overview_en": episode_data.get("overview"),
        "overview_ar": overview_ar,
        "image": f"{IMAGE_BASE_URL}{episode_data['still_path']}" if episode_data.get("still_path") else None,
        "duration": episode_data.get("runtime"),
        "videos": [v for v in episode_data.get("videos", {}).get("results", []) if v.get("site") == "YouTube"]
    }

def fetch_episode_by_tmdb(tmdb_id: str, season: int, episode: int):
    """Synchronous version for command line usage with optimized API calls"""
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
  
    


    
    
    # Single optimized API call with append_to_response
    episode_url = (
        f"{TMDB_API_BASE}/tv/{tmdb_id}/season/{season}/episode/{episode}?"
        "language=en-US&"
        "append_to_response=translations,images,videos"
    )
    
    episode_data = get_json(episode_url)
    if not episode_data or episode_data.get("success") is False:
        return {"error": f"Episode S{season}E{episode} not found."}

    # Extract Arabic title and overview from translations
    title_ar = overview_ar = None
    if translations := episode_data.get("translations", {}).get("translations", []):
        ar_translation = next((t for t in translations if t.get("iso_639_1") == "ar"), None)
        if ar_translation:
            title_ar = ar_translation.get("data", {}).get("name")
            overview_ar = ar_translation.get("data", {}).get("overview")

    return {
        "title_en": episode_data.get("name"),
        "title_ar": title_ar,
        "overview_en": episode_data.get("overview"),
        "overview_ar": overview_ar,
        "image": f"{IMAGE_BASE_URL}{episode_data['still_path']}" if episode_data.get("still_path") else None,
        "duration": episode_data.get("runtime"),
        "videos": [v for v in episode_data.get("videos", {}).get("results", []) if v.get("site") == "YouTube"]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch TMDB TV series or episode data")
    parser.add_argument("--title", help="TV series title to search for")
    parser.add_argument("--year", help="First air date year (optional)")
    parser.add_argument("--imdb", help="IMDB ID for episode query (e.g., tt0903747)")
    parser.add_argument("--season", type=int, help="Season number for episode query")
    parser.add_argument("--episode", type=int, help="Episode number for episode query")
    parser.add_argument("--tmdb",  help="Output result as JSON with TMDB ID")
    args = parser.parse_args()

    if args.imdb and args.season is not None and args.episode is not None:
        # Fetch episode data by IMDB ID
        result = fetch_episode_by_imdb(args.imdb, args.season, args.episode)
    elif args.title:
        # Fetch series data by title
        result = fetch_series_data_by_title_year(args.title, args.year)
    elif args.tmdb and args.season is not None and args.episode is not None:
        # Fetch episode data by TMDB ID
        result = fetch_episode_by_tmdb(args.tmdb, args.season, args.episode)
    elif args.tmdb:
        # Fetch series data by TMDB ID
        result = fetch_series_data_by_tmdb(args.tmdb)
    else:
        parser.error("Either --title or (--imdb --season --episode) is required")
    
    print(json.dumps(result, ensure_ascii=False, indent=2))