# iFLYTEK Voiceprint Scripts

这个目录只放科大讯飞声纹识别代码，不依赖腾讯云代码。

当前使用的是科大讯飞开放平台新版声纹 API：

```text
/v1/private/s1aa729d0
```

## 功能

- `create-group`：创建声纹特征库。
- `enroll`：注册某个人的声纹。
- `verify`：把新音频和已注册声纹做 1:1 比对。
- `list`：查询特征库里的声纹列表。
- `prepare`：把音频转成 16 kHz / 16 bit / 单声道 PCM。

## 目录

```text
xfyun_voiceprint/
├── xfyun_voiceprint_tool.py
├── xfyun_voiceprint.py
├── xfyun_credentials.example.json
└── README.md
```

## 密钥

真实密钥不要提交到 GitHub。推荐放在仓库根目录的 `private/xfyun_credentials.json`：

```json
{
  "app_id": "your_app_id",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret"
}
```

也可以用环境变量：

```bash
export XFYUN_APP_ID="your_app_id"
export XFYUN_API_KEY="your_api_key"
export XFYUN_API_SECRET="your_api_secret"
```

## 从仓库根目录运行

创建特征库：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json create-group --group-id voice_test --group-name voice_test
```

注册 `kkk`：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json enroll --group-id voice_test --feature-id kkk --file audio/kkk.m4a --keep-converted
```

验证 `kkkk.m4a` 是否是 `kkk`：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json verify --group-id voice_test --feature-id kkk --file audio/kkkk.m4a --threshold 0.75
```

查询已注册声纹：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json list --group-id voice_test
```

## 结果判断

`verify` 输出里的 `Score` 是声纹相似度。默认阈值是 `0.6`，可以用 `--threshold 0.75` 或更高值提高严格度。

```text
Score: 0.75
Threshold: 0.75
Decision: PASS
```

讯飞返回里可能附带 `age`、`gender`，它们只能辅助显示；身份认证主要看 `Score`。

## 时间要求

讯飞 HMAC 鉴权依赖请求里的 GMT 时间。官方要求请求 `date` 和服务端时间偏差不能超过 300 秒。开发板如果没有 RTC，重启后要先等 NTP 同步。
