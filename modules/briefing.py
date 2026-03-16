from __future__ import annotations

from datetime import datetime

from modules.calendar import (
    fetch_period_events,
    format_calendar_briefing,
    format_weekly_briefing,
    should_include_weekly_briefing,
)
from modules.common import KST
from modules.gmail import build_mail_briefing
from modules.weather import fetch_today_weather, format_weather_briefing, get_daily_motivation

SEPARATOR = "\n" + "─" * 30 + "\n"
SINGLE_MESSAGE_TARGET = 1750


def _compact_mail_text(mail_text: str) -> str:
    marker = "\n\n고객사 현황:\n"
    if marker in mail_text:
        return mail_text.split(marker, 1)[0].rstrip()
    return mail_text


def _join_sections(header: str, sections: list[str], now_str: str, include_motivation: bool) -> str:
    body = SEPARATOR.join(section for section in sections if section)
    text = f"{header} {now_str}" + SEPARATOR + body
    if include_motivation:
        text += f"\n\n한마디: {get_daily_motivation()}"
    text += f"\n\n발송 시각: {now_str} (KST)"
    return text


def build_full_briefing(mode: str = "am", now: datetime | None = None) -> str:
    now = now or datetime.now(KST)
    now_str = now.strftime("%Y-%m-%d %H:%M")

    try:
        weather_text = format_weather_briefing(fetch_today_weather())
    except Exception as exc:
        weather_text = f"🌤 오늘 날씨 요약 생성 실패: {exc}"

    try:
        include_weekly = should_include_weekly_briefing(now)
        events = fetch_period_events(days_ahead=8 if include_weekly else 2)
        calendar_text = format_calendar_briefing(events, now=now)
        if include_weekly:
            calendar_text += "\n\n" + format_weekly_briefing(events, now=now)
    except Exception as exc:
        calendar_text = f"📅 일정 수집 실패: {exc}"

    try:
        mail_text = build_mail_briefing(mode=mode, max_results=30)
    except Exception as exc:
        mail_text = f"📧 업무 메일 요약 생성 실패: {exc}"

    header = "[노무법인 위너스 업무 브리핑]" if mode == "am" else "[노무법인 위너스 오후 업무 브리핑]"

    full_text = _join_sections(header, [weather_text, calendar_text, mail_text], now_str, include_motivation=True)
    if len(full_text) <= SINGLE_MESSAGE_TARGET:
        return full_text

    compact_text = _join_sections(header, [calendar_text, _compact_mail_text(mail_text)], now_str, include_motivation=False)
    if len(compact_text) <= SINGLE_MESSAGE_TARGET:
        return compact_text

    return compact_text
