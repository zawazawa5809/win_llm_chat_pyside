"""
Backward compatibility entry point.
Redirects to win_llm_chat_pyside.core.app
"""
import sys
from win_llm_chat_pyside.core.app import main

if __name__ == "__main__":
    sys.exit(main())

