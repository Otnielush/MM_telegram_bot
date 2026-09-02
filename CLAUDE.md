# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Django-based Telegram bot that manages a knowledge base of YouTube-sourced lessons for a chat community. It downloads YouTube videos, transcribes audio, generates embeddings/summaries, stores lesson content in Neo4j, publishes lessons to Telegram on a schedule, and filters spam/moderates incoming Telegram messages (with an LLM-backed Q&A feature over the lesson knowledge base).

## Commands

```bash
# Setup
pip install -r requirements.txt
cp .env.example .env   # then fill in secrets

# Development server
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Production
python manage.py collectstatic
gunicorn mmtelegrambot.wsgi:application --bind 0.0.0.0:8000
```

There is no configured test runner beyond Django's default `manage.py test` (per-app `tests.py` files are currently empty boilerplate) and no lint/format tooling configured in the repo.

### Telegram webhook management
```bash
python manage.py set_webhook
python manage.py delete_webhook
python manage.py set_my_commands
```

### Content pipeline (intended to run periodically, e.g. via cron — no scheduler is defined in-repo)
Run in this order; each command picks up `Lesson` rows left in the right state by the previous step:
```bash
python manage.py check_new_videos        # discover new YouTube uploads -> creates Lesson rows
python manage.py download_audio          # download audio+subtitles for one pending Lesson via yt-dlp
python manage.py make_summary            # generate a short GPT summary from subtitles
python manage.py send_lesson_to_telegram # publish a downloaded lesson to the Telegram chat
python manage.py insert_lesson_to_db     # embed + insert published lesson into Neo4j
python manage.py publish_current_date    # publish/update the day's schedule message
```

### Maintenance commands
```bash
python manage.py delete_old_messages
python manage.py remove_duplicate_messages
python manage.py clear_deleted_messages
python manage.py delete_date_message_without_lessons
python manage.py train_spam_filter       # retrain the scikit-learn spam classifier from Message history
```

## Architecture

Django project `mmtelegrambot` with three installed apps plus a standalone processing package:

- **cleaner/** — Telegram webhook entry point and message moderation.
  - `views.telegram_bot` (mounted at `/webhook/getpost/`) is the single webhook handler for all incoming Telegram updates: validates `WEBHOOK_SECRET_TOKEN`, persists messages to `Message`, runs `spam_detector` (scikit-learn) to flag/delete spam, and handles `@BOT_MENTION` questions by rate-limiting the user (`is_rate_limited`, Redis-backed via Django cache), running `Similarity_search_audio.search_scripts.similarity_search` against Neo4j, then asking an Ollama-hosted model to answer using only the retrieved lesson text (`Question` model stores the result).
  - `Message`/`Question` models live here.

- **youtuber/** — YouTube lesson ingestion pipeline, driven entirely by management commands (no views/scheduler in-repo — expected to be cron-driven). The `Lesson` model's boolean flags (`is_downloaded`, `is_published`, `is_inserted_to_db`, `skip`) form the pipeline state machine each command queries against (see Commands section above for the sequence). `Lesson.save()` auto-clears `audio_file`/`subtitles_file` once a lesson is both published and inserted into Neo4j, and signal handlers (`pre_save`/`post_delete`) delete the corresponding files from disk to avoid orphaned media.

- **calendarer/** — Tracks the daily schedule message (`Date` model) posted to Telegram; `publish_current_date` builds/edits that message from the day's `Lesson` rows, `delete_date_message_without_lessons` cleans up empty ones.

- **Similarity_search_audio/** — Not a Django app; a plain Python package for the AI/embedding side of the pipeline, imported directly by `cleaner/views.py` and `youtuber/management/commands/insert_lesson_to_db.py`:
  - `get_audio.py` — YouTube audio extraction helpers
  - `recognize_audio.py` / `local_speach_recognition.py` — ASR (Lemonfox API or local)
  - `embd_database.py` — builds embeddings and writes them into Neo4j
  - `search_scripts.py` — vector similarity search against Neo4j (used by the Q&A flow in `cleaner/views.py`)
  - `all_steps_add_lesson_to_base.py` — orchestrates the above into one insert call, used by `insert_lesson_to_db`

- **v1/** — legacy/archived standalone version of this bot (pre-Django). Not wired into the current Django project; avoid changes here unless explicitly asked to touch legacy code.

### Data flow
Telegram webhook → `cleaner.views` → `Message`/spam filter, or Q&A → Neo4j similarity search → Ollama.
YouTube URL → `check_new_videos`/`download_audio` (yt-dlp) → `make_summary` (OpenAI) → `send_lesson_to_telegram` → `insert_lesson_to_db` (embeddings → Neo4j) → local audio/subtitle files deleted.

### Storage layers
- **SQLite** (`db.sqlite3`) via Django ORM: `Message`, `Question`, `Lesson`, `Date`.
- **Neo4j**: lesson text + embeddings, queried for semantic search (`NEO4J_EMBD_INDEX`, `NEO4J_FULLTEXT_INDEX`).
- **Redis**: Django cache backend, used for rate limiting in `cleaner/views.py`.

### Configuration
All config is environment-driven via `.env` (see `.env.example`) and read into `mmtelegrambot/settings.py`, including `WHITELISTED_USERS`, `ADMIN_ID`, `TOKEN_BOT`/`WEBHOOK_SECRET_TOKEN`, OpenAI/Ollama/Lemonfox keys, and Neo4j connection details. Logging goes to `logs/telegram_bot.log` (rotating, 5MB/5 backups) and is currently only wired up for the `cleaner.views` logger.
