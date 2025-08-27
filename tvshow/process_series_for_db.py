import csv
import os
from typing import Dict, List, Any
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import requests

# TMDB API Configuration
TMDB_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def get_tmdb_series_info(title: str, year: str = None) -> Dict:
    """
    Fetch series information from TMDB API
    
    Args:
        title: Series title
        year: Release year (optional)
        
    Returns:
        Dictionary containing series information or error message
    """
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {TMDB_API_KEY}"
    }
    
    # Search for the series
    search_url = f"{TMDB_BASE_URL}/search/tv?query={title}"
    if year and year != '0':
        search_url += f"&first_air_date_year={year}"
    
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('results'):
            return {"error": f"No results found for '{title}'"}
            
        # Get the first result
        series_data = data['results'][0]
        series_id = series_data['id']
        
        # Get detailed series info including external IDs
        details_url = f"{TMDB_BASE_URL}/tv/{series_id}?language=en-US"
        details_response = requests.get(details_url, headers=headers)
        details_response.raise_for_status()
        details = details_response.json()
        
        # Get external IDs (includes IMDB ID)
        external_ids_url = f"{TMDB_BASE_URL}/tv/{series_id}/external_ids"
        external_response = requests.get(external_ids_url, headers=headers)
        external_response.raise_for_status()
        external_ids = external_response.json()
        
        # Get seasons info
        seasons = []
        for season in details.get('seasons', []):
            if season['season_number'] > 0:  # Skip special seasons (season 0)
                seasons.append({
                    'season_number': season['season_number'],
                    'episode_count': season['episode_count']
                })
        
        return {
            'tmdb_id': series_id,
            'imdb_id': external_ids.get('imdb_id', ''),
            'title': details.get('name', title),
            'year': year,
            'seasons': seasons,
            'original_title': details.get('original_name', ''),
            'overview': details.get('overview', ''),
            'poster_path': f"https://image.tmdb.org/t/p/original{details.get('poster_path', '')}" if details.get('poster_path') else None,
            'backdrop_path': f"https://image.tmdb.org/t/p/original{details.get('backdrop_path', '')}" if details.get('backdrop_path') else None
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching data from TMDB: {str(e)}"}

def create_episode_structure(episode_count: int) -> List[Dict[str, str]]:
    """
    Create a list of episode status dictionaries.
    
    Args:
        episode_count: Number of episodes in the season
        
    Returns:
        List of episode status dictionaries with string keys for MongoDB compatibility
    """
    return [{str(i+1): 'pending'} for i in range(episode_count)]

def process_series_list(csv_path: str) -> None:
    """
    Process a list of series from CSV and insert into MongoDB
    
    Args:
        csv_path: Path to the input CSV file
    """
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://generic:generic@cluster0.jpbz8z6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client['for_help']
    collection = db['series']
    
    # Create index on tmdb_id to prevent duplicates
    collection.create_index('tmdb_id', unique=True)
    
    # Track stats
    total_processed = 0
    inserted_count = 0
    duplicate_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            title = row['title']
            year = row['year']
            
            print(f"Processing: {title} ({year})...")
            total_processed += 1
            
            try:
                # Fetch series data from TMDB
                series_info = get_tmdb_series_info(title, year if year != '0' else None)
                
                if 'error' in series_info:
                    print(f"  {series_info['error']}")
                    continue
                
                # Create the series entry
                series_entry = {
                    'tmdb_id': str(series_info['tmdb_id']),  # Convert to string for consistency
                    'imdb_id': series_info['imdb_id'],
                    'title': series_info['title'],
                    'year': series_info['year'],
                    'season': [],
                    'sql_db_id': ''
                }
                
                # Add seasons and episodes
                for season in series_info.get('seasons', []):
                    season_num = season['season_number']
                    episode_count = season['episode_count']
                    
                    season_entry = {
                        str(season_num): create_episode_structure(episode_count),
                        'season_status': 'pending',
                        'sql_db_id': ''
                    }
                    series_entry['season'].append(season_entry)
                
                # Insert into MongoDB
                try:
                    collection.insert_one(series_entry)
                    inserted_count += 1
                    print(f"  Inserted {series_entry['title']} with {len(series_entry['season'])} seasons")
                except DuplicateKeyError:
                    duplicate_count += 1
                    print(f"  Duplicate found: {series_entry['title']} (TMDB ID: {series_entry['tmdb_id']})")
                
            except Exception as e:
                print(f"  Error processing {title}: {str(e)}")
                continue
    
    # Print summary
    print("\nProcessing complete!")
    print(f"Total processed: {total_processed}")
    print(f"Newly inserted: {inserted_count}")
    print(f"Duplicates skipped: {duplicate_count}")
    print(f"Total in database: {collection.count_documents({})}")
    
    # Close the connection
    client.close()

if __name__ == "__main__":
    # Define CSV path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(os.path.dirname(current_dir), 'track-server', 'series_title_year.csv')
    
    # Process the series list
    process_series_list(csv_path)
