import os
import re

TARGET_DIRS = ["src/win_llm_chat_pyside", "tests"]

REPLACEMENTS = [
    (r"from win_llm_chat_pyside\.profile_repository", "from win_llm_chat_pyside.core.profile_repository"),
    (r"from \.profile_repository", "from win_llm_chat_pyside.core.profile_repository"),
]

def main():
    for d in TARGET_DIRS:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    apply_replacements(path, REPLACEMENTS)

def apply_replacements(path, replacements):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        new_content = content
        for pattern, repl in replacements:
            new_content = re.sub(pattern, repl, new_content)
        
        if new_content != content:
            print(f"Updated: {path}")
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
    except Exception as e:
        print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    main()

