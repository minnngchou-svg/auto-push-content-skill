# Auto Push Content Skill

This repository publishes the `ai-opportunity-watcher` Codex skill.

The skill bootstraps a multi-source AI opportunity watcher that:

- monitors `linux.do`, `NodeSeek`, and `V2EX`
- sends email digests
- supports reply commands like `1`, `2+`, `3-`, and `4 note: ...`
- saves structured articles into `saved_articles/`

## Install

On Windows, run:

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" --repo minnngchou-svg/auto-push-content-skill --path ai-opportunity-watcher
```

Then restart Codex.

## Use

After restarting Codex, say:

```text
Use $ai-opportunity-watcher to install the watcher in the current workspace and create the scheduled tasks.
```

The installed skill will scaffold the watcher project, create `config.json` from the template when needed, and can set up the Windows scheduled tasks.

## Repository Layout

- `ai-opportunity-watcher/`: the published Codex skill

## Local Development Note

This repo is used to publish the skill. Runtime watcher state, logs, and personal configs are intentionally ignored and stay local.
