"""程序主流程。"""

from __future__ import annotations

import sys

from .cli import load_credentials, parse_args, validate_args
from .output import parse_speaker_labels, print_result
from .tasks import poll_task, submit_task


def main(force_speaker_diarization: bool = False) -> int:
    """运行命令行工具。"""
    args = parse_args()  # 读取命令行参数，例如 --file kkk.m4a
    if force_speaker_diarization and args.speaker_diarization is None:
        args.speaker_diarization = 1  # 专用入口默认开启说话人分离

    try:
        validate_args(args)  # 先检查参数组合是否合法，避免请求发出去后才失败
        speaker_labels = parse_speaker_labels(args.speaker_label)
        creds = load_credentials(args)  # 读取腾讯云 SecretId 和 SecretKey

        task_id = submit_task(args, creds)  # 创建语音识别任务，腾讯云返回 TaskId
        result = poll_task(task_id, args, creds)  # 用 TaskId 轮询任务状态，直到成功或失败
        print_result(result, speaker_labels)  # 打印最终识别文本和分段信息
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)  # 用户按 Ctrl+C 中断程序
        return 130  # Linux 里 130 通常表示被 Ctrl+C 中断
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(str(exc), file=sys.stderr)  # 把错误信息输出到 stderr，方便命令行查看
        return 1  # 返回非 0，表示程序执行失败

    return 0  # 返回 0，表示程序执行成功
