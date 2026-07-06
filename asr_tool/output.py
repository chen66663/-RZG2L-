"""识别结果输出格式化。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def parse_speaker_labels(items: list[str]) -> dict[str, str]:
    """解析命令行传入的 speaker 标签映射。"""
    labels: dict[str, str] = {}
    for item in items:
        speaker_id, name = item.split("=", 1)
        labels[speaker_id.strip()] = name.strip()
    return labels


def speaker_name(speaker_id: Any, labels: dict[str, str]) -> str:
    """把腾讯云 speaker id 转成更容易读的显示名称。"""
    key = str(speaker_id)
    if key in labels:
        return f"{labels[key]}(speaker={key})"
    return f"speaker={key}"


def format_ms(value: Any) -> str:
    """把毫秒时间戳格式化成 mm:ss.mmm。"""
    try:
        millis = int(value)
    except (TypeError, ValueError):
        return str(value)

    minutes, remainder = divmod(millis, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def get_speaker_id(item: dict[str, Any]) -> Any:
    """兼容不同字段大小写的 speaker id。"""
    return item.get("SpeakerId", item.get("speakerId", item.get("speaker_id", "?")))


def get_sentence(item: dict[str, Any]) -> str:
    """兼容腾讯云不同结果格式里的句子字段。"""
    return str(
        item.get(
            "FinalSentence",
            item.get("Sentence", item.get("sentence", "")),
        )
    ).strip()


def print_result(data: dict[str, Any], labels: dict[str, str] | None = None) -> None:
    """打印完整识别文本和分段信息。"""
    speaker_labels = labels or {}
    transcript = str(data.get("Result", "")).rstrip()  # Result 是腾讯云返回的整段识别文本
    segments = data.get("ResultDetail") or []  # ResultDetail 是分句/分段详情

    print("\n=== Transcript ===")  # 完整文本标题
    print(transcript or "(empty)")  # 没有文本时显示 empty

    if not isinstance(segments, list) or not segments:
        return  # 没有分段详情就直接结束

    by_speaker: dict[str, list[str]] = defaultdict(list)

    print("\n=== Speaker Timeline ===")  # 按时间顺序展示谁在什么时候说了什么
    for item in segments:
        if not isinstance(item, dict):
            continue  # 防御异常数据，跳过不是 dict 的分段
        speaker_id = get_speaker_id(item)  # 说话人编号
        start_ms = item.get("StartMs", "?")  # 这一句开始时间，单位毫秒
        end_ms = item.get("EndMs", "?")  # 这一句结束时间，单位毫秒
        sentence = get_sentence(item)  # 这一句最终识别文本
        display_name = speaker_name(speaker_id, speaker_labels)
        print(f"[{format_ms(start_ms)}-{format_ms(end_ms)}] {display_name}: {sentence}")  # 打印一行分段结果
        if sentence:
            by_speaker[str(speaker_id)].append(sentence)

    if not by_speaker:
        return

    print("\n=== By Speaker ===")  # 按说话人聚合，方便看每个人总共说了什么
    for speaker_id in sorted(by_speaker):
        display_name = speaker_name(speaker_id, speaker_labels)
        print(f"{display_name}:")
        for sentence in by_speaker[speaker_id]:
            print(f"  {sentence}")
