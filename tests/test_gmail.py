from modules.gmail import _is_likely_business_email


def test_filters_business_email_by_keywords():
    email = {
        "sender": "담당자 <hr@example.com>",
        "subject": "쿠우쿠우 퇴사자 급여 처리 요청",
        "snippet": "",
        "body": "",
        "attachments": [],
    }
    assert _is_likely_business_email(email) is True


def test_filters_out_newsletter_like_email():
    email = {
        "sender": "newsletter@example.com",
        "subject": "이번 주 뉴스레터",
        "snippet": "unsubscribe here",
        "body": "",
        "attachments": [],
    }
    assert _is_likely_business_email(email) is False


def test_filters_out_ignored_sender():
    email = {
        "sender": "박현웅 노무사 <labor@example.com>",
        "subject": "금품청산 기한 안내",
        "snippet": "",
        "body": "",
        "attachments": [],
    }
    assert _is_likely_business_email(email) is False
