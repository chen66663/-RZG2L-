# RZ/G2L Voice ASR + iFLYTEK Voiceprint Demo

这是一个面向 RZ/G2L / 瑞米派开发板的语音识别和声纹认证测试项目。

项目当前提交的是 Python 版本，适合快速测试、学习接口流程：

- 语音转文字 ASR：使用腾讯云录音文件识别，入口是 `asr_test.py`。
- 多人说话分离：使用腾讯云 ASR 说话人分离，入口是 `asr_speakers.py`。
- 声纹身份认证：当前主用科大讯飞开放平台新版声纹 API，入口是 `xfyun_voiceprint_tool.py`。
- 腾讯云声纹工具 `voiceprint_tool.py` 仅保留为历史/备用方案。

## 功能

- 支持腾讯云录音文件识别接口。
- 支持本地音频文件上传，Python 版本也支持公网 URL。
- 支持查询任务状态，直到识别完成。
- 支持输出完整识别文本和分段结果。
- 支持科大讯飞声纹特征库创建、声纹注册、1:1 声纹比对、特征列表查询。
- Python 代码中保留了中文注释，方便新手按流程阅读。

## 目录

```text
.
├── asr_test.py                 # Python 命令行入口
├── asr_speakers.py             # 默认开启多人说话分离的 ASR 入口
├── xfyun_voiceprint_tool.py    # 当前推荐使用的科大讯飞声纹命令行入口
├── voiceprint_tool.py          # 腾讯云声纹旧/备用入口
├── asr_tool/                   # Python 功能模块
│   ├── app.py                  # 主流程
│   ├── cli.py                  # 参数解析和密钥读取
│   ├── auth.py                 # 腾讯云 TC3 签名
│   ├── api.py                  # HTTPS 请求
│   ├── tasks.py                # 创建任务和轮询状态
│   ├── output.py               # 识别结果输出
│   ├── voiceprint.py           # 腾讯云声纹旧/备用工具函数
│   ├── xfyun_voiceprint.py     # 科大讯飞声纹 HTTP API 工具函数
│   └── common.py               # 公共常量和工具
├── asr_credentials.example.json # 密钥配置示例
├── xfyun_credentials.example.json # 科大讯飞密钥配置示例
├── README_ASR_TEST.md          # Python 版本详细说明
└── ASR_FLOWCHART.md            # 中文流程图
```

## Python 版本使用

开发板上需要有 Python 3。当前代码已经兼容 Python 3.8。

先创建密钥文件：

```bash
cp asr_credentials.example.json asr_credentials.json
```

编辑 `asr_credentials.json`：

```json
{
  "secret_id": "your_secret_id",
  "secret_key": "your_secret_key",
  "token": ""
}
```

识别本地音频：

```bash
python3 asr_test.py --file kkk.m4a --engine-model 16k_zh
```

识别公网音频：

```bash
python3 asr_test.py --url "https://example.com/audio.m4a" --engine-model 16k_zh
```

## 多人说话识别

如果录音里有多个人说话，优先使用专用入口：

```bash
python3 asr_speakers.py --file kkk.m4a --engine-model 16k_zh
```

它默认开启腾讯云说话人分离，输出会包含：

- `Speaker Timeline`：按时间顺序显示每一句属于哪个 `speaker`。
- `By Speaker`：按 `speaker` 汇总每个人说过的话。

如果你已经知道 `speaker=0`、`speaker=1` 分别是谁，可以手动加标签：

```bash
python3 asr_speakers.py --file kkk.m4a --speaker-label 0=zhangsan --speaker-label 1=lisi
```

注意：说话人分离只能区分“不同声音”，不能自动知道这个人真实是谁。要自动识别身份，需要额外接声纹识别 API。

腾讯云录音文件识别还提供“角色分离”增值能力。如果你有某个人的纯净参考音频公网 URL，可以尝试：

```bash
python3 asr_speakers.py \
  --url "https://example.com/meeting.wav" \
  --engine-model 16k_zh_en \
  --speaker-diarization 3 \
  --speaker-role zhangsan=https://example.com/zhangsan_ref.wav
```

这个模式要求 `16k_zh_en` 引擎，且参考音频需要是公网可访问 URL；当前腾讯云文档说明仅支持传入一组角色声纹信息。

## 科大讯飞声纹识别（当前主用）

当前声纹身份认证主用科大讯飞开放平台新版声纹 API，服务标识是 `s1aa729d0`，脚本入口是：

```bash
python3 xfyun_voiceprint_tool.py --help
```

密钥可以放在 `xfyun_credentials.json`，格式参考 `xfyun_credentials.example.json`：

```json
{
  "app_id": "your_app_id",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret"
}
```

推荐流程：

```bash
python3 xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json create-group --group-id voice_test --group-name voice_test
python3 xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json enroll --group-id voice_test --feature-id kkk --file audio/kkk.m4a --keep-converted
python3 xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json verify --group-id voice_test --feature-id kkk --file audio/kkkk.m4a --threshold 0.75
python3 xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json list --group-id voice_test
```

`verify` 输出里的 `Score` 是相似度，默认阈值是 `0.6`；可以用 `--threshold 0.75` 提高通过要求。`Decision: PASS` 表示按当前阈值判断为同一个人。讯飞返回里可能附带 `age`、`gender`，它们只能辅助显示，身份认证主要看 `Score`。

如果返回：

```text
does not have authorization for func: createGroup
```

说明当前讯飞应用还没有开通这个声纹特征库接口权限。新版接口对应 `s1aa729d0` 服务，需要具备 `createGroup`、`createFeature`、`searchScoreFea` 这几个能力。

## 腾讯云声纹旧/备用工具

`voiceprint_tool.py` 调用腾讯云 `VoicePrintEnroll` 和 `VoicePrintVerify`。当前项目已经改为主用科大讯飞声纹接口；这个工具保留用于腾讯云声纹额度可用时的对照测试。

注册说话人：

```bash
python3 voiceprint_tool.py enroll --file zhangsan.wav --speaker-nick zhangsan
```

认证新音频：

```bash
python3 voiceprint_tool.py verify --voice-print-id vp_xxx --file test.wav
```

## 开发板注意事项

开发板系统时间必须正确。腾讯云 HTTPS 证书校验、腾讯云 TC3 签名、科大讯飞 HMAC 鉴权都依赖时间。讯飞官方接口要求请求 `date` 和服务端时间偏差不能超过 300 秒。

如果时间错误，可能出现：

```text
certificate verify failed: certificate is not yet valid
```

可以先临时校时：

```bash
date -s '2026-07-03 10:00:00 CST'
```

长期使用建议配置 NTP 或开机自动校时。

## 安全说明

不要提交真实密钥文件。

本项目已经通过 `.gitignore` 排除了：

- `asr_credentials.json`
- `xfyun_credentials.json`
- `private/`
- 编译产物
- Python 缓存
- 本地音频文件
- 本地调试记录

公开仓库里只保留 `asr_credentials.example.json` 和 `xfyun_credentials.example.json` 作为配置模板。
