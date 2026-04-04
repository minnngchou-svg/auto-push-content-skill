# Replication Notes

## Default Replication Path

For a fresh workspace, the recommended path is:

`python C:\Users\Y9000P\.codex\skills\ai-opportunity-watcher\scripts\bootstrap_watcher.py --target "<workspace>"`

That command will:

- copy the watcher template into the target workspace
- create `config.json` from `config.example.json` when it does not already exist
- run `doctor.ps1` unless `--skip-doctor` is passed

After bootstrap, the recommended scheduler is Codex automations:

- one automation runs `powershell -ExecutionPolicy Bypass -File .\run_linux_do_watcher.ps1` at `09:00`, `12:00`, `15:00`, `18:00`, and `21:00`
- one automation runs `powershell -ExecutionPolicy Bypass -File .\run_linux_do_reply_processor.ps1` every hour from `09:00` through `23:00`

Why hourly replies instead of every 10 minutes:

- Codex automations currently support hourly intervals, not 10-minute intervals
- to keep the project on one scheduler system, hourly reply handling is the aligned default

## Optional Windows Fallback

If a user explicitly wants OS-level scheduling instead of Codex automations, the template still ships with:

- `install_tasks.ps1`

That fallback script creates:

- `LinuxDoWatcher3H`: from `09:00` to `23:00`, every 180 minutes
- `LinuxDoReplyProcessor1H`: from `09:00` to `23:00`, every 60 minutes

The Windows fallback also keeps:

- hidden PowerShell windows
- AC-only behavior by default

## Scaffolded Files

The template currently ships with:

- `linux_do_watcher.py`
- `config.example.json`
- `run_linux_do_watcher.ps1`
- `run_linux_do_reply_processor.ps1`
- `install_tasks.ps1`
- `doctor.ps1`
- `README.md`
- `.gitignore`

## Runtime Files To Keep Private

Do not copy these between users unless you explicitly want to share runtime state:

- `config.json`
- `state.json`
- `watcher_runs.jsonl`
- `reply_state.json`
- `last_sent_batch.json`
- `saved_articles/`
- `sent_batches/`
- `feedback_profiles.json`

## Secret Handling

Before sharing the project, replace or reset any real SMTP or IMAP secrets and keep only placeholder values in `config.example.json`.

## Proxy Safety

The bundled launcher scripts clear common proxy environment variables before starting Python. This protects new installs from dead local proxy settings that would otherwise break HTTP requests.

## Supported Reply Commands

The scaffolded watcher already supports:

- `1 3 5` to save selected entries
- `2+` to prefer similar entries
- `3-` to reduce similar entries
- `4 note: this looks legit` to attach a note to an entry

## When To Patch Instead Of Re-Scaffold

If a user already has a running watcher, prefer patching the existing workspace when they only need source, filter, ranking, or reply-command changes. Re-scaffold only when they want a clean copy or an intentional template refresh.
