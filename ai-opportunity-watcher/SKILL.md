---
name: ai-opportunity-watcher
description: Use when the user wants to scaffold, replicate, update, or operate the multi-source AI opportunity watcher that monitors linux.do, NodeSeek, and V2EX, sends email notifications, supports reply commands like `1`, `2+`, `3-`, and `4 note: ...`, and keeps a structured `saved_articles` knowledge base.
---

# AI Opportunity Watcher

## Overview

This skill packages the watcher as a reusable installer. For a new workspace, prefer the bootstrap script so the watcher can be copied in one command and then wired to Codex automations.

## Default Action

When the user wants a fresh install or an easy replication flow, run:

`python C:\Users\Y9000P\.codex\skills\ai-opportunity-watcher\scripts\bootstrap_watcher.py --target "<workspace>"`

That command:

- scaffolds the template files
- creates `config.json` from `config.example.json` when missing
- runs `doctor.ps1` unless the caller disables it

After scaffolding, the default automation flow is:

- create one Codex automation that runs `python .\linux_do_watcher.py --config .\config.json` every 3 hours
- create one Codex automation that runs `python .\linux_do_watcher.py --config .\config.json --process-replies-only` every 1 hour

If the user explicitly wants OS-level scheduling instead, `install_tasks.ps1` remains available as a Windows fallback.

## Workflow

1. For a new install, use the bootstrap script.
   - `python C:\Users\Y9000P\.codex\skills\ai-opportunity-watcher\scripts\bootstrap_watcher.py --target "<workspace>"`
   - add `--install-tasks` only when the user explicitly wants the legacy Windows fallback
   - add `--force` only when refreshing non-secret template files is intentional
2. Fill `config.json` in the target workspace.
   - Add SMTP and IMAP credentials.
   - Set the recipient email.
   - Adjust sources, filters, and reply-processing settings if needed.
3. Create the Codex automations unless the user explicitly asked for another scheduler.
   - watcher: every 3 hours
   - reply processor: every 1 hour
   - mention that Codex automations currently do not support every-10-minute schedules, so hourly reply handling is the aligned default
4. Validate from the target workspace when the user wants a manual sanity check.
   - `python .\linux_do_watcher.py --config .\config.json --dry-run`
   - `python .\linux_do_watcher.py --config .\config.json --process-replies-only`
5. For partial refreshes or template updates, use `scripts\scaffold_watcher.py` directly instead of bootstrap so secrets and runtime files stay untouched.
6. Use `doctor.ps1` in the target workspace when replication or environment debugging is needed.

## What This Skill Scaffolds

The template project includes:

- `linux_do_watcher.py`
- `config.example.json`
- `run_linux_do_watcher.ps1`
- `run_linux_do_reply_processor.ps1`
- `install_tasks.ps1`
- `doctor.ps1`
- `README.md`
- `.gitignore`

The scaffolded watcher supports:

- `linux.do`, `NodeSeek`, and `V2EX`
- email push
- reply commands: `1 3 5`, `2+`, `3-`, `4 note: ...`
- structured article saving and indexes in `saved_articles/`

## Update Existing Installs

- Do not overwrite `config.json`, state files, logs, `saved_articles/`, or `sent_batches/` unless the user explicitly asks.
- Prefer patching the existing workspace when the user only wants source, filter, or reply-command changes.
- Use `--force` with the scaffold script or bootstrap script only when refreshing non-secret template files is intentional.

## Resources

- `scripts\bootstrap_watcher.py`: the fastest install path for a new workspace.
- `scripts\scaffold_watcher.py`: copies the reusable watcher package into a workspace without extra setup steps.
- Read `references\replication.md` when the user wants setup, sharing, Codex automation, fallback scheduler, or secret-handling guidance.
- `assets\project-template\`: reusable watcher template files.
