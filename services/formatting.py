from __future__ import annotations

import html
import re


_DAY_RE = re.compile(
    r"^(?:\*+\s*)?(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье)[,:]?\s*(.*)$",
    re.IGNORECASE,
)


def format_workout_plan_text(raw: str) -> str:
    """
    Convert plain AI text into readable Telegram HTML.
    """
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return "План пустой. Попробуйте запросить /plan ещё раз."

    out: list[str] = ["🏋️ <b>План тренировок на неделю</b>", ""]
    started_day_block = False
    for line in lines:
        clean = line.strip("• ").strip()
        day_match = _DAY_RE.match(clean.strip("* "))
        if day_match:
            day_name = day_match.group(1).capitalize()
            suffix = day_match.group(2).strip(" -")
            if started_day_block:
                out.append("")
            if suffix:
                out.append(f"📅 <b>{html.escape(day_name)}</b> — <b>{html.escape(suffix)}</b>")
            else:
                out.append(f"📅 <b>{html.escape(day_name)}</b>")
            started_day_block = True
            continue

        if clean.startswith("-"):
            clean = clean.lstrip("- ").strip()
        if re.match(r"^\d+\)", clean):
            out.append(f"   • {html.escape(clean)}")
        elif ":" in clean and len(clean) < 220:
            out.append(f"   • {html.escape(clean)}")
        else:
            out.append(f"   {html.escape(clean)}")

    text = "\n".join(out)
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    return text


def format_nutrition_text(raw: str) -> str:
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return "Советы по питанию пустые. Попробуйте /nutrition ещё раз."
    out = ["🥗 <b>Рекомендации по питанию</b>", ""]
    for line in lines:
        clean = line.strip("• ").strip()
        if clean.startswith("-"):
            clean = clean.lstrip("- ").strip()
        if ":" in clean and len(clean) < 120:
            out.append("")
            out.append(f"🔹 <b>{html.escape(clean)}</b>")
        else:
            out.append(f"   • {html.escape(clean)}")
    text = "\n".join(out)
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    return text

