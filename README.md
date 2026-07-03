# RZ/G2L Tencent Cloud ASR Demo

这是一个面向 RZ/G2L / 瑞米派开发板的腾讯云语音识别测试项目。

项目当前提交的是 Python 版本，适合快速测试、学习接口流程，入口是 `asr_test.py`。

## 功能

- 支持腾讯云录音文件识别接口。
- 支持本地音频文件上传，Python 版本也支持公网 URL。
- 支持查询任务状态，直到识别完成。
- 支持输出完整识别文本和分段结果。
- Python 代码中保留了中文注释，方便新手按流程阅读。

## 目录

```text
.
├── asr_test.py                 # Python 命令行入口
├── asr_tool/                   # Python 功能模块
│   ├── app.py                  # 主流程
│   ├── cli.py                  # 参数解析和密钥读取
│   ├── auth.py                 # 腾讯云 TC3 签名
│   ├── api.py                  # HTTPS 请求
│   ├── tasks.py                # 创建任务和轮询状态
│   ├── output.py               # 识别结果输出
│   └── common.py               # 公共常量和工具
├── asr_credentials.example.json # 密钥配置示例
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

## 开发板注意事项

开发板系统时间必须正确。腾讯云 HTTPS 证书校验和 TC3 签名都依赖时间。

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
- 编译产物
- Python 缓存
- 本地音频文件
- 本地调试记录

公开仓库里只保留 `asr_credentials.example.json` 作为配置模板。
