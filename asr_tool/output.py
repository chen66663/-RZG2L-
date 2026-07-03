"""识别结果输出格式化。"""

from __future__ import annotations

from typing import Any


def print_result(data: dict[str, Any]) -> None:
    """打印完整识别文本和分段信息。"""
    transcript = str(data.get("Result", "")).rstrip()  # Result 是腾讯云返回的整段识别文本
    segments = data.get("ResultDetail") or []  # ResultDetail 是分句/分段详情

    print("\n=== Transcript ===")  # 完整文本标题
    print(transcript or "(empty)")  # 没有文本时显示 empty

    if not isinstance(segments, list) or not segments:
        return  # 没有分段详情就直接结束

    print("\n=== Segments ===")  # 分段详情标题
    for item in segments:
        if not isinstance(item, dict):
            continue  # 防御异常数据，跳过不是 dict 的分段
        speaker_id = item.get("SpeakerId", "?")  # 说话人编号
        start_ms = item.get("StartMs", "?")  # 这一句开始时间，单位毫秒
        end_ms = item.get("EndMs", "?")  # 这一句结束时间，单位毫秒
        sentence = item.get("FinalSentence", "")  # 这一句最终识别文本
        print(f"[{start_ms}-{end_ms}] speaker={speaker_id}: {sentence}")  # 打印一行分段结果
