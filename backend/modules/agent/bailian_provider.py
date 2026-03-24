from typing import Optional

import httpx

from modules.shared.config import settings


class BailianProvider:
    @staticmethod
    def is_enabled() -> bool:
        return bool(settings.bailian_api_key)

    @staticmethod
    async def chat_completion(
        *,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        if not settings.bailian_api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")

        endpoint = settings.bailian_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": model or settings.bailian_planner_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=settings.bailian_timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {settings.bailian_api_key}",
                    },
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Bailian request failed: {exc.response.status_code} {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Bailian network error: {exc}") from exc

        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("Bailian response has no choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()

        raise RuntimeError("Bailian response content is empty")
