import httpx
import json
import logging
from app.config import TMDB_API_KEY, TMDB_BASE_URL, TMDB_IMAGE_BASE

logger = logging.getLogger(__name__)


async def fetch_movie(tmdb_id: int) -> dict | None:
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "ar-SA",
        "append_to_response": "credits",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        cast = []
        director = ""
        if "credits" in data:
            cast = [
                {"name": m["name"], "character": m.get("character", ""), "profile": _img(m.get("profile_path"), "w185")}
                for m in data["credits"].get("cast", [])[:15]
            ]
            for c in data["credits"].get("crew", []):
                if c.get("job") == "Director":
                    director = c["name"]
                    break

        genres = [g["name"] for g in data.get("genres", [])]

        title = data.get("title", "")
        title_ar = ""
        overview_ar = ""
        if data.get("original_language") != "ar":
            ar_data = await _fetch_ar_translations(tmdb_id, "movie")
            title_ar = ar_data.get("title", "")
            overview_ar = ar_data.get("overview", "")

        return {
            "tmdb_id": tmdb_id,
            "title": title,
            "title_ar": title_ar or title,
            "overview": data.get("overview", ""),
            "overview_ar": overview_ar or data.get("overview", ""),
            "poster_path": _img(data.get("poster_path"), "w500"),
            "backdrop_path": _img(data.get("backdrop_path"), "w1280"),
            "release_date": data.get("release_date", ""),
            "runtime": data.get("runtime", 0),
            "genres": json.dumps(genres, ensure_ascii=False),
            "cast": json.dumps(cast, ensure_ascii=False),
            "director": director,
            "rating": round(data.get("vote_average", 0), 1),
            "vote_count": data.get("vote_count", 0),
        }
    except Exception as e:
        logger.error(f"TMDB movie fetch error for {tmdb_id}: {e}")
        return None


async def fetch_series(tmdb_id: int) -> dict | None:
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "ar-SA",
        "append_to_response": "credits",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        cast = []
        if "credits" in data:
            cast = [
                {"name": m["name"], "character": m.get("character", ""), "profile": _img(m.get("profile_path"), "w185")}
                for m in data["credits"].get("cast", [])[:15]
            ]

        creators = [c["name"] for c in data.get("created_by", [])]
        genres = [g["name"] for g in data.get("genres", [])]

        title = data.get("name", "")
        title_ar = ""
        overview_ar = ""
        if data.get("original_language") != "ar":
            ar_data = await _fetch_ar_translations(tmdb_id, "tv")
            title_ar = ar_data.get("name", "")
            overview_ar = ar_data.get("overview", "")

        return {
            "tmdb_id": tmdb_id,
            "title": title,
            "title_ar": title_ar or title,
            "overview": data.get("overview", ""),
            "overview_ar": overview_ar or data.get("overview", ""),
            "poster_path": _img(data.get("poster_path"), "w500"),
            "backdrop_path": _img(data.get("backdrop_path"), "w1280"),
            "first_air_date": data.get("first_air_date", ""),
            "genres": json.dumps(genres, ensure_ascii=False),
            "cast": json.dumps(cast, ensure_ascii=False),
            "creator": ", ".join(creators),
            "rating": round(data.get("vote_average", 0), 1),
            "vote_count": data.get("vote_count", 0),
            "total_seasons": data.get("number_of_seasons", 0),
            "status": data.get("status", ""),
        }
    except Exception as e:
        logger.error(f"TMDB series fetch error for {tmdb_id}: {e}")
        return None


async def fetch_episode_info(tmdb_id: int, season: int, episode: int) -> dict | None:
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}/season/{season}/episode/{episode}"
    params = {"api_key": TMDB_API_KEY, "language": "ar-SA"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        return {
            "title": data.get("name", ""),
            "overview": data.get("overview", ""),
            "still_path": _img(data.get("still_path"), "w300"),
            "air_date": data.get("air_date", ""),
            "runtime": data.get("runtime", 0),
        }
    except Exception as e:
        logger.warning(f"TMDB episode info error: {e}")
        return None


async def _fetch_ar_translations(tmdb_id: int, media_type: str) -> dict:
    url = f"{TMDB_BASE_URL}/{media_type}/{tmdb_id}/translations"
    params = {"api_key": TMDB_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        for t in data.get("translations", []):
            if t.get("iso_639_1") == "ar":
                return t.get("data", {})
    except Exception:
        pass
    return {}


def _img(path: str | None, size: str) -> str:
    if not path:
        return ""
    return f"{TMDB_IMAGE_BASE}/{size}{path}"
