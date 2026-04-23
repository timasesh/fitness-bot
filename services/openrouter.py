from __future__ import annotations

from dataclasses import dataclass

import httpx

from config import settings


class OpenRouterUnauthorizedError(RuntimeError):
    pass


class OpenRouterRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    base_url: str
    model: str
    max_tokens: int


class OpenRouterClient:
    def __init__(self, cfg: OpenRouterConfig) -> None:
        self.cfg = cfg
        self._client = httpx.AsyncClient(base_url=cfg.base_url, timeout=15.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(self, *, system: str, user: str) -> tuple[str, int | None]:
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.cfg.api_key.strip()}",
            "Content-Type": "application/json",
        }
        if settings.app_url:
            headers["HTTP-Referer"] = settings.app_url
        if settings.app_name:
            headers["X-Title"] = settings.app_name

        try:
            resp = await self._client.post(
                "/chat/completions",
                headers=headers,
                json={
                    "model": self.cfg.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": self.cfg.max_tokens,
                },
            )
        except httpx.RequestError as e:
            raise OpenRouterRequestError(f"Network error: {e!s}") from e

        if resp.status_code == 401:
            detail = ""
            try:
                detail = resp.text
            except Exception:
                detail = ""
            raise OpenRouterUnauthorizedError(f"401 Unauthorized. {detail}".strip())

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text
            except Exception:
                body = ""
            raise OpenRouterRequestError(f"HTTP {e.response.status_code}. {body}".strip()) from e
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        tokens = None
        usage = data.get("usage")
        if isinstance(usage, dict):
            tokens = usage.get("total_tokens")
        return content, tokens

