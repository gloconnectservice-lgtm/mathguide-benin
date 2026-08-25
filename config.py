"""
Configuration de MathGuide Bénin.
Toutes les valeurs sensibles / variables passent par l'environnement (.env).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR
PROGRAMMES_DIR = BASE_DIR  # PDF déposés directement à la racine du dépôt (structure plate)
EXERCISES_DIR = BASE_DIR
CHROMA_DIR = BASE_DIR / "chroma_db"
PROGRESS_DB_PATH = BASE_DIR / "progress.json"

# --- LLM ---
# Fournisseur : "xai" (Grok), "openai", "mistral", "groq" — tous compatibles avec le SDK openai
# via base_url personnalisée. Groq est recommandé pour démarrer gratuitement (voir README).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

LLM_API_KEY = (
    os.getenv("GROQ_API_KEY")
    or os.getenv("XAI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("MISTRAL_API_KEY")
    or ""
)

PROVIDER_BASE_URLS = {
    "xai": "https://api.x.ai/v1",
    "openai": "https://api.openai.com/v1",
    "mistral": "https://api.mistral.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
}

PROVIDER_DEFAULT_MODELS = {
    "xai": "grok-4-fast",
    "openai": "gpt-4o-mini",
    "mistral": "mistral-large-latest",
    "groq": "llama-3.3-70b-versatile",
}

LLM_BASE_URL = os.getenv("LLM_BASE_URL", PROVIDER_BASE_URLS.get(LLM_PROVIDER, PROVIDER_BASE_URLS["xai"]))
LLM_MODEL = os.getenv("LLM_MODEL", PROVIDER_DEFAULT_MODELS.get(LLM_PROVIDER, PROVIDER_DEFAULT_MODELS["xai"]))

# --- RAG ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
RAG_COLLECTION_NAME = "programmes_benin"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))

# --- OCR ---
OCR_ENGINE = os.getenv("OCR_ENGINE", "easyocr")  # "easyocr" ou "tesseract"
OCR_LANGUAGES = ["fr"]

# --- Application ---
APP_TITLE = "MathGuide Bénin"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# --- Programme : classes et séries ---
CLASSES = ["6e", "5e", "4e", "3e", "2nde", "1ere", "Terminale"]
SERIES_PAR_CLASSE = {
    "6e": [],
    "5e": [],
    "4e": [],
    "3e": [],
    "2nde": ["A", "C"],
    "1ere": ["A1", "A2", "B", "C", "D"],
    "Terminale": ["A1", "A2", "B", "C", "D"],
}

COMPETENCES_DOMAINES = [
    "Numérique et algèbre",
    "Géométrie",
    "Grandeurs et mesures",
    "Organisation de données / statistiques",
    "Fonctions",
    "Suites",
    "Probabilités",
    "Analyse (dérivées, intégrales, limites)",
    "Vecteurs et géométrie analytique",
]

if not LLM_API_KEY:
    print("[MathGuide Bénin] ATTENTION : aucune clé API LLM détectée "
          "(GROQ_API_KEY / XAI_API_KEY / OPENAI_API_KEY / MISTRAL_API_KEY). "
          "Définissez-la dans le fichier .env avant de lancer l'application. "
          "Groq (console.groq.com) offre un accès gratuit rapide pour démarrer.")

# --- Supabase (persistance de la progression) ---
# Si non renseigné, l'application bascule automatiquement sur un stockage JSON local
# (pratique pour le développement, mais non persistant sur la plupart des hébergeurs gratuits).
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # clé "anon" ou "service_role" selon le contexte
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)
