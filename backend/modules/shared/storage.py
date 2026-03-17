from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESOURCES_ROOT = PROJECT_ROOT / "resources"
RESOURCE_DIRS = {
    "product_images": RESOURCES_ROOT / "product_images",
    "customer_avatars": RESOURCES_ROOT / "customer_avatars",
    "user_avatars": RESOURCES_ROOT / "user_avatars",
    "warehouse_covers": RESOURCES_ROOT / "warehouse_covers",
    "other": RESOURCES_ROOT / "other",
}

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def ensure_resource_dirs() -> None:
    for resource_dir in RESOURCE_DIRS.values():
        resource_dir.mkdir(parents=True, exist_ok=True)


def _guess_extension(upload_file: UploadFile) -> str:
    original_name = upload_file.filename or ""
    suffix = Path(original_name).suffix.lower()
    if suffix in ALLOWED_IMAGE_EXTENSIONS:
        return suffix

    content_type = (upload_file.content_type or "").lower()
    content_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    if content_type in content_map:
        return content_map[content_type]

    raise HTTPException(status_code=400, detail="Unsupported image format")


async def save_image_file(upload_file: UploadFile, bucket: str, entity_prefix: str, entity_id: int) -> str:
    if bucket not in RESOURCE_DIRS:
        raise HTTPException(status_code=500, detail="Invalid resource bucket")

    extension = _guess_extension(upload_file)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    unique_tag = uuid4().hex[:8]
    filename = f"{entity_prefix}_{entity_id}_{timestamp}_{unique_tag}{extension}"

    target_dir = RESOURCE_DIRS[bucket]
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename

    content = await upload_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty upload file")

    target_path.write_bytes(content)
    return f"/resources/{bucket}/{filename}"


def delete_resource_file_by_url(resource_url: str | None) -> bool:
    if not resource_url or not resource_url.startswith("/resources/"):
        return False

    relative = resource_url.removeprefix("/resources/")
    candidate = (RESOURCES_ROOT / relative).resolve()
    root = RESOURCES_ROOT.resolve()

    # Guard against path traversal and accidental out-of-root deletions.
    if root not in candidate.parents:
        return False

    if candidate.is_file():
        candidate.unlink()
        return True
    return False
