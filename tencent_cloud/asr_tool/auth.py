"""腾讯云 TC3 签名工具函数。"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac

from .common import API_VERSION, HOST, SERVICE, Credentials


def sha256_hex(data: bytes) -> str:
    """计算 SHA256，并返回十六进制字符串。"""
    return hashlib.sha256(data).hexdigest()  # 腾讯云签名需要请求体和规范请求的 SHA256


def hmac_sha256(key: bytes, message: str) -> bytes:
    """计算 HMAC-SHA256，并返回原始 bytes。"""
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()  # 用上一步密钥继续派生


def build_authorization_header(
    secret_id: str,
    secret_key: str,
    timestamp: int,
    body: str,
) -> str:
    """生成 Authorization 请求头。"""
    date = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).strftime("%Y-%m-%d")  # 签名日期必须用 UTC
    canonical_headers = (
        "content-type:application/json; charset=utf-8\n"
        f"host:{HOST}\n"
    )  # 参与签名的请求头，格式必须严格匹配腾讯云规则
    signed_headers = "content-type;host"  # 告诉腾讯云哪些请求头参与了签名
    payload_hash = sha256_hex(body.encode("utf-8"))  # 先对 JSON 请求体做 SHA256
    canonical_request = "\n".join(
        [
            "POST",  # 请求方法
            "/",  # 请求路径
            "",  # 查询字符串为空
            canonical_headers,  # 规范化请求头
            signed_headers,  # 已签名请求头列表
            payload_hash,  # 请求体哈希
        ]
    )  # 腾讯云称这个字符串为 CanonicalRequest
    credential_scope = f"{date}/{SERVICE}/tc3_request"  # 签名作用范围：日期/服务/tc3_request
    string_to_sign = "\n".join(
        [
            "TC3-HMAC-SHA256",  # 签名算法名称
            str(timestamp),  # 秒级时间戳，必须和请求头 X-TC-Timestamp 一致
            credential_scope,  # 上面生成的作用范围
            sha256_hex(canonical_request.encode("utf-8")),  # CanonicalRequest 的哈希
        ]
    )  # 腾讯云称这个字符串为 StringToSign

    secret_date = hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)  # 第一步：用日期派生密钥
    secret_service = hmac_sha256(secret_date, SERVICE)  # 第二步：用服务名 asr 派生密钥
    secret_signing = hmac_sha256(secret_service, "tc3_request")  # 第三步：得到最终签名密钥
    signature = hmac.new(
        secret_signing,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()  # 对 StringToSign 做 HMAC，得到最终签名

    return (
        "TC3-HMAC-SHA256 "
        f"Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )  # 这整段字符串会放入 HTTP Authorization 请求头


def build_headers(
    action: str,
    region: str,
    body: str,
    creds: Credentials,
    timestamp: int,
) -> dict[str, str]:
    """生成腾讯云接口需要的 HTTP 请求头。"""
    headers = {
        "Authorization": build_authorization_header(
            creds.secret_id,
            creds.secret_key,
            timestamp,
            body,
        ),  # 签名结果，腾讯云用它验证请求是不是你发的
        "Content-Type": "application/json; charset=utf-8",  # 请求体是 JSON
        "X-TC-Action": action,  # 接口动作名，例如 CreateRecTask
        "X-TC-Version": API_VERSION,  # 接口版本
        "X-TC-Timestamp": str(timestamp),  # 签名时间戳
    }
    if region:
        headers["X-TC-Region"] = region  # 地域，例如 ap-shanghai
    if creds.token:
        headers["X-TC-Token"] = creds.token  # 临时密钥必须带 token
    return headers  # 返回给 urllib.request.Request 使用
