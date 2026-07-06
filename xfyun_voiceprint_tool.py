#!/usr/bin/env python3
"""讯飞开放平台声纹识别命令行工具。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from asr_tool.xfyun_voiceprint import (
    DEFAULT_GROUP_ID,
    DEFAULT_THRESHOLD,
    create_feature,
    create_group,
    compare_feature,
    load_credentials,
    prepare_audio,
    query_features,
    score_passed,
)


def add_credential_args(parser: argparse.ArgumentParser) -> None:
    """添加讯飞鉴权参数。"""
    parser.add_argument(
        "--credentials",
        default=argparse.SUPPRESS,  # 不传时由 load_credentials 默认读 xfyun_credentials.json
        help="JSON file with app_id, api_key and api_secret",
    )
    parser.add_argument("--app-id", default=argparse.SUPPRESS, help="XFYUN APPID")  # 也可以命令行直接传 APPID
    parser.add_argument("--api-key", default=argparse.SUPPRESS, help="XFYUN APIKey")  # 也可以命令行直接传 APIKey
    parser.add_argument("--api-secret", default=argparse.SUPPRESS, help="XFYUN APISecret")  # 也可以命令行直接传 APISecret


def add_group_arg(parser: argparse.ArgumentParser) -> None:
    """添加 group id 参数。"""
    parser.add_argument(
        "--group-id",
        default=os.getenv("XFYUN_GROUP_ID", DEFAULT_GROUP_ID),  # 支持用环境变量切换默认特征库
        help=f"Voiceprint group id (default: {DEFAULT_GROUP_ID})",
    )


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    credential_parser = argparse.ArgumentParser(add_help=False)  # 子命令共享同一套鉴权参数
    add_credential_args(credential_parser)  # --credentials/--app-id/--api-key/--api-secret

    parser = argparse.ArgumentParser(
        description="iFLYTEK voiceprint create-group/enroll/verify tool",
        parents=[credential_parser],  # 允许凭据参数放在子命令前
    )
    subparsers = parser.add_subparsers(dest="command", required=True)  # 必须指定 prepare/create-group/enroll/verify/list

    prepare_parser = subparsers.add_parser("prepare", help="Convert audio to 16 kHz 16-bit mono PCM")
    prepare_parser.add_argument("--file", required=True, help="Input audio file")  # 输入 m4a/wav/mp3/pcm 等
    prepare_parser.add_argument("--output", default=None, help="Output PCM path")  # 不传则生成 <name>_xfyun.pcm

    group_parser = subparsers.add_parser(
        "create-group",
        parents=[credential_parser],
        help="Create a voiceprint feature group",
    )
    add_group_arg(group_parser)  # --group-id 默认 voice_test
    group_parser.add_argument("--group-name", default=None, help="Optional group name")  # 人类可读库名
    group_parser.add_argument("--group-info", default=None, help="Optional group description")  # 特征库备注

    enroll_parser = subparsers.add_parser(
        "enroll",
        parents=[credential_parser],
        help="Register an audio sample as a voiceprint feature",
    )
    add_group_arg(enroll_parser)  # 注册到哪个特征库
    enroll_parser.add_argument("--file", required=True, help="Input audio file; converted to PCM if needed")  # 注册音频
    enroll_parser.add_argument("--feature-id", required=True, help="Feature id, 1-32 letters/digits/underscores")  # 人员 ID
    enroll_parser.add_argument("--feature-info", default=None, help="Optional feature description")  # 注册备注
    enroll_parser.add_argument(
        "--keep-converted",
        action="store_true",  # 保留转换后的 PCM，便于排查和复用
        help="Keep converted <name>_xfyun.pcm next to source audio",
    )

    verify_parser = subparsers.add_parser(
        "verify",
        parents=[credential_parser],
        help="Compare an audio sample against an enrolled feature",
    )
    add_group_arg(verify_parser)  # 从哪个特征库里找目标人
    verify_parser.add_argument("--file", required=True, help="Input audio file; converted to PCM if needed")  # 待认证音频
    verify_parser.add_argument("--feature-id", required=True, help="Feature id to compare against")  # 和哪个已注册人比
    verify_parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,  # 默认 0.6，可以用 0.75/0.8 提高严格度
        help=f"Pass threshold (default: {DEFAULT_THRESHOLD})",
    )
    verify_parser.add_argument(
        "--keep-converted",
        action="store_true",  # 保留转换后的 PCM，便于排查和复用
        help="Keep converted <name>_xfyun.pcm next to source audio",
    )

    list_parser = subparsers.add_parser(
        "list",
        parents=[credential_parser],
        help="List voiceprint features in a group",
    )
    add_group_arg(list_parser)  # 查询指定特征库里的 featureId 列表

    return parser.parse_args()


def print_jsonish(title: str, data: object) -> None:
    """简单打印业务结果。"""
    print(f"=== {title} ===")
    print(data)


def main() -> int:
    """运行讯飞声纹工具。"""
    args = parse_args()
    try:
        if args.command == "prepare":
            output = prepare_audio(args.file, args.output)  # 只转音频，不请求讯飞
            print(f"Prepared: {output}")
            return 0

        creds = load_credentials(args)  # 读取讯飞 APPID/APIKey/APISecret
        if args.command == "create-group":
            result = create_group(creds, args.group_id, args.group_name, args.group_info)  # 创建特征库
            print_jsonish("XFYUN Create Group", result)
        elif args.command == "enroll":
            result = create_feature(
                creds,  # 讯飞凭据
                args.group_id,  # 特征库 ID
                args.feature_id,  # 注册成哪个人
                args.feature_info,  # 备注信息
                args.file,  # 注册音频路径
                keep_converted=args.keep_converted,  # 是否保留 PCM
            )  # 调 createFeature
            print_jsonish("XFYUN Enroll", result)
        elif args.command == "verify":
            result = compare_feature(
                creds,  # 讯飞凭据
                args.group_id,  # 特征库 ID
                args.feature_id,  # 目标已注册声纹
                args.file,  # 待认证音频路径
                keep_converted=args.keep_converted,  # 是否保留 PCM
            )  # 调 searchScoreFea 做 1:1 比对
            score = result.get("score") if isinstance(result, dict) else None  # 讯飞返回的相似度
            passed = score_passed(score, args.threshold)  # 按阈值转成 PASS/FAIL
            print("=== XFYUN Verify ===")
            print(f"FeatureId: {args.feature_id}")
            print(f"Score: {score}")
            print(f"Threshold: {args.threshold}")
            print(f"Decision: {'PASS' if passed else 'FAIL'}")
            print(f"Raw: {result}")
        elif args.command == "list":
            result = query_features(creds, args.group_id)  # 查询库内已注册 featureId
            print_jsonish("XFYUN Feature List", result)
        else:
            raise RuntimeError(f"Unknown command: {args.command}")
    except subprocess.CalledProcessError as exc:  # type: ignore[name-defined]
        print(f"ffmpeg failed with exit code {exc.returncode}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
