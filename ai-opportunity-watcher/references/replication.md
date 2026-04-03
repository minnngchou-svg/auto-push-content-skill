# Replication Notes

## Fastest Install Path

For a fresh workspace on Windows, the fastest path is:

`python C:\Users\Y9000P\.codex\skills\ai-opportunity-watcher\scripts\bootstrap_watcher.py --target "<workspace>" --install-tasks`

That single command will:

- copy the watcher template into the target workspace
- create `config.json` from `config.example.json` when it does not already exist
- install the `LinuxDoWatcher3H` and `LinuxDoReplyProcessor10M` scheduled tasks when `--install-tasks` is included
- run `doctor.ps1` unless `--skip-doctor` is passed
- configure the scheduled tasks so they do not start or continue on battery power

Use `scripts\scaffold_watcher.py` only when you want the files without the extra bootstrap steps.

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

Before sharing the project, replace or reset any real SMTP/IMAP secrets and keep only placeholder values in `config.example.json`.

## Scheduler Defaults

The bundled Windows tasks expect:

- `LinuxDoWatcher3H`: every 3 hours from 14:10
- `LinuxDoReplyProcessor10M`: every 10 minutes from 00:00
- the task installer also keeps the default AC-only battery policy for both tasks

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
