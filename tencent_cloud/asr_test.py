#!/usr/bin/env python3
"""腾讯云 ASR 命令行入口。"""

from __future__ import annotations

from asr_tool.app import main  # 导入真正的主流程函数


if __name__ == "__main__":
    raise SystemExit(main())  # 执行 main()，并把返回值作为程序退出码
