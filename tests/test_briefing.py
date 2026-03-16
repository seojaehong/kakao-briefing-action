from datetime import datetime

from modules.briefing import build_full_briefing
from modules.common import KST


def test_build_full_briefing_with_mocked_dependencies(monkeypatch):
    monkeypatch.setattr("modules.briefing.fetch_today_weather", lambda: {
        "location_name": "서울",
        "weather_label": "흐림",
        "current_temp": 10,
        "max_temp": 13,
        "min_temp": 4,
        "precipitation_probability": 20,
        "windspeed": 5,
    })
    monkeypatch.setattr("modules.briefing.fetch_period_events", lambda days_ahead=2: [])
    monkeypatch.setattr("modules.briefing.build_mail_briefing", lambda mode="am", max_results=30: "📧 업무 메일 요약\n\n테스트 메일")
    text = build_full_briefing(mode="am", now=datetime(2026, 3, 16, 7, 30, tzinfo=KST))
    assert "[노무법인 위너스 업무 브리핑]" in text
    assert "📧 업무 메일 요약" in text
    assert "한마디:" in text
