"""
Configuration for the evaluation pipeline.
"""

from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Populate os.environ so third-party SDKs (e.g. Langfuse) can read the vars
_ENV_FILE = Path(__file__).parent.parent / ".env"
load_dotenv(_ENV_FILE, override=False)


class Settings(BaseSettings):
    # Shared credentials (same vars as main app)
    ai_api_key: str
    langfuse_secret_key: str
    langfuse_public_key: str
    langfuse_host: str

    class Config:
        env_file = _ENV_FILE
        extra = "ignore"


settings = Settings()  # pyright: ignore

# ---------------------------------------------------------------------------
# Evaluation-specific constants (not from env)
# ---------------------------------------------------------------------------
_EVAL_DIR = Path(__file__).parent
_DATA_DIR = _EVAL_DIR.parent / "data"

DATA_DIR = str(_DATA_DIR)
SETS_DIR = str(_DATA_DIR / "sets")
CHALLENGES_DIR = str(_DATA_DIR / "challenges")
ANSWERS_DIR = str(_DATA_DIR / "answers")

SIMILARITY_THRESHOLD = 0.75   # Minimum similarity score to pass (0.0 to 1.0)
EMBEDDING_MODEL = "models/gemini-embedding-001"  # Only available embedding model
LANGFUSE_EXPERIMENT_PREFIX = "eval"

SIMILARITY_EXCELLENT = 0.90   # 0.90-1.00: Excellent - Nearly identical meaning
SIMILARITY_GOOD = 0.75        # 0.75-0.89: Good - Similar meaning with minor variations
SIMILARITY_FAIR = 0.60        # 0.60-0.74: Fair - Related but noticeable differences
# 0.00-0.59: Poor - Significantly different meaning