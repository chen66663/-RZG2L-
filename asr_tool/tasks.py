"""ASR 任务创建和轮询。"""

from __future__ import annotations

import argparse
import base64
import sys
import time
from pathlib import Path
from typing import Any

from .api import call_api
from .common import FILE_SIZE_LIMIT, Credentials


def read_audio_file(path_text: str) -> bytes:
    """读取并检查本地音频文件。"""
    audio_path = Path(path_text)  # 把字符串路径转成 Path 对象，方便判断和读取
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")  # 文件不存在就直接报错

    audio_bytes = audio_path.read_bytes()  # 读取整个音频文件，得到 bytes
    if len(audio_bytes) > FILE_SIZE_LIMIT:
        raise ValueError("Local audio file is larger than 5 MB; use --url instead.")  # 直传限制 5MB
    return audio_bytes  # 返回音频原始字节


def build_create_task_payload(args: argparse.Namespace) -> dict[str, Any]:
    """组装 CreateRecTask 接口请求参数。"""
    payload: dict[str, Any] = {
        "EngineModelType": args.engine_model,  # 识别模型，例如 16k_zh、8k_en
        "ChannelNum": args.channel_num,  # 声道数，普通录音一般是 1
        "ResTextFormat": args.res_text_format,  # 识别结果格式，2 表示带标点和分段
        "SourceType": 1 if args.file else 0,  # 1 表示本地文件上传，0 表示 URL
    }
    if args.speaker_diarization is not None:
        payload["SpeakerDiarization"] = args.speaker_diarization  # 是否开启说话人分离
    if args.speaker_number is not None:
        payload["SpeakerNumber"] = args.speaker_number  # 预期说话人数，部分模型才支持
    if args.callback_url:
        payload["CallbackUrl"] = args.callback_url  # 回调地址，本脚本通常不用

    if args.file:
        audio_bytes = read_audio_file(args.file)  # 读取本地音频文件
        payload["Data"] = base64.b64encode(audio_bytes).decode("ascii")  # 音频 bytes 转 base64 字符串
        payload["DataLen"] = len(audio_bytes)  # 原始音频字节数，腾讯云接口要求传
    else:
        payload["Url"] = args.url  # 公网音频 URL，腾讯云服务器会自己下载

    return payload  # 返回给 submit_task() 发送请求


def submit_task(args: argparse.Namespace, creds: Credentials) -> int:
    """创建一个 ASR 任务，并返回 TaskId。"""
    payload = build_create_task_payload(args)  # 先组装 CreateRecTask 请求参数
    response = call_api(
        "CreateRecTask",  # 腾讯云创建识别任务的接口名
        payload,  # 请求参数
        args.region,  # 地域
        creds,  # 腾讯云密钥
    )  # 发送 HTTPS 请求
    data = response.get("Data")  # 成功响应里的 Data 字段包含 TaskId
    if not isinstance(data, dict) or "TaskId" not in data:
        raise RuntimeError("CreateRecTask succeeded but TaskId is missing.")  # 防御异常返回

    task_id = int(data["TaskId"])  # TaskId 是后面查询任务状态的唯一编号
    print(f"TaskId: {task_id}")  # 打印出来，方便人工记录
    return task_id  # 返回给 poll_task()


def poll_task(task_id: int, args: argparse.Namespace, creds: Credentials) -> dict[str, Any]:
    """轮询 DescribeTaskStatus，直到任务完成。"""
    deadline = time.time() + args.timeout  # 计算超时时刻，超过就不再等
    delay = args.poll_interval  # 当前轮询间隔，初始值来自 --poll-interval

    while True:
        response = call_api(
            "DescribeTaskStatus",  # 腾讯云查询任务状态的接口名
            {"TaskId": task_id},  # 查询时只需要传 TaskId
            args.region,  # 地域要和创建任务时一致
            creds,  # 腾讯云密钥
        )  # 发送一次查询请求
        data = response.get("Data")  # 查询结果在 Data 字段里
        if not isinstance(data, dict):
            raise RuntimeError("DescribeTaskStatus returned no Data object.")  # 防御异常返回

        status = int(data.get("Status", -1))  # 0=等待，1=处理中，2=成功，3=失败
        status_text = str(data.get("StatusStr", ""))  # 腾讯云返回的状态文字
        print(f"status={status} ({status_text})", file=sys.stderr)  # 进度打印到 stderr，不影响最终文本

        if status == 2:
            return data  # 识别成功，返回完整结果
        if status == 3:
            error_message = data.get("ErrorMsg", "Unknown task failure.")  # 失败原因
            raise RuntimeError(f"Task failed: {error_message}")  # 抛给 main() 打印
        if time.time() >= deadline:
            raise TimeoutError(f"Timed out waiting for task {task_id}")  # 等太久就退出

        time.sleep(delay)  # 任务还没完成，等一会再查
        delay = min(delay * 1.5, args.max_poll_interval)  # 逐步拉长间隔，但不超过最大值
