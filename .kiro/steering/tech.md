# Tech Stack & Build Guide

## Core Framework
- **Django 4.2.4**: Web framework and ORM
- **Python 3.x**: Primary language (see `.python-version` for exact version)
- **SQLite**: Default database (can be configured)
- **Redis**: Caching layer and session storage

## Key Dependencies

### Telegram Integration
- **pyTelegramBotAPI 4.12.0**: Telegram bot library
- **python-dotenv**: Environment variable management

### Audio & Media Processing
- **yt-dlp**: YouTube video downloading
- **mutagen 1.47.0**: Audio metadata handling
- **scipy, numpy**: Audio processing and numerical computing

### AI & NLP
- **openai 1.88.0**: OpenAI API integration
- **ollama 0.6.1**: Local LLM integration
- **scikit-learn 1.7.2**: ML models (spam detection)
- **pydantic 2.9.2**: Data validation

### Database & Knowledge Graph
- **neo4j 5.24.0**: Graph database driver
- **neo4j-graphrag 1.7.0**: Graph RAG capabilities
- **pandas 2.0.3**: Data manipulation

### Web & HTTP
- **gunicorn 22.0.0**: WSGI server for production
- **httpx 0.28.1**: Async HTTP client
- **requests 2.32.2**: HTTP library

### Utilities
- **tqdm**: Progress bars
- **PyYAML**: YAML parsing
- **websockets**: WebSocket support

## Project Structure

The project uses Django's standard structure with **three main apps**:
- `cleaner/` - Spam detection and message filtering
- `youtuber/` - YouTube content management
- `calendarer/` - Schedule and calendar management

## Build & Deployment Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python manage.py runserver

# Create/apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Management Commands
Management commands are located in `{app}/management/commands/`:
```bash
# Examples (run from project root)
python manage.py set_webhook           # Configure Telegram webhook
python manage.py delete_webhook        # Remove webhook
python manage.py set_my_commands       # Set bot commands
python manage.py publish_current_date  # Publish lesson schedule
python manage.py delete_old_messages   # Clean up old messages
python manage.py train_spam_filter     # Train ML spam model
python manage.py remove_duplicate_messages
```

### Production Deployment
```bash
# Collect static files
python manage.py collectstatic

# Run with Gunicorn (typically behind reverse proxy)
gunicorn mmtelegrambot.wsgi:application --bind 0.0.0.0:8000
```

## Configuration

### Environment Variables
All configuration comes from `.env` file (see `.env.example`):
- `DEBUG`: Development mode flag
- `SECRET_KEY`: Django secret key
- `TOKEN_BOT`: Telegram bot token
- `WEBHOOK_URL`: Webhook endpoint
- `OPENAI_KEY`: OpenAI API key
- `NEO4J_URI`, `NEO4J_AUTH`: Neo4j connection
- `REDIS_LOCATION`: Redis connection string
- `WHITELISTED_USERS`: Comma-separated user IDs

### Logging
- Logs written to `logs/telegram_bot.log`
- Rotating file handler: 5MB max, 5 backups
- Configured for `cleaner.views` at INFO level

## External Services

- **Telegram**: Bot API via `pyTelegramBotAPI`
- **OpenAI**: GPT models for content generation
- **Neo4j**: Graph database for knowledge storage
- **Ollama**: Local model serving (optional)
- **Lemonfox ASR**: Speech recognition API (optional)
- **Redis**: Session/cache backend

## Code Style & Conventions

- Follow Django conventions (models in `models.py`, views in `views.py`)
- Use F-strings for string formatting
- Type hints where appropriate
- Django ORM for database queries
- Management commands for async/batch tasks
