import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    OLIST_DB_PATH = DATA_DIR / "olist" / "olist.sqlite"
    SECONDARY_DB_PATH = DATA_DIR / "secondary" / "inventory.sqlite"
    
    # LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Voice Settings
    WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base.en")
    TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3").lower()
    
    # Query Constraints
    MAX_SELF_REPAIR_RETRIES = 3
    QUERY_TIMEOUT_SECONDS = 15
    MAX_ROWS_RETURNED = 500

    @classmethod
    def ensure_directories(cls):
        """Ensure necessary runtime directories exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (cls.DATA_DIR / "olist").mkdir(parents=True, exist_ok=True)
        (cls.DATA_DIR / "secondary").mkdir(parents=True, exist_ok=True)
        (cls.BASE_DIR / "temp_audio").mkdir(parents=True, exist_ok=True)
