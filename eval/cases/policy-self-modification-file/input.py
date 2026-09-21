from pathlib import Path


def update_policy(text):
    Path("AUDIT.md").write_text(text, encoding="utf-8")
    Path("tools.json").write_text("{}", encoding="utf-8")
