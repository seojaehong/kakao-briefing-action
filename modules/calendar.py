from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from googleapiclient.discovery import build

from modules.common import KST, WEEKDAY_KO, now_kst
from modules.google_auth import build_google_credentials


def get_calendar_service():
    return build("calendar", "v3", credentials=build_google_credentials())


def _normalize_event(event: dict) -> dict:
    start = event.get("start", {})
    end = event.get("end", {})

    if "dateTime" in start:
        start_at = datetime.fromisoformat(start["dateTime"]).astimezone(KST)
        end_at = datetime.fromisoformat(end["dateTime"]).astimezone(KST)
        time_label = f"{start_at.strftime('%H:%M')} ~ {end_at.strftime('%H:%M')}"
        is_all_day = False
    else:
        start_at = datetime.fromisoformat(start["date"]).replace(tzinfo=KST)
        time_label = "종일"
        is_all_day = True

    return {
        "title": event.get("summary", "(제목 없음)"),
        "time": time_label,
        "location": event.get("location", ""),
        "attendees_count": len(event.get("attendees", [])),
        "is_all_day": is_all_day,
        "start_at": start_at,
        "date": start_at.date(),
    }


def fetch_period_events(days_ahead: int = 2, max_results: int = 80) -> list[dict]:
    now = now_kst()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = today_start + timedelta(days=days_ahead)

    result = (
        get_calendar_service()
        .events()
        .list(
            calendarId="primary",
            timeMin=today_start.isoformat(),
            timeMax=period_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
        )
        .execute()
    )
    return [_normalize_event(item) for item in result.get("items", [])]


def should_include_weekly_briefing(now: datetime | None = None) -> bool:
    now = now or now_kst()
    return (now.weekday() == 6 and now.hour >= 18) or (now.weekday() == 0 and now.hour < 12)


def _format_event_line(event: dict) -> str:
    parts = [f"• {'[종일]' if event['is_all_day'] else event['time']}  {event['title']}"]
    if event["location"]:
        parts.append(f"📍{event['location']}")
    if event["attendees_count"] > 0:
        parts.append(f"👥{event['attendees_count']}명")
    return "  ".join(parts)


def format_calendar_briefing(events: list[dict], now: datetime | None = None) -> str:
    now = now or now_kst()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    today_events = [event for event in events if event["date"] == today]
    tomorrow_events = [event for event in events if event["date"] == tomorrow]

    if not today_events and not tomorrow_events:
        date_label = now.strftime(f"%m월 %d일 ({WEEKDAY_KO[now.weekday()]})")
        return f"📅 오늘/내일 일정 ({date_label} 기준)\n\n등록된 일정이 없습니다."

    tomorrow_dt = now + timedelta(days=1)
    lines = ["📅 오늘/내일 일정", ""]
    lines.append(f"오늘 ({now.strftime(f'%m월 %d일 ({WEEKDAY_KO[now.weekday()]})')}) — 총 {len(today_events)}건")
    lines.extend([_format_event_line(event) for event in today_events] or ["• 등록된 일정이 없습니다."])
    lines.append("")
    lines.append(f"내일 ({tomorrow_dt.strftime(f'%m월 %d일 ({WEEKDAY_KO[tomorrow_dt.weekday()]})')}) — 총 {len(tomorrow_events)}건")
    lines.extend([_format_event_line(event) for event in tomorrow_events] or ["• 등록된 일정이 없습니다."])
    return "\n".join(lines)


def format_weekly_briefing(events: list[dict], now: datetime | None = None) -> str:
    now = now or now_kst()
    today = now.date()
    week_start = today + timedelta(days=1) if now.weekday() == 6 else today
    week_end = week_start + timedelta(days=6)

    grouped: dict = defaultdict(list)
    for event in events:
        if week_start <= event["date"] <= week_end:
            grouped[event["date"]].append(event)

    if not grouped:
        return f"🗓 이번 주 일정 요약 ({week_start.strftime('%m/%d')}~{week_end.strftime('%m/%d')})\n\n등록된 일정이 없습니다."

    lines = [f"🗓 이번 주 일정 요약 ({week_start.strftime('%m/%d')}~{week_end.strftime('%m/%d')})", ""]
    for date_key in sorted(grouped):
        lines.append(f"{date_key.strftime('%m월 %d일')} ({WEEKDAY_KO[date_key.weekday()]}) — {len(grouped[date_key])}건")
        for event in grouped[date_key][:4]:
            lines.append(_format_event_line(event))
        if len(grouped[date_key]) > 4:
            lines.append(f"• 그 외 {len(grouped[date_key]) - 4}건")
        lines.append("")
    return "\n".join(lines).strip()

