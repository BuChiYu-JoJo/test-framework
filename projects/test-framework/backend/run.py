#!/usr/bin/env python3
"""
Backend 启动脚本

用法：
    python run.py                    # 开发模式（默认 0.0.0.0:8000）
    python run.py --host 0.0.0.0 --port 8000
"""

import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test Framework Backend")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开启热重载")
    args = parser.parse_args()

    print(f"Starting Test Framework API on {args.host}:{args.port}")
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload or True,  # 开发模式默认开启 reload
    )


if __name__ == "__main__":
    main()
