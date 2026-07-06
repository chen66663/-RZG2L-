#!/usr/bin/env python3
"""腾讯云声纹注册和说话人认证命令行入口。"""

from __future__ import annotations

import argparse
import os
import sys

from asr_tool.cli import load_credentials
from asr_tool.common import DEFAULT_REGION
from asr_tool.voiceprint import (
    add_common_voiceprint_args,
    enroll_speaker,
    verify_speaker,
)


def add_credential_args(parser: argparse.ArgumentParser) -> None:
    """添加腾讯云密钥参数。"""
    parser.add_argument(
        "--region",
        default=os.getenv("TENCENTCLOUD_REGION", DEFAULT_REGION),
        help=f"Tencent Cloud region (default: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--credentials",
        default=None,
        help="JSON file with secret_id, secret_key and optional token",
    )
    parser.add_argument("--secret-id", default=None, help="Tencent Cloud SecretId")
    parser.add_argument("--secret-key", default=None, help="Tencent Cloud SecretKey")
    parser.add_argument("--token", default=None, help="Temporary token for STS credentials")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    credential_parser = argparse.ArgumentParser(add_help=False)
    add_credential_args(credential_parser)

    parser = argparse.ArgumentParser(
        description="Tencent Cloud voiceprint enroll/verify tool",
        parents=[credential_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    enroll_parser = subparsers.add_parser(
        "enroll",
        parents=[credential_parser],
        help="Register a speaker and return VoicePrintId",
    )
    add_common_voiceprint_args(enroll_parser)
    enroll_parser.add_argument("--speaker-nick", required=True, help="Speaker nickname, max 32 bytes")
    enroll_parser.add_argument(
        "--group-id",
        default=None,
        help="Optional group ID for later 1:N verification; letters and underscores only",
    )

    verify_parser = subparsers.add_parser(
        "verify",
        parents=[credential_parser],
        help="Verify audio against an existing VoicePrintId",
    )
    add_common_voiceprint_args(verify_parser)
    verify_parser.add_argument("--voice-print-id", required=True, help="Registered Tencent Cloud VoicePrintId")

    return parser.parse_args()


def print_enroll_result(data: dict[str, object]) -> None:
    """打印注册结果。"""
    print("=== VoicePrint Enroll ===")
    print(f"VoicePrintId: {data.get('VoicePrintId', '')}")
    print(f"SpeakerNick: {data.get('SpeakerNick', '')}")


def print_verify_result(data: dict[str, object]) -> None:
    """打印认证结果。"""
    decision = data.get("Decision")
    passed = "PASS" if decision == 1 else "FAIL"
    print("=== VoicePrint Verify ===")
    print(f"VoicePrintId: {data.get('VoicePrintId', '')}")
    print(f"Decision: {decision} ({passed})")
    print(f"Score: {data.get('Score', '')}")


def main() -> int:
    """运行声纹命令行工具。"""
    args = parse_args()
    try:
        creds = load_credentials(args)
        if args.command == "enroll":
            print_enroll_result(enroll_speaker(args, creds))
        elif args.command == "verify":
            print_verify_result(verify_speaker(args, creds))
        else:
            raise RuntimeError(f"Unknown command: {args.command}")
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
