# Tencent Cloud Voice Scripts

这个目录只放腾讯云相关代码，不依赖科大讯飞代码。

## 功能

- `asr_test.py`：腾讯云录音文件识别，把音频转成文字。
- `asr_speakers.py`：腾讯云 ASR 说话人分离入口，默认开启 `SpeakerDiarization=1`。
- `voiceprint_tool.py`：腾讯云声纹注册和 1:1 认证工具。
- `asr_tool/`：腾讯云 ASR 和腾讯云声纹的公共模块。

## 目录

```text
tencent_cloud/
├── asr_test.py
├── asr_speakers.py
├── voiceprint_tool.py
├── asr_credentials.example.json
├── ASR_FLOWCHART.md
└── asr_tool/
    ├── api.py
    ├── app.py
    ├── auth.py
    ├── cli.py
    ├── common.py
    ├── output.py
    ├── tasks.py
    └── voiceprint.py
```

## 密钥

可以在仓库根目录或 `tencent_cloud/` 目录放 `asr_credentials.json`：

```json
{
  "secret_id": "your_secret_id",
  "secret_key": "your_secret_key",
  "token": ""
}
```

也可以用环境变量：

```bash
export TENCENTCLOUD_SECRET_ID="your_secret_id"
export TENCENTCLOUD_SECRET_KEY="your_secret_key"
export TENCENTCLOUD_REGION="ap-shanghai"
```

## ASR 转写

从仓库根目录运行：

```bash
python3 tencent_cloud/asr_test.py --file kkk.m4a --engine-model 16k_zh
```

公网 URL：

```bash
python3 tencent_cloud/asr_test.py --url "https://example.com/audio.wav" --engine-model 16k_zh
```

## 多人说话分离

```bash
python3 tencent_cloud/asr_speakers.py --file kkk.m4a --engine-model 16k_zh
```

手动给 speaker 编号加名字：

```bash
python3 tencent_cloud/asr_speakers.py --file kkk.m4a --speaker-label 0=zhangsan --speaker-label 1=lisi
```

## 腾讯云声纹

注册说话人：

```bash
python3 tencent_cloud/voiceprint_tool.py enroll --file zhangsan.wav --speaker-nick zhangsan
```

认证新音频：

```bash
python3 tencent_cloud/voiceprint_tool.py verify --voice-print-id vp_xxx --file test.wav
```

## 注意

腾讯云 HTTPS 证书校验和 TC3 签名依赖系统时间。开发板如果没有 RTC，重启后要先等 NTP 同步。
