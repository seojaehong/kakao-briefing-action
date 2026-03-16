from __future__ import annotations

import base64
import os
import re
from collections import Counter
from datetime import timedelta

from googleapiclient.discovery import build
from openai import OpenAI

from modules.common import now_kst
from modules.google_auth import build_google_credentials

CUSTOMER_KEYWORDS = [
    "쿠우쿠우",
    "다이닝원",
    "엘릭서",
    "내산",
    "코지",
    "리버호텔",
    "금별맥주",
    "피지벤처스",
]
IMPORTANT_ATTACHMENT_KEYWORDS = [
    "신고서",
    "원천징수",
    "영수증",
    "계약서",
    "급여",
    "보수총액",
    "이직확인서",
]


def get_gmail_service():
    return build("gmail", "v1", credentials=build_google_credentials())


def _extract_body(payload: dict) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore").strip()
            nested = _extract_body(part)
            if nested:
                return nested
        return ""
    data = payload.get("body", {}).get("data", "")
    if not data:
        return ""
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore").strip()


def _extract_attachment_names(payload: dict) -> list[str]:
    attachments: list[str] = []
    for part in payload.get("parts", []):
        filename = (part.get("filename") or "").strip()
        if filename:
            attachments.append(filename)
        attachments.extend(_extract_attachment_names(part))
    return attachments


def _customer_bucket(text: str) -> str:
    for keyword in CUSTOMER_KEYWORDS:
        if keyword in text:
            return keyword
    if "security alert" in text.lower() or "보안" in text:
        return "보안알림"
    return "기타"


def fetch_recent_emails(max_results: int = 30, mode: str = "am") -> list[dict]:
    service = get_gmail_service()
    now = now_kst()
    if mode == "pm":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=6)
    query = f"after:{int(start.timestamp())}"

    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    email_list = []
    for item in results.get("messages", []):
        message = service.users().messages().get(userId="me", id=item["id"], format="full").execute()
        headers = {header["name"]: header["value"] for header in message["payload"]["headers"]}
        email_list.append(
            {
                "id": item["id"],
                "subject": headers.get("Subject", "(제목 없음)"),
                "sender": headers.get("From", "(발신자 불명)"),
                "snippet": message.get("snippet", ""),
                "body": _extract_body(message["payload"])[:1200],
                "attachments": _extract_attachment_names(message["payload"]),
            }
        )
    return email_list


def _serialize_emails(email_list: list[dict]) -> str:
    blocks = []
    for idx, email in enumerate(email_list, 1):
        attachment_text = ", ".join(email["attachments"][:5]) if email["attachments"] else "없음"
        blocks.append(
            "\n".join(
                [
                    f"[메일 {idx}]",
                    f"발신자: {email['sender']}",
                    f"제목: {email['subject']}",
                    f"미리보기: {email['snippet']}",
                    f"본문: {email['body'][:400]}",
                    f"첨부: {attachment_text}",
                ]
            )
        )
    return "\n---\n".join(blocks)


def summarize_emails(email_list: list[dict]) -> str:
    if not email_list:
        return "📧 업무 메일 요약\n\n오늘 확인할 신규 업무 메일이 없습니다."

    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = f"""당신은 노무법인 담당자의 업무 브리핑 비서입니다.
아래 이메일들을 바탕으로 카카오톡용 업무 브리핑을 한국어로 작성하세요.

[출력 형식]
핵심 요약:
- 오늘 메일 흐름을 2~3문장으로 요약

즉시 처리 필요:
- 최대 3건

참고/보류:
- 최대 4건

첨부파일 처리:
- 첨부 확인이 필요한 건만 최대 3건

[규칙]
- 업무용 문체
- 과장 금지
- 전체 900자 이내
- 메일이 없으면 없다고 명확히 작성

[이메일 목록]
{_serialize_emails(email_list)}
"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1000,
    )
    return "📧 업무 메일 요약\n\n" + response.choices[0].message.content.strip()


def build_customer_counts(email_list: list[dict]) -> list[str]:
    counts = Counter()
    for email in email_list:
        counts[_customer_bucket(f"{email['sender']} {email['subject']}")] += 1
    return [f"- {name}: {count}건" for name, count in counts.most_common()]


def build_attachment_highlights(email_list: list[dict], limit: int = 3) -> list[str]:
    highlights: list[str] = []
    for email in email_list:
        for name in email["attachments"]:
            if any(keyword in name for keyword in IMPORTANT_ATTACHMENT_KEYWORDS):
                highlights.append(f"- {name}")
            if len(highlights) >= limit:
                return highlights
    return highlights


def build_mail_briefing(mode: str = "am", max_results: int = 30) -> str:
    email_list = fetch_recent_emails(max_results=max_results, mode=mode)
    summary = summarize_emails(email_list)
    customer_counts = build_customer_counts(email_list)
    attachment_highlights = build_attachment_highlights(email_list)

    sections = [summary]
    if customer_counts:
        sections.append("고객사별 현황:\n" + "\n".join(customer_counts[:6]))
    if attachment_highlights:
        sections.append("중요 첨부 도착:\n" + "\n".join(attachment_highlights))
    return "\n\n".join(sections)

