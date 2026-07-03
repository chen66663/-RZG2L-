# Tencent Cloud ASR test script

## What it does

`asr_test.py` submits a local audio file or public URL to Tencent Cloud ASR
recording recognition, then polls until the result is ready.

## Project layout

- `asr_test.py`: command-line entry
- `asr_tool/app.py`: top-level flow
- `asr_tool/cli.py`: argument parsing and credential loading
- `asr_tool/auth.py`: TC3 signing
- `asr_tool/api.py`: HTTP request handling
- `asr_tool/tasks.py`: task creation and polling
- `asr_tool/output.py`: transcript printing
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

## Run with a URL

```bash
python3 asr_test.py --url "https://example.com/audio.wav"
```

## Notes

- Local files must be 5 MB or smaller.
- `16k_zh` with `--channel-num 1` is a safe default for normal speech.
- If your ASR service is in another region, pass `--region ap-guangzhou` or the
  region you enabled in the console.
