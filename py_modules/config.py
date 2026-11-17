# config.py - freedeckCY 配置与日志

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


class _PrivateRotatingFileHandler(RotatingFileHandler):
    """轮转日志始终用 0600 创建，避免新日志文件按 umask 变成 0644。"""

    def _open(self):
        fd = os.open(self.baseFilename, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        return os.fdopen(fd, self.mode, encoding=self.encoding)


def setup_logger() -> logging.Logger:
    """初始化日志器（带轮转，避免 /tmp/freedeckcy.log 无限增长）。"""
    logger = logging.getLogger("freedeckcy")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s | %(filename)s:%(lineno)s:%(funcName)s] %(levelname)s: %(message)s"
    )
    handler: logging.Handler
    try:
        handler = _PrivateRotatingFileHandler(
            "/tmp/freedeckcy.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
    except Exception:
        # 只读环境等场景退化到 stderr，至少不丢日志。
        handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # 日志可能含分享令牌/会话片段，固定 0600，避免同机其他用户读取。
    try:
        os.chmod("/tmp/freedeckcy.log", 0o600)
    except Exception:
        pass
    # 不向 root logger 传播，避免和 Decky 自己的日志配置互相覆盖。
    logger.propagate = False
    return logger


logger = setup_logger()
logger.setLevel(logging.INFO)

# 路径配置
HOME_DIR = str(Path.home())
DOWNLOADS_DIR = str(Path.home() / "Downloads")
SHARE_DIR = str(Path.home() / ".local" / "share")
DECKY_SEND_DIR = os.path.join(SHARE_DIR, "freedeckCY")

# 服务配置
# 仅监听回环地址，禁止局域网访问。
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 59271
PORT_CHECK_RETRIES = 5
PORT_CHECK_RETRY_DELAY = 0.3
PORT_RELEASE_TIMEOUT = 5.0

# 后台维护间隔（秒）：下载进度同步与安装补做，不依赖前端轮询。
MAINTENANCE_INTERVAL_SECONDS = 8.0

# 设置键
SETTINGS_KEY = "freedeckcy_settings"
SETTING_RUNNING = "running"
SETTING_PORT = "port"
SETTING_DOWNLOAD_DIR = "download_dir"
