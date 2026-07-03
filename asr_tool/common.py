"""公共常量和小工具函数。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


API_VERSION = "2019-06-14"  # 腾讯云语音识别接口版本，签名请求头里要用
SERVICE = "asr"  # 腾讯云服务名，TC3 签名计算时要用
HOST = "asr.tencentcloudapi.com"  # 腾讯云 ASR 官方接口域名
ENDPOINT = f"https://{HOST}/"  # 最终请求地址，所有接口都 POST 到这里
DEFAULT_REGION = "ap-shanghai"  # 默认地域，不传 --region 时使用上海
FILE_SIZE_LIMIT = 5 * 1024 * 1024  # 本地文件直传最大 5MB，超过要用 --url
DEFAULT_TIMEOUT = 60  # 每一次 HTTPS 请求最多等待 60 秒


@dataclass(frozen=True)
class Credentials:
    """腾讯云密钥对象。"""

    secret_id: str  # 腾讯云 SecretId
    secret_key: str  # 腾讯云 SecretKey
    token: str | None = None  # 临时密钥才需要 token，永久密钥一般为 None


def json_dumps(data: Any) -> str:
    """把 Python 对象转成稳定的 JSON 字符串。"""
    return json.dumps(
        data,
        ensure_ascii=False,  # 保留中文，不转成 \uXXXX
        separators=(",", ":"),  # 去掉多余空格，让请求体更紧凑
        sort_keys=True,  # 固定 key 顺序，签名时请求体更稳定
    )
