"""腾讯云声纹注册和认证旧/备用工具函数。"""

from __future__ import annotations

import argparse
import base64
import re
from pathlib import Path
from typing import Any

from .api import call_api
from .common import Credentials


VOICEPRINT_FILE_SIZE_LIMIT = 2 * 1024 * 1024
GROUP_ID_PATTERN = re.compile(r"^[A-Za-z_]{1,128}$")


def add_common_voiceprint_args(parser: argparse.ArgumentParser) -> None:
    """添加声纹接口通用参数。"""
    parser.add_argument(
        "--voice-format",
        type=int,
        choices=[0, 1],
        default=1,
        help="Audio format: 0=pcm, 1=wav (default: 1)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        choices=[16000],
        default=16000,
        help="Audio sample rate in Hz; Tencent Cloud voiceprint currently supports 16000",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--file",
        help="Local 16 kHz mono PCM/WAV voiceprint audio, base64 uploaded, <= 2 MB and <= 30 s",
    )
    source.add_argument(
        "--audio-url",
        help="Tencent Cloud COS audio URL for voiceprint audio",
    )


def read_voiceprint_audio(path_text: str) -> bytes:
    """读取并检查本地声纹音频。"""
    audio_path = Path(path_text)
    if not audio_path.is_file():
        raise FileNotFoundError(f"Voiceprint audio file not found: {audio_path}")

    audio_bytes = audio_path.read_bytes()
    if len(audio_bytes) > VOICEPRINT_FILE_SIZE_LIMIT:
        raise ValueError("Voiceprint local audio is larger than 2 MB; use --audio-url instead.")
    return audio_bytes


def build_audio_payload(args: argparse.Namespace) -> dict[str, Any]:
    """组装声纹接口共用的音频字段。"""
    payload: dict[str, Any] = {
        "VoiceFormat": args.voice_format,
        "SampleRate": args.sample_rate,
    }
    if args.file:
        audio_bytes = read_voiceprint_audio(args.file)
        payload["Data"] = base64.b64encode(audio_bytes).decode("ascii")
    else:
        payload["AudioUrl"] = args.audio_url
    return payload


def build_enroll_payload(args: argparse.Namespace) -> dict[str, Any]:
    """组装 VoicePrintEnroll 请求参数。"""
    payload = build_audio_payload(args)
    if args.speaker_nick:
        payload["SpeakerNick"] = args.speaker_nick
    if args.group_id:
        if not GROUP_ID_PATTERN.fullmatch(args.group_id):
            raise ValueError("--group-id must use only letters and underscores, max 128 chars.")
        payload["GroupId"] = args.group_id
    return payload


def build_verify_payload(args: argparse.Namespace) -> dict[str, Any]:
    """组装 VoicePrintVerify 请求参数。"""
    payload = build_audio_payload(args)
    payload["VoicePrintId"] = args.voice_print_id
    return payload


def enroll_speaker(args: argparse.Namespace, creds: Credentials) -> dict[str, Any]:
    """注册说话人，并返回腾讯云 Data 字段。"""
    response = call_api("VoicePrintEnroll", build_enroll_payload(args), args.region, creds)
    data = response.get("Data")
    if not isinstance(data, dict):
        raise RuntimeError("VoicePrintEnroll returned no Data object.")
    return data


def verify_speaker(args: argparse.Namespace, creds: Credentials) -> dict[str, Any]:
    """认证说话人，并返回腾讯云 Data 字段。"""
    response = call_api("VoicePrintVerify", build_verify_payload(args), args.region, creds)
    data = response.get("Data")
    if not isinstance(data, dict):
        raise RuntimeError("VoicePrintVerify returned no Data object.")
    return data
