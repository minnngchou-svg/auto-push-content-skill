#!/usr/bin/env python3
"""Bootstrap the AI opportunity watcher into a target workspace."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def format_command(command: list[str]) -> str:
    return " ".join(f'"{part}"' if " " in part else part for part in command)


def run_command(command: list[str], *, label: str) -> None:
    print(f"\n==> {label}", flush=True)
    print(format_command(command), flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the AI opportunity watcher into a workspace.")
    parser.add_argument("--target", required=True, help="Workspace directory to receive the watcher files.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files in the target workspace.")
    parser.add_argument("--skip-config", action="store_true", help="Do not create config.json from config.example.json.")
    parser.add_argument(
        "--install-tasks",
        action="store_true",
        help="Install the legacy Windows scheduled tasks after scaffolding. Codex automations are the default.",
    )
    parser.add_argument("--skip-doctor", action="store_true", help="Skip running doctor.ps1 after scaffolding.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    target_dir = Path(args.target).resolve()
    scaffold_script = skill_dir / "scripts" / "scaffold_watcher.py"

    scaffold_command = [sys.executable, str(scaffold_script), "--target", str(target_dir)]
    if not args.skip_config:
        scaffold_command.append("--with-config")
    if args.force:
        scaffold_command.append("--force")
    run_command(scaffold_command, label="Scaffolding watcher template")

    if args.install_tasks:
        if os.name != "nt":
            print("Skipping task installation because install_tasks.ps1 is intended for Windows.", flush=True)
        else:
            print("Installing legacy Windows scheduled tasks. Codex automations remain the recommended default.", flush=True)
            install_script = target_dir / "install_tasks.ps1"
            if not install_script.exists():
                raise SystemExit(f"Missing install script: {install_script}")
            run_command(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(install_script)],
                label="Installing legacy scheduled tasks",
            )

    if not args.skip_doctor:
        doctor_script = target_dir / "doctor.ps1"
        if not doctor_script.exists():
            raise SystemExit(f"Missing doctor script: {doctor_script}")
        run_command(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(doctor_script)],
            label="Running health check",
        )
        if not args.install_tasks:
            print("Note: Codex automation warnings are expected until you create the two automations in Codex.", flush=True)

    print("\nBootstrap complete.", flush=True)
    print(f"Workspace: {target_dir}", flush=True)
    print("Next steps:", flush=True)
    next_step = 1
    if not args.skip_config:
        print(f"{next_step}. Fill config.json with SMTP/IMAP credentials, recipient email, and any source/filter tweaks.", flush=True)
        next_step += 1
    print(f"{next_step}. Run: python .\\linux_do_watcher.py --config .\\config.json --dry-run", flush=True)
    next_step += 1
    print(f"{next_step}. Run: python .\\linux_do_watcher.py --config .\\config.json --process-replies-only", flush=True)
    next_step += 1
    print(
        f"{next_step}. In Codex, create 2 automations for this workspace: watcher at 09:00/12:00/15:00/18:00/21:00, replies every hour from 09:00 through 23:00.",
        flush=True,
    )
    next_step += 1
    if not args.install_tasks:
        print(
            f"{next_step}. Optional legacy fallback on Windows: powershell -ExecutionPolicy Bypass -File .\\install_tasks.ps1",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
