import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / '.env')


class Settings:
    database_url: str = os.getenv('DATABASE_URL', '')
    jwt_secret_key: str = os.getenv('JWT_SECRET_KEY', 'wms-dispatch-dev-secret')
    jwt_algorithm: str = os.getenv('JWT_ALGORITHM', 'HS256')
    jwt_expire_hours: int = int(os.getenv('JWT_EXPIRE_HOURS', '24'))

    def __init__(self) -> None:
        if not self.database_url:
            raise RuntimeError('DATABASE_URL is missing in .env')
        parsed = urlparse(self.database_url)
        if not parsed.scheme:
            raise RuntimeError('DATABASE_URL is invalid: missing scheme')
        if not parsed.hostname:
            raise RuntimeError('DATABASE_URL is invalid: missing hostname')
        if not parsed.path or parsed.path.strip('/') == '':
            raise RuntimeError('DATABASE_URL is invalid: missing database name')


settings = Settings()
