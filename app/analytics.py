"""
Analytics System
Comprehensive analytics, reporting, and insights generation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

from app import database as db

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Advanced analytics and insights engine"""

    @staticmethod
    def get_user_engagement_metrics(
            user_id: int, days: int = 30) -> Dict[str, Any]:
        """Calculate comprehensive user engagement metrics"""
        try:
            stats = db.get_user_statistics(user_id)
            if not stats:
                return {}

            # Calculate engagement score (0-100)
            engagement_score = AnalyticsEngine._calculate_engagement_score(
                stats)

            # Get recent activity
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            activity = db.get_user_activity(
                user_id=user_id,
                start_date=start_date,
                limit=1000
            )

            # Activity breakdown
            activity_breakdown = {}
            for act in activity.get('activities', []):
                act_type = act['activity_type']
                activity_breakdown[act_type] = activity_breakdown.get(
                    act_type, 0) + 1

            return {
                "user_id": user_id,
                "period_days": days,
                "engagement_score": engagement_score,
                "total_watch_time": stats.get(
                    'total_watch_time',
                    0),
                "total_content_watched": stats.get(
                    'total_movies_watched',
                    0) +
                stats.get(
                    'total_episodes_watched',
                    0),
                "completion_rate": stats.get(
                    'completion_rate',
                    0),
                "average_session_duration": stats.get(
                    'average_session_duration',
                    0),
                "activity_breakdown": activity_breakdown,
                "binge_score": stats.get(
                    'binge_score',
                    0),
                "favorite_genre": stats.get(
                    'favorite_genre',
                    'Unknown'),
                "favorite_time_slot": stats.get(
                    'favorite_time_slot',
                    'Unknown'),
                "most_watched_day": stats.get(
                    'most_watched_day',
                    'Unknown')}
        except Exception as e:
            logger.error(f"Error calculating engagement metrics: {e}")
            return {}

    @staticmethod
    def _calculate_engagement_score(stats: Dict) -> float:
        """Calculate user engagement score (0-100)"""
        try:
            # Weighted scoring system
            weights = {
                'watch_time': 0.3,
                'completion_rate': 0.25,
                'session_frequency': 0.2,
                'content_diversity': 0.15,
                'interaction': 0.1
            }

            # Normalize watch time (max 10 hours = 100%)
            watch_time_score = min(
                stats.get(
                    'total_watch_time',
                    0) / 36000,
                1.0) * 100

            # Completion rate
            completion_score = stats.get('completion_rate', 0)

            # Session frequency (normalize to daily sessions)
            total_sessions = stats.get('total_sessions', 0)
            session_score = min(
                total_sessions / 30,
                1.0) * 100  # 30 sessions = 100%

            # Content diversity (ratings + favorites)
            diversity_score = min(
                (stats.get('total_ratings', 0) + stats.get('total_favorites', 0)) / 20, 1.0) * 100

            # Interaction (searches + shares)
            interaction_score = min(
                (stats.get('total_searches', 0) + stats.get('total_shares', 0)) / 50, 1.0) * 100

            # Calculate weighted score
            engagement_score = (
                watch_time_score * weights['watch_time'] +
                completion_score * weights['completion_rate'] +
                session_score * weights['session_frequency'] +
                diversity_score * weights['content_diversity'] +
                interaction_score * weights['interaction']
            )

            return round(engagement_score, 2)
        except Exception as e:
            logger.error(f"Error calculating engagement score: {e}")
            return 0.0

    @staticmethod
    def get_content_performance(
            content_type: str, content_id: str, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for specific content"""
        try:
            conn = db.get_connection()
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            # Total views
            total_views = conn.execute("""
                SELECT COUNT(*) FROM analytics_views
                WHERE content_type=? AND content_id=? AND created_at >= ?
            """, (content_type, content_id, start_date)).fetchone()[0]

            # Unique viewers
            unique_viewers = conn.execute("""
                SELECT COUNT(DISTINCT user_id) FROM analytics_views
                WHERE content_type=? AND content_id=? AND created_at >= ?
            """, (content_type, content_id, start_date)).fetchone()[0]

            # Average watch duration
            avg_duration = conn.execute("""
                SELECT AVG(watch_duration) FROM analytics_views
                WHERE content_type=? AND content_id=? AND created_at >= ?
                AND watch_duration > 0
            """, (content_type, content_id, start_date)).fetchone()[0]

            # Completion rate
            total_started = conn.execute("""
                SELECT COUNT(*) FROM watch_history
                WHERE content_type=? AND content_id=? AND last_watched >= ?
            """, (content_type, content_id, start_date)).fetchone()[0]

            total_completed = conn.execute("""
                SELECT COUNT(*) FROM watch_history
                WHERE content_type=? AND content_id=? AND completed=1 AND last_watched >= ?
            """, (content_type, content_id, start_date)).fetchone()[0]

            completion_rate = (
                total_completed /
                total_started *
                100) if total_started > 0 else 0

            # Ratings
            ratings_data = db.get_content_ratings(content_type, content_id)

            # Favorites count
            favorites_count = conn.execute("""
                SELECT COUNT(*) FROM user_favorites
                WHERE content_type=? AND content_id=?
            """, (content_type, content_id)).fetchone()[0]

            conn.close()

            return {
                "content_type": content_type,
                "content_id": content_id,
                "period_days": days,
                "total_views": total_views,
                "unique_viewers": unique_viewers,
                "average_watch_duration": int(avg_duration) if avg_duration else 0,
                "completion_rate": round(
                    completion_rate,
                    2),
                "average_rating": ratings_data.get(
                    'average_rating',
                    0),
                "total_ratings": ratings_data.get(
                    'total_ratings',
                    0),
                "favorites_count": favorites_count,
                "popularity_score": AnalyticsEngine._calculate_popularity_score(
                    total_views,
                    unique_viewers,
                    completion_rate,
                    ratings_data.get(
                        'average_rating',
                        0),
                    favorites_count)}
        except Exception as e:
            logger.error(f"Error getting content performance: {e}")
            return {}

    @staticmethod
    def _calculate_popularity_score(views: int, unique_viewers: int,
                                    completion_rate: float, avg_rating: float,
                                    favorites: int) -> float:
        """Calculate content popularity score (0-100)"""
        try:
            # Weighted scoring
            view_score = min(views / 1000, 1.0) * 100
            viewer_score = min(unique_viewers / 500, 1.0) * 100
            completion_score = completion_rate
            rating_score = (avg_rating / 5) * 100
            favorite_score = min(favorites / 100, 1.0) * 100

            popularity = (
                view_score * 0.25 +
                viewer_score * 0.25 +
                completion_score * 0.2 +
                rating_score * 0.2 +
                favorite_score * 0.1
            )

            return round(popularity, 2)
        except Exception as e:
            logger.error(f"Error calculating popularity score: {e}")
            return 0.0

    @staticmethod
    def get_trending_content(content_type: str = None, limit: int = 10,
                             days: int = 7) -> List[Dict[str, Any]]:
        """Get trending content based on recent activity"""
        try:
            conn = db.get_connection()
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            query = """
                SELECT
                    content_type,
                    content_id,
                    COUNT(*) as view_count,
                    COUNT(DISTINCT user_id) as unique_viewers,
                    AVG(watch_duration) as avg_duration
                FROM analytics_views
                WHERE created_at >= ?
            """
            params = [start_date]

            if content_type:
                query += " AND content_type=?"
                params.append(content_type)

            query += """
                GROUP BY content_type, content_id
                ORDER BY view_count DESC, unique_viewers DESC
                LIMIT ?
            """
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            conn.close()

            trending = []
            for row in rows:
                item = dict(row)
                # Get additional details
                if item['content_type'] == 'movie':
                    content = db.get_movie(item['content_id'])
                elif item['content_type'] == 'series':
                    content = db.get_series(item['content_id'])
                else:
                    content = None

                if content:
                    item['title'] = content.get('title', 'Unknown')
                    item['poster_path'] = content.get('poster_path', '')
                    item['rating'] = content.get('rating', 0)

                trending.append(item)

            return trending
        except Exception as e:
            logger.error(f"Error getting trending content: {e}")
            return []

    @staticmethod
    def get_user_recommendations(
            user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Generate personalized recommendations for user"""
        try:
            # Get user preferences and history
            db.get_user_preferences(user_id)
            watch_history = db.get_watch_history(user_id, limit=50)
            db.get_user_favorites(user_id)
            ratings = db.get_user_activity(  # noqa: F841
                user_id, activity_type='rate', limit=50)

            # Extract user's favorite genres from watch history
            conn = db.get_connection()

            # Get genres from watched content
            watched_genres = []
            for item in watch_history:
                if item['content_type'] == 'movie':
                    movie = db.get_movie(item['content_id'])
                    if movie and movie.get('genres'):
                        watched_genres.extend(json.loads(movie['genres']))

            # Count genre frequency
            genre_counts = {}
            for genre in watched_genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1

            # Get top genres
            top_genres = sorted(
                genre_counts.items(),
                key=lambda x: x[1],
                reverse=True)[
                :3]
            top_genre_names = [g[0] for g in top_genres]

            # Find similar content
            recommendations = []

            if top_genre_names:
                # Get movies with similar genres
                for genre in top_genre_names:
                    movies = conn.execute("""
                        SELECT * FROM movies
                        WHERE genres LIKE ? AND rating >= 7.0
                        ORDER BY rating DESC, vote_count DESC
                        LIMIT ?
                    """, (f'%{genre}%', limit // len(top_genre_names) + 1)).fetchall()

                    for movie in movies:
                        movie_dict = dict(movie)
                        # Check if not already watched
                        already_watched = any(
                            h['content_id'] == movie_dict['id']
                            for h in watch_history
                        )
                        if not already_watched:
                            movie_dict[
                                'recommendation_reason'] = f"Based on your interest in {genre}"
                            recommendations.append(movie_dict)

            conn.close()

            # Remove duplicates and limit
            seen = set()
            unique_recommendations = []
            for rec in recommendations:
                if rec['id'] not in seen:
                    seen.add(rec['id'])
                    unique_recommendations.append(rec)
                    if len(unique_recommendations) >= limit:
                        break

            return unique_recommendations
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    @staticmethod
    def get_platform_statistics(days: int = 30) -> Dict[str, Any]:
        """Get overall platform statistics"""
        try:
            conn = db.get_connection()
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            # Total users
            total_users = conn.execute(
                "SELECT COUNT(*) FROM users").fetchone()[0]

            # Active users (logged in within period)
            active_users = conn.execute("""
                SELECT COUNT(DISTINCT user_id) FROM user_activity
                WHERE created_at >= ?
            """, (start_date,)).fetchone()[0]

            # Total content
            total_movies = conn.execute(
                "SELECT COUNT(*) FROM movies").fetchone()[0]
            total_series = conn.execute(
                "SELECT COUNT(*) FROM series").fetchone()[0]
            total_episodes = conn.execute(
                "SELECT COUNT(*) FROM episodes").fetchone()[0]

            # Total views
            total_views = conn.execute("""
                SELECT COUNT(*) FROM analytics_views WHERE created_at >= ?
            """, (start_date,)).fetchone()[0]

            # Total watch time
            total_watch_time = conn.execute("""
                SELECT SUM(watch_duration) FROM analytics_views
                WHERE created_at >= ? AND watch_duration > 0
            """, (start_date,)).fetchone()[0]

            # Total searches
            total_searches = conn.execute("""
                SELECT COUNT(*) FROM analytics_searches WHERE created_at >= ?
            """, (start_date,)).fetchone()[0]

            # Average session duration
            avg_session = conn.execute("""
                SELECT AVG(session_duration) FROM user_sessions
                WHERE login_time >= ? AND session_duration > 0
            """, (start_date,)).fetchone()[0]

            # Most popular content
            most_viewed = conn.execute("""
                SELECT content_type, content_id, COUNT(*) as views
                FROM analytics_views
                WHERE created_at >= ?
                GROUP BY content_type, content_id
                ORDER BY views DESC
                LIMIT 1
            """, (start_date,)).fetchone()

            conn.close()

            return {
                "period_days": days,
                "total_users": total_users,
                "active_users": active_users,
                "user_retention_rate": round(
                    (active_users / total_users * 100) if total_users > 0 else 0,
                    2),
                "total_content": {
                    "movies": total_movies,
                    "series": total_series,
                    "episodes": total_episodes,
                    "total": total_movies + total_series},
                "engagement": {
                    "total_views": total_views,
                    "total_watch_time_hours": round(
                        (total_watch_time or 0) / 3600,
                        2),
                    "total_searches": total_searches,
                    "average_session_minutes": round(
                        (avg_session or 0) / 60,
                        2)},
                "most_viewed_content": dict(most_viewed) if most_viewed else None}
        except Exception as e:
            logger.error(f"Error getting platform statistics: {e}")
            return {}

    @staticmethod
    def get_user_cohort_analysis(
            cohort_period: str = 'month') -> List[Dict[str, Any]]:
        """Analyze user cohorts based on registration date"""
        try:
            conn = db.get_connection()

            # Group users by cohort
            if cohort_period == 'month':
                pass
            elif cohort_period == 'week':
                pass
            else:  # day
                pass

            # Fixed: Validate date_format against whitelist to prevent SQL
            # injection
            allowed_formats = {
                'month': '%Y-%m',
                'week': '%Y-W%W',
                'day': '%Y-%m-%d'
            }
            safe_date_format = allowed_formats.get(cohort_period, '%Y-%m-%d')

            cohorts = conn.execute("""
                SELECT
                    strftime('{safe_date_format}', created_at) as cohort,
                    COUNT(*) as user_count,
                    SUM(CASE WHEN is_premium=1 THEN 1 ELSE 0 END) as premium_count
                FROM users
                GROUP BY cohort
                ORDER BY cohort DESC
                LIMIT 12
            """).fetchall()

            cohort_data = []
            for cohort in cohorts:
                cohort_dict = dict(cohort)

                # Get retention for this cohort
                # Fixed: Use validated date_format
                retention = conn.execute("""
                    SELECT COUNT(DISTINCT ua.user_id) as active_users
                    FROM user_activity ua
                    JOIN users u ON ua.user_id = u.user_id
                    WHERE strftime('{safe_date_format}', u.created_at) = ?
                    AND ua.created_at >= date('now', '-30 days')
                """, (cohort_dict['cohort'],)).fetchone()[0]

                cohort_dict['retention_rate'] = round(
                    (retention /
                     cohort_dict['user_count'] *
                        100) if cohort_dict['user_count'] > 0 else 0,
                    2)
                cohort_dict['premium_rate'] = round(
                    (cohort_dict['premium_count'] /
                     cohort_dict['user_count'] *
                        100) if cohort_dict['user_count'] > 0 else 0,
                    2)

                cohort_data.append(cohort_dict)

            conn.close()
            return cohort_data
        except Exception as e:
            logger.error(f"Error in cohort analysis: {e}")
            return []

    @staticmethod
    def generate_user_report(user_id: int) -> Dict[str, Any]:
        """Generate comprehensive user report"""
        try:
            return {
                "user_info": db.get_user(user_id),
                "profile": db.get_user_profile(user_id),
                "statistics": db.get_user_statistics(user_id),
                "engagement_metrics": AnalyticsEngine.get_user_engagement_metrics(user_id),
                "preferences": db.get_user_preferences(user_id),
                "recent_activity": db.get_user_activity(
                    user_id,
                    limit=20),
                "watch_history": db.get_watch_history(
                    user_id,
                    limit=20),
                "favorites": db.get_user_favorites(user_id),
                "devices": db.get_user_devices(user_id),
                "active_sessions": db.get_active_sessions(user_id),
                "recommendations": AnalyticsEngine.get_user_recommendations(
                    user_id,
                    limit=5)}
        except Exception as e:
            logger.error(f"Error generating user report: {e}")
            return {}


# Utility functions for quick analytics

def get_daily_active_users(days: int = 7) -> List[Dict[str, Any]]:
    """Get daily active users for the past N days"""
    try:
        conn = db.get_connection()
        daily_stats = []

        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            start = f"{date} 00:00:00"
            end = f"{date} 23:59:59"

            active_count = conn.execute("""
                SELECT COUNT(DISTINCT user_id) FROM user_activity
                WHERE created_at BETWEEN ? AND ?
            """, (start, end)).fetchone()[0]

            daily_stats.append({
                "date": str(date),
                "active_users": active_count
            })

        conn.close()
        return daily_stats
    except Exception as e:
        logger.error(f"Error getting daily active users: {e}")
        return []


def get_content_library_stats() -> Dict[str, Any]:
    """Get content library statistics"""
    try:
        conn = db.get_connection()

        stats = {
            "movies": {
                "total": conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0],
                "with_files": conn.execute("SELECT COUNT(*) FROM movies WHERE file_id IS NOT NULL").fetchone()[0],
                "average_rating": conn.execute("SELECT AVG(rating) FROM movies WHERE rating > 0").fetchone()[0] or 0},
            "series": {
                "total": conn.execute("SELECT COUNT(*) FROM series").fetchone()[0],
                "total_episodes": conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],
                "episodes_with_files": conn.execute("SELECT COUNT(*) FROM episodes WHERE file_id IS NOT NULL").fetchone()[0],
                "average_rating": conn.execute("SELECT AVG(rating) FROM series WHERE rating > 0").fetchone()[0] or 0}}

        conn.close()
        return stats
    except Exception as e:
        logger.error(f"Error getting library stats: {e}")
        return {}

# Made with Bob
