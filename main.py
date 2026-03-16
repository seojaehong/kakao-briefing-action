from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from modules.briefing import build_full_briefing
from modules.kakao import send_briefing


def _configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GitHub Actions용 카카오 업무 브리핑")
    parser.add_argument("--mode", choices=["am", "pm"], default="am")
    parser.add_argument("--dry-run", action="store_true", help="카카오 전송 대신 콘솔 출력")
    return parser.parse_args()


def main() -> None:
    _configure_stdio()
    args = parse_args()
    dry_run = args.dry_run or os.environ.get("DRY_RUN", "").lower() == "true"

    print("=" * 50)
    print("카카오 업무 브리핑 시작")
    print("=" * 50)

    briefing = build_full_briefing(mode=args.mode)
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    (artifacts_dir / f"briefing_{args.mode}.txt").write_text(briefing, encoding="utf-8")

    try:
        send_briefing(briefing, dry_run=dry_run)
        print("\n✅ 브리핑 처리 완료")
    except Exception as exc:
        print(f"\n❌ 브리핑 실패: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
