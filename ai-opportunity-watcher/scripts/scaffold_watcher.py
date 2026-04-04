#!/usr/bin/env python3
"""Copy the AI opportunity watcher template into a target workspace."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

TEMPLATE_FILES = [
    ".gitignore",
    "README.md",
    "config.example.json",
    "linux_do_watcher.py",
    "run_linux_do_watcher.ps1",
    "run_linux_do_reply_processor.ps1",
    "install_tasks.ps1",
    "doctor.ps1",
]


def copy_file(source: Path, target: Path, *, force: bool) -> str:
    if target.exists() and not force:
        return "skipped"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return "copied"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold the AI opportunity watcher into a workspace.")
    parser.add_argument("--target", required=True, help="Workspace directory to receive the template files.")
    parser.add_argument("--with-config", action="store_true", help="Also create config.json from config.example.json when missing.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files in the target workspace.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    template_dir = skill_dir / "assets" / "project-template"
    target_dir = Path(args.target).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[str] = []

    for relative_name in TEMPLATE_FILES:
        source = template_dir / relative_name
        target = target_dir / relative_name
        result = copy_file(source, target, force=args.force)
        if result == "copied":
            copied.append(relative_name)
        else:
            skipped.append(relative_name)

    if args.with_config:
        source = target_dir / "config.example.json"
        target = target_dir / "config.json"
        if source.exists():
            result = copy_file(source, target, force=args.force)
            if result == "copied":
                copied.append("config.json")
            else:
                skipped.append("config.json")

    print(f"Scaffolded watcher into: {target_dir}")
    print(f"Copied: {copied}")
    print(f"Skipped: {skipped}")
    print("Next steps:")
    print("1. Fill config.json with SMTP/IMAP settings and recipient email.")
    print("2. Run: python .\\linux_do_watcher.py --config .\\config.json --dry-run")
    print("3. In Codex, create 2 automations for this workspace: watcher every 3 hours, replies every 1 hour.")
    print("4. Optional legacy fallback on Windows: powershell -ExecutionPolicy Bypass -File .\\install_tasks.ps1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
