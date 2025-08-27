from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from functools import wraps
import json

app = Flask(__name__)

# MongoDB connection
client = MongoClient("mongodb+srv://generic:generic@cluster0.jpbz8z6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['for_help']
collection = db['series']

def json_response(data=None, status=200, message=None):
    """Helper function to create JSON responses"""
    response = {}
    if data is not None:
        response['data'] = data
    if message is not None:
        response['message'] = message
    return jsonify(response), status

@app.route('/series/<series_id>/season/<int:season_number>', methods=['PUT'])
def update_season_status(series_id, season_number):
    # Get request data
    data = request.get_json()
    if not data:
        return json_response(status=400, message="No data provided")

    # Find the series
    series = collection.find_one({"_id": ObjectId(series_id)})
    if not series:
        return json_response(status=404, message="Series not found")

    # Find and update the season
    season_updated = False
    for season in series.get('season', []):
        if str(season_number) in season:
            if 'status' in data:
                season['season_status'] = data['status']
            if 'sql_db_id' in data:
                season['sql_db_id'] = data['sql_db_id']
            season_updated = True
            break

    if not season_updated:
        return json_response(status=404, message=f"Season {season_number} not found")

    # Update the document
    result = collection.update_one(
        {"_id": ObjectId(series_id)},
        {"$set": {"season": series['season']}}
    )

    if result.modified_count == 0:
        return json_response(status=500, message="Failed to update season status")

    return json_response(message=f"Season {season_number} status updated")

@app.route('/series/<series_id>/season/<int:season_number>/episode/<int:episode_number>', methods=['PUT'])
def update_episode_status(series_id, season_number, episode_number):
    # Get request data
    data = request.get_json()
    if not data or 'status' not in data:
        return json_response(status=400, message="Status is required")

    # Find the series
    series = collection.find_one({"_id": ObjectId(series_id)})
    if not series:
        return json_response(status=404, message="Series not found")

    # Find and update the episode
    episode_updated = False
    for season in series.get('season', []):
        if str(season_number) in season:
            episodes = season[str(season_number)]
            for episode in episodes:
                if str(episode_number) in episode:
                    episode[str(episode_number)] = data['status']
                    episode_updated = True
                    break
            break

    if not episode_updated:
        return json_response(status=404, message=f"Episode {episode_number} in season {season_number} not found")

    # Update the document
    result = collection.update_one(
        {"_id": ObjectId(series_id)},
        {"$set": {"season": series['season']}}
    )

    if result.modified_count == 0:
        return json_response(status=500, message="Failed to update episode status")

    return json_response(message=f"Season {season_number} Episode {episode_number} status updated")

@app.route('/series/<series_id>/sql_id', methods=['PUT'])
def update_series_sql_id(series_id):
    sql_id = request.args.get('sql_id')
    if not sql_id:
        return json_response(status=400, message="sql_id parameter is required")

    result = collection.update_one(
        {"_id": ObjectId(series_id)},
        {"$set": {"sql_db_id": sql_id}}
    )

    if result.matched_count == 0:
        return json_response(status=404, message="Series not found or no changes made")

    return json_response(message=f"SQL ID updated for series {series_id}")

@app.route('/series/first', methods=['GET'])
def get_first_unprocessed_series():
    """
    Get the first pending episode from any season where season_status is 'working' and has sql_id
    """
    # Find all series with year != 0
    series = collection.find_one({"year": {"$ne": 0}})
 
    if not series:
        return json_response(status=404, message="No unprocessed series found")
    # Find the first pending episode in any working season with sql_id
    for season in series.get('season', []):
        if season.get('season_status') != 'working' and season.get('season_status') != 'pending' :
            continue
                
            # Find the first season number (key that's not 'season_status' or 'sql_db_id')
        season_num = next((k for k in season.keys() if k not in ['season_status', 'sql_db_id']), None)
        if not season_num:
            continue
            
        # Find first pending episode
        episodes = season[season_num]
        print(episodes)
        for episode in episodes:
            ep_num, status = next(iter(episode.items()))
            if status == 'pending':
                return json_response(data={
                    'imdb_id': series.get('imdb_id', ''),
                    'tmdb_id': series.get('tmdb_id', ''),
                    'series_id': str(series['_id']),
                    'series_title': series.get('title', ''),
                    'season_number': int(season_num),
                    'episode_number': int(ep_num),
                    'series_sql_id': series.get('sql_db_id', ''),
                    'season_sql_id': season.get('sql_db_id', '')
                    })
    
    return json_response(status=404, message="No pending episodes found in working seasons with sql_id")

@app.route('/series/<series_id>/mark-processed', methods=['PUT'])
def mark_series_processed(series_id):
    """
    Set the year of a series to 0 to mark it as processed
    """
    result = collection.update_one(
        {"_id": ObjectId(series_id)},
        {"$set": {"year": 0}}
    )

    if result.matched_count == 0:
        return json_response(status=404, message="Series not found")

    return json_response(message=f"Series {series_id} marked as processed (year set to 0)")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
