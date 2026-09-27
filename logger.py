"""
📝 Logger with emojis.

- Terminal: colorful lines with emojis
- File:     logs/YYYY-MM-DD.log  -> one file per day, a new one starts at midnight

Usage in any file:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("📄 Resume uploaded: ali_cv.pdf")

Test it:
    python logger.py
"""

import logging
import sys
from datetime import date
from pathlib import Path

import config

LEVEL_EMOJI = {
    logging.DEBUG: "🔍",
    logging.INFO: "✅",
    logging.WARNING: "⚠️ ",
    logging.ERROR: "❌",
    logging.CRITICAL: "🔥",
}

LEVEL_COLOR = {
    logging.DEBUG: "\033[90m",     # gray
    logging.INFO: "\033[36m",      # cyan
    logging.WARNING: "\033[33m",   # yellow
    logging.ERROR: "\033[31m",     # red
    logging.CRITICAL: "\033[41m",  # red background
}
RESET = "\033[0m"

LINE_FORMAT = "%(asctime)s | {emoji} %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class EmojiFormatter(logging.Formatter):
    """Adds the level emoji, plus color when printing to the terminal."""

    def __init__(self, use_color: bool):
        super().__init__(datefmt=DATE_FORMAT)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        emoji = LEVEL_EMOJI.get(record.levelno, "•")
        self._style._fmt = LINE_FORMAT.format(emoji=emoji)
        line = super().format(record)
        if self.use_color:
            return f"{LEVEL_COLOR.get(record.levelno, '')}{line}{RESET}"
        return line


class DailyFileHandler(logging.FileHandler):
    """Writes to logs/<today>.log and switches to a new file when the date changes."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_day = date.today()
        super().__init__(self._path_for(self.current_day), encoding="utf-8", delay=True)

    def _path_for(self, day: date) -> str:
        return str(self.log_dir / f"{day.isoformat()}.log")

    def emit(self, record: logging.LogRecord) -> None:
        today = date.today()
        if today != self.current_day:
            self.acquire()
            try:
                self.close()
                self.current_day = today
                self.baseFilename = self._path_for(today)
            finally:
                self.release()
        super().emit(record)


def _console_stream():
    # Windows terminals break on emojis unless output is UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return sys.stdout


_ROOT_NAME = "resume_evaluator"


def _setup_root() -> logging.Logger:
    root = logging.getLogger(_ROOT_NAME)
    if root.handlers:  # Streamlit re-runs the script often - don't add handlers twice
        return root

    root.setLevel(config.LOG_LEVEL.upper())
    root.propagate = False

    console = logging.StreamHandler(_console_stream())
    console.setFormatter(EmojiFormatter(use_color=True))
    root.addHandler(console)

    try:
        file_handler = DailyFileHandler(config.LOGS_DIR)
        file_handler.setFormatter(EmojiFormatter(use_color=False))
        root.addHandler(file_handler)
    except OSError as e:
        # Some hosts have read-only disks - keep going with terminal logs only
        root.warning(f"Could not create logs folder, file logging is off: {e}")

    return root


def get_logger(name: str) -> logging.Logger:
    _setup_root()
    return logging.getLogger(f"{_ROOT_NAME}.{name}")


if __name__ == "__main__":
    log = get_logger("test")
    log.debug("🔍 Debug message (only shows when LOG_LEVEL=DEBUG)")
    log.info("🚀 Logger is working")
    log.info(f"🤖 Model: {config.CLAUDE_MODEL}")
    if config.CLAUDE_API_KEY:
        log.info("🔑 API key loaded from .env")
    else:
        log.error("🔑 API key NOT found. Check that .env has a line like: claude=sk-ant-...")
    log.warning("⚠️ This is how a warning looks")
    log.error("❌ This is how an error looks")
    log.info(f"📁 Log file: {config.LOGS_DIR / (date.today().isoformat() + '.log')}")
