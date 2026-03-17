import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / '.env')


class Settings:
    database_url: str = os.getenv('DATABASE_URL', '')

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
