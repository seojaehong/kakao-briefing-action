from modules.kakao import split_briefing_messages


def test_split_briefing_messages_keeps_numbering():
    text = "[업무 브리핑]\n" + ("\n" + "─" * 30 + "\n").join(
        [
            "첫 섹션",
            "둘째 섹션 " + ("가" * 1800),
            "셋째 섹션",
        ]
    )
    chunks = split_briefing_messages(text, max_len=500)
    assert len(chunks) >= 2
    assert chunks[-1].endswith(f"({len(chunks)}/{len(chunks)})")

