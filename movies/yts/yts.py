import aiohttp
import asyncio
import urllib.parse
from typing import Dict, Any
import logging

# Set up logging (optional)
logger = logging.getLogger(__name__)

async def fetch_yts_movie(query: str) -> Dict[str, Any]:
    """
    Fetch movie information from YTS API.
    Returns a dictionary with title, imdb_id, year, and sorted torrents.
    """
    url = "https://yts.mx/api/v2/list_movies.json"
    params = {
        "query_term": query,
        "limit": 1
    }

    # Tracker list
    trackers = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://open.tracker.cl:1337/announce",
        "udp://p4p.arenabg.com:1337/announce",
        "udp://tracker.torrent.eu.org:451/announce",
        "udp://tracker.dler.org:6969/announce",
        "udp://open.stealth.si:80/announce",
        "udp://ipv4.tracker.harry.lu:80/announce",
        "https://opentracker.i2p.rocks:443/announce",
        "udp://tracker.tiny-vps.com:6969/announce",
        "udp://exodus.desync.com:6969/announce",
        "udp://tracker.openbittorrent.com:6969/announce",
        "udp://retracker.lanta-net.ru:2710/announce"
    ]

    max_retries = 3
    timeout = aiohttp.ClientTimeout(total=30)

    # Helper to parse size string to MB
    def parse_size(size_str: str) -> float:
        try:
            num, unit = size_str.split()
            num = float(num)
            return num * 1024 if unit.lower() == "gb" else num
        except Exception:
            return float("inf")  # Put unknown sizes at the end

    # Torrent quality sort priority
    quality_order = {"1080p": 0, "720p": 1, "480p": 2}

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        if attempt == max_retries - 1:
                            return {"error": f"Request failed with status {response.status}"}
                        continue

                    data = await response.json()

                    if data["status"] != "ok" or data["data"]["movie_count"] == 0:
                        return {"error": "Movie not found"}

                    movie = data["data"]["movies"][0]

                    result = {
                        "title": movie['title_long'],
                        "imdb_id": movie['imdb_code'],
                        "year": movie['year'],
                        "torrents": []
                    }

                    for torrent in movie.get('torrents', []):
                        try:
                            infohash = torrent['hash']
                            qs = [
                                ("xt", f"urn:btih:{infohash}"),
                                ("dn", movie['title_long']),
                            ]
                            qs += [("tr", t) for t in trackers]
                            magnet = "magnet:?" + urllib.parse.urlencode(qs, doseq=True)

                            result["torrents"].append({
                                "quality": torrent.get('quality', 'unknown'),
                                "type": torrent.get('type', 'unknown'),
                                "size": torrent.get('size', 'unknown'),
                                "codec": torrent.get('video_codec', 'unknown'),
                                "magnet": magnet
                            })
                        except (KeyError, TypeError) as e:
                            logger.warning(f"Skipping malformed torrent: {e}")
                            continue

                    # Sort by quality then size
                    result["torrents"].sort(
                        key=lambda x: (
                            quality_order.get(x.get("quality", "").lower(), 3),
                            parse_size(x.get("size", "999 GB"))
                        )
                    )

                    return result

        except asyncio.TimeoutError:
            if attempt == max_retries - 1:
                return {"error": "Request timed out"}
        except aiohttp.ClientError:
            if attempt == max_retries - 1:
                return {"error": "Network connection failed"}
        except (KeyError, TypeError, ValueError) as e:
            return {"error": f"Invalid response format: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

        # Exponential backoff before retry
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)
