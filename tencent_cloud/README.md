# Tencent Cloud Voice Scripts

这个目录是一套独立的腾讯云代码，只使用腾讯云接口，不依赖 `xfyun_voiceprint/`。

## 能做什么

- `asr_test.py`：调用腾讯云录音文件识别，把音频转成文字。
- `asr_speakers.py`：调用腾讯云 ASR 说话人分离，默认开启 `SpeakerDiarization=1`。
- `voiceprint_tool.py`：调用腾讯云声纹注册和 1:1 声纹认证。
- `asr_tool/`：腾讯云签名、HTTP 请求、任务轮询、结果输出等公共代码。

## 文件结构

```text
tencent_cloud/
├── README.md
├── ASR_FLOWCHART.md
├── asr_credentials.example.json
├── asr_test.py
├── asr_speakers.py
├── voiceprint_tool.py
└── asr_tool/
    ├── __init__.py
    ├── api.py
    ├── app.py
    ├── auth.py
    ├── cli.py
    ├── common.py
    ├── output.py
    ├── tasks.py
    └── voiceprint.py
```

## 准备密钥

推荐从仓库根目录运行命令，所以密钥也放仓库根目录：

```bash
cp tencent_cloud/asr_credentials.example.json asr_credentials.json
```

编辑 `asr_credentials.json`：

```json
{
  "secret_id": "your_secret_id",
  "secret_key": "your_secret_key",
  "token": ""
}
```

如果你把密钥放在其他位置，命令里要显式指定：

```bash
python3 tencent_cloud/asr_test.py --credentials /path/to/asr_credentials.json --file kkk.m4a
```

也可以用环境变量：

```bash
export TENCENTCLOUD_SECRET_ID="your_secret_id"
export TENCENTCLOUD_SECRET_KEY="your_secret_key"
export TENCENTCLOUD_REGION="ap-shanghai"
```

## ASR 转文字

本地文件：

```bash
python3 tencent_cloud/asr_test.py --file kkk.m4a --engine-model 16k_zh
```

公网 URL：

```bash
python3 tencent_cloud/asr_test.py --url "https://example.com/audio.wav" --engine-model 16k_zh
```

常用参数：

```bash
--engine-model 16k_zh
--channel-num 1
--res-text-format 2
--timeout 1800
```

## 多人说话分离

直接使用专用入口：

```bash
python3 tencent_cloud/asr_speakers.py --file kkk.m4a --engine-model 16k_zh
```

输出会包含：

- `Transcript`：完整识别文本。
- `Speaker Timeline`：按时间顺序显示每句话属于哪个 speaker。
- `By Speaker`：按 speaker 汇总每个人说的话。

如果你知道 speaker 编号对应谁，可以加标签：

```bash
python3 tencent_cloud/asr_speakers.py --file kkk.m4a --speaker-label 0=zhangsan --speaker-label 1=lisi
```

腾讯云角色分离示例：

```bash
python3 tencent_cloud/asr_speakers.py \
  --url "https://example.com/meeting.wav" \
  --engine-model 16k_zh_en \
  --speaker-diarization 3 \
  --speaker-role zhangsan=https://example.com/zhangsan_ref.wav
```

## 腾讯云声纹

注册一个说话人：

```bash
python3 tencent_cloud/voiceprint_tool.py enroll --file zhangsan.wav --speaker-nick zhangsan
```

注册成功后会输出 `VoicePrintId`，认证时要使用这个 ID：

```bash
python3 tencent_cloud/voiceprint_tool.py verify --voice-print-id vp_xxx --file test.wav
```

PCM 文件需要指定格式：

```bash
python3 tencent_cloud/voiceprint_tool.py enroll --file zhangsan.pcm --voice-format 0 --speaker-nick zhangsan
```

## 常见问题

- 本地 ASR 文件直传限制是 5 MB，超过后用 `--url`。
- 腾讯云声纹本地文件限制是 2 MB，建议 16 kHz、16 bit、单声道 PCM/WAV。
- 开发板系统时间必须正确，否则 HTTPS 证书校验和 TC3 签名可能失败。
- 如果开发板没有 RTC，重启后先等 NTP 同步再调用接口。
