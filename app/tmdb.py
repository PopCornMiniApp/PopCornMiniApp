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
            cast = [{"name": m["name"], "character": m.get("character", ""), "profile": _img(
                m.get("profile_path"), "w185")} for m in data["credits"].get("cast", [])[:15]]
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
            cast = [{"name": m["name"], "character": m.get("character", ""), "profile": _img(
                m.get("profile_path"), "w185")} for m in data["credits"].get("cast", [])[:15]]

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


async def fetch_episode_info(
        tmdb_id: int,
        season: int,
        episode: int) -> dict | None:
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


async def fetch_movie_cast(tmdb_id: int) -> list:
    """Fetch cast information for a movie from TMDB"""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits"
    params = {"api_key": TMDB_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        
        cast = []
        for member in data.get("cast", [])[:20]:  # Get top 20 cast members
            cast.append({
                "id": member.get("id"),
                "name": member.get("name", ""),
                "character": member.get("character", ""),
                "profile_path": _img(member.get("profile_path"), "w185"),
                "order": member.get("order", 999)
            })
        return cast
    except Exception as e:
        logger.error(f"TMDB cast fetch error for movie {tmdb_id}: {e}")
        return []


async def fetch_series_cast(tmdb_id: int) -> list:
    """Fetch cast information for a TV series from TMDB"""
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}/credits"
    params = {"api_key": TMDB_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        
        cast = []
        for member in data.get("cast", [])[:20]:  # Get top 20 cast members
            cast.append({
                "id": member.get("id"),
                "name": member.get("name", ""),
                "character": member.get("character", ""),
                "profile_path": _img(member.get("profile_path"), "w185"),
                "order": member.get("order", 999)
            })
        return cast
    except Exception as e:
        logger.error(f"TMDB cast fetch error for series {tmdb_id}: {e}")
        return []


async def fetch_movie_reviews(tmdb_id: int) -> list:
    """Fetch reviews for a movie from TMDB"""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/reviews"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        
        reviews = []
        for review in data.get("results", [])[:10]:  # Get top 10 reviews
            author_details = review.get("author_details", {})
            reviews.append({
                "id": review.get("id"),
                "author": review.get("author", "Anonymous"),
                "author_details": {
                    "name": author_details.get("name", ""),
                    "username": author_details.get("username", ""),
                    "avatar_path": _img(author_details.get("avatar_path"), "w45") if author_details.get("avatar_path") and not author_details.get("avatar_path", "").startswith("http") else author_details.get("avatar_path", ""),
                    "rating": author_details.get("rating")
                },
                "content": review.get("content", ""),
                "created_at": review.get("created_at", ""),
                "updated_at": review.get("updated_at", ""),
                "url": review.get("url", "")
            })
        return reviews
    except Exception as e:
        logger.error(f"TMDB reviews fetch error for movie {tmdb_id}: {e}")
        return []


async def fetch_series_reviews(tmdb_id: int) -> list:
    """Fetch reviews for a TV series from TMDB"""
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}/reviews"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        
        reviews = []
        for review in data.get("results", [])[:10]:  # Get top 10 reviews
            author_details = review.get("author_details", {})
            reviews.append({
                "id": review.get("id"),
                "author": review.get("author", "Anonymous"),
                "author_details": {
                    "name": author_details.get("name", ""),
                    "username": author_details.get("username", ""),
                    "avatar_path": _img(author_details.get("avatar_path"), "w45") if author_details.get("avatar_path") and not author_details.get("avatar_path", "").startswith("http") else author_details.get("avatar_path", ""),
                    "rating": author_details.get("rating")
                },
                "content": review.get("content", ""),
                "created_at": review.get("created_at", ""),
                "updated_at": review.get("updated_at", ""),
                "url": review.get("url", "")
            })
        return reviews
    except Exception as e:
        logger.error(f"TMDB reviews fetch error for series {tmdb_id}: {e}")
        return []


def _img(path: str | None, size: str) -> str:
    if not path:
        return ""
    return f"{TMDB_IMAGE_BASE}/{size}{path}"
