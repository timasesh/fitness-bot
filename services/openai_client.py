from __future__ import annotations

from dataclasses import dataclass

import httpx


class OpenAIUnauthorizedError(RuntimeError):
    pass


class OpenAIRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    base_url: str
    model: str
    max_tokens: int


class OpenAIClient:
    def __init__(self, cfg: OpenAIConfig) -> None:
        self.cfg = cfg
        self._client = httpx.AsyncClient(base_url=cfg.base_url, timeout=45.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(self, *, system: str, user: str) -> tuple[str, int | None]:
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key.strip()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self.cfg.max_tokens,
        }
        last_error: Exception | None = None
        for _attempt in range(3):
            try:
                resp = await self._client.post(
                    "/chat/completions",
                    headers=headers,
                    json=payload,
                )
                break
            except httpx.RequestError as e:
                last_error = e
        else:
            err_name = type(last_error).__name__ if last_error else "RequestError"
            err_text = str(last_error).strip() if last_error else ""
            raise OpenAIRequestError(f"Network error: {err_name} {err_text}".strip())

        if resp.status_code == 401:
            raise OpenAIUnauthorizedError(f"401 Unauthorized. {resp.text}".strip())

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise OpenAIRequestError(f"HTTP {e.response.status_code}. {e.response.text}".strip()) from e

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = None
        usage = data.get("usage")
        if isinstance(usage, dict):
            tokens = usage.get("total_tokens")
        return content, tokens
