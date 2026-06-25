# Product Overview

## MM Telegram Bot

A Django-based Telegram bot that manages multimedia content from YouTube videos with integrated AI capabilities.

### Core Capabilities

- **Content Management**: Process YouTube videos and extract audio content (lessons)
- **Message Filtering**: Spam detection and moderation for Telegram messages using machine learning
- **Knowledge Base**: Store lesson content in Neo4j graph database with semantic search capabilities
- **AI Integration**: Process audio transcription, semantic embeddings, and content summarization
- **Calendar Management**: Track and publish lesson schedules

### Key Features

- YouTube video downloading and audio extraction
- Audio transcription via multiple ASR providers (Lemonfox API, local recognition)
- Spam filtering using scikit-learn with probability scoring
- Semantic search using vector embeddings (OpenAI, custom models)
- Neo4j integration for knowledge graph storage
- Telegram webhook integration for real-time message handling
- Management commands for batch operations and maintenance

### User Roles

- **Admin**: Full control via admin dashboard
- **Whitelisted Users**: Can interact with specific bot commands
- **Chat Members**: Receive scheduled content and can ask questions
