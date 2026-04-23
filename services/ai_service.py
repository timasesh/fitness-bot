from __future__ import annotations

import datetime as dt

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import settings
from db.models import AIUsageLog, NutritionTip, User, WorkoutPlan
from services.openai_client import (
    OpenAIClient,
    OpenAIConfig,
    OpenAIRequestError,
    OpenAIUnauthorizedError,
)


class AIService:
    def __init__(self, *, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self.sessionmaker = sessionmaker
        self.client = OpenAIClient(
            OpenAIConfig(
                api_key=settings.llm_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
                max_tokens=settings.ai_max_tokens,
            )
        )

    async def aclose(self) -> None:
        await self.client.aclose()

    async def _log_usage(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        request_type: str,
        tokens_used: int | None,
    ) -> None:
        session.add(AIUsageLog(user_id=user_id, request_type=request_type, tokens_used=tokens_used))
        await session.flush()

    async def generate_workout_plan(self, *, user: User) -> str:
        system = (
            "Ты — персональный фитнес‑тренер. Дай безопасный и реалистичный план тренировок. "
            "Пиши на русском. Структурируй ответ списком по дням/тренировкам. "
            "На каждую тренировку 3–4 упражнения, подходы/повторения и краткая техника (1–2 предложения). "
            "Соблюдай формат: сначала день недели и время, затем маркеры упражнений."
        )
        user_prompt = (
            f"Профиль:\n"
            f"- Цель: {user.goal}\n"
            f"- Уровень: {user.level}\n"
            f"- Тренировок в неделю: {user.frequency}\n"
            f"- Где: {user.location}\n"
            f"- Предпочтительное время: {user.preferred_time}\n\n"
            "Сгенерируй план на 1 неделю.\n"
            "Требования:\n"
            "- по дням недели;\n"
            "- 3-4 упражнения на день;\n"
            "- укажи подходы/повторы;\n"
            "- короткая техника для каждого упражнения."
        )

        async with self.sessionmaker() as session:
            try:
                text, tokens = await self.client.chat(system=system, user=user_prompt)
            except OpenAIUnauthorizedError as e:
                return (
                    "AI API вернул <b>401 Unauthorized</b>.\n\n"
                    f"Ответ: <code>{str(e)[:180]}</code>\n\n"
                    "Проверьте, что в `.env` указан корректный ключ "
                    "(для NVIDIA Build обычно <code>nvapi-...</code>) без пробелов/кавычек.\n"
                    "После замены ключа — <b>перезапустите</b> бота."
                )
            except OpenAIRequestError as e:
                return (
                    "Не получилось получить план от AI.\n"
                    f"Техническая причина: <code>{str(e)[:220]}</code>"
                )

            await self._log_usage(session, user_id=user.id, request_type="plan", tokens_used=tokens)
            session.add(WorkoutPlan(user_id=user.id, plan_json={"text": text}))
            await session.commit()
            return text

    async def get_nutrition_tips(self, *, user: User, force_refresh: bool = False) -> str:
        # По требованию продукта: используем последний сохранённый совет, пока
        # пользователь явно не попросит обновление.
        async with self.sessionmaker() as session:
            if not force_refresh:
                q = (
                    select(NutritionTip)
                    .where(NutritionTip.user_id == user.id)
                    .order_by(desc(NutritionTip.generated_at))
                    .limit(1)
                )
                res = await session.execute(q)
                last = res.scalar_one_or_none()
                if last:
                    return last.content

        system = (
            "Ты — нутрициолог. Дай практичные рекомендации по питанию под цель. "
            "Пиши на русском, коротко и по делу. Добавь примеры блюд и ориентиры по БЖУ."
        )
        user_prompt = f"Цель пользователя: {user.goal}. Дай рекомендации на ближайшие 3 дня."

        async with self.sessionmaker() as session:
            try:
                text, tokens = await self.client.chat(system=system, user=user_prompt)
            except OpenAIUnauthorizedError as e:
                return (
                    "AI API вернул <b>401 Unauthorized</b>.\n\n"
                    f"Ответ: <code>{str(e)[:180]}</code>\n\n"
                    "Проверьте, что в `.env` указан корректный ключ "
                    "(для NVIDIA Build обычно <code>nvapi-...</code>) без пробелов/кавычек.\n"
                    "После замены ключа — <b>перезапустите</b> бота."
                )
            except OpenAIRequestError as e:
                return (
                    "Не получилось получить рекомендации от AI.\n"
                    f"Техническая причина: <code>{str(e)[:220]}</code>"
                )

            await self._log_usage(session, user_id=user.id, request_type="nutrition", tokens_used=tokens)
            session.add(NutritionTip(user_id=user.id, content=text))
            await session.commit()

        return text

