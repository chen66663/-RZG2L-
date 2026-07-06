"""命令行参数解析和腾讯云密钥读取。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .common import Credentials, DEFAULT_REGION


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="Tencent Cloud ASR recording-file test",  # --help 里显示的程序说明
    )
    source = parser.add_mutually_exclusive_group(required=True)  # --file 和 --url 必须二选一
    source.add_argument(
        "--file",
        help="Local audio file path (base64 uploaded, <= 5 MB)",  # 本地音频文件路径
    )
    source.add_argument("--url", help="Publicly reachable audio URL")  # 公网可访问的音频 URL

    parser.add_argument(
        "--region",
        default=os.getenv("TENCENTCLOUD_REGION", DEFAULT_REGION),  # 可用环境变量覆盖默认地域
        help=f"Tencent Cloud region (default: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--credentials",
        default=None,  # 不传时默认读取当前目录的 asr_credentials.json
        help="JSON file with secret_id, secret_key and optional token",
    )
    parser.add_argument("--secret-id", default=None, help="Tencent Cloud SecretId")  # 命令行传 SecretId
    parser.add_argument("--secret-key", default=None, help="Tencent Cloud SecretKey")  # 命令行传 SecretKey
    parser.add_argument(
        "--token",
        default=None,  # 临时密钥才需要 token，永久密钥一般为空
        help="Temporary token for STS credentials",
    )
    parser.add_argument(
        "--engine-model",
        default="16k_zh",  # 默认中文 16k 模型，普通中文录音先用这个
        help="Example: 16k_zh, 8k_zh, 16k_en",
    )
    parser.add_argument(
        "--channel-num",
        type=int,
        default=1,  # 单声道最常用，16k 模型也要求单声道
        choices=[1, 2],  # 限制只能输入 1 或 2
        help="16k models should stay at 1; 2 is mainly for 8k dual-channel audio",
    )
    parser.add_argument(
        "--res-text-format",
        type=int,
        default=2,  # 2 会返回带标点和分段的详细文本
        choices=[0, 1, 2, 3, 4, 5],  # 腾讯云接口允许的结果格式编号
        help="2 returns detailed text with punctuation",
    )
    parser.add_argument(
        "--speaker-diarization",
        type=int,
        choices=[0, 1, 3],  # 0 关闭，1 普通说话人分离，3 腾讯云角色分离
        default=None,  # 不传就不向腾讯云发送这个字段
        help="0 disables speaker split, 1 enables it, 3 enables Tencent Cloud role separation",
    )
    parser.add_argument(
        "--speaker-label",
        action="append",
        default=[],
        metavar="ID=NAME",
        help="Friendly speaker label, for example: --speaker-label 0=Alice",
    )
    parser.add_argument(
        "--speaker-role",
        action="append",
        default=[],
        metavar="NAME=URL",
        help="Known speaker role audio URL for --speaker-diarization 3; example: --speaker-role Alice=https://...",
    )
    parser.add_argument(
        "--speaker-number",
        type=int,
        default=None,  # 指定说话人数，部分模型才支持
        help="Expected speaker count, only valid for supported non-16k models",
    )
    parser.add_argument(
        "--callback-url",
        default=None,  # 本脚本主要靠轮询，通常不需要回调地址
        help="Optional callback URL for async results",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,  # 第一次轮询等待 2 秒
        help="Initial polling interval in seconds",
    )
    parser.add_argument(
        "--max-poll-interval",
        type=float,
        default=10.0,  # 后续轮询间隔最多增长到 10 秒
        help="Maximum polling interval in seconds",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1800.0,  # 最多等待 1800 秒，也就是 30 分钟
        help="Max total wait time in seconds",
    )
    return parser.parse_args()  # 返回 argparse.Namespace，后面用 args.xxx 读取参数


def validate_args(args: argparse.Namespace) -> None:
    """提前拒绝腾讯云不支持的参数组合。"""
    if args.channel_num == 2 and args.engine_model.startswith("16k_"):
        raise ValueError("16k models only support --channel-num 1.")  # 16k 模型不能用双声道

    if args.speaker_number is not None and args.speaker_number not in range(0, 11):
        raise ValueError("--speaker-number must be between 0 and 10.")  # 腾讯云限制说话人数范围

    if args.speaker_number not in (None, 0) and args.engine_model.startswith("16k_"):
        raise ValueError("16k models do not support a fixed --speaker-number.")  # 16k 模型不支持固定人数

    if args.speaker_diarization == 3 and args.engine_model != "16k_zh_en":
        raise ValueError("--speaker-diarization 3 only supports --engine-model 16k_zh_en.")

    if args.speaker_role and args.speaker_diarization != 3:
        raise ValueError("--speaker-role requires --speaker-diarization 3.")

    if len(args.speaker_role) > 1:
        raise ValueError("Tencent Cloud role separation currently supports one --speaker-role.")

    for label in args.speaker_label:
        if "=" not in label:
            raise ValueError("--speaker-label must use ID=NAME, for example 0=Alice.")
        speaker_id, name = label.split("=", 1)
        if not speaker_id.strip() or not name.strip():
            raise ValueError("--speaker-label must include both speaker ID and name.")

    for role in args.speaker_role:
        if "=" not in role:
            raise ValueError("--speaker-role must use NAME=URL, for example Alice=https://...")
        role_name, audio_url = role.split("=", 1)
        if not role_name.strip() or not audio_url.strip():
            raise ValueError("--speaker-role must include both role name and audio URL.")


def load_credentials(args: argparse.Namespace) -> Credentials:
    """从命令行、环境变量或 JSON 文件读取腾讯云密钥。"""
    secret_id = (args.secret_id or os.getenv("TENCENTCLOUD_SECRET_ID", "")).strip()  # 优先命令行，其次环境变量
    secret_key = (args.secret_key or os.getenv("TENCENTCLOUD_SECRET_KEY", "")).strip()  # 优先命令行，其次环境变量
    token = (args.token or os.getenv("TENCENTCLOUD_TOKEN", "")).strip() or None  # 临时密钥才有 token

    credentials_path = (
        Path(args.credentials) if args.credentials else Path("asr_credentials.json")  # 默认读取当前目录密钥文件
    )
    if credentials_path.is_file():
        # 板子上推荐放 asr_credentials.json，这样运行命令时不用暴露密钥。
        with credentials_path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)  # 读取 JSON，得到一个 dict
        secret_id = secret_id or str(data.get("secret_id", "")).strip()  # 命令行/环境变量为空时才用文件值
        secret_key = secret_key or str(data.get("secret_key", "")).strip()  # 命令行/环境变量为空时才用文件值
        token = token or str(data.get("token", "")).strip() or None  # token 可以为空字符串

    if not secret_id or not secret_key:
        raise RuntimeError(
            "Missing credentials. Set TENCENTCLOUD_SECRET_ID and "
            "TENCENTCLOUD_SECRET_KEY, pass --secret-id/--secret-key, "
            "or create asr_credentials.json."
        )  # SecretId 和 SecretKey 缺一不可

    return Credentials(secret_id=secret_id, secret_key=secret_key, token=token)  # 打包成统一的凭据对象
