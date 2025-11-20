"""
エントリポイント。QApplication を起動し、未処理例外をトップレベルでハンドリングする。
"""

import sys
import ctypes
import platform
import traceback
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from win_llm_chat_pyside.ui.main_window import MainWindow
from win_llm_chat_pyside.core.app_logger import app_logger


def setup_app_user_model_id():
    """Windows タスクバーで正しくアイコンを表示するための AppUserModelID を設定する。"""
    if platform.system() == "Windows":
        # 任意のユニークなID
        myappid = 'win_llm_chat_pyside.client.v1'
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass


def set_app_icon(app: QApplication):
    """アプリケーション全体のアイコンを設定する。"""
    # このファイルは src/win_llm_chat_pyside/core/app.py にある
    # プロジェクトルートの app.ico を参照する: core -> win_llm_chat_pyside -> src -> root
    icon_path = Path(__file__).resolve().parents[3] / "app.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))


def exception_hook(exc_type, exc_value, exc_traceback):
    """未処理例外をキャッチしてユーザーに通知する。"""
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"Unhandled exception:\n{error_msg}", file=sys.stderr)
    try:
        app_logger.error(
            "app.unhandled_exception",
            {
                "exc_type": getattr(exc_type, "__name__", str(exc_type)),
                "exc_value": str(exc_value),
            },
        )
    except Exception:
        # ログ出力でさらに例外を起こさないようにする
        pass
    
    QMessageBox.critical(
        None,
        "予期しないエラー",
        f"アプリケーションで予期しないエラーが発生しました:\n\n{exc_value}\n\n"
        "詳細はコンソールログを確認してください。"
    )


def main():
    """アプリケーションのメインエントリポイント。"""
    # Windows タスクバーのアイコン分離対策
    setup_app_user_model_id()

    sys.excepthook = exception_hook
    
    app = QApplication(sys.argv)
    app.setApplicationName("LLM Chat Client")
    app.setOrganizationName("win-llm-chat-pyside")

    # アプリアイコンの設定
    set_app_icon(app)

    window = MainWindow()
    if getattr(window, "should_show_on_launch", True):
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()


