#!/usr/bin/env python3
"""默认开启说话人分离的腾讯云 ASR 命令行入口。"""

from __future__ import annotations

from asr_tool.app import main


if __name__ == "__main__":
    raise SystemExit(main(force_speaker_diarization=True))
