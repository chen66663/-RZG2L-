# iFLYTEK Voiceprint Scripts

这个目录是一套独立的科大讯飞声纹识别代码，只使用科大讯飞接口，不依赖 `tencent_cloud/`。

当前使用科大讯飞开放平台新版声纹 API：

```text
https://api.xf-yun.com/v1/private/s1aa729d0
```

## 能做什么

- `prepare`：把音频转成 16 kHz / 16 bit / 单声道裸 PCM。
- `create-group`：创建声纹特征库。
- `enroll`：把一段音频注册成某个人的声纹。
- `verify`：把新音频和已注册声纹做 1:1 比对。
- `list`：查看特征库里已经注册的声纹。

## 文件结构

```text
xfyun_voiceprint/
├── README.md
├── xfyun_credentials.example.json
├── xfyun_voiceprint.py
└── xfyun_voiceprint_tool.py
```

核心文件：

- `xfyun_voiceprint_tool.py`：命令行入口。
- `xfyun_voiceprint.py`：讯飞 HMAC 鉴权、请求体组装、音频转换、注册和比对逻辑。

## 准备密钥

推荐把真实密钥放在仓库根目录的 `private/xfyun_credentials.json`：

```bash
mkdir -p private
cp xfyun_voiceprint/xfyun_credentials.example.json private/xfyun_credentials.json
chmod 600 private/xfyun_credentials.json
```

编辑 `private/xfyun_credentials.json`：

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

## 准备音频

推荐把测试音频放在仓库根目录的 `audio/`：

```bash
mkdir -p audio generated
```

示例：

```text
audio/kkk.m4a
audio/kkkk.m4a
```

可以先手动转换成讯飞要求的 PCM：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py prepare --file audio/kkk.m4a --output generated/kkk_xfyun.pcm
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py prepare --file audio/kkkk.m4a --output generated/kkkk_xfyun.pcm
```

不手动转换也可以，`enroll` 和 `verify` 会自动调用 `ffmpeg` 临时转换。

## 基本流程

创建特征库：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json create-group --group-id voice_test --group-name voice_test
```

注册 `kkk`：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json enroll --group-id voice_test --feature-id kkk --file audio/kkk.m4a --keep-converted
```

把 `kkkk.m4a` 和已注册的 `kkk` 比对：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json verify --group-id voice_test --feature-id kkk --file audio/kkkk.m4a --threshold 0.75
```

查询已注册声纹：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json list --group-id voice_test
```

## 结果怎么看

示例输出：

```text
=== XFYUN Verify ===
FeatureId: kkk
Score: 0.75
Threshold: 0.75
Decision: PASS
Raw: {'age': 'youth', 'gender': 'female', 'featureId': 'kkk', 'score': 0.75}
```

字段含义：

- `Score`：声纹相似度。
- `Threshold`：当前判定阈值。
- `Decision`：`PASS` 表示 `Score >= Threshold`。
- `age`、`gender`：讯飞返回的附带年龄段和性别信息，只能辅助显示。

默认阈值是 `0.6`。如果要更严格，可以使用：

```bash
--threshold 0.75
--threshold 0.8
```

## 常见问题

如果提示缺少 `ffmpeg`：

```text
ffmpeg is required to convert audio for XFYUN voiceprint
```

需要先安装 `ffmpeg`，或者提前传入已经转换好的 16 kHz / 16 bit / 单声道 PCM 文件。

如果提示鉴权失败，先检查：

- `private/xfyun_credentials.json` 是否存在。
- `app_id`、`api_key`、`api_secret` 是否填对。
- 开发板时间是否已经 NTP 同步。

科大讯飞 HMAC 鉴权依赖请求里的 GMT 时间，官方要求请求 `date` 和服务端时间偏差不能超过 300 秒。开发板如果没有 RTC，重启后要先等 NTP 同步。
