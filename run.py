#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学迹 StudyTrace — 一键启动主脚本
支持生产模式（默认单端口 8000 托管）与开发模式（--dev 热更新）
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"


def check_python_version():
    """Python 版本守卫：必须为 3.11.x"""
    major, minor = sys.version_info[:2]
    if major != 3 or minor != 11:
        print(f"❌ [版本守卫错误] 当前 Python 版本为 {major}.{minor}，系统要求必须为 Python 3.11。")
        print("💡 请使用 'uv run python run.py' 启动，或激活 .venv 虚拟环境。")
        sys.exit(1)


def check_node_version():
    """Node 版本守卫：必须 >= 20"""
    try:
        res = subprocess.run(["node", "-v"], capture_output=True, text=True, check=True)
        version_str = res.stdout.strip().lstrip("v")
        major = int(version_str.split(".")[0])
        if major < 20:
            print(f"❌ [版本守卫错误] 当前 Node 版本为 v{version_str}，系统要求 Node >= 20 LTS。")
            print("💡 请使用 fnm 激活 Node 22（如执行 'fnm use 22'）。")
            sys.exit(1)
        return major
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ [版本守卫错误] 未找到 Node.js 命令。")
        print("💡 请安装 Node 22 LTS 或通过 fnm 安装。")
        sys.exit(1)


def run_prod():
    """生产模式：单端口一体化托管（8000 端口）"""
    print("🚀 正在启动「学迹 StudyTrace」生产服务（单端口 8000 模式）...")
    if not FRONTEND_DIST.exists():
        print("📦 检测到前端构建产物不存在，正在自动执行一次 npm run build...")
        check_node_version()
        subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIR), check=True, shell=True)

    import uvicorn
    print("✨ 服务已就绪！")
    print("🌐 本地访问地址: http://127.0.0.1:8000")
    print("📱 家庭内网手机访问: http://<你的电脑内网IP>:8000")
    print("🔒 退出请按 Ctrl + C")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=False)


def run_dev():
    """开发模式：Vite 5173 前端热更新 + FastAPI 8000 后端 reload"""
    check_node_version()
    print("🛠️ 正在启动「学迹 StudyTrace」开发调试模式...")
    print("🌐 前端 Vite HMR 运行在: http://127.0.0.1:5173")
    print("🔌 后端 API 运行在: http://127.0.0.1:8000 (支持 --reload)")

    import subprocess
    import signal

    vite_proc = subprocess.Popen(["npm", "run", "dev"], cwd=str(FRONTEND_DIR), shell=True)

    try:
        import uvicorn
        uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
    finally:
        print("\n🛑 正在停止开发服务器...")
        vite_proc.terminate()


def main():
    check_python_version()
    parser = argparse.ArgumentParser(description="学迹 StudyTrace 启动程序")
    parser.add_argument("--dev", action="store_true", help="以开发模式启动（支持前端 HMR 热更新）")
    args = parser.parse_args()

    if args.dev:
        run_dev()
    else:
        run_prod()


if __name__ == "__main__":
    main()
