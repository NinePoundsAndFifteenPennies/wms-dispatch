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
    dispatcher_active_work_order_limit: int = int(os.getenv('DISPATCHER_ACTIVE_WORK_ORDER_LIMIT', '5'))
    bailian_api_key: str = os.getenv('DASHSCOPE_API_KEY', '').strip()
    bailian_base_url: str = os.getenv('BAILIAN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1').strip()
    bailian_planner_model: str = os.getenv('BAILIAN_PLANNER_MODEL', 'qwen3.5-plus').strip()
    bailian_fast_model: str = os.getenv('BAILIAN_FAST_MODEL', 'qwen3.5-flash').strip()
    bailian_timeout_seconds: int = int(os.getenv('BAILIAN_TIMEOUT_SECONDS', '20'))
    bailian_refine_timeout_seconds: int = int(os.getenv('BAILIAN_REFINE_TIMEOUT_SECONDS', '6'))
    bailian_refine_attempt_timeout_seconds: int = int(os.getenv('BAILIAN_REFINE_ATTEMPT_TIMEOUT_SECONDS', '4'))
    bailian_refine_max_model_attempts: int = int(os.getenv('BAILIAN_REFINE_MAX_MODEL_ATTEMPTS', '3'))
    bailian_stage_model_picking: str = os.getenv('BAILIAN_STAGE_MODEL_PICKING', '').strip()
    bailian_stage_model_staging: str = os.getenv('BAILIAN_STAGE_MODEL_STAGING', '').strip()
    bailian_stage_model_shipping: str = os.getenv('BAILIAN_STAGE_MODEL_SHIPPING', '').strip()
    bailian_fallback_models_raw: str = os.getenv(
        'BAILIAN_FALLBACK_MODELS',
        'glm-5,qwen3.5-plus-2026-02-15,qwen3.5-122b-a10b,MiniMax-M2.5,kimi-k2.5,qwen3.5-flash',
    ).strip()
    cors_allow_origins_raw: str = os.getenv('CORS_ALLOW_ORIGINS', '*').strip()

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
        if self.dispatcher_active_work_order_limit < 1:
            raise RuntimeError('DISPATCHER_ACTIVE_WORK_ORDER_LIMIT must be >= 1')
        if self.bailian_timeout_seconds < 1:
            raise RuntimeError('BAILIAN_TIMEOUT_SECONDS must be >= 1')
        if self.bailian_refine_timeout_seconds < 1:
            raise RuntimeError('BAILIAN_REFINE_TIMEOUT_SECONDS must be >= 1')
        if self.bailian_refine_attempt_timeout_seconds < 1:
            raise RuntimeError('BAILIAN_REFINE_ATTEMPT_TIMEOUT_SECONDS must be >= 1')
        if self.bailian_refine_max_model_attempts < 1:
            raise RuntimeError('BAILIAN_REFINE_MAX_MODEL_ATTEMPTS must be >= 1')

    @property
    def cors_allow_origins(self) -> list[str]:
        raw = self.cors_allow_origins_raw
        if not raw:
            return ['*']
        return [item.strip() for item in raw.split(',') if item.strip()]

    @property
    def bailian_fallback_models(self) -> list[str]:
        raw = self.bailian_fallback_models_raw
        if not raw:
            return []
        return [item.strip() for item in raw.split(',') if item.strip()]


settings = Settings()
