from pathlib import Path
import tempfile

from win_llm_chat_pyside.core.config import Config
from win_llm_chat_pyside.core.app_logger import AppLogger


def test_app_logger_filters_sensitive_keys():
    cfg = Config()
    with tempfile.TemporaryDirectory() as td:
        logs_dir = Path(td)
        cfg.logging_dir = str(logs_dir)
        logger = AppLogger()
        try:
            logger.configure(cfg)

            logger.info(
                "test.event",
                {
                    "prompt": "これはログに残ってほしくない",
                    "api_key": "super-secret",
                    "other": "ok",
                },
            )

            log_file = logs_dir / "app.log"
            data = log_file.read_text(encoding="utf-8")
            assert "test.event" in data
            # センシティブな値はフィルタされていること
            assert "super-secret" not in data
            assert "これはログに残ってほしくない" not in data
            assert "[filtered]" in data
        finally:
            logger.close()


def test_app_logger_respects_enabled_flag():
    cfg = Config(logging_enabled=False)
    with tempfile.TemporaryDirectory() as td:
        logs_dir = Path(td)
        cfg.logging_dir = str(logs_dir)
        logger = AppLogger()
        try:
            logger.configure(cfg)

            logger.info("test.event", {"foo": "bar"})

            # 無効時はログファイルが生成されない想定
            assert not (logs_dir / "app.log").exists()
        finally:
            logger.close()


