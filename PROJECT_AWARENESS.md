
# PopCorn Mini App - Project Awareness Document

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Structure](#architecture--structure)
3. [Database Schema (55 Tables)](#database-schema-55-tables)
4. [API Endpoints (100+)](#api-endpoints-100)
5. [Frontend Components](#frontend-components)
6. [Integrated Systems](#integrated-systems)
7. [Known Issues (94 Errors)](#known-issues-94-errors)
8. [Performance Metrics](#performance-metrics)
9. [Configuration & Deployment](#configuration--deployment)
10. [Technical Debt](#technical-debt)

---

## 🎯 Project Overview

### Description
PopCorn is a comprehensive streaming platform mini-app built for Telegram, offering movies and series streaming with advanced social features including watch rooms, friend systems, and real-time messaging.

### Goals
- Provide seamless streaming experience for 10,000+ concurrent users
- Integrate social features (friends, messaging, watch rooms)
- Maintain 99.9% uptime with distributed mirror system
- Deliver content with <2s load time
- Support multiple content sources (21 bots)

### Technologies Used

#### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLite with connection pooling
- **Caching**: Redis-compatible smart cache
- **API Integration**: TMDB API v3
- **Bot Framework**: Telethon (Telegram)
- **Async**: asyncio, aiohttp

#### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: React Hooks
- **Routing**: React Router v6
- **Icons**: Lucide React

#### Infrastructure
- **Hosting**: HuggingFace Spaces (Gradio)
- **Storage**: HuggingFace Datasets
- **CDN**: Telegram CDN (via bots)
- **Monitoring**: Custom health monitoring system

### Current Status
- **Development Stage**: Production-ready with optimization needed
- **Content**: 500+ movies, 200+ series, 1000+ episodes
- **Users**: Ready for 1-2 concurrent viewers (needs scaling)
- **Deployment**: Deployed on HuggingFace Spaces
- **Test Coverage**: 62.5% (needs improvement)

---

## 🏗️ Architecture & Structure

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Web App    │  │ Telegram Bot │  │  Admin Panel │      │
│  │  (React)     │  │  Interface   │  │   (React)    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────┐
│                    API Gateway Layer                          │
│                    ┌───────▼────────┐                        │
│                    │   FastAPI      │                        │
│                    │   Main App     │                        │
│                    └───────┬────────┘                        │
└────────────────────────────┼─────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
┌─────────▼────────┐ ┌──────▼──────┐ ┌────────▼─────────┐
│  Business Logic  │ │   Caching   │ │   External APIs  │
│                  │ │             │ │                  │
│ • Authentication │ │ • Smart     │ │ • TMDB API       │
│ • Content Mgmt   │ │   Cache     │ │ • Telegram API   │
│ • User Tracking  │ │ • Redis     │ │ • Bot Network    │
│ • Friends System │ │   Compatible│ │                  │
│ • Messaging      │ │             │ │                  │
│ • Watch Rooms    │ │             │ │                  │
│ • Streaming      │ │             │ │                  │
└─────────┬────────┘ └──────┬──────┘ └────────┬─────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                     Data Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   SQLite DB  │  │  HF Datasets │  │  File System │      │
│  │  (55 tables) │  │   (Backup)   │  │   (Temp)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                  Content Delivery Network                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Mirror System (9 Groups)                     │    │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │    │
│  │  │Group1│ │Group2│ │Group3│ │Group4│ │Group5│ ... │    │
│  │  │3 bots│ │3 bots│ │3 bots│ │3 bots│ │3 bots│     │    │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘     │    │
│  │         Total: 21 Telegram Bots                     │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Component Relationships

```
FastAPI Main App
├── Authentication & Security
│   ├── JWT Token Management
│   ├── Session Management
│   └── Rate Limiting
│
├── Content Management
│   ├── TMDB Integration
│   ├── Scanner System
│   ├── Multi-Source Sync
│   └── Content Metadata
│
├── User Management
│   ├── User Profiles
│   ├── User Activity Tracking
│   ├── Watch History
│   └── Preferences
│
├── Social Features
│   ├── Friends System
│   │   ├── Friend Requests
│   │   ├── Friendships
│   │   └── Friend Activity
│   ├── Messaging System
│   │   ├── Conversations
│   │   ├── Messages
│   │   └── Real-time Updates
│   └── Watch Rooms
│       ├── Room Management
│       ├── Participants
│       └── Synchronization
│
├── Streaming System
│   ├── Mirror Manager (9 groups)
│   ├── Health Monitoring
│   ├── Load Balancing
│   └── Failover System
│
├── Caching System
│   ├── Smart Cache
│   ├── Content Cache
│   └── API Response Cache
│
└── Analytics & Monitoring
    ├── Performance Monitoring
    ├── User Analytics
    ├── Resource Monitoring
    └── Audit Logs
```

### Data Flow

```
User Request → API Gateway → Authentication → Business Logic
                                                    ↓
                                            Check Cache
                                                    ↓
                                            Cache Hit? → Return
                                                    ↓ No
                                            Query Database
                                                    ↓
                                            Process Data
                                                    ↓
                                            Update Cache
                                                    ↓
                                            Return Response
```

---

## 🗄️ Database Schema (55 Tables)

### Content Tables

#### 1. movies
```sql
CREATE TABLE movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL,
    original_title TEXT,
    overview TEXT,
    release_date TEXT,
    poster_path TEXT,
    backdrop_path TEXT,
    vote_average REAL,
    vote_count INTEGER,
    popularity REAL,
    runtime INTEGER,
    budget INTEGER,
    revenue INTEGER,
    status TEXT,
    tagline TEXT,
    genres TEXT,  -- JSON array
    production_companies TEXT,  -- JSON array
    production_countries TEXT,  -- JSON array
    spoken_languages TEXT,  -- JSON array
    imdb_id TEXT,
    homepage TEXT,
    adult BOOLEAN DEFAULT 0,
    video BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_movies_tmdb_id ON movies(tmdb_id);
CREATE INDEX idx_movies_title ON movies(title);
CREATE INDEX idx_movies_release_date ON movies(release_date);
CREATE INDEX idx_movies_popularity ON movies(popularity DESC);
```

#### 2. series
```sql
CREATE TABLE series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    original_name TEXT,
    overview TEXT,
    first_air_date TEXT,
    last_air_date TEXT,
    poster_path TEXT,
    backdrop_path TEXT,
    vote_average REAL,
    vote_count INTEGER,
    popularity REAL,
    status TEXT,
    type TEXT,
    number_of_seasons INTEGER,
    number_of_episodes INTEGER,
    genres TEXT,  -- JSON array
    networks TEXT,  -- JSON array
    production_companies TEXT,  -- JSON array
    created_by TEXT,  -- JSON array
    episode_run_time TEXT,  -- JSON array
    in_production BOOLEAN,
    languages TEXT,  -- JSON array
    origin_country TEXT,  -- JSON array
    homepage TEXT,
    adult BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_series_tmdb_id ON series(tmdb_id);
CREATE INDEX idx_series_name ON series(name);
CREATE INDEX idx_series_first_air_date ON series(first_air_date);
CREATE INDEX idx_series_popularity ON series(popularity DESC);
```

#### 3. seasons
```sql
CREATE TABLE seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    tmdb_id INTEGER,
    season_number INTEGER NOT NULL,
    name TEXT,
    overview TEXT,
    air_date TEXT,
    poster_path TEXT,
    episode_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
    UNIQUE(series_id, season_number)
);
CREATE INDEX idx_seasons_series_id ON seasons(series_id);
CREATE INDEX idx_seasons_season_number ON seasons(season_number);
```

#### 4. episodes
```sql
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    season_id INTEGER NOT NULL,
    tmdb_id INTEGER,
    episode_number INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    name TEXT,
    overview TEXT,
    air_date TEXT,
    still_path TEXT,
    vote_average REAL,
    vote_count INTEGER,
    runtime INTEGER,
    production_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
    FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE,
    UNIQUE(series_id, season_number, episode_number)
);
CREATE INDEX idx_episodes_series_id ON episodes(series_id);
CREATE INDEX idx_episodes_season_id ON episodes(season_id);
CREATE INDEX idx_episodes_episode_number ON episodes(episode_number);
```

### User Tables

#### 5. user_profiles
```sql
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT DEFAULT 'en',
    is_premium BOOLEAN DEFAULT 0,
    subscription_type TEXT DEFAULT 'free',
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preferences TEXT,  -- JSON object
    avatar_url TEXT,
    bio TEXT,
    is_active BOOLEAN DEFAULT 1,
    is_banned BOOLEAN DEFAULT 0,
    ban_reason TEXT,
    banned_at TIMESTAMP,
    total_watch_time INTEGER DEFAULT 0,
    content_watched_count INTEGER DEFAULT 0
);
CREATE INDEX idx_user_profiles_telegram_id ON user_profiles(telegram_id);
CREATE INDEX idx_user_profiles_username ON user_profiles(username);
CREATE INDEX idx_user_profiles_is_premium ON user_profiles(is_premium);
```

#### 6. user_activity
```sql
CREATE TABLE user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activity_type TEXT NOT NULL,  -- 'view', 'search', 'play', 'pause', etc.
    content_type TEXT,  -- 'movie', 'series', 'episode'
    content_id INTEGER,
    metadata TEXT,  -- JSON object
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_activity_user_id ON user_activity(user_id);
CREATE INDEX idx_user_activity_type ON user_activity(activity_type);
CREATE INDEX idx_user_activity_created_at ON user_activity(created_at DESC);
```

#### 7. watch_history
```sql
CREATE TABLE watch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content_type TEXT NOT NULL,  -- 'movie' or 'episode'
    content_id INTEGER NOT NULL,
    progress INTEGER DEFAULT 0,  -- seconds watched
    duration INTEGER,  -- total duration in seconds
    completed BOOLEAN DEFAULT 0,
    last_watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
    UNIQUE(user_id, content_type, content_id)
);
CREATE INDEX idx_watch_history_user_id ON watch_history(user_id);
CREATE INDEX idx_watch_history_last_watched ON watch_history(last_watched_at DESC);
```

### Friends System Tables

#### 8. friendships
```sql
CREATE TABLE friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    friend_id INTEGER NOT NULL,
    status TEXT DEFAULT 'active',  -- 'active', 'blocked'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (friend_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
    UNIQUE(user_id, friend_id),
    CHECK(user_id != friend_id)
);
CREATE INDEX idx_friendships_user_id ON friendships(user_id);
CREATE INDEX idx_friendships_friend_id ON friendships(friend_id);
CREATE INDEX idx_friendships_status ON friendships(status);
```

#### 9. friend_requests
```sql
CREATE TABLE friend_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',  -- 'pending', 'accepted', 'rejected'
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
    UNIQUE(sender_id, receiver_id),
    CHECK(sender_id != receiver_id)
);
CREATE INDEX idx_friend_requests_sender_id ON friend_requests(sender_id);
CREATE INDEX idx_friend_requests_receiver_id ON friend_requests(receiver_id);
CREATE INDEX idx_friend_requests_status ON friend_requests(status);
```

#### 10. friend_activity
```sql
CREATE TABLE friend_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activity_type TEXT NOT NULL,  -- 'watching', 'completed', 'rated'
    content_type TEXT NOT NULL,
    content_id INTEGER NOT NULL,
    visibility TEXT DEFAULT 'friends',  -- 'public', 'friends', 'private'
    metadata TEXT,  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE
);
CREATE INDEX idx_friend_activity_user_id ON friend_activity(user_id);
CREATE INDEX idx_friend_activity_created_at ON friend_activity(created_at DESC);
```

### Messaging Tables

#### 11. conversations
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT DEFAULT 'direct',  -- 'direct', 'group'
    name TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES user_profiles(id) ON DELETE SET NULL
);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at DESC);
CREATE INDEX idx_conversations_type ON conversations(type);
```

#### 12. conversation_participants
```sql
CREATE TABLE conversation_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT DEFAULT 'member',  -- 'admin', 'member'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    left_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    unread_count INTEGER DEFAULT 0,
    last_read_at TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
    UNIQUE(conversation_id, user_id)
);
CREATE INDEX idx_conv_participants_conversation_id ON conversation_participants(conversation_id);
CREATE INDEX idx_conv_participants_user_id ON conversation_participants(user_id);
```

#### 13. messages
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',  -- 'text', 'image', 'video', 'file'
    metadata TEXT,  -- JSON object
    reply_to_id INTEGER,
    is_edited BOOLEAN DEFAULT 0,
    edited_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT 0,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (reply_to_id) REFERENCES messages(id) ON DELETE SET NULL
);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
```

### Watch Rooms Tables

#### 14. watch_rooms
```sql
CREATE TABLE watch_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    host_id INTEGER NOT NULL,
    content_type TEXT NOT NULL,  -- 'movie' or 'episode'
    content_id INTEGER NOT NULL,
    status TEXT DEFAULT 'waiting',  -- 'waiting', 'playing', 'paused', 'ended'
    is_public BOOLEAN DEFAULT 1,
    password TEXT,
    max_participants INTEGER DEFAULT 10,
    current_time INTEGER DEFAULT 0,  -- seconds
    playback_rate REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    FOREIGN KEY (host_id) REFERENCES user_profiles(id) ON DELETE CASCADE
);
CREATE INDEX idx_watch_rooms_host_id ON watch_rooms(host_id);
CREATE INDEX idx_watch_rooms_status ON watch_rooms(status);
CREATE INDEX idx_watch_rooms_is_public ON watch_rooms(is_public);
```

#### 15. room_participants
```sql
CREATE TABLE room_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT DEFAULT 'viewer',  -- 'host', 'moderator', 'viewer'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    left_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    current_time INTEGER DEFAULT 0,
    is_ready BOOLEAN DEFAULT 0,
    FOREIGN KEY (room_id) REFERENCES watch_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
    UNIQUE(room_id, user_id)
);
CREATE INDEX idx_room_participants_room_id ON room_participants(room_id);
CREATE INDEX idx_room_participants_user_id ON room_participants(user_id);
```

#### 16. room_messages
```sql
CREATE TABLE room_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    message_type TEXT DEFAULT 'chat',  -- 'chat', 'system', 'reaction'
    metadata TEXT,  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES watch_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE
);
CREATE INDEX idx_room_messages_room_id ON room_messages(room_id);
CREATE INDEX idx_room_messages_created_at ON room_messages(created_at DESC);
```

### Mirror System Tables

#### 17. mirror_groups
```sql
CREATE TABLE mirror_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER UNIQUE NOT NULL,
    group_name TEXT NOT NULL,
    group_username TEXT,
    status TEXT DEFAULT 'active',  -- 'active', 'inactive', 'maintenance'
    priority INTEGER DEFAULT 1,
    max_capacity INTEGER DEFAULT 1000,
    current_load INTEGER DEFAULT 0,
    health_score REAL DEFAULT 100.0,
    last_health_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_mirror_groups_status ON mirror_groups(status);
CREATE INDEX idx_mirror_groups_priority ON mirror_groups(priority DESC);
CREATE INDEX idx_mirror_groups_health_score ON mirror_groups(health_score DESC);
```

#### 18. mirror_bots
```sql
CREATE TABLE mirror_bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_token TEXT UNIQUE NOT NULL,
    bot_username TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    status TEXT DEFAULT 'active',  -- 'active', 'inactive', 'error'
    is_primary BOOLEAN DEFAULT 0,
    health_score REAL DEFAULT 100.0,
    last_health_check TIMESTAMP,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_error_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES mirror_groups(id) ON DELETE CASCADE
);
CREATE INDEX idx_mirror_bots_group_id ON mirror_bots(group_id);
CREATE INDEX idx_mirror_bots_status ON mirror_bots(status);
CREATE INDEX idx_mirror_bots_health_score ON mirror_bots(health_score DESC);
```

#### 19. mirror_health
```sql
CREATE TABLE mirror_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL,
    response_time REAL,  -- milliseconds
    success_rate REAL,
    error_rate REAL,
    bandwidth_usage INTEGER,  -- bytes
    active_streams INTEGER,
    cpu_usage REAL,
    memory_usage REAL,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES mirror_bots(id) ON DELETE CASCADE
);
CREATE INDEX idx_mirror_health_bot_id ON mirror_health(bot_id);
CREATE INDEX idx_mirror_health_checked_at ON mirror_health(checked_at DESC);
```

#### 20. content_mirrors
```sql
CREATE TABLE content_mirrors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL,  -- 'movie' or 'episode'
    content_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    bot_id INTEGER NOT NULL,
    telegram_file_id TEXT NOT NULL,
    file_size INTEGER,
    quality TEXT,  -- '720p', '1080p', etc.
    status TEXT DEFAULT 'active',  -- 'active', 'inactive', 'failed'
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    FOREIGN KEY (group_id) REFERENCES mirror_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (bot_id) REFERENCES mirror_bots(id) ON DELETE CASCADE,
    UNIQUE(content_type, content_id, group_id, quality)
);
CREATE INDEX idx_content_mirrors_content ON content_mirrors(content_type, content_id);
CREATE INDEX idx_content_mirrors_group_id ON content_mirrors(group_id);
CREATE INDEX idx_content_mirrors_status ON content_mirrors(status);
```

### Additional Tables (21-55)

#### 21-25: Analytics Tables
- `page_views`: Track page visits
- `search_queries`: Track search behavior
- `content_ratings`: User ratings
- `content_reviews`: User reviews
- `playback_analytics`: Streaming metrics

#### 26-30: Notification Tables
- `notifications`: User notifications
- `notification_preferences`: User preferences
- `push_subscriptions`: Push notification tokens
- `email_queue`: Email notifications queue
- `notification_templates`: Notification templates

#### 31-35: Admin Tables
- `admin_users`: Admin accounts
- `admin_roles`: Role definitions
- `admin_permissions`: Permission definitions
- `audit_logs`: System audit trail
- `system_settings`: Configuration settings

#### 36-40: Cache Tables
- `cache_entries`: Cache storage
- `cache_stats`: Cache statistics
- `api_cache`: API response cache
- `content_cache`: Content metadata cache
- `user_cache`: User data cache

#### 41-45: Queue Tables
- `job_queue`: Background jobs
- `scan_queue`: Content scan queue
- `sync_queue`: Sync operations queue
- `notification_queue`: Notification queue
- `cleanup_queue`: Cleanup operations queue

#### 46-50: Session Tables
- `user_sessions`: Active sessions
- `api_tokens`: API access tokens
- `refresh_tokens`: JWT refresh tokens
- `device_tokens`: Device identifications
- `login_history`: Login attempts log

#### 51-55: Miscellaneous Tables
- `genres`: Genre definitions
- `tags`: Content tags
- `collections`: Content collections
- `playlists`: User playlists
- `bookmarks`: User bookmarks

---

## 🔌 API Endpoints (100+)

### Authentication Endpoints (10)

```
POST   /api/auth/register          - Register new user
POST   /api/auth/login             - User login
POST   /api/auth/logout            - User logout
POST   /api/auth/refresh           - Refresh access token
GET    /api/auth/me                - Get current user
PUT    /api/auth/profile           - Update profile
POST   /api/auth/change-password   - Change password
POST   /api/auth/forgot-password   - Request password reset
POST   /api/auth/reset-password    - Reset password
DELETE /api/auth/account           - Delete account
```

### Content Endpoints - Movies (15)

```
GET    /api/movies                 - List movies (paginated)
GET    /api/movies/popular         - Popular movies
GET    /api/movies/trending        - Trending movies
GET    /api/movies/top-rated       - Top rated movies
GET    /api/movies/upcoming        - Upcoming movies
GET    /api/movies/now-playing     - Now playing movies
GET    /api/movies/{id}            - Get movie details
GET    /api/movies/{id}/similar    - Similar movies
GET    /api/movies/{id}/recommendations - Recommended movies
GET    /api/movies/{id}/credits    - Movie credits
GET    /api/movies/{id}/videos     - Movie trailers/videos
GET    /api/movies/{id}/images     - Movie images
POST   /api/movies/{id}/rate       - Rate movie
GET    /api/movies/{id}/stream     - Get streaming link
POST   /api/movies/scan            - Trigger movie scan
```

### Content Endpoints - Series (20)

```
GET    /api/series                 - List series (paginated)
GET    /api/series/popular         - Popular series
GET    /api/series/trending        - Trending series
GET    /api/series/top-rated       - Top rated series
GET    /api/series/on-air          - Currently airing series
GET    /api/series/{id}            - Get series details
GET    /api/series/{id}/seasons    - Get all seasons
GET    /api/series/{id}/season/{season_num} - Get season details
GET    /api/series/{id}/season/{season_num}/episodes - Get episodes
GET    /api/series/{id}/season/{season_num}/episode/{ep_num} - Episode details
GET    /api/series/{id}/similar    - Similar series
GET    /api/series/{id}/recommendations - Recommended series
GET    /api/series/{id}/credits    - Series credits
GET    /api/series/{id}/videos     - Series trailers/videos
GET    /api/series/{id}/images     - Series images
POST   /api/series/{id}/rate       - Rate series
GET    /api/series/{id}/stream     - Get streaming link
POST   /api/series/scan            - Trigger series scan
GET    /api/episodes/{id}/stream   - Get episode streaming link
POST   /api/episodes/{id}/rate     - Rate episode
```

### Search Endpoints (5)

```
GET    /api/search                 - Multi-search (movies + series)
GET    /api/search/movies          - Search movies
GET    /api/search/series          - Search series
GET    /api/search/people          - Search people
GET    /api/search/suggestions     - Search suggestions
```

### User Management Endpoints (10)

```
GET    /api/users/{id}             - Get user profile
PUT    /api/users/{id}             - Update user profile
GET    /api/users/{id}/activity    - Get user activity
GET    /api/users/{id}/history     - Get watch history
POST   /api/users/{id}/history     - Add to watch history
DELETE /api/users/{id}/history/{item_id} - Remove from history
GET    /api/users/{id}/favorites   - Get favorites
POST   /api/users/{id}/favorites   - Add to favorites
DELETE /api/users/{id}/favorites/{item_id} - Remove from favorites
GET    /api/users/{id}/watchlist   - Get watchlist
```

### Friends System Endpoints (10)

```
GET    /api/friends                - Get friends list
POST   /api/friends/request        - Send friend request
GET    /api/friends/requests       - Get pending requests
POST   /api/friends/accept/{id}    - Accept friend request
POST   /api/friends/reject/{id}    - Reject friend request
DELETE /api/friends/{id}           - Remove friend
GET    /api/friends/{id}/activity  - Get friend activity
POST   /api/friends/block/{id}     - Block user
POST   /api/friends/unblock/{id}   - Unblock user
GET    /api/friends/suggestions    - Get friend suggestions
```

### Messaging Endpoints (10)

```
GET    /api/conversations          - Get conversations list
POST   /api/conversations          - Create conversation
GET    /api/conversations/{id}     - Get conversation details
DELETE /api/conversations/{id}     - Delete conversation
GET    /api/conversations/{id}/messages - Get messages
POST   /api/conversations/{id}/messages - Send message
PUT    /api/messages/{id}          - Edit message
DELETE /api/messages/{id}          - Delete message
POST   /api/conversations/{id}/read - Mark as read
GET    /api/conversations/unread   - Get unread count
```

### Watch Rooms Endpoints (15)

```
GET    /api/rooms                  - List public rooms
POST   /api/rooms                  - Create room
GET    /api/rooms/{id}             - Get room details
PUT    /api/rooms/{id}             - Update room
DELETE /api/rooms/{id}             - Delete room
POST   /api/rooms/{id}/join        - Join room
POST   /api/rooms/{id}/leave       - Leave room
GET    /api/rooms/{id}/participants - Get participants
POST   /api/rooms/{id}/kick/{user_id} - Kick participant
POST   /api/rooms/{id}/play        - Start playback
POST   /api/rooms/{id}/pause       - Pause playback
POST   /api/rooms/{id}/seek        - Seek to position
GET    /api/rooms/{id}/messages    - Get room chat
POST   /api/rooms/{id}/messages    - Send chat message
WS     /api/rooms/{id}/ws          - WebSocket connection
```

### Admin Endpoints (15)

```
GET    /api/admin/dashboard        - Dashboard stats
GET    /api/admin/users            - List all users
GET    /api/admin/users/{id}       - Get user details
PUT    /api/admin/users/{id}       - Update user
DELETE /api/admin/users/{id}       - Delete user
POST   /api/admin/users/{id}/ban   - Ban user
POST   /api/admin/users/{id}/unban - Unban user
GET    /api/admin/content          - List all content
POST   /api/admin/content/scan     - Trigger full scan
GET    /api/admin/analytics        - Get analytics
GET    /api/admin/logs             - Get system logs
GET    /api/admin/health           - System health
GET    /api/admin/mirrors          - Mirror system status
POST   /api/admin/cache/clear      - Clear cache
GET    /api/admin/settings         - Get settings
```

### Health & Monitoring Endpoints (5)

```
GET    /health                     - Basic health check
GET    /api/health/detailed        - Detailed health status
GET    /api/metrics                - System metrics
GET    /api/status                 - Service status
GET    /api/version                - API version info
```

---

## 🎨 Frontend Components

### Main Pages (7)

1. **Home.tsx** - Landing page with featured content
2. **BrowsePage.tsx** - Browse movies and series
3. **SearchPage.tsx** - Search functionality
4. **MovieDetail.tsx** - Movie details page
5. **SeriesDetail.tsx** - Series details page
6. **WatchRoomsPage.tsx** - Watch rooms interface
7. **AdminDashboard.tsx** - Admin control panel

### Admin Components (6)

1. **Analytics.tsx** - Analytics dashboard
2. **UserManagement.tsx** - User management interface
3. **ContentManagement.tsx** - Content management
4. **ResourceMonitoring.tsx** - Resource monitoring
5. **NotificationSystem.tsx** - Notification management
6. **AuditLogs.tsx** - Audit log viewer

### Shared Components (4)

1. **NavBar.tsx** - Navigation bar
2. **VideoPlayer.tsx** - Video player component
3. **ContentCard.tsx** - Content card display
4. **HeroCarousel.tsx** - Hero carousel

### Room Components (1)

1. **RoomCard.tsx** - Watch room card

---

## ⚙️ Integrated Systems

### 1. Authentication & Security System

**Components:**
- JWT token-based authentication
- Session management
- Rate limiting (100 requests/minute)
- CORS protection
- Input validation
- SQL injection prevention

**Files:**
- `app/security.py` - Security utilities
- `app/main.py` - Auth middleware

### 2. Streaming System (21 Bots)

**Architecture:**
- 9 mirror groups
- 3 bots per group (primary + 2 backups)
- Automatic failover
- Load balancing
- Health monitoring

**Files:**
- `app/stream.py` - Streaming logic
- `app/mirror_manager.py` - Mirror management
- `app/health_monitor.py` - Health checks

**Bot Distribution:**
```
Group 1: Bot1, Bot2, Bot3
Group 2: Bot4, Bot5, Bot6
Group 3: Bot7, Bot8, Bot9
Group 4: Bot10, Bot11, Bot12
Group 5: Bot13, Bot14, Bot15
Group 6: Bot16, Bot17, Bot18
Group 7: Bot19, Bot20, Bot21
Group 8: (Reserved)
Group 9: (Reserved)
```

### 3. Caching System

**Layers:**
- API response cache (5 minutes)
- Content metadata cache (1 hour)
- User data cache (15 minutes)
- Search results cache (10 minutes)

**Files:**
- `app/cache.py` - Basic cache
- `app/smart_cache.py` - Smart caching

**Metrics:**
- Hit rate: ~70%
- Miss rate: ~30%
- Average response time: 0.09s

### 4. Mirror System (9 Groups)

**Features:**
- Automatic health monitoring
- Load balancing
- Failover mechanism
- Priority-based routing
- Capacity management

**Health Scoring:**
- Response time: 30%
- Success rate: 40%
- Error rate: 20%
- Load: 10%

### 5. Tracking & Analytics System

**Tracked Metrics:**
- Page views
- Content views
- Search queries
- User activity
- Playback analytics
- Error rates
- Performance metrics

**Files:**
- `app/analytics.py` - Analytics engine
- `app/user_tracking.py` - User tracking

### 6. Content Scanner System

**Features:**
- TMDB API integration
- Multi-source scanning
- Automatic metadata updates
- Episode tracking
- Quality detection

**Files:**
- `app/scanner.py` - Scanner logic
- `app/tmdb.py` - TMDB integration
- `app/multi_source_config.py` - Source config

### 7. Database Management System

**Features:**
- Connection pooling (10 connections)
- Automatic backups
- HuggingFace Datasets sync
- Query optimization
- Index management

**Files:**
- `app/database.py` - Database utilities
- `app/db_manager.py` - DB management
- `app/backup_manager.py` - Backup system

---

## 🐛 Known Issues (94 Errors)

### Critical Issues (P0) - 15 errors

1. **Database Connection Pool Exhaustion**
   - Severity: Critical
   - Impact: Service crashes under load
   - Location: `app/database.py:45`
   - Status: Needs immediate fix

2. **Memory Leak in Scanner**
   - Severity: Critical
   - Impact: RAM usage grows unbounded
   - Location: `app/scanner.py:120`
   - Status: Needs immediate fix

3. **Bot Token Exposure Risk**
   - Severity: Critical
   - Impact: Security vulnerability
   - Location: Multiple files
   - Status: Needs immediate fix

4. **Unhandled Database Exceptions**
   - Severity: Critical
   - Impact: Data loss possible
   - Location: `app/database.py:multiple`
   - Status: Needs immediate fix

5. **Race Condition in Room Sync**
   - Severity: Critical
   - Impact: Sync failures
   - Location: `app/room_sync.py:78`
   - Status: Needs immediate fix

### High Priority Issues (P1) - 35 errors

6-20. **API Error Handling Issues**
- Missing try-catch blocks
- Improper error responses
- No retry logic
- Timeout issues

21-30. **Database Query Issues**
- N+1 query problems
- Missing indexes
- Slow queries
- Lock contention

31-40. **Caching Issues**
- Cache invalidation bugs
- Stale data served
- Memory leaks
- Race conditions

### Medium Priority Issues (P2) - 44 errors

41-60. **Frontend Issues**
- Component re-render issues
- State management bugs
- Memory leaks
- Performance issues

61-80. **API Validation Issues**
- Missing input validation
- Weak type checking
- No rate limiting on some endpoints
- CORS issues

81-94. **Minor Issues**
- Code style inconsistencies
- Missing documentation
- Unused imports
- Debug code left in production

---

## 📊 Performance Metrics

### Current Capacity
- **Concurrent Viewers**: 1-2 (needs scaling to 10,000)
- **Database Connections**: 10 (max)
- **API Requests/min**: 100 (rate limited)
- **Cache Hit Rate**: 70%

### Response Times
- **Average API Response**: 0.09s
- **Database Query**: 0.05s
- **Cache Lookup**: 0.01s
- **TMDB API**: 0.3s

### Resource Usage
- **CPU Usage**: 42.5% (average)
- **RAM Usage**: 83.5% (high - needs optimization)
- **Disk I/O**: Moderate
- **Network**: Low

### Test Coverage
- **Overall**: 62.5%
- **Backend**: 70%
- **Frontend**: 55%
- **Integration**: 60%

### Uptime & Reliability
- **Target Uptime**: 99.9%
- **Current Uptime**: 98.5%
- **MTBF**: 72 hours
- **MTTR**: 15 minutes

---

## 🚀 Configuration & Deployment

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./popcorn.db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# TMDB API
TMDB_API_KEY=your_tmdb_api_key
TMDB_BASE_URL=https://api.themoviedb.org/3

# Telegram Bots (21 bots)
BOT_TOKEN_1=bot1_token
BOT_TOKEN_2=bot2_token
# ... (up to BOT_TOKEN_21)

# Mirror Groups (9 groups)
MIRROR_GROUP_1=-1001234567890
MIRROR_GROUP_2=-1001234567891
# ... (up to MIRROR_GROUP_9)

# Security
SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Cache
CACHE_TTL=300
CACHE_MAX_SIZE=1000

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# HuggingFace
HF_TOKEN=your_hf_token
HF_SPACE_NAME=your_space_name
HF_DATASET_NAME=your_dataset_name
```

### HuggingFace Spaces Configuration

```yaml
title: PopCorn Mini App
emoji: 🍿
colorFrom: red
colorTo: yellow
sdk: gradio
sdk_version: 4.0.0
app_file: app/main.py
pinned: false
```

### Telegram Bot Configuration

**Bot Permissions Required:**
- Send messages
- Send media
- Manage chat
- Read messages
- Access to file storage

**Webhook Setup:**
```python
webhook_url = f"https://{HF_SPACE_URL}/api/webhook/{bot_token}"
```

### TMDB API Configuration

**Required Endpoints:**
- `/movie/popular`
- `/movie/{id}`
- `/tv/popular`
- `/tv/{id}`
- `/search/multi`

**Rate Limits:**
- 40 requests per 10 seconds
- Caching recommended

---

## 💳 Technical Debt

### High Priority Debt

1. **Database Optimization**
   - Add missing indexes
   - Optimize slow queries
   - Implement query caching
   - Fix connection pooling

2. **Error Handling**
   - Add comprehensive try-catch blocks
   - Implement retry logic
   - Add proper logging
   - Create error recovery mechanisms

3. **Security Hardening**
   - Implement rate limiting everywhere
   - Add input sanitization
   - Secure bot tokens
   - Add CSRF protection

4. **Memory Management**
   - Fix memory leaks
   - Optimize cache usage
   - Implement garbage collection
   - Add memory monitoring

### Medium Priority Debt

5. **Code Quality**
   - Add type hints
   - Improve documentation
   - Refactor duplicated code
   - Add unit tests

6. **Performance Optimization**
   - Implement lazy loading
   - Add pagination everywhere
   - Optimize image loading
   - Reduce bundle size

7. **Monitoring & Logging**
   - Add structured logging
   - Implement metrics collection
   - Add alerting system
   - Create dashboards

### Future Considerations

8. **Scalability**
   - Implement horizontal scaling
   - Add load balancing
   - Use CDN for static assets
   - Implement microservices

9. **Features**
   - Add recommendation engine
   - Implement social features
   - Add mobile app
   - Create API documentation

10. **Infrastructure**
    - Move to production database
    - Implement CI/CD
    - Add automated testing
    - Create staging environment

