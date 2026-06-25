# Project Structure & Organization

## Directory Layout

```
MM_telegram_bot/
├── mmtelegrambot/              # Django project settings & config
│   ├── settings.py             # Main Django settings
│   ├── urls.py                 # URL routing
│   ├── wsgi.py                 # WSGI application
│   └── asgi.py                 # ASGI application
│
├── cleaner/                    # App: Spam detection & message filtering
│   ├── management/commands/    # Management commands
│   │   ├── set_webhook.py
│   │   ├── delete_webhook.py
│   │   ├── train_spam_filter.py
│   │   ├── delete_old_messages.py
│   │   ├── remove_duplicate_messages.py
│   │   ├── clear_deleted_messages.py
│   │   └── set_my_commands.py
│   ├── migrations/             # Database migrations
│   ├── models.py               # Message, Question models
│   ├── views.py                # Webhook handler for messages
│   ├── spam_detector.py        # ML spam detection logic
│   ├── utils.py                # Helper functions
│   └── admin.py                # Django admin configuration
│
├── youtuber/                   # App: YouTube content & lesson management
│   ├── management/commands/
│   │   └── download_audio.py   # Download audio from YouTube videos
│   ├── migrations/
│   ├── models.py               # Lesson model
│   ├── views.py                # Lesson-related views
│   ├── urls.py                 # URL patterns
│   └── admin.py                # Admin configuration
│
├── calendarer/                 # App: Schedule & calendar management
│   ├── management/commands/
│   │   ├── publish_current_date.py
│   │   └── delete_date_message_without_lessons.py
│   ├── migrations/
│   ├── models.py               # Date model
│   ├── views.py                # Calendar views
│   └── admin.py
│
├── Similarity_search_audio/    # Audio processing & semantic search utilities
│   ├── notebooks/              # Jupyter notebooks for exploration
│   ├── all_steps_add_lesson_to_base.py
│   ├── embd_database.py        # Embedding & Neo4j integration
│   ├── get_audio.py            # Audio download utilities
│   ├── recognize_audio.py      # Audio transcription (API-based)
│   ├── local_speach_recognition.py  # Local speech recognition
│   ├── search_scripts.py       # Semantic search implementation
│   └── README.md
│
├── templates/                  # Django HTML templates
│
├── media/                      # User-uploaded media files
│   └── audio/                  # Downloaded lesson audio files
│
├── logs/                       # Application logs
│   └── telegram_bot.log        # Main log file
│
├── v1/                         # Legacy/archived code
│
├── .kiro/                      # Kiro configuration
│   ├── steering/               # Steering rules (this directory)
│   └── settings/
│
├── manage.py                   # Django CLI
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (local only)
├── .env.example                # Example env template
├── .python-version             # Python version specification
├── .gitignore                  # Git ignore rules
└── db.sqlite3                  # SQLite database (local dev only)
```

## App Responsibilities

### `cleaner/` - Spam Detection & Message Filtering
**Purpose**: Filter and manage Telegram messages, detect spam using ML

**Key Components**:
- `Message` model: Stores raw Telegram messages with metadata
- `Question` model: Stores user questions for Q&A functionality
- `spam_detector.py`: scikit-learn-based spam classification
- Webhook handler in `views.py`: Receives messages from Telegram
- Management commands: Train model, delete old messages, set bot commands

**Key Methods**:
- `set_webhook.py`: Configure Telegram webhook endpoint
- `train_spam_filter.py`: Train spam classifier from message history
- `delete_old_messages.py`: Cleanup old messages by date

### `youtuber/` - YouTube Content Management
**Purpose**: Download and manage YouTube video content (lessons)

**Key Components**:
- `Lesson` model: Represents a YouTube video lesson with:
  - `youtube_id`: Unique YouTube video identifier
  - `audio_file`, `subtitles_file`: Downloaded media
  - `is_downloaded`, `is_published`, `is_inserted_to_db`: Status flags
  - Auto-cleanup of audio files after publishing
- `download_audio.py`: Management command to download audio from YouTube

**Workflow**:
1. Add YouTube URL
2. Download audio via `yt-dlp`
3. Transcribe audio (via API or local recognition)
4. Store in Neo4j
5. Publish to Telegram
6. Clean up local files

### `calendarer/` - Schedule Management
**Purpose**: Track and publish lesson schedules

**Key Components**:
- Date model: Lesson schedule tracking
- `publish_current_date.py`: Send scheduled lessons to Telegram
- `delete_date_message_without_lessons.py`: Cleanup orphaned schedules

### `Similarity_search_audio/` - Audio Processing & Search
**Purpose**: Audio transcription, embedding generation, and semantic search

**Key Modules**:
- `recognize_audio.py`: Convert audio to text (API-based ASR)
- `local_speach_recognition.py`: Local speech recognition option
- `embd_database.py`: Generate embeddings and store in Neo4j
- `search_scripts.py`: Semantic search via vector similarity
- `get_audio.py`: YouTube audio extraction utilities

## Model Relationships

```
Telegram Message (cleaner.Message)
├── Contains text content
├── Links to user_id
└── Classified as spam/ham

Question (cleaner.Question)
├── Linked to Message
├── Stores JSON result from LLM
└── Tracks user interactions

Lesson (youtuber.Lesson)
├── YouTube video reference
├── Audio file storage
├── Publishing status
└── Neo4j knowledge graph insertion status

Date (calendarer.Date)
└── References published lessons
```

## Data Flow

1. **Message Reception**: Telegram webhook → `cleaner.views` → Store in `Message` model
2. **Spam Filtering**: Message → `spam_detector.py` → Classification stored in DB
3. **Content Ingestion**: YouTube URL → `download_audio.py` → Audio file → Transcription
4. **Knowledge Storage**: Transcribed text → `embd_database.py` → Neo4j with embeddings
5. **Search**: User query → `search_scripts.py` → Semantic search in Neo4j
6. **Publication**: Scheduled lessons → `publish_current_date.py` → Telegram message

## Configuration & Secrets

- **Django Settings**: `mmtelegrambot/settings.py`
- **Environment Variables**: `.env` file (not in git)
- **Logging Config**: Defined in `settings.py`
- **Database**: Configurable via Django settings (defaults to SQLite)

## Database Layers

1. **SQLite/PostgreSQL**: Django ORM for messages, lessons, questions
2. **Neo4j**: Graph database for lesson content and semantic relationships
3. **Redis**: Cache and session storage
