"""
エントリポイント。QApplication を起動し、未処理例外をトップレベルでハンドリングする。
"""

import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox

from .ui_main import MainWindow


def exception_hook(exc_type, exc_value, exc_traceback):
    """未処理例外をキャッチしてユーザーに通知する。"""
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"Unhandled exception:\n{error_msg}", file=sys.stderr)
    
    QMessageBox.critical(
        None,
        "予期しないエラー",
        f"アプリケーションで予期しないエラーが発生しました:\n\n{exc_value}\n\n"
        "詳細はコンソールログを確認してください。"
    )


def main():
    """アプリケーションのメインエントリポイント。"""
    sys.excepthook = exception_hook
    
    app = QApplication(sys.argv)
    app.setApplicationName("LLM Chat Client")
    app.setOrganizationName("win-llm-chat-pyside")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


