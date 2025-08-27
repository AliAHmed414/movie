import requests
from insert.admin import upload_movie

TMDB_API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

TMDB_HEADERS = {
    "accept": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
}
def get_movie_data(imdb_id: str):
    """
    Fetch movie details from TMDB by IMDb ID and return
    a dict ready for upload_movie().
    """
    # Step 1: Find movie by IMDb ID
    url = f"{TMDB_API_BASE}/find/{imdb_id}?external_source=imdb_id"
    res = requests.get(url, headers=TMDB_HEADERS)
    res.raise_for_status()
    data = res.json()

    if not data.get("movie_results"):
        raise ValueError(f"No movie found for IMDb ID {imdb_id}")

    movie = data["movie_results"][0]
    movie_id = movie["id"]

    # Step 2: Get full details (runtime, genres, videos, credits, production, etc.)
    details_url = f"{TMDB_API_BASE}/movie/{movie_id}?append_to_response=videos,credits"
    details = requests.get(details_url, headers=TMDB_HEADERS).json()

    # Trailer (YouTube only)
    trailer_url = ""
    for v in details.get("videos", {}).get("results", []):
        if v["type"] == "Trailer" and v["site"] == "YouTube":
            trailer_url = f"https://www.youtube.com/watch?v={v['key']}"
            break

    # Directors, Actors, Authors
    directors = [c["name"] for c in details.get("credits", {}).get("crew", []) if c.get("job") == "Director"]
    authors = [c["name"] for c in details.get("credits", {}).get("crew", []) if c.get("job") in ["Writer", "Screenplay"]]
    actors = [c["name"] for c in details.get("credits", {}).get("cast", [])[:10]]  # top 10 actors

    # Companies, Countries
    companies = [c["name"] for c in details.get("production_companies", [])]
    countries = [c["name"] for c in details.get("production_countries", [])]

    # Genres, Languages
    genres = [g["name"] for g in details.get("genres", [])]
    languages = [details.get("original_language", "")]

    # Rating (if provided)
    age_rating = details.get("adult", False)
    age_rating = "18+" if age_rating else "PG"

    # Ensure release_year is an int (not a string!)
    release_year = 0
    if details.get("release_date"):
        try:
            release_year = int(details["release_date"][:4])
        except ValueError:
            release_year = 0

    return {
        "title": details.get("title", ""),
        "imdb_id": imdb_id,
        "description": details.get("overview", ""),
        "duration": details.get("runtime", 0),
        "release_year": release_year,   # ✅ now an int
        "poster_url": f"{IMAGE_BASE_URL}{details['poster_path']}" if details.get("poster_path") else "",
        "backdrop_url": f"{IMAGE_BASE_URL}{details['backdrop_path']}" if details.get("backdrop_path") else "",
        "mobile_url": f"{IMAGE_BASE_URL}{details['poster_path']}" if details.get("poster_path") else "",
        "trailer_url": trailer_url,
        "logo_url": "",
        "hot_video_url": "",
        "status": "released" if details.get("status") == "Released" else details.get("status", ""),
        "age_rating": age_rating,
        "subtitles": [],
        "directors": directors,
        "actors": actors,
        "authors": authors,
        "companies": companies,
        "countries": countries,
        "genres": genres,
        "languages": languages,
        "categories": ['asds'],
        "dubbed": False,
        "free_video_sources": None,
        "free_download_links": None,
        "free_third_party_links": None,
        "paid_video_sources": None,
        "paid_download_links": None,
        "paid_third_party_links": None,
    }


async def main():
    list = ["tt0111161","tt0068646","tt0468569","tt0071562","tt0050083","tt0167260","tt0108052","tt0110912","tt0120737","tt0060196","tt0109830","tt0167261","tt0137523","tt1375666","tt0080684","tt0133093","tt0099685","tt0816692","tt0073486","tt0114369","tt0038650","tt0102926","tt0047478","tt0120815","tt0120689","tt0317248","tt0118799","tt0103064","tt0076759","tt0088763","tt0245429","tt0253474","tt0172495","tt6751668","tt0054215","tt0110357","tt0095327","tt0407887","tt2582802","tt0056058","tt0482571","tt0120586","tt0110413","tt9362722","tt0034583","tt0095765","tt0114814","tt1675434","tt0078748","tt0027977","tt0047396","tt1853728","tt0064116","tt0021749","tt0078788","tt0910970","tt0209144","tt15239678","tt0082971","tt4154756","tt0405094","tt0043014","tt4633694","tt0051201","tt0050825","tt0081505","tt0032553","tt0361748","tt23849204","tt0090605","tt1345836","tt2380307","tt0086879","tt4154796","tt0114709","tt0119217","tt0057565","tt0057012","tt0364569","tt0082096","tt0112573","tt5311514","tt0119698","tt0169547","tt1187043","tt7286456","tt8267604","tt0087843","tt0045152","tt0091251","tt0180093","tt0086190","tt0435761","tt2106476","tt0044741","tt0338013","tt1255953","tt0053604","tt0056172","tt0062622","tt0105236","tt0086250","tt0113277","tt0036775","tt0053125","tt1049413","tt0022100","tt0033467","tt0093058","tt0052357","tt0211915","tt0986264","tt1832382","tt0056592","tt0095016","tt0097576","tt0070735","tt0066921","tt0017136","tt15398776","tt0208092","tt8579674","tt0119488","tt0252488","tt0040522","tt0363163","tt5074352","tt0993846","tt6966692","tt8503618","tt0120382","tt0075314","tt0372784","tt0059578","tt0055031","tt1130884","tt0053291","tt0107290","tt0012349","tt10272386","tt0042192","tt0469494","tt0167404","tt0089881","tt0112641","tt1745960","tt0477348","tt0084787","tt0105695","tt0457430","tt0266697","tt0268978","tt1392214","tt0040897","tt0055630","tt0266543","tt0347149","tt0346336","tt0057115","tt0071853","tt0080678","tt4729430","tt0046912","tt0031381","tt1305806","tt0071315","tt0120735","tt0042876","tt0434409","tt2096673","tt5027774","tt0264464","tt0117951","tt0050212","tt0081398","tt1201607","tt29623480","tt0116282","tt1291584","tt0405159","tt1205489","tt0052618","tt0097165","tt1392190","tt0072684","tt0096283","tt0118849","tt2119532","tt2278388","tt2024544","tt0112471","tt10872600","tt0083658","tt0353969","tt2267998","tt0382932","tt0892769","tt0198781","tt0107207","tt0073195","tt3011894","tt0015864","tt1950186","tt0015324","tt0978762","tt0077416","tt0046268","tt0017925","tt0031679","tt0047296","tt3315342","tt0075148","tt0050986","tt0046438","tt0041959","tt1895587","tt0325980","tt26548265","tt0088247","tt0118715","tt0113247","tt0050976","tt3170832","tt15097216","tt0395169","tt0091763","tt0036868","tt0381681","tt0059742","tt0070047","tt0317705","tt1028532","tt1979320","tt0032138","tt0019254","tt0092005","tt5323662","tt0129167","tt0476735","tt0074958","tt4016934","tt0058946","tt0032551","tt0035446","tt0758758","tt1454029","tt0107048","tt4430212","tt11032374","tt1954470"]
    for imdb_id in list:
        movie_data = get_movie_data(imdb_id)
        data = await upload_movie(**movie_data)




if __name__ == "__main__":
    import asyncio
    asyncio.run(main())