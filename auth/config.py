
import os
from pathlib import Path

from dotenv import load_dotenv

# Жобаның негізгі папкасы
BASE_DIR = Path(__file__).resolve().parent.parent

# .env файлындағы параметрлерді оқу
load_dotenv(BASE_DIR / ".env")

# Авторизация режимі:
# mock - тестілік жүйе
# oidc - университеттің ресми SSO жүйесі
AUTH_MODE = os.getenv("AUTH_MODE", "mock")

# ENU Opportunity AI серверінің мекенжайы
BASE_URL = os.getenv(
    "BASE_URL",
    "http://127.0.0.1:8000"
)

# Университеттің ресми SSO параметрлері
# Қазір бос болады, кейін рұқсат алған соң толтырамыз
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "")
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")

OIDC_REDIRECT_URI = os.getenv(
    "OIDC_REDIRECT_URI",
    f"{BASE_URL}/auth/callback"
)

OIDC_SCOPES = "openid profile email"

# Тек тестілік ортада қолданылатын параметр
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
