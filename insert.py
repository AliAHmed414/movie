import insert
import json
from tvshow import series_info
from movies.movie_info.translate_title_description import translate_description_only,translate_title_only

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
import re
import logging



def safe_detect_language(text, expected_lang="ar"):
    """Safely detect language with error handling"""
    try:
        if not text or not text.strip():
            return False
        detected = detect(text.strip())
        return detected == expected_lang
    except (LangDetectException, Exception):
        return False

async def main():
 


    read_file = '/home/kda/Pictures/bot/for_help.series.json'


    ids = json.loads(open(read_file, 'r').read())
    for id in ids:
        tmdb_id = id['tmdb_id']
        imdb_id = id['imdb_id']

        data =series_info.fetch_series_data_by_tmdb(tmdb_id)

        name_ar = data.get('name_ar', '')
        name_en = data.get('name_en', '')
        overview_en = data.get('overview_en', '')
        overview_ar = data.get('overview_ar', '')

        # Collapse multiple spaces and trim before translating
        name_en = re.sub(r"\s+", " ", name_en).strip()
        overview_en = re.sub(r"\s+", " ", overview_en).strip()

        # Fallback translation if Arabic is missing or incorrect
        if not name_ar or not safe_detect_language(name_ar, "ar"):
            name_ar = translate_title_only(name_en)

            # ✅ Ensure it's a dictionary
            if isinstance(name_ar, dict):
                name_ar = name_ar.get('title', '')
            else:
                print(f"❌ Unexpected response from translate_name_description: {name_ar}")
                name_ar = name_ar or ''

        # Construct the final values
        name = f"{name_en}|{name_ar}" if name_ar else name_en
        if not overview_ar or not safe_detect_language(overview_ar, 'ar'):
            if overview_en !='':
                overview_ar = translate_description_only(overview_en)
                overview_ar = overview_ar.get('description', '')
            else:
                overview_ar = 'null'
        else:
            overview_ar = overview_ar
        description = f"{overview_en}|{overview_ar}" if overview_ar else overview_en

        # Clean up final description
        description = re.sub(r"\s+", " ", description).strip()
        description = re.sub(r"[-]{2,}", " ", description)
        description = re.sub(r"[.]{2,}", " ", description)
        description = description.replace('"', '')
        final_id = f"{tmdb_id}|{imdb_id}"
        directors = data.get('directors', [])
        actors = data.get('cast', [])
        authors = data.get('creators', [])
        countries = data.get('production_countries', [])
        languages = data.get('original_language', [])
        categories = ['series']
        seen = set()
        companies = []
        for c in data.get('production_companies', []) + data.get('networks', []):
            if c not in seen:
                seen.add(c)
                companies.append(c)
        genres_ar = data.get('genres_ar', [])
        genres_en = data.get('genres_en', [])
        genres = [*genres_ar, *genres_en]
        status = data.get("status")

        tmdb_to_enum = {
            "Planned": "upcoming",
            "In Production": "upcoming",
            "Pilot": "released",
            "Returning Series": "released",
            "Ended": "completed",
            "Canceled": "completed",
        }

        content_status = tmdb_to_enum.get(status, None)
        print(content_status+"**************"+ tmdb_id)

        try:
            res = await insert.create_three(
                    type_='anime',
                    imdb_id=final_id,
                    title=name,
                    age_rating=data.get('age_rating', ''),
                    directors=directors,
                    actors=actors,
                    authors=authors,
                    countries=countries,
                    languages=[languages or 'null'],
                    categories=categories,
                    companies=companies,
                    genres=genres,
                    status=content_status
                )
            
            if res.get("response", {}).get("code") == 201:
                series_id = res.get('data')
                # Only log errors, remove success message
            else:
                logging.error(f"❌ Failed to insert series: {name} (TMDB: {tmdb_id}). Response: {res}")
                continue  # Skip to next series if series insertion failed
        except Exception as e:
            logging.error(f"❌ Error inserting series {name} (TMDB: {tmdb_id}): {str(e)}")
            continue
            
        for season in data.get('seasons', []):

                
                season_number= season.get('season_number')
                release_date = data.get("first_air_date")  
                if release_date and "-" in release_date:
                    release_year = int(release_date.split("-")[0])
                elif release_date:  # only a year like "2025"
                    release_year = int(release_date)
                else:
                    release_year = 1950

                if season_number == 1:
                    season_poster=data['poster']
                    season_backdrop = data['backdrop']
                    season_logo = data['poster']
                    
                    try:
                        season_res = await insert.create_season(
                            type_='anime',
                            series_id=series_id,
                            title=name,
                            description=description,
                            season=season_number,
                            logo_url=season_logo,
                            poster_url=season_poster,
                            backdrop_url=season_backdrop,
                            release_year=release_year,
                            episode_count=season.get('episode_count'),
                            trailer_url=data.get('trailer', ''),
                        )

                        if season_res.get("response", {}).get("code") == 200:
                            season_sql_id = season_res.get("data")
                            # Only log errors, remove success message
                        else:
                            logging.error(f"  Failed to insert Season {season_number} for {name}. Response: {season_res}")
                    except Exception as e:
                        logging.error(f"  Error inserting Season {season_number} for {name}: {str(e)}")
                    continue
                
                overview_en = season.get('overview_en', 'null')
                overview_ar = season.get('overview_ar', '')
                if not overview_ar or not safe_detect_language(overview_ar, 'ar'):
                    if overview_ar != '':
                        overview_ar = translate_description_only(overview_en)
                        overview_ar = overview_ar.get('description', '')
                    else:
                        overview_ar = 'null'
                if overview_en == '':
                    overview_en = 'null'

                overview_season = f"{overview_en}|{overview_ar}" if overview_ar else overview_en
                try:
                    season_res = await insert.create_season(
                        type_='anime',
                        series_id=series_id,ba
                        title=name,
                        description=overview_season,
                        season=season_number,
                        logo_url=season.get('logo', ''),
                        poster_url=season.get('poster', ''),
                        backdrop_url=season.get('backdrop', ''),
                        release_year=release_year,
                        episode_count=season.get('episode_count',0),
                        trailer_url=season.get('trailer', 'null'),
                    )

                    if season_res.get("response", {}).get("code") == 200:
                        season_sql_id = season_res.get("data")
                        logging.info(f"  Successfully inserted Season {season_number} for {name} (SQL ID: {season_sql_id})")
                    else:
                        logging.error(f"  Failed to insert Season {season_number} for {name}. Response: {season_res}")
                except Exception as e:
                    logging.error(f"  Error inserting Season {season_number} for {name}: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())