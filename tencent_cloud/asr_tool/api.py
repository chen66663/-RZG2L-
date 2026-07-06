"""HTTP 请求工具函数。"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from .auth import build_headers
from .common import (
    DEFAULT_TIMEOUT,
    ENDPOINT,
    Credentials,
    json_dumps,
)


def call_api(
    action: str,
    payload: dict[str, Any],
    region: str,
    creds: Credentials,
) -> dict[str, Any]:
    """发送一次腾讯云 JSON 请求，并返回 Response 字段。"""
    body = json_dumps(payload)  # 把请求参数 dict 转成 JSON 字符串
    timestamp = int(time.time())  # 当前秒级时间戳，签名和请求头都要用

    # 腾讯云接口使用 HTTPS + JSON；签名依赖 body 和 timestamp，所以先准备这两个值。
    request = urllib.request.Request(
        ENDPOINT,
        data=body.encode("utf-8"),  # HTTP body 必须是 bytes
        headers=build_headers(action, region, body, creds, timestamp),  # 生成签名请求头
        method="POST",  # 腾讯云 API 使用 POST
    )  # 构造 urllib 请求对象

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            raw_text = response.read().decode("utf-8")  # 腾讯云返回 UTF-8 JSON 字符串
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")  # HTTP 错误时，腾讯云也会返回 JSON 错误详情
        raise RuntimeError(f"HTTP {exc.code} calling {action}: {detail}") from exc  # 抛给 main() 统一打印
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error calling {action}: {exc}") from exc  # 网络/DNS/证书错误会走这里

    # 腾讯云返回格式一般是 {"Response": {...}}，真正数据在 Response 里面。
    try:
        data = json.loads(raw_text)  # JSON 字符串转 Python dict
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {action}: {raw_text}") from exc  # 防御异常响应

    response = data.get("Response")  # 取出腾讯云标准 Response 字段
    if not isinstance(response, dict):
        raise RuntimeError(f"Unexpected {action} response: missing Response object.")  # 没有 Response 说明格式不对

    error_info = response.get("Error")  # 腾讯云业务错误会放在 Response.Error
    if isinstance(error_info, dict):
        code = error_info.get("Code", "UnknownError")  # 错误码，例如 AuthFailure
        message = error_info.get("Message", "No error message returned.")  # 错误说明
        raise RuntimeError(f"{action} failed: {code}: {message}")  # 转成统一异常

    return response  # 成功时返回 Response dict
