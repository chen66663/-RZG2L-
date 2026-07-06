"""讯飞开放平台声纹识别 HTTP API 工具函数。"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.utils import formatdate
from pathlib import Path
from typing import Any


HOST = "api.xf-yun.com"  # 讯飞新版声纹 API 域名
PATH = "/v1/private/s1aa729d0"  # 当前开通的声纹服务路径
ENDPOINT = f"https://{HOST}{PATH}"  # 最终 HTTPS 请求地址
SERVICE = "s1aa729d0"  # 请求 parameter 里的服务名，必须和 PATH 对应
DEFAULT_GROUP_ID = "voice_test"  # 默认声纹特征库 ID
DEFAULT_THRESHOLD = 0.6  # 官方 FAQ 建议 0.6 以上可作为通过参考
DEFAULT_TIMEOUT = 60  # 每次 HTTP 请求最多等待 60 秒
MAX_BASE64_AUDIO = 4 * 1024 * 1024  # 讯飞 payload.resource.audio 的 base64 大小上限
ID_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,32}$")  # groupId/featureId 只允许字母数字下划线


@dataclass(frozen=True)
class XfyunCredentials:
    """讯飞开放平台鉴权信息。"""

    app_id: str
    api_key: str
    api_secret: str


def json_dumps(data: Any) -> str:
    """生成紧凑且稳定的 JSON 字符串。"""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def load_credentials(args: argparse.Namespace) -> XfyunCredentials:
    """从命令行、环境变量或 JSON 文件读取讯飞密钥。"""
    app_id = (getattr(args, "app_id", None) or os.getenv("XFYUN_APP_ID", "")).strip()  # 优先命令行，其次环境变量
    api_key = (getattr(args, "api_key", None) or os.getenv("XFYUN_API_KEY", "")).strip()  # APIKey 用于 authorization
    api_secret = (getattr(args, "api_secret", None) or os.getenv("XFYUN_API_SECRET", "")).strip()  # APISecret 用于 HMAC 签名

    credentials_path = Path(getattr(args, "credentials", None) or "xfyun_credentials.json")  # 默认读取本地凭据文件
    if credentials_path.is_file():
        with credentials_path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)  # 凭据文件只放本地，不能提交到 GitHub
        app_id = app_id or str(data.get("app_id", "")).strip()  # 命令行/环境变量为空时才用文件值
        api_key = api_key or str(data.get("api_key", "")).strip()  # 避免文件覆盖显式传入的值
        api_secret = api_secret or str(data.get("api_secret", "")).strip()  # 避免文件覆盖显式传入的值

    if not app_id or not api_key or not api_secret:
        raise RuntimeError(
            "Missing XFYUN credentials. Set XFYUN_APP_ID/XFYUN_API_KEY/"
            "XFYUN_API_SECRET, pass --app-id/--api-key/--api-secret, "
            "or create xfyun_credentials.json."
        )

    return XfyunCredentials(app_id=app_id, api_key=api_key, api_secret=api_secret)


def validate_id(name: str, value: str) -> None:
    """校验讯飞 groupId/featureId。"""
    if not ID_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must use 1-32 letters, digits or underscores.")


def build_auth_url(creds: XfyunCredentials) -> str:
    """按讯飞 HMAC-SHA256 规则生成鉴权 URL。"""
    date_text = formatdate(timeval=None, localtime=False, usegmt=True)  # HTTP GMT 时间，和服务端偏差不能超过 300 秒
    signature_origin = f"host: {HOST}\ndate: {date_text}\nPOST {PATH} HTTP/1.1"  # 讯飞要求参与签名的原始字符串
    signature_sha = hmac.new(
        creds.api_secret.encode("utf-8"),  # HMAC key 是 APISecret
        signature_origin.encode("utf-8"),  # HMAC message 是 host/date/request-line
        hashlib.sha256,
    ).digest()  # 得到二进制签名
    signature = base64.b64encode(signature_sha).decode("ascii")  # 讯飞要求签名再 base64
    authorization_origin = (
        f'api_key="{creds.api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )  # authorization 原文，字段顺序必须符合讯飞文档
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("ascii")  # URL 参数里放 base64 后的 authorization
    query = urllib.parse.urlencode(
        {
            "authorization": authorization,  # 鉴权信息
            "host": HOST,  # 参与签名的 host
            "date": date_text,  # 参与签名的 GMT 时间
        }
    )
    return f"{ENDPOINT}?{query}"  # 讯飞鉴权参数放在 query string 里


def decode_result_text(response: dict[str, Any], result_key: str) -> Any:
    """解码 payload.<result_key>.text 里的 base64 JSON。"""
    payload = response.get("payload")  # 讯飞业务结果放在 payload.<xxx>.text
    if not isinstance(payload, dict):
        return {}
    result = payload.get(result_key)  # result_key 例如 createFeatureRes/searchScoreFeaRes
    if not isinstance(result, dict):
        return {}
    text = result.get("text")  # text 是 base64 后的 JSON 字符串
    if not isinstance(text, str) or not text:
        return {}
    raw = base64.b64decode(text).decode("utf-8")  # 先 base64 解码，再按 UTF-8 解析 JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def call_xfyun(payload: dict[str, Any], result_key: str, creds: XfyunCredentials) -> Any:
    """调用一次讯飞声纹 HTTP API，并返回 text 解码后的业务结果。"""
    body = json_dumps(payload).encode("utf-8")  # 请求体必须和签名 URL 同一次生成
    request = urllib.request.Request(
        build_auth_url(creds),  # 带 authorization/date/host 的完整 URL
        data=body,  # HTTP body 是 JSON bytes
        headers={"Content-Type": "application/json"},  # 讯飞接口使用 JSON
        method="POST",  # 新版声纹接口固定 POST
    )

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            raw_text = response.read().decode("utf-8")  # 讯飞返回 UTF-8 JSON
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling XFYUN voiceprint: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error calling XFYUN voiceprint: {exc}") from exc

    try:
        data = json.loads(raw_text)  # 顶层响应包含 header 和 payload
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from XFYUN voiceprint: {raw_text}") from exc

    header = data.get("header")  # header.code 是接口级错误码
    if not isinstance(header, dict):
        raise RuntimeError(f"Unexpected XFYUN response: {raw_text}")
    code = int(header.get("code", -1))
    if code != 0:
        message = header.get("message", "No error message returned.")
        sid = header.get("sid", "")
        raise RuntimeError(f"XFYUN voiceprint failed: code={code}, sid={sid}, message={message}")

    result = decode_result_text(data, result_key)  # 业务结果需要从 payload.<result_key>.text 解码
    if isinstance(result, dict) and result.get("code") not in (None, 0, "0"):
        raise RuntimeError(f"XFYUN voiceprint business error: {result}")
    return result


def run_ffmpeg(input_path: Path, output_path: Path) -> None:
    """把任意输入音频转成讯飞新版声纹要求的 16k/16bit/单声道 PCM。"""
    ffmpeg_command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",  # 单声道
        "-ar",
        "16000",  # 16 kHz 采样率
        "-f",
        "s16le",  # 裸 PCM little-endian 格式
        "-acodec",
        "pcm_s16le",  # 16 bit PCM 编码
        str(output_path),
    ]
    try:
        subprocess.run(ffmpeg_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg is required to convert audio for XFYUN voiceprint. "
            "Install ffmpeg or pass an already converted 16 kHz mono PCM file."
        ) from exc


def prepare_audio(input_path: str, output_path: str | None = None) -> Path:
    """生成可上传给讯飞新版声纹接口的 PCM 文件。"""
    source = Path(input_path)  # 支持 m4a/wav/mp3/pcm 等本地文件路径
    if not source.is_file():
        raise FileNotFoundError(f"Audio file not found: {source}")

    if output_path:
        target = Path(output_path)  # 用户指定输出路径
    else:
        target = source.with_name(f"{source.stem}_xfyun.pcm")  # 默认生成同目录 <name>_xfyun.pcm
    target.parent.mkdir(parents=True, exist_ok=True)  # 输出目录不存在时自动创建
    run_ffmpeg(source, target)  # 调 ffmpeg 转成讯飞要求的 PCM
    return target


def read_audio_for_upload(input_path: str, keep_converted: bool = False) -> bytes:
    """读取音频；必要时先临时转换成 16k/16bit/单声道 PCM。"""
    source = Path(input_path)  # 输入可以是已转换 PCM，也可以是普通音频
    if not source.is_file():
        raise FileNotFoundError(f"Audio file not found: {source}")

    suffix = source.suffix.lower()  # 根据后缀判断是否需要转码
    if suffix in (".pcm", ".raw"):
        audio_bytes = source.read_bytes()  # 已经是裸 PCM，直接读取
    elif keep_converted:
        converted = prepare_audio(str(source))  # 保留转换后的 <name>_xfyun.pcm，方便下次复用
        audio_bytes = converted.read_bytes()  # 读取转换后的 PCM
    else:
        with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as tmp:
            converted_path = Path(tmp.name)  # 默认用临时 PCM，避免污染工作目录
        try:
            run_ffmpeg(source, converted_path)  # 临时转换成 16k/16bit/mono PCM
            audio_bytes = converted_path.read_bytes()  # 读取准备上传的 PCM bytes
        finally:
            converted_path.unlink(missing_ok=True)  # 不保留临时音频

    encoded_size = len(base64.b64encode(audio_bytes))  # 讯飞限制的是 base64 后的大小
    if encoded_size > MAX_BASE64_AUDIO:
        raise ValueError("Base64 audio is larger than 4 MB; use a shorter clip.")
    return audio_bytes


def result_format(key: str) -> dict[str, str]:
    """生成讯飞结果格式配置。"""
    return {
        key: {
            "encoding": "utf8",  # 返回文本按 UTF-8 编码
            "compress": "raw",  # 不压缩
            "format": "json",  # 返回 JSON
        }
    }


def base_payload(creds: XfyunCredentials, params: dict[str, Any]) -> dict[str, Any]:
    """生成无音频请求体。"""
    return {
        "header": {
            "app_id": creds.app_id,  # 讯飞 APPID
            "status": 3,  # 单次完整请求，固定传 3
        },
        "parameter": {
            SERVICE: params,  # s1aa729d0 服务参数
        },
    }


def audio_payload(creds: XfyunCredentials, params: dict[str, Any], audio_bytes: bytes) -> dict[str, Any]:
    """生成带音频请求体。"""
    payload = base_payload(creds, params)  # 先生成 header/parameter
    payload["payload"] = {
        "resource": {
            "encoding": "raw",  # 上传裸 PCM，不是 mp3/lame
            "sample_rate": 16000,  # 16 kHz
            "channels": 1,  # 单声道
            "bit_depth": 16,  # 16 bit
            "status": 3,  # 单包完整音频
            "audio": base64.b64encode(audio_bytes).decode("ascii"),  # PCM bytes 转 base64
        }
    }
    return payload


def create_group(creds: XfyunCredentials, group_id: str, group_name: str | None, group_info: str | None) -> Any:
    """创建声纹特征库。"""
    validate_id("--group-id", group_id)  # 先本地校验，避免请求到云端才失败
    params: dict[str, Any] = {
        "func": "createGroup",  # 创建声纹特征库
        "groupId": group_id,  # 特征库 ID
        **result_format("createGroupRes"),  # 告诉讯飞返回 createGroupRes
    }
    if group_name:
        params["groupName"] = group_name
    if group_info:
        params["groupInfo"] = group_info
    return call_xfyun(base_payload(creds, params), "createGroupRes", creds)  # 创建库不需要上传音频


def create_feature(
    creds: XfyunCredentials,
    group_id: str,
    feature_id: str,
    feature_info: str | None,
    audio_file: str,
    keep_converted: bool = False,
) -> Any:
    """添加音频特征。"""
    validate_id("--group-id", group_id)  # 特征库 ID
    validate_id("--feature-id", feature_id)  # 人员/声纹 ID
    info = feature_info or f"{feature_id}_{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"  # 默认备注带注册时间
    params = {
        "func": "createFeature",  # 注册声纹特征
        "groupId": group_id,  # 注册到哪个特征库
        "featureId": feature_id,  # 注册成哪个人
        "featureInfo": info,  # 备注信息，后面 list 会显示
        **result_format("createFeatureRes"),  # 告诉讯飞返回 createFeatureRes
    }
    audio_bytes = read_audio_for_upload(audio_file, keep_converted=keep_converted)  # 准备 16k/16bit/mono PCM
    return call_xfyun(audio_payload(creds, params, audio_bytes), "createFeatureRes", creds)  # 上传音频并注册


def compare_feature(
    creds: XfyunCredentials,
    group_id: str,
    feature_id: str,
    audio_file: str,
    keep_converted: bool = False,
) -> Any:
    """用输入音频和库中指定特征做 1:1 比对。"""
    validate_id("--group-id", group_id)  # 特征库 ID
    validate_id("--feature-id", feature_id)  # 目标已注册声纹 ID
    params = {
        "func": "searchScoreFea",  # 1:1 声纹比对
        "groupId": group_id,  # 从哪个特征库查
        "dstFeatureId": feature_id,  # 和哪个已注册人比
        **result_format("searchScoreFeaRes"),  # 告诉讯飞返回 searchScoreFeaRes
    }
    audio_bytes = read_audio_for_upload(audio_file, keep_converted=keep_converted)  # 准备待比对音频
    return call_xfyun(audio_payload(creds, params, audio_bytes), "searchScoreFeaRes", creds)  # 返回 score/age/gender 等结果


def query_features(creds: XfyunCredentials, group_id: str) -> Any:
    """查询特征列表。"""
    validate_id("--group-id", group_id)  # 特征库 ID
    params = {
        "func": "queryFeatureList",  # 查询库内已注册声纹
        "groupId": group_id,  # 要查询的特征库
        **result_format("queryFeatureListRes"),  # 告诉讯飞返回 queryFeatureListRes
    }
    return call_xfyun(base_payload(creds, params), "queryFeatureListRes", creds)  # 查询列表不需要上传音频


def score_passed(score: Any, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """根据相似度分数判断是否通过。"""
    try:
        return float(score) >= threshold  # score 大于等于阈值就判定通过
    except (TypeError, ValueError):
        return False
