from __future__ import annotations

import json
import os

import requests

MAX_KAKAO_TEXT = 1950


def refresh_access_token() -> str:
    data = {
        "grant_type": "refresh_token",
        "client_id": os.environ["KAKAO_REST_API_KEY"],
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
        "client_secret": os.environ["KAKAO_CLIENT_SECRET"],
    }
    response = requests.post("https://kauth.kakao.com/oauth/token", data=data, timeout=10)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"카카오 토큰 갱신 실패: {payload.get('error_description', payload['error'])}")

    new_refresh = payload.get("refresh_token")
    if new_refresh:
        print("[ACTION REQUIRED] KAKAO_REFRESH_TOKEN이 갱신되었습니다. GitHub Secrets 값을 업데이트하세요.")
        print(new_refresh)
    return payload["access_token"]


def _split_long_section(section: str, max_len: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in section.splitlines():
        candidate = f"{current}\n{line}".strip() if current else line
        if len(candidate) <= max_len:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = line
        else:
            chunks.append(line[:max_len])
            current = line[max_len:]
    if current:
        chunks.append(current)
    return chunks


def split_briefing_messages(full_text: str, max_len: int = MAX_KAKAO_TEXT) -> list[str]:
    separator = "\n" + "─" * 30 + "\n"
    parts = full_text.split(separator)
    if len(parts) == 1 and len(full_text) <= max_len:
        return [full_text]

    header = parts[0].strip()
    sections = [part.strip() for part in parts[1:] if part.strip()]
    messages: list[str] = []
    current = header

    for section in sections:
        candidate = f"{current}{separator}{section}" if current else section
        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            messages.append(current)
            current = ""

        section_with_header = f"{header}{separator}{section}"
        if len(section_with_header) <= max_len:
            current = section_with_header
            continue

        for chunk in _split_long_section(section, max_len - len(header) - len(separator)):
            chunk_text = f"{header}{separator}{chunk}"
            messages.append(chunk_text[:max_len])

    if current:
        messages.append(current)

    if len(messages) <= 1:
        return messages

    numbered: list[str] = []
    for idx, message in enumerate(messages, 1):
        suffix = f"\n\n({idx}/{len(messages)})"
        numbered.append((message[: max_len - len(suffix)] if len(message) + len(suffix) > max_len else message) + suffix)
    return numbered


def send_kakao_message(text: str, access_token: str) -> bool:
    payload = {
        "object_type": "text",
        "text": text[:MAX_KAKAO_TEXT],
        "link": {
            "web_url": os.environ.get("KAKAO_TEMPLATE_WEB_URL", "https://github.com/"),
            "mobile_web_url": os.environ.get("KAKAO_TEMPLATE_WEB_URL", "https://github.com/"),
        },
    }
    response = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"template_object": json.dumps(payload, ensure_ascii=False)},
        timeout=10,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("result_code") != 0:
        raise RuntimeError(f"카카오톡 전송 실패: {result}")
    print("[INFO] 카카오톡 메시지 전송 성공")
    return True


def send_briefing(full_text: str, dry_run: bool = False) -> None:
    messages = split_briefing_messages(full_text)
    if dry_run:
        for message in messages:
            print("=" * 60)
            print(message)
            print("=" * 60)
        return

    access_token = refresh_access_token()
    for message in messages:
        send_kakao_message(message, access_token)
