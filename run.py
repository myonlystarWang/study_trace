#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智学迹 StudyTrace — 一键启动主脚本
支持生产模式（默认单端口 28000 托管）与开发模式（--dev 热更新）
"""

import os
import sys
import logging
import logging.config
import subprocess
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

# 显式将 Node 22 与 uv 路径置顶到进程 PATH 最前端，彻底超越系统 Machine PATH 中的 Node 14
_node_22_dir = Path(os.environ.get("APPDATA", "")) / "fnm/node-versions/v22.23.2/installation"
_uv_dir = Path(os.environ.get("USERPROFILE", "")) / ".local/bin"
_prepend_paths = [str(p) for p in [_node_22_dir, _uv_dir] if p.exists()]
if _prepend_paths:
    os.environ["PATH"] = os.pathsep.join(_prepend_paths + [os.environ.get("PATH", "")])


# ---------------------------------------------------------------------------
# 统一日志：带时间戳 + 级别。INFO 及以上走 stdout（被 NSSM 写进 AppStdout），
# ERROR 走 stderr（被 NSSM 写进 AppStderr），方便直接从日志定位问题。
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": LOG_FORMAT, "datefmt": LOG_DATEFMT},
    },
    "handlers": {
        "out": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default",
        },
        "err": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "default",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["out"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["err"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["out"], "level": "INFO", "propagate": False},
        "StudyTrace": {"handlers": ["out"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["out"], "level": "INFO"},
}

_log = logging.getLogger("StudyTrace")


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)


def check_python_version():
    """Python 版本守卫：必须为 3.11.x"""
    major, minor = sys.version_info[:2]
    if major != 3 or minor != 11:
        _log.error("当前 Python 版本为 %s.%s，系统要求必须为 Python 3.11。", major, minor)
        _log.error("请使用 .venv 虚拟环境（venv 内的 python.exe）启动。")
        sys.exit(1)


def check_node_version():
    """Node 版本守卫：必须 >= 20"""
    try:
        res = subprocess.run(["node", "-v"], capture_output=True, text=True, check=True)
        version_str = res.stdout.strip().lstrip("v")
        major = int(version_str.split(".")[0])
        if major < 20:
            _log.error("当前 Node 版本为 v%s，系统要求 Node >= 20 LTS。", version_str)
            _log.error("请使用 fnm 激活 Node 22（如执行 'fnm use 22'）。")
            sys.exit(1)
        return major
    except (subprocess.CalledProcessError, FileNotFoundError):
        _log.error("未找到 Node.js 命令。")
        _log.error("请安装 Node 22 LTS 或通过 fnm 安装。")
        sys.exit(1)


def get_lan_ips():
    """获取本机在家庭局域网中的候选 IP 地址"""
    import socket
    ips = []
    try:
        candidates = socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in candidates:
            if ip.startswith("127.") or ip.startswith("198.18."):
                continue
            ips.append(ip)
    except Exception:
        pass
    # 优先将真实的局域网非 .1 网段排在最前面
    ips.sort(key=lambda x: (x.endswith(".1"), x))
    return ips


def ensure_database_migrated():
    """确保数据库迁移已升级至最新 head 版本（杜绝依赖手动执行或未迁移崩溃）"""
    _log.info("检查并自动执行数据库迁移 (Alembic upgrade head)...")
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config(str(BASE_DIR / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


def run_prod():
    """生产模式：单端口一体化托管（28000 端口）"""
    from backend.app.config import settings
    _log.info("正在启动生产服务（单端口 %s 模式）...", settings.PORT)
    ensure_database_migrated()
    if not FRONTEND_DIST.exists():
        _log.info("检测到前端构建产物不存在，正在自动执行前端构建...")
        check_node_version()
        if not (FRONTEND_DIR / "node_modules").exists():
            _log.info("检测到前端依赖未安装，正在自动执行 npm install...")
            subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), check=True, shell=True)
        subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIR), check=True, shell=True)

    import uvicorn
    _log.info("服务已就绪！")
    _log.info("  本地电脑访问: http://127.0.0.1:%s", settings.PORT)
    lan_ips = get_lan_ips()
    for ip in lan_ips:
        _log.info("  家庭内网访问: http://%s:%s", ip, settings.PORT)
    _log.info("  退出请按 Ctrl + C")
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=False,
        log_config=LOGGING_CONFIG,
    )


def run_dev():
    """开发模式：Vite 5173 前端热更新 + FastAPI 28001 后端 reload"""
    from backend.app.config import settings
    check_node_version()
    ensure_database_migrated()
    if not (FRONTEND_DIR / "node_modules").exists():
        _log.info("检测到前端依赖未安装，正在自动执行 npm install...")
        subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), check=True, shell=True)
    _log.info("正在启动开发调试模式...")
    _log.info("  前端 Vite HMR 运行在: http://127.0.0.1:5173")
    _log.info("  后端 API 运行在: http://127.0.0.1:%s (支持 --reload)", settings.DEV_PORT)

    import subprocess as _sp
    import signal

    dev_env = os.environ.copy()
    dev_env["VITE_BACKEND_PORT"] = str(settings.DEV_PORT)
    vite_proc = _sp.Popen(["npm", "run", "dev"], cwd=str(FRONTEND_DIR), shell=True, env=dev_env)

    try:
        import uvicorn
        uvicorn.run(
            "backend.app.main:app",
            host="0.0.0.0",
            port=settings.DEV_PORT,
            reload=True,
            log_config=LOGGING_CONFIG,
        )
    finally:
        _log.info("正在停止开发服务器...")
        vite_proc.terminate()


def main():
    setup_logging()
    try:
        check_python_version()
        parser = argparse.ArgumentParser(description="智学迹 StudyTrace 启动程序")
        parser.add_argument("--dev", action="store_true", help="以开发模式启动（支持前端 HMR 热更新）")
        args = parser.parse_args()

        if args.dev:
            run_dev()
        else:
            run_prod()
    except SystemExit:
        # 版本/环境守卫主动退出，原样上抛退出码
        raise
    except Exception:
        _log.error("服务启动失败（未捕获异常），详见下方堆栈：", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
