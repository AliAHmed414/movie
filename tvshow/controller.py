import download 
import extractor
import series_info
from pymongo import MongoClient
import json
from bson import ObjectId





def main():
    client = MongoClient("mongodb+srv://generic:generic@cluster0.jpbz8z6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client['for_help']
    collection = db['series']
    
    data = collection.find_one({'year': None})      
    if data and "season" in data:
        for season in data["season"]:
            season_number = None
            season_sql_id = season.get("sql_db_id")

            # get season number and episodes list
            for key, value in season.items():
                if key.isdigit():  # season number
                    season_number = int(key)
                    episodes = value
                    break

            if season.get("season_status") == "pending" and season_number:
                # find first pending episode
                for ep in episodes:
                    for ep_num, status in ep.items():
                        if status == "pending":
                            result = {
                                "season_sql_id": season_sql_id,
                                "season_number": season_number,
                                "episode_number": int(ep_num)
                            }
                            print(result)
                            return 


def update_show(collection, show_id, year=None, season_number=None, episode_number=None, new_status=None, new_season_status=None):
    """
    Update year, episode status, and/or season status for a show.

    Args:
        collection: MongoDB collection object
        show_id: str | ObjectId - ID of the show (_id or other unique field)
        year: int | None - new year to set
        season_number: int | None - season number to update
        episode_number: int | None - episode number to update
        new_status: str | None - new episode status (e.g. "done")
        new_season_status: str | None - new season status (e.g. "done")
    """
    query = {"_id": show_id}
    update_doc = {}

    if year is not None:
        update_doc["year"] = year

    if season_number is not None:
        # Find the right season element
        season_key = str(season_number)

        if new_season_status:
            update_doc["season.$[s].season_status"] = new_season_status

        if episode_number is not None and new_status is not None:
            # episode array index will be updated by matching filter
            update_doc[f"season.$[s].{season_key}.$[e].{episode_number}"] = new_status

    if not update_doc:
        return None  # nothing to update

    # Build array filters
    array_filters = []
    if season_number is not None:
        array_filters.append({"s." + str(season_number): {"$exists": True}})
    if episode_number is not None:
        array_filters.append({"e." + str(episode_number): {"$exists": True}})

    result = collection.update_one(
        query,
        {"$set": update_doc},
        array_filters=array_filters if array_filters else None
    )
    return result.modified_count


if __name__ == "__main__":
    main()