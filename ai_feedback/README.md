# AI Feedback API

A FastAPI-based service that provides AI-powered feedback analysis for video presentations. The system transcribes audio from video submissions, analyzes speaking style and content accuracy, and generates comprehensive feedback based on predefined script requirements.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Evaluation Pipeline & CI/CD](#evaluation-pipeline--cicd)
- [Development](#development)
- [Deployment](#deployment)
- [Monitoring and Analytics](#monitoring-and-analytics)

## Overview

This service is designed to evaluate video presentations against predefined scripts and key elements. It leverages Google's Gemini AI models to:

- Transcribe audio from video files
- Analyze speaking style and confidence
- Match spoken content against required keywords and scripts
- Generate detailed, actionable feedback
- Track user interactions and feedback quality

## Features

### Core Capabilities

- **Video Processing**: Automatic conversion of video files to audio format using FFmpeg
- **Multimodal Video Analysis**: Direct video processing with Gemini's multimodal capabilities (audio + visual)
- **AI-Powered Transcription**: Accurate speech-to-text conversion with filler word detection
- **Visual Presentation Analysis**: Assessment of body language, facial expressions, and gestures
- **Keyword Matching**: Intelligent matching of spoken content against required keywords and scripts
- **Confidence Scoring**: Automated assessment of speaker confidence and delivery quality
- **Accuracy Scoring**: Evaluation of content coverage based on key elements
- **Feedback Generation**: Comprehensive, structured feedback with specific improvement suggestions
- **User Authentication**: JWT-based authentication for secure API access
- **Session Tracking**: Integration with Langfuse for monitoring and analytics
- **Feedback Quality Control**: AI-based judgment of generated feedback quality

### AI Models

The service uses Google's Gemini models:
- Primary model: `gemini-2.0-flash`
- Supports both OpenAI-compatible API and native Google GenAI SDK

## Architecture

### Technology Stack

- **Framework**: FastAPI
- **AI Provider**: Google Gemini (via OpenAI-compatible API)
- **Authentication**: JWT with python-jose
- **Monitoring**: Langfuse for observability and tracing
- **Video Processing**: FFmpeg
- **Structured Output**: Instructor library for type-safe AI responses
- **Logging**: Loguru for enhanced logging
- **Validation**: Pydantic for data validation

### Processing Pipeline

1. **Authentication**: User authenticates via `/login` endpoint
2. **Video Upload**: Client uploads video with script requirements
3. **Audio Extraction**: FFmpeg converts video to audio format
4. **Transcription**: AI transcribes audio and analyzes speaking style
5. **Keyword Extraction**: AI identifies keyword equivalents in transcript
6. **Scoring**: System calculates accuracy and confidence scores
7. **Feedback Generation**: AI generates comprehensive feedback
8. **Response**: API returns feedback with scores and session ID
9. **Quality Control**: Optional feedback judgment for quality assurance

## Prerequisites

### System Requirements

- Python 3.10 or higher (up to 3.13)
- FFmpeg installed on the system
- Docker (optional, for containerized deployment)

### External Services

- Google AI API key (for Gemini models)
- Langfuse account (for monitoring and analytics)

## Installation

### Local Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ai_feedback
```

2. Install dependencies using Poetry:
```bash
poetry install
```

Alternatively, using pip:
```bash
pip install -r requirements.txt
```

3. Install FFmpeg:
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y ffmpeg

# macOS
brew install ffmpeg
```

### Docker Setup

Build the Docker image:
```bash
make build
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# AI Configuration
AI_API_KEY=your_google_ai_api_key

# Langfuse Configuration
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_HOST=https://us.cloud.langfuse.com

# Authentication
LOGIN_USERNAME=your_username
LOGIN_PASSWORD=your_password
JWT_SECRET_KEY=your_jwt_secret_key
```

### Configuration File

The service configuration is managed in `ai_feedback/config.py` using Pydantic Settings:

- **ai_api_key**: Google AI API key for Gemini models
- **ai_base_url**: Base URL for AI API (defaults to Google's OpenAI-compatible endpoint)
- **ai_model_name**: Model to use (default: `gemini-2.0-flash`)
- **langfuse_secret_key**: Langfuse secret key for analytics
- **langfuse_public_key**: Langfuse public key
- **langfuse_host**: Langfuse host URL
- **login_username**: Username for API authentication
- **login_password**: Password for API authentication
- **jwt_secret_key**: Secret key for JWT token generation
- **algorithm**: JWT algorithm (default: HS256)
- **access_token_expire_minutes**: Token expiration time (default: 30 minutes)

## Usage

### Starting the Server

#### Using Make (Recommended)

```bash
# Build and start with Docker
make start-server
```

#### Using Poetry

```bash
poetry run uvicorn ai_feedback.main:app --host 0.0.0.0 --port 8080
```

#### Using Docker Directly

```bash
docker run --env-file .env -p 8080:8080 propractice-ai:local
```

### Making Requests

#### Authentication

First, obtain an access token:

```bash
curl -X POST http://localhost:8080/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Submitting Feedback Request

```bash
curl -X POST http://localhost:8080/feedback \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "video=@path/to/video.mp4" \
  -F 'feedback_input_str={
    "challenge": "1",
    "question": "Why does a customer need this service?",
    "briefing": "Brief description of the topic",
    "keyElements": [
      {
        "script": "Expected script content",
        "keywords": ["keyword1", "keyword2"]
      }
    ],
    "user_id": "user123",
    "tags": ["tag1", "tag2"]
  }'
```

#### Using the Test Script

The project includes a test script for easy testing:

```bash
make send-request
```

Or directly:

```bash
poetry run python ./scripts/send_request.py
```

## API Endpoints

### POST /login

Authenticate and receive a JWT token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### POST /feedback

Generate AI feedback for a video submission.

**Authentication:** Required (Bearer token)

**Request:**
- **video** (file): Video file (MP4, WebM, etc.)
- **feedback_input_str** (form data): JSON string containing:
  - **challenge** (string|int): Challenge identifier
  - **question** (string): The question or topic
  - **briefing** (string): Context and background information
  - **keyElements** (array): Array of script elements with keywords
    - **script** (string): Expected script content
    - **keywords** (array): Required keywords
  - **user_id** (string, optional): User identifier
  - **tags** (array, optional): Tags for categorization

**Response:**
```json
{
  "feedback": "Detailed feedback text...",
  "accuracy": 85,
  "confidence": 100,
  "session_id": "uuid-string"
}
```

### POST /feedback_video

Generate AI feedback for a video submission using multimodal analysis (audio + visual).

**Authentication:** Required (Bearer token)

**Request:**
- **video** (file): Video file (MP4, WebM, MOV, AVI, etc.)
- **feedback_input_str** (form data): JSON string containing:
  - **challenge** (string|int): Challenge identifier
  - **question** (string): The question or topic
  - **briefing** (string): Context and background information
  - **keyElements** (array): Array of script elements with keywords
    - **script** (string): Expected script content
    - **keywords** (array): Required keywords
  - **user_id** (string, optional): User identifier
  - **tags** (array, optional): Tags for categorization

**Response:**
```json
{
  "feedback": "Detailed feedback text including visual analysis...",
  "accuracy": 85,
  "confidence": 100,
  "session_id": "uuid-string"
}
```

**Key Differences from /feedback:**
- Processes video directly using Gemini's multimodal capabilities
- Includes analysis of visual elements (body language, facial expressions, gestures)
- Uses File API for better support of larger video files
- Provides richer, more comprehensive feedback

**Example:**
```bash
curl -X POST http://localhost:8080/feedback_video \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "video=@path/to/video.mp4" \
  -F 'feedback_input_str={
    "challenge": "1",
    "question": "Why does a customer need this service?",
    "briefing": "Brief description of the topic",
    "keyElements": [
      {
        "script": "Expected script content",
        "keywords": ["keyword1", "keyword2"]
      }
    ],
    "user_id": "user123",
    "tags": ["tag1", "tag2"]
  }'
```


### POST /like

Record user feedback on the AI-generated response.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "session_id": "uuid-string",
  "positive_feedback": true
}
```

**Note:** If `positive_feedback` is false, the system automatically triggers a quality judgment of the feedback.

### POST /judge

Manually trigger quality judgment for a feedback session.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "session_id": "uuid-string"
}
```

## Project Structure

```
ai_feedback/
├── ai_feedback/                 # Main application package
│   ├── __init__.py
│   ├── main.py                 # FastAPI application and endpoints
│   ├── ai.py                   # AI processing logic and model interactions
│   ├── models.py               # Pydantic models for request/response
│   ├── config.py               # Configuration management
│   ├── authentication.py       # JWT authentication logic
│   ├── utils.py                # Utility functions (video conversion, logging)
│   └── constants/              # Prompt templates and constants
│       ├── prompts.py          # Main AI prompts
│       ├── conditional_prompts.py  # Conditional prompt logic
│       └── fallback_prompts.py     # Fallback prompts
├── evaluation/                 # Evaluation pipeline for feedback quality
│   ├── evaluation_config.py    # Evaluation configuration
│   ├── extractor.py            # Extract style coaching from feedback
│   ├── similarity.py           # Semantic similarity calculation
│   ├── evaluator.py            # Main evaluation orchestrator
│   ├── api_client.py           # Feedback API client
│   ├── run_evaluation.py       # CLI script to run evaluations
│   ├── README.md               # Evaluation documentation
│   └── LANGFUSE_GUIDE.md       # Langfuse integration guide
├── scripts/                    # Utility scripts
│   ├── send_request.py         # Test script for API requests
│   ├── deploy.sh               # Production deployment script
│   └── deploy-dev.sh           # Development deployment script
├── data/                       # Test data and sample videos
│   ├── sets/                   # Test video sets
│   ├── challenges/             # Challenge payloads
│   └── answers/                # Reference answers for evaluation
├── Dockerfile                  # Docker container definition
├── Makefile                    # Build and deployment commands
├── pyproject.toml              # Poetry dependencies and project metadata
├── requirements.txt            # Pip requirements (generated from Poetry)
└── README.md                   # This file
```

### Key Components

#### main.py

The FastAPI application entry point containing:
- CORS middleware configuration
- Authentication endpoints
- Feedback generation endpoints (`/feedback` and `/feedback_video`)
- User feedback and judgment endpoints

#### ai.py

Core AI processing logic:
- `get_audio_analysis()`: Transcribes audio and analyzes speaking style
- `get_video_analysis()`: Analyzes video using multimodal capabilities (audio + visual)
- `get_keyword_equivalents()`: Matches transcript keywords with required keywords
- `get_text_analysis()`: Generates comprehensive feedback
- `judge_feedback()`: Evaluates feedback quality
- `get_feedback()`: Main orchestration function for audio-based feedback
- `get_feedback_from_video()`: Main orchestration function for video-based feedback

#### models.py

Pydantic models for type-safe data handling:
- `KeyElement`: Script element with keywords
- `ScriptDetails`: Question, briefing, and key elements
- `FeedbackInput`: Complete feedback request data
- `FeedbackResponse`: Feedback with scores and session ID
- `AudioAnalysis`: Transcript and speaking analysis
- `LessonDetailsExtractedKeywords`: Keyword matching results

#### utils.py

Utility functions:
- `convert_video_to_audio()`: FFmpeg video-to-audio conversion
- `read_audio()`: Audio file reading
- `generate_session_id()`: UUID generation
- `langfuse_log()`: Langfuse trace logging
- `langfuse_user_like()`: User feedback recording
- `fetch_feedback_input_output()`: Retrieve session data

#### authentication.py

JWT-based authentication:
- Token creation and validation
- Password verification
- Token dependency for protected endpoints

## Evaluation Pipeline & CI/CD

The project includes a comprehensive evaluation system that measures AI feedback quality by comparing generated style coaching against reference answers using semantic similarity.

### Automated CI/CD

The evaluation pipeline runs automatically via `.github/workflows/evaluation.yml`:

> [!NOTE]
> Evaluations are skipped for **draft Pull Requests** to save API quota. Mark the PR as **"Ready for Review"** to trigger the pipeline.

| Trigger | Experiment name | Result reported as |
|---|---|---|
| Pull request → `dev`/`main` | `pr-<number>` | Sticky PR comment with scores |
| Merge to `main` | `main` | GitHub Actions job summary |
| Merge to `dev` | `dev` | GitHub Actions job summary |
| Manual dispatch | custom / `manual-<run>` | GitHub Actions job summary |

#### Required GitHub Secrets

Add these in **Repository → Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `AI_API_KEY` | Google AI API key (Gemini + embeddings) |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| `LANGFUSE_HOST` | Langfuse host URL (e.g. `https://us.cloud.langfuse.com`) |

### Quick start (local)

```bash
# Run evaluation on all test sets
make evaluate

# Run with custom experiment name
make evaluate-experiment NAME=prompt_v2

# Run on a specific set
make evaluate-set SET=set_1 EXP=baseline
```

### Langfuse — where to find results

All results are stored in **Datasets → `ai_feedback_eval` → Runs** — one row per example, one column per experiment. Each trace also captures the full prompt and a stable `pipeline_run` timestamp tag so you can always trace which exact prompt produced which score.

See [evaluation/README.md](evaluation/README.md) for full setup, Langfuse navigation guide, and prompt-tuning workflow.

## Development

### Running Tests

Send a test request:
```bash
make send-request
```

### Generating Requirements

Update `requirements.txt` from Poetry dependencies:
```bash
make generate-requirements
```

### Code Quality

The project uses:
- **Pydantic**: For data validation and settings management
- **Type hints**: Throughout the codebase for better IDE support
- **Loguru**: For structured logging
- **Instructor**: For type-safe AI responses

### Adding New Features

1. Define new models in `models.py`
2. Add AI processing logic in `ai.py`
3. Create new endpoints in `main.py`
4. Update prompts in `constants/prompts.py`
5. Add tests in `scripts/send_request.py`

## Deployment

### Google Cloud Run (Production)

Deploy to production:
```bash
make deploy
```

This runs the `scripts/deploy.sh` script which:
- Sources environment variables from `.env`
- Deploys to Google Cloud Run in `us-central1`
- Sets all required environment variables
- Configures the service as publicly accessible

### Google Cloud Run (Development)

Deploy to development environment:
```bash
make deploy-dev
```

### Docker Deployment

Build and run locally with Docker:
```bash
make build
make start-server
```

### Manual Deployment

1. Generate requirements:
```bash
poetry export -f requirements.txt --without-hashes > requirements.txt
```

2. Build Docker image:
```bash
docker build -t propractice-ai:latest .
```

3. Run container:
```bash
docker run --env-file .env -p 8080:8080 propractice-ai:latest
```

## Monitoring and Analytics

### Langfuse Integration

The service integrates with Langfuse for:
- **Trace Logging**: All AI interactions are logged with session IDs
- **User Feedback**: Like/dislike tracking for feedback quality
- **Session Analysis**: Retrieve and analyze past sessions
- **Quality Metrics**: Automated feedback quality assessment

### Logging

The service uses Loguru for structured logging:
- Request/response logging
- Error tracking with stack traces
- AI interaction logging
- Session ID tracking

### Session Tracking

Each feedback request generates a unique session ID that tracks:
- Audio analysis results
- Keyword extraction
- Text analysis and feedback generation
- User feedback (like/dislike)
- Quality judgment results

## Troubleshooting

### Common Issues

**FFmpeg not found:**
```bash
# Install FFmpeg
sudo apt-get install ffmpeg  # Linux
brew install ffmpeg          # macOS
```

**Authentication errors:**
- Verify `.env` file contains correct credentials
- Check JWT secret key is set
- Ensure token hasn't expired

**AI API errors:**
- Verify Google AI API key is valid
- Check API quota and rate limits
- Ensure correct model name is configured

**Langfuse connection issues:**
- Verify Langfuse credentials in `.env`
- Check Langfuse host URL is correct
- Ensure network connectivity to Langfuse
