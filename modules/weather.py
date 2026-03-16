from __future__ import annotations

import os

import requests

from modules.common import now_kst

DEFAULT_LAT = 37.5665
DEFAULT_LON = 126.9780
DEFAULT_LOCATION_NAME = "서울"

WEATHER_CODE_LABELS = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분적으로 흐림",
    3: "흐림",
    45: "안개",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    71: "약한 눈",
    73: "눈",
    80: "약한 소나기",
    81: "소나기",
    95: "뇌우",
}

DAILY_QUOTES = [
    "작은 진전이 쌓이면 결국 큰 신뢰가 됩니다. 오늘도 차분하게 한 건씩 정리해봅시다.",
    "완벽함보다 꾸준함이 업무를 앞으로 움직입니다. 오늘도 필요한 일부터 정확히 처리해봅시다.",
    "바쁜 날일수록 우선순위가 실력을 만듭니다. 가장 중요한 한 가지부터 시작해봅시다.",
    "응답이 빠른 사람보다, 끝까지 책임지는 사람이 더 오래 기억됩니다. 오늘도 마무리까지 챙겨봅시다.",
    "하루의 분위기는 첫 한 건으로 달라집니다. 오늘도 좋은 흐름을 우리가 만들어봅시다.",
    "업무는 결국 신뢰의 반복입니다. 오늘도 한 번 더 확인하고, 한 번 더 정리해봅시다.",
    "해야 할 일이 많아도 방향이 분명하면 흔들리지 않습니다. 오늘도 중요한 일에 집중해봅시다.",
]


def _location() -> tuple[float, float, str]:
    lat_raw = str(os.environ.get("WEATHER_LAT", "")).strip()
    lon_raw = str(os.environ.get("WEATHER_LON", "")).strip()
    name_raw = str(os.environ.get("WEATHER_LOCATION_NAME", "")).strip()

    lat = float(lat_raw) if lat_raw else DEFAULT_LAT
    lon = float(lon_raw) if lon_raw else DEFAULT_LON
    name = name_raw or DEFAULT_LOCATION_NAME
    return lat, lon, name


def fetch_today_weather() -> dict:
    lat, lon, name = _location()
    today = now_kst().date().isoformat()
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "current_weather": "true",
            "timezone": "Asia/Seoul",
            "start_date": today,
            "end_date": today,
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    current = data.get("current_weather", {})
    daily = data.get("daily", {})
    weather_code = daily.get("weathercode", [current.get("weathercode", 0)])[0]
    return {
        "location_name": name,
        "weather_label": WEATHER_CODE_LABELS.get(weather_code, "변동성 있는 날씨"),
        "current_temp": round(current.get("temperature", 0)),
        "max_temp": round(daily.get("temperature_2m_max", [current.get("temperature", 0)])[0]),
        "min_temp": round(daily.get("temperature_2m_min", [current.get("temperature", 0)])[0]),
        "precipitation_probability": int(daily.get("precipitation_probability_max", [0])[0] or 0),
        "windspeed": round(current.get("windspeed", 0)),
    }


def _clothing_tip(weather: dict) -> str:
    max_temp = weather["max_temp"]
    min_temp = weather["min_temp"]
    rain_prob = weather["precipitation_probability"]
    windspeed = weather["windspeed"]

    if max_temp >= 28:
        tip = "가벼운 반팔 차림이 무난하고, 실내 냉방을 대비해 얇은 겉옷 하나 정도 챙기면 좋겠습니다."
    elif max_temp >= 23:
        tip = "얇은 셔츠나 가벼운 긴팔 정도가 무난하고, 아침저녁 기온 차를 대비해 얇은 겉옷이 있으면 좋겠습니다."
    elif max_temp >= 17:
        tip = "긴팔이나 얇은 자켓 차림이 무난하겠고, 오전 일정이 있다면 가벼운 겉옷이 잘 맞겠습니다."
    elif max_temp >= 10:
        tip = "니트나 자켓 정도의 간절기 차림이 좋고, 이른 시간 외출이 있다면 보온을 조금 더 챙기는 편이 좋겠습니다."
    else:
        tip = "코트나 두께감 있는 외투가 어울리겠고, 체감온도가 더 낮을 수 있어 보온에 신경 쓰는 편이 좋겠습니다."

    if rain_prob >= 60:
        tip += " 비 가능성이 높아 우산을 챙기는 편이 좋겠습니다."
    elif rain_prob >= 30:
        tip += " 늦은 시간 비 가능성이 있어 작은 우산을 챙겨두면 무난하겠습니다."

    if windspeed >= 20:
        tip += " 바람이 다소 강할 수 있어 얇더라도 바람을 막아주는 겉옷이 있으면 좋겠습니다."
    if min_temp <= 5 and max_temp - min_temp >= 8:
        tip += " 일교차가 큰 편이라 겹쳐 입기 좋은 차림을 추천드립니다."
    return tip


def format_weather_briefing(weather: dict) -> str:
    return (
        f"🌤 오늘 날씨 ({weather['location_name']})\n\n"
        f"{weather['weather_label']} 예상, 현재 {weather['current_temp']}도 / 최고 {weather['max_temp']}도 / 최저 {weather['min_temp']}도입니다.\n"
        f"{_clothing_tip(weather)}"
    )


def get_daily_motivation() -> str:
    return DAILY_QUOTES[now_kst().toordinal() % len(DAILY_QUOTES)]
