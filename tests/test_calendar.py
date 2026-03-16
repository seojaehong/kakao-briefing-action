from datetime import datetime

from modules.calendar import format_calendar_briefing, format_weekly_briefing, should_include_weekly_briefing
from modules.common import KST


def test_should_include_weekly_briefing_for_sunday_evening():
    now = datetime(2026, 3, 15, 18, 30, tzinfo=KST)
    assert should_include_weekly_briefing(now) is True


def test_should_include_weekly_briefing_for_tuesday_morning():
    now = datetime(2026, 3, 17, 9, 0, tzinfo=KST)
    assert should_include_weekly_briefing(now) is False


def test_format_calendar_briefing_with_empty_events():
    now = datetime(2026, 3, 16, 7, 30, tzinfo=KST)
    text = format_calendar_briefing([], now=now)
    assert "등록된 일정이 없습니다." in text
    assert "오늘/내일 일정" in text


def test_format_weekly_briefing_groups_by_date():
    now = datetime(2026, 3, 16, 9, 0, tzinfo=KST)
    events = [
        {
            "title": "고객사 상담",
            "time": "10:00 ~ 11:00",
            "location": "회의실",
            "attendees_count": 2,
            "is_all_day": False,
            "date": datetime(2026, 3, 16, tzinfo=KST).date(),
        },
        {
            "title": "서류 검토",
            "time": "종일",
            "location": "",
            "attendees_count": 0,
            "is_all_day": True,
            "date": datetime(2026, 3, 17, tzinfo=KST).date(),
        },
    ]
    text = format_weekly_briefing(events, now=now)
    assert "이번 주 일정 요약" in text
    assert "고객사 상담" in text
    assert "서류 검토" in text

