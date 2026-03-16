from __future__ import annotations

import base64
import os
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
BUSINESS_KEYWORDS = [
    "급여",
    "퇴사",
    "입사",
    "근로",
    "노무",
    "보험",
    "고용",
    "산재",
    "원천",
    "세무",
    "신고",
    "정산",
    "상담",
    "미팅",
    "회의",
    "계약",
    "회신",
    "요청",
    "영수증",
    "이직확인서",
]
NON_BUSINESS_KEYWORDS = [
    "newsletter",
    "news",
    "광고",
    "프로모션",
    "홍보",
    "수신거부",
    "unsubscribe",
    "github",
]
IGNORED_SENDER_KEYWORDS = [
    "박현웅 노무사",
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


def _is_likely_business_email(email: dict) -> bool:
    sender = email.get("sender", "")
    haystack = " ".join(
        [
            sender,
            email.get("subject", ""),
            email.get("snippet", ""),
            email.get("body", "")[:300],
            " ".join(email.get("attachments", [])),
        ]
    )
    if any(keyword in haystack for keyword in IGNORED_SENDER_KEYWORDS):
        return False

    haystack = haystack.lower()

    if any(keyword.lower() in haystack for keyword in CUSTOMER_KEYWORDS):
        return True
    if any(keyword.lower() in haystack for keyword in IMPORTANT_ATTACHMENT_KEYWORDS):
        return True
    if any(keyword.lower() in haystack for keyword in BUSINESS_KEYWORDS):
        return True
    if any(keyword.lower() in haystack for keyword in NON_BUSINESS_KEYWORDS):
        return False
    return False


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
업무와 직접 관련 없는 메일, 보안알림, 뉴스레터, 홍보성 메일은 언급하지 마세요.

[출력 형식]
핵심:
- 오늘 업무 메일 흐름을 1~2문장으로 요약

즉시 처리 필요:
- 최대 3건

참고:
- 최대 3건

[규칙]
- 업무용 문체
- 과장 금지
- 이미 위에서 말한 내용을 반복하지 말 것
- 첨부파일 목록을 길게 나열하지 말 것
- 전체 550자 이내
- 메일이 없으면 없다고 명확히 작성

[이메일 목록]
{_serialize_emails(email_list[:12])}
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
    business_emails = [email for email in email_list if _is_likely_business_email(email)]
    summary = summarize_emails(business_emails)
    customer_counts = build_customer_counts(business_emails)

    if customer_counts:
        top_counts = [
            line
            for line in customer_counts
            if not line.startswith("- 기타") and not line.startswith("- 보안알림")
        ][:3]
        if top_counts:
            summary += "\n\n고객사 현황:\n" + "\n".join(top_counts)
    return summary
