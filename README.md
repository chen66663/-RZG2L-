# RZ/G2L Voice API Demos

这个仓库故意分成两套互相独立的代码，避免把腾讯云和科大讯飞混在同一套实现里。

## 两套代码

```text
.
├── tencent_cloud/      # 腾讯云 ASR / 腾讯云声纹代码
└── xfyun_voiceprint/   # 科大讯飞声纹识别代码
```

## 腾讯云代码

目录：`tencent_cloud/`

包含：

- 腾讯云录音文件识别 ASR：`tencent_cloud/asr_test.py`
- 腾讯云说话人分离入口：`tencent_cloud/asr_speakers.py`
- 腾讯云声纹注册/认证：`tencent_cloud/voiceprint_tool.py`

查看说明：

```bash
cat tencent_cloud/README.md
```

## 科大讯飞代码

目录：`xfyun_voiceprint/`

包含：

- 科大讯飞新版声纹 API：`s1aa729d0`
- 声纹特征库创建
- 声纹注册
- 1:1 声纹比对
- 特征列表查询

查看说明：

```bash
cat xfyun_voiceprint/README.md
```

从仓库根目录直接运行科大讯飞声纹工具：

```bash
python3 xfyun_voiceprint/xfyun_voiceprint_tool.py --help
```

## 安全说明

不要提交真实密钥和音频样本。`.gitignore` 已排除：

- `asr_credentials.json`
- `xfyun_credentials.json`
- `private/`
- `audio/`
- `generated/`
- 常见音频文件和 Python 缓存
