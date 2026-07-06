# Tencent Cloud ASR and iFLYTEK voiceprint test scripts

## What it does

`asr_test.py` submits a local audio file or public URL to Tencent Cloud ASR
recording recognition, then polls until the result is ready.

Voiceprint speaker verification is currently handled by iFLYTEK Open Platform
through `xfyun_voiceprint_tool.py`. The Tencent Cloud voiceprint helper is kept
only as a legacy/fallback tool.

## Project layout

- `asr_test.py`: command-line entry
- `asr_speakers.py`: ASR entry with speaker diarization enabled by default
- `xfyun_voiceprint_tool.py`: current voiceprint enrollment/verification entry
- `voiceprint_tool.py`: legacy/fallback Tencent Cloud voiceprint entry
- `asr_tool/app.py`: top-level flow
- `asr_tool/cli.py`: argument parsing and credential loading
- `asr_tool/auth.py`: TC3 signing
- `asr_tool/api.py`: HTTP request handling
- `asr_tool/tasks.py`: task creation and polling
- `asr_tool/output.py`: transcript printing
- `asr_tool/xfyun_voiceprint.py`: iFLYTEK voiceprint HTTP API helper
- `asr_tool/voiceprint.py`: legacy/fallback Tencent Cloud voiceprint helper
- `asr_tool/common.py`: shared constants and JSON helpers

## Setup

Set credentials in the shell:

```bash
export TENCENTCLOUD_SECRET_ID="your_secret_id"
export TENCENTCLOUD_SECRET_KEY="your_secret_key"
export TENCENTCLOUD_REGION="ap-shanghai"
```

Or create a local `asr_credentials.json` next to the script:

```json
{
  "secret_id": "your_secret_id",
  "secret_key": "your_secret_key",
  "token": ""
}
```

## Run with a local file

```bash
python3 asr_test.py --file /path/to/audio.wav
```

You can also point to a different file:

```bash
python3 asr_test.py --credentials /path/to/asr_credentials.json --file /path/to/audio.wav
```

If you want speaker separation:

```bash
python3 asr_test.py --file /path/to/audio.wav --speaker-diarization 1
```

Or use the dedicated speaker entry, which enables speaker separation by default
and prints a timeline plus a per-speaker summary:

```bash
python3 asr_speakers.py --file /path/to/audio.wav
python3 asr_speakers.py --file /path/to/audio.wav --speaker-label 0=zhangsan --speaker-label 1=lisi
```

Tencent Cloud also supports paid role separation for known speakers. This mode
requires `16k_zh_en`, a public role-reference audio URL, and currently supports
one role reference:

```bash
python3 asr_speakers.py --url "https://example.com/meeting.wav" --engine-model 16k_zh_en --speaker-diarization 3 --speaker-role zhangsan=https://example.com/zhangsan_ref.wav
```

## Current voiceprint speaker verification

Use `xfyun_voiceprint_tool.py` for the current voiceprint path. It calls the
iFLYTEK `s1aa729d0` voiceprint API and reads credentials from
`xfyun_credentials.json`, `private/xfyun_credentials.json`, or the
`XFYUN_APP_ID`, `XFYUN_API_KEY`, and `XFYUN_API_SECRET` environment variables.

```bash
python3 xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json create-group --group-id voice_test --group-name voice_test
python3 xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json enroll --group-id voice_test --feature-id kkk --file audio/kkk.m4a --keep-converted
python3 xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json verify --group-id voice_test --feature-id kkk --file audio/kkkk.m4a --threshold 0.75
python3 xfyun_voiceprint_tool.py --credentials private/xfyun_credentials.json list --group-id voice_test
```

`Score` is the voiceprint similarity score. The default pass threshold is `0.6`;
raise it with `--threshold` if you need stricter verification.

If the API returns `does not have authorization for func: createGroup`, the
current iFLYTEK app is not authorized for the `s1aa729d0` voiceprint feature
group API. Enable that service/capability in the iFLYTEK console before running
enroll/verify.

## Legacy Tencent Cloud voiceprint

`voiceprint_tool.py` calls Tencent Cloud `VoicePrintEnroll` and
`VoicePrintVerify`. Keep it for fallback testing when Tencent Cloud voiceprint
quota is available.

```bash
python3 voiceprint_tool.py enroll --file zhangsan.wav --speaker-nick zhangsan
python3 voiceprint_tool.py verify --voice-print-id vp_xxx --file test.wav
```

## Run with a URL

```bash
python3 asr_test.py --url "https://example.com/audio.wav"
```

## Notes

- Local files must be 5 MB or smaller.
- `16k_zh` with `--channel-num 1` is a safe default for normal speech.
- If your ASR service is in another region, pass `--region ap-guangzhou` or the
  region you enabled in the console.
