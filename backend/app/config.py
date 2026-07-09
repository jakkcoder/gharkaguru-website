import os
from pathlib import Path

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "vertex-ai-learning-487906")
DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp/website-data"))
DB_PATH = DATA_DIR / "website.db"
GCS_STATE_PATH = DATA_DIR / ".gcs_website_state.json"
WEBSITE_DB_GCS = os.getenv(
    "WEBSITE_DB_GCS",
    "gs://vertex-ai-learning-487906-gharka-leads/website.db",
)
UPLOADS_GCS_PREFIX = os.getenv(
    "UPLOADS_GCS_PREFIX",
    "gs://vertex-ai-learning-487906-gharka-leads/website-uploads",
)
PULL_ON_STARTUP = os.getenv("PULL_ON_STARTUP", "true").lower() in {"1", "true", "yes"}
GCS_LOCK_MAX_AGE_SECONDS = int(os.getenv("GCS_LOCK_MAX_AGE_SECONDS", "300"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "https://gharkaguru.com,https://www.gharkaguru.com,https://gharkaguru-website-lmquvtnfja-as.a.run.app,http://localhost:5173",
    ).split(",")
    if origin.strip()
]