"""
Configuration for the evaluation pipeline.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from parent .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# AI API for embeddings (uses same key as main app)
AI_API_KEY = os.getenv("AI_API_KEY", "")

# Langfuse configuration (uses same credentials as main app)
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")

# Test data paths (absolute paths - data dir is at same level as evaluation dir)
_EVAL_DIR = Path(__file__).parent
_DATA_DIR = _EVAL_DIR.parent / "data"

DATA_DIR = str(_DATA_DIR)
SETS_DIR = str(_DATA_DIR / "sets")
CHALLENGES_DIR = str(_DATA_DIR / "challenges")
ANSWERS_DIR = str(_DATA_DIR / "answers")
